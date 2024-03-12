import os
import re
import hashlib
import json
from copy import copy

from datetime import datetime

from orangebeard.OrangebeardClient import OrangebeardClient
from orangebeard.config import AutoConfig
from orangebeard.entity.Attachment import AttachmentFile, AttachmentMetaData, Attachment
from orangebeard.entity.Attribute import Attribute
from orangebeard.entity.FinishStep import FinishStep
from orangebeard.entity.FinishTest import FinishTest
from orangebeard.entity.FinishTestRun import FinishTestRun
from orangebeard.entity.Log import Log
from orangebeard.entity.LogFormat import LogFormat
from orangebeard.entity.LogLevel import LogLevel
from orangebeard.entity.StartStep import StartStep
from orangebeard.entity.StartSuite import StartSuite
from orangebeard.entity.StartTest import StartTest
from orangebeard.entity.StartTestRun import StartTestRun
from orangebeard.entity.TestStatus import TestStatus
from orangebeard.entity.TestType import TestType
from pytz import reference

from robot.libraries.BuiltIn import BuiltIn
from robot.api.interfaces import ListenerV2

tz = reference.LocalTimezone()


def get_variable(name, default_value=None):
    return BuiltIn().get_variable_value("${" + name + "}", default_value)


def get_status(status_str) -> TestStatus:
    if status_str == "FAIL":
        return TestStatus.FAILED
    if status_str == "PASS":
        return TestStatus.PASSED
    if status_str in ("NOT RUN", "SKIP"):
        return TestStatus.SKIPPED
    else:
        raise ValueError("Unknown status: {0}".format(status_str))


def get_level(level_str) -> LogLevel:
    if level_str == "INFO":
        return LogLevel.INFO
    if level_str == "WARN":
        return LogLevel.WARN
    if level_str in ("ERROR", "FATAL", "FAIL"):
        return LogLevel.ERROR
    if level_str in ("DEBUG", "TRACE"):
        return LogLevel.DEBUG
    else:
        raise ValueError("Unknown level: {0}".format(level_str))


def pad_suite_name(suite_name) -> str:
    if len(suite_name) < 3:
        return suite_name + "  "
    return suite_name


def truncate_description(description: str) -> str:
    return description[:1020] + "..." if description is not None and len(description) > 1024 else description


class listener(ListenerV2):
    def __init__(self):
        self.output_dir = None
        self.orangebeard_client = None
        self.test_run_uuid = None

        self.suites = {}
        self.tests = {}
        self.steps = []

    def start_suite(self, name, attributes):
        if attributes['id'] == 's1':
            self.start_test_run()

        suite_key = attributes.get("longname")
        suite_names = list(map(pad_suite_name, suite_key.split(".")))

        if not self.suites.get(suite_key):
            start_suite_obj = StartSuite(self.test_run_uuid, copy(suite_names),
                                         description=truncate_description(attributes.get('doc')))

            started_suites = self.orangebeard_client.start_suite(start_suite_obj)
            started_suites.reverse()

            for suite in started_suites:
                self.suites[".".join(suite_names)] = suite
                suite_names.pop()

    def start_test(self, name, attributes):
        suite_names_str = attributes.get("longname")[: -len(name) - 1]
        suite_names = list(map(pad_suite_name, suite_names_str.split(".")))
        suite_key = ".".join(suite_names)

        suite_uuid = self.suites.get(suite_key)

        template = attributes.get("template")
        tags = attributes.get("tags")

        orangebeard_attributes = []

        if len(template) > 0 or len(tags) > 0:
            if len(template) > 0:
                orangebeard_attributes.append(Attribute("template", template))
            if len(tags) > 0:
                for tag in tags:
                    orangebeard_attributes.append(Attribute(value=tag))

        test_uuid = self.orangebeard_client.start_test(
            StartTest(
                self.test_run_uuid,
                copy(suite_uuid),
                name,
                datetime.now(tz),
                TestType.TEST,
                description=truncate_description(attributes.get("doc")),
                attributes=orangebeard_attributes if len(orangebeard_attributes) > 0 else None
            )
        )
        self.tests[attributes.get("id")] = test_uuid

    def end_test(self, name, attributes):
        test_uuid = self.tests.get(attributes.get("id"))
        status = get_status(attributes.get("status"))
        message = attributes.get("message")
        if len(message) > 0:
            level = LogLevel.INFO if status == TestStatus.PASSED else LogLevel.ERROR
            self.orangebeard_client.log(
                Log(
                    self.test_run_uuid,
                    test_uuid,
                    message,
                    level,
                    LogFormat.PLAIN_TEXT,
                    None,
                    datetime.now(tz)
                )
            )

        self.orangebeard_client.finish_test(test_uuid, FinishTest(self.test_run_uuid, status, datetime.now(tz)))
        self.tests.pop(attributes.get("id"))

    def start_keyword(self, name, attributes):
        test_uuid = list(self.tests.values())[-1] if len(self.tests) else None
        parent_step_uuid = self.steps[-1] if len(self.steps) > 0 else None

        if test_uuid is None:
            # start suite keyword (setup) as a virtual test (BEFORE_TEST)
            keyword_hash = hashlib.md5(
                (
                        name
                        + json.dumps(attributes.get("args"), sort_keys=True)
                ).encode("utf-8")
            ).hexdigest()

            step_type_prefix = attributes.get("type")
            before_step_name = "{0}: {1}".format(step_type_prefix.capitalize(), attributes.get("kwname"))

            suite_uuid = list(self.suites.values())[-1]
            test_uuid = self.orangebeard_client.start_test(
                StartTest(
                    self.test_run_uuid,
                    suite_uuid,
                    before_step_name,
                    datetime.now(tz),
                    TestType.BEFORE,
                    description=truncate_description(attributes.get("doc")),
                    attributes=None
                )
            )

            self.tests[keyword_hash] = test_uuid

        else:
            step_name = (
                attributes.get("kwname")
                if len(attributes.get("kwname")) > 0
                else attributes.get("type")
            )
            step_type_prefix = attributes.get("type")
            step_args = attributes.get("args")
            description = None
            step_display_name = (
                "{0}: {1} ({2})".format(
                    step_type_prefix.capitalize(), step_name, ", ".join(step_args)
                )
                if len(step_args) > 0
                else "{0}: {1}".format(step_type_prefix.capitalize(), step_name)
            )
            if step_type_prefix.lower() == "keyword":
                step_display_name = step_display_name[9:]

            # omit args if too long
            if len(step_display_name) > 128:
                step_display_name = "{0}: {1}".format(
                    step_type_prefix.capitalize(), " ".join(step_name.split())
                )
                if len(step_display_name) > 128:
                    step_display_name = "{0}...".format(step_display_name[:125])

                description = ", ".join(step_args)

            step_uuid = self.orangebeard_client.start_step(
                StartStep(
                    self.test_run_uuid,
                    test_uuid,
                    step_display_name,
                    datetime.now(tz),
                    parent_step_uuid,
                    truncate_description(description)
                )
            )

            self.steps.append(step_uuid)

    def end_keyword(self, name, attributes):
        step_uuid = self.steps[-1] if len(self.steps) > 0 else None

        if step_uuid is None:
            # Was a suite setup step wrapped in test item
            keyword_hash = hashlib.md5(
                (
                        name
                        + json.dumps(attributes.get("args"), sort_keys=True)
                ).encode("utf-8")
            ).hexdigest()

            test_uuid = self.tests.get(keyword_hash)
            status = get_status(attributes.get("status"))

            self.orangebeard_client.finish_test(test_uuid, FinishTest(self.test_run_uuid, status, datetime.now(tz)))
            self.tests.pop(keyword_hash)

        else:
            status = get_status(attributes.get("status"))
            self.orangebeard_client.finish_step(step_uuid, FinishStep(self.test_run_uuid, status, datetime.now(tz)))
            self.steps.pop()

    def log_message(self, message):
        step_uuid = self.steps[-1] if len(self.steps) > 0 else None

        test_uuid = list(self.tests.values())[-1]

        level = get_level(message["level"])
        log_msg = message["message"]

        if message["html"] == "yes":
            images = re.findall('src="(.+?)"', log_msg)
            if len(images) > 0:
                log_uuid = self.orangebeard_client.log(
                    Log(
                        self.test_run_uuid,
                        test_uuid,
                        images[0],
                        level,
                        LogFormat.PLAIN_TEXT,
                        step_uuid,
                        datetime.now(tz),
                    )
                )

                attachment_file = AttachmentFile(
                    images[0],
                    open(
                        "{0}{1}{2}".format(self.output_dir, os.path.sep, images[0]), "rb"
                    ).read(),
                )
                attachment_meta_data = AttachmentMetaData(
                    self.test_run_uuid,
                    test_uuid,
                    log_uuid,
                    step_uuid,
                    datetime.now(tz),
                )

                self.orangebeard_client.send_attachment(Attachment(attachment_file, attachment_meta_data))

            else:
                self.orangebeard_client.log(
                    Log(
                        self.test_run_uuid,
                        test_uuid,
                        log_msg,
                        level,
                        LogFormat.PLAIN_TEXT,
                        step_uuid,
                        datetime.now(tz)
                    )
                )

        else:
            self.orangebeard_client.log(
                Log(
                    self.test_run_uuid,
                    test_uuid,
                    log_msg,
                    level,
                    LogFormat.PLAIN_TEXT,
                    step_uuid,
                    datetime.now(tz)
                )
            )

    def start_test_run(self):

        config = AutoConfig.config

        config.endpoint = get_variable("orangebeard_endpoint", config.endpoint)
        config.token = get_variable("orangebeard_accesstoken", config.token)
        config.project = get_variable("orangebeard_project", config.project)
        config.test_set = get_variable("orangebeard_testset", config.testset)
        config.description = get_variable("orangebeard_description", config.description)

        self.output_dir = get_variable("OUTPUT_DIR")
        self.orangebeard_client = OrangebeardClient(orangebeard_config=config)

        print(config.to_json())

        self.test_run_uuid = self.orangebeard_client.start_test_run(
            StartTestRun(config.test_set, datetime.now(tz), config.description))

    def close(self):
        self.orangebeard_client.finish_test_run(self.test_run_uuid, FinishTestRun(datetime.now(tz)))

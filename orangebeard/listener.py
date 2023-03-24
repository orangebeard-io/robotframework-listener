import asyncio
import os
import platform
import re

from orangebeard.async_client import AsyncOrangebeardClient
from orangebeard.entity.TestType import TestType
from orangebeard.entity.TestStatus import TestStatus
from orangebeard.entity.LogLevel import LogLevel
from orangebeard.entity.LogFormat import LogFormat
from orangebeard.entity.Attachment import AttachmentFile, AttachmentMetaData
from robot.libraries.BuiltIn import BuiltIn


def get_variable(name, defaultValue=None):
    return BuiltIn().get_variable_value("${" + name + "}", defaultValue)


def get_status(statusStr) -> TestStatus:
    if statusStr == "FAIL":
        return TestStatus.FAILED
    if statusStr == "PASS":
        return TestStatus.PASSED
    if statusStr in ("NOT RUN", "SKIP"):
        return TestStatus.SKIPPED
    else:
        raise Exception("Unknown status: {0}".format(statusStr))


def get_level(levelStr) -> LogLevel:
    if levelStr == "INFO":
        return LogLevel.INFO
    if levelStr == "WARN":
        return LogLevel.WARN
    if levelStr in ("ERROR", "FATAL", "FAIL"):
        return LogLevel.ERROR
    if levelStr in ("DEBUG", "TRACE"):
        return LogLevel.DEBUG
    else:
        raise Exception("Unknown level: {0}".format(levelStr))


class listener:
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self):
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        self.suites = {}
        self.tests = {}
        self.steps = []

    def start_suite(self, name, attributes):
        ## start suite and register in context
        self.startTestRunIfNeeded()

    def start_test(self, name, attributes):
        suiteNames = attributes.get("longname").split(".")
        suiteNames.pop()
        suiteKey = ".".join(suiteNames)

        if not self.suites.get(suiteKey):
            startedSuites = asyncio.run(
                self.client.startSuite(self.testRunUUID, suiteNames)
            )
            for suite in startedSuites:
                self.suites[".".join(suiteNames)] = suite
                suiteNames.pop()

        suiteUUID = self.suites.get(suiteKey)

        testUUID = asyncio.run(
            self.client.startTest(self.testRunUUID, suiteUUID, name, TestType.TEST)
        )
        self.tests[attributes.get("id")] = testUUID

    def end_test(self, name, attributes):
        testUUID = self.tests.get(attributes.get("id"))
        status = get_status(attributes.get("status"))
        message = attributes.get("message")
        if len(message) > 0:
            level = LogLevel.INFO if status == TestStatus.PASSED else LogLevel.ERROR
            asyncio.run(self.client.log(self.testRunUUID, testUUID, level, message))
        asyncio.run(self.client.finishTest(testUUID, self.testRunUUID, status))
        self.tests.pop(attributes.get("id"))

    def start_keyword(self, name, attributes):
        testUUID = list(self.tests.values())[-1]
        parentStepUUID = self.steps[-1] if len(self.steps) > 0 else None

        stepUUID = asyncio.run(
            self.client.startStep(
                self.testRunUUID, testUUID, attributes.get("kwname"), parentStepUUID
            )
        )

        self.steps.append(stepUUID)

    def end_keyword(self, name, attributes):
        stepUUID = self.steps[-1]
        status = get_status(attributes.get("status"))

        asyncio.run(self.client.finishStep(stepUUID, self.testRunUUID, status))
        self.steps.pop()

    def log_message(self, message):
        stepUUID = self.steps[-1] if len(self.steps) > 0 else None

        testUUID = testUUID = list(self.tests.values())[-1]

        level = get_level(message["level"])
        logMsg = message["message"]

        if message["html"] is "yes":
            images = re.findall('src="(.+?)"', logMsg)
            if len(images) > 0:
                logUUID = asyncio.run(
                    self.client.log(
                        self.testRunUUID, testUUID, level, images[0], stepUUID
                    )
                )

                attachmentFile = AttachmentFile(
                    images[0],
                    open(
                        "{0}{1}{2}".format(self.outDir, os.path.sep, images[0]), "rb"
                    ).read(),
                )
                attachmentMeta = AttachmentMetaData(
                    self.testRunUUID, testUUID, logUUID, stepUUID
                )
                asyncio.run(self.client.logAttachment(attachmentFile, attachmentMeta))
            else:
                asyncio.run(
                    self.client.log(
                        self.testRunUUID,
                        testUUID,
                        level,
                        logMsg,
                        stepUUID,
                        LogFormat.HTML,
                    )
                )
        else:
            asyncio.run(
                self.client.log(self.testRunUUID, testUUID, level, logMsg, stepUUID)
            )

    # #def message(self, message):
    #     ## Send log
    #     #print("SysLog: {0}".format(message))

    # def output_file(self, path):
    #     ## attach file to last log
    #     print("OutFile: {0}".format(path))

    # def log_file(self, path):
    #     ## attach file to log?
    #     print("LogFile: {0}".format(path))

    def close(self):
        asyncio.run(self.client.finishTestRun(self.testRunUUID))
        self.eventLoop.close()

    def startTestRunIfNeeded(self):
        if not hasattr(self, "testRunUUID"):
            self.endpoint = get_variable("orangebeard_endpoint")
            self.accessToken = get_variable("orangebeard_accesstoken")
            self.project = get_variable("orangebeard_project")
            self.testset = get_variable("orangebeard_testset")
            self.description = get_variable("orangebeard_description")
            self.outDir = get_variable("OUTPUT_DIR")

            ##create client and initialize context
            self.client = AsyncOrangebeardClient(
                self.endpoint, self.accessToken, self.project
            )

            ##start test run
            self.testRunUUID = asyncio.run(
                self.client.startTestrun(self.testset, description=self.description)
            )

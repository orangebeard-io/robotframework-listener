<h1 align="center">
  <a href="https://github.com/orangebeard-io/robotframework-listener">
    <img src="https://raw.githubusercontent.com/orangebeard-io/robotframework-listener/master/.github/logo.svg" alt="Orangebeard.io Robot Framework Listener" height="200">
  </a>
  <br>Orangebeard.io Robot Framework Listener<br>
</h1>

<h4 align="center">Orangebeard Robot Framework Listener</h4>

<p align="center">
  <a href="https://github.com/orangebeard-io/robotframework-listener/actions">
    <img src="https://img.shields.io/github/workflow/status/orangebeard-io/robotframework-listener/release?style=flat-square"
      alt="Build Status" />
  </a>
  <a href="https://github.com/orangebeard-io/robotframework-listener/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/orangebeard-io/robotframework-listener?style=flat-square"
      alt="License" />
  </a>
</p>

<div align="center">
  <h4>
    <a href="https://orangebeard.io">Orangebeard</a> |
    <a href="#installation">Installation</a>
  </h4>
</div>

## Installation

### Install the pip package

`pip install orangebeard-robotframework`


## Usage

Run your tests as usual with the listener registered:
```
robot \
--listener orangebeard_robotframework.listener \
--variable orangebeard_endpoint:"https://my-instance.orangebeard-staging.app" \
--variable orangebeard_accesstoken:"your-orangebeard-access-token"  \
--variable orangebeard_project:"project_name" \
--variable orangebeard_testset:"Testset name" \
--variable orangebeard_loglevel:"INFO" \
--variable orangebeard_reference_url:"https://orangebeard.io/myref"
./tests
```
The loglevel is optional and defaults to INFO. Valid options are DEBUG, INFO, WARN, ERROR.
DEBUG log level includes TRACE logs from RobotFramework. It can only be set using a RF variable, not from json or environment

You can also provide the (partial) configuration parameters from a json file (called orangebeard.json) in the working directory or up in the directory structure:

```json [orangebeard.json]
{
  "endpoint": "https://my-instance.orangebeard.app",
  "token": "your-orangebeard-access-token",
  "project": "project_name",
  "testset": "RobotFramework Tests",
  "description": "A run from robot framework",
  "attributes": [
    {
      "key": "Key 1",
      "value": "Some value"
    },
    {
      "value": "Tag value"
    }
  ],
  "referenceUrl": "https://link.to.my/build-server",
  "loglevel": "INFO"
}
```

Or using environment variables:
```bash
export ORANGEBEARD_ENDPOINT=https://my-instance.orangebeard.app
export ORANGEBEARD_TOKEN=your-orangebeard-access-token
export ORANGEBEARD_TESTSET="RobotFramework Tests"
export ORANGEBEARD_PROJECT=project_name
export ORANGEBEARD_DESCRIPTION="A run from robot framework"
export ORANGEBEARD_ATTRIBUTES="key1:some value;Tag value"
export ORANGEBEARD_REF_URL=https://link.to.my/build-server
```

Note that the `--listener orangebeard_robotframework.listener ` argument should always be provided to robotframework to register the listener.

Configuration is applied in the following order:
1. Json file configuration is read
2. Configuration parameters are enriched/overwritten from environment variables
3. Configuration parameters are enriched/overwritten from listener variables
  
This way, configuration can be provided using a combination ove the beforementioned methods. i.e. setting endpoint and
project from json, and providing token, test set name, etc from environment and/or listener command variables.

## Parallel test reporting with pabot
When using pabot, the Orangebeard run should be started before the runners start and finished
after full completion, otherwise every thread will report its own Orangebeard run. This can be achieved using the
orangebeard Python client's CLI utility.
Example:

```shell
#!/bin/bash
testrunUuid=$(orangebeard-cli -x start)
pabot --listener orangebeard_robotframework.listener  --variable orangebeard_testrun:"$testrunUuid" --console verbose .
orangebeard-cli -x finish -id $testrunUuid
```

This will start the run in Orangebeard (using json or environment autoconfig) and get the run's UUID in a variable. Then
start the test run and finish the run upon process completion.

For more CLI configuration options, see https://github.com/orangebeard-io/python-client?tab=readme-ov-file#cli or run `orangebeard-cli -h`
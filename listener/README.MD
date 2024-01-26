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
--listener orangebeard.listener \
--variable orangebeard_endpoint:"https://my-instance.orangebeard-staging.app" \
--variable orangebeard_accesstoken:"your-orangbeard-access-token"  \
--variable orangebeard_project:"project_name" \
--variable orangebeard_testset:"Testset name" \
./tests
```


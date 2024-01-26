# Samle tests to demo Listener
### Dependency installation:

```
pip install -r requirements.txt
rfbrowser init   
```

### Running tests:
```
robot --listener orangebeard_robotframework.listener \
    --variable orangebeard_endpoint:https://my-instance.orangebeard.app \
    --variable orangebeard_accesstoken:[orangebeard-access-token] \
    --variable orangebeard_project:orangebeard-project \
    --variable orangebeard_testset:"Test set name" ./
```

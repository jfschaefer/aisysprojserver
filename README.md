# README

## Terminology
* **Agent**
* **Environment**
* **Run**
* **Performance**
* **Action**
* **Action request**
* **Percept**


## Environment API
TODO


## Build docker image

```
sudo service start docker
sudo docker build -t jfschaefer/gs:0.0.5 .
sudo docker build -t jfschaefer/gs:latest .
sudo docker run -v /tmp/persistent:/app/persistent -p 80:80 jfschaefer/gs
sudo docker push jfschaefer/gs:0.0.5
sudo docker push jfschaefer/gs:latest
```


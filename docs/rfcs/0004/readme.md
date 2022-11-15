---
authors: Bill Johnson <billj@hpe.com>
state: discussion
discussion: 
---
Near Node Flash Smoke Test
==================================
Near Node Flash Smoke Test erects a framework that can perform a number of smoke test related functions, including:
* Creation of a docker container - complete
* Pull Rabbit components from github - complete (more or less)
* Build each Rabbit component - in progress (some components fail to build)
* Deploy Rabbit components using nnf-deploy
* Run stock or custom tests against Rabbit software
* Capture the results of tests
* Mark/report the tests as successful or failed

##Container build
Final Image Tools Requirements
* Docker in Docker
** docker run -v /var/run/docker.sock:/var/run/docker.sock -it docker
* Golang
* Git
* Make

Images - alpine based
  - Contains apk-tools (alpine package manager)
  - Contains docker CLI
  - Contains wget, make
  - Does not have git (apk add git)
  - Does not have bash (apk add bash)
  - Does not have golang (Dockerfile COPY)
  - Does not have kustomize


##Container run examples

The following is helpful for development...it runs the container and drops you in a shell.  From there you can edit and run main.sh.  main.sh is mapped from your dev directory so any changes that you make persist after the container stops or is removed.

    docker run --entrypoint sh -v /var/run/docker.sock:/var/run/docker.sock -v $HOME/.kube/config:/app/.kube/config -v <your path to>/main.sh:/app/main.sh -it smoke:latest

This is a normal run, which will attempt to build and deploy all components.  Ultimately, this would also run the unit tests.

    docker run --entrypoint sh -v $HOME/.kube/config:/app/.kube/config -it smoke:latest

An example showing how to ignore any "developer labels" and to increase runtime verbosity.

    docker run -v <your path to >/somek8s.cfg:/app/.kube/config -v /var/run/docker.sock:/var/run/docker.sock -it smoke:latest -v -v -v --ignore-dev

##Misc helpful commands

Building the container image.
    docker build -t smoke:latest .

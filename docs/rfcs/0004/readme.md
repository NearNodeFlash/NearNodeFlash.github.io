---
authors: Bill Johnson <billj@hpe.com>
state: discussion
discussion: 
---
Near Node Flash Smoke Test
==================================
Near Node Flash Smoke Test erects a framework that can perform a number of smoke test related functions, including:
* Creation of a docker container - complete (more or less)
* Pull Rabbit components from github - complete (more or less)
* Build each Rabbit component - in progress (some components fail to build)
* Deploy Rabbit components using nnf-deploy (todo)
* Run stock or custom tests against Rabbit software (todo)
* Capture the results of tests (todo)
* Mark/report the tests as successful or failed (todo)

## Container build
Final Image Tools Requirements
* Docker in Docker
** docker run -v /var/run/docker.sock:/var/run/docker.sock -it docker
* Golang
* git
* make
* kustomize

Images - uses the docker image which is alpine based
  - Contains apk-tools (alpine package manager)
  - Contains docker CLI
  - Contains wget, make
  - Does not have git (apk add git)
  - Does not have bash (apk add bash)
  - Does not have golang (Dockerfile COPY)
  - Does not have kustomize (kustomize installer)

## Basic FLow
  - Basic validation 
    - Kube config info present **(complete-ish)**
    - Not in use by a developer (by namespace name) **(complete-ish)**
    - No previous test failure (smoke test namespace exists) **(complete-ish)**
    - Cluster nodes healthy **(complete-ish)**
  - Initialization
    - Create the test namespace **(complete-ish)**
    - Pull and build nnf-deploy **(complete-ish)**
  - Build and Deploy
    - Use nnf-deploy to undeploy any existing components (may require nnf-deploy modifications) **(in progress)**
    - Use nff-deploy to build and deploy fresh components **(in progress)**
    - Run tests **(todo)**
    - Evaluate test runs **(todo)**
  - Cleanup

## Considerations
  - Once built, the image can be run multiple times with different tests if desired
  - The kubernetes cluster can be changed by volume mapping in different kube configs
  - nnf-deploy does not return failure status codes which can make failures in the process non-obvious

## Container run examples

The following is helpful for development...it runs the container and drops you in a shell.  From there you can edit and run main.sh.  main.sh is mapped from your dev directory so any changes that you make persist after the container stops or is removed.

    docker run --entrypoint sh -v /var/run/docker.sock:/var/run/docker.sock -v $HOME/.kube/config:/app/.kube/config -v <your path to>/main.sh:/app/main.sh -it smoke:latest

This is a normal run, which will attempt to build and deploy all components.  Ultimately, this would also run the unit tests.

    docker run --entrypoint sh -v $HOME/.kube/config:/app/.kube/config -it smoke:latest

An example showing how to ignore any "developer labels" and to increase runtime verbosity.

    docker run -v <your path to >/somek8s.cfg:/app/.kube/config -v /var/run/docker.sock:/var/run/docker.sock -it smoke:latest -v -v -v --ignore-dev

## Misc helpful commands

Building the container image.

    docker build -t smoke:latest .

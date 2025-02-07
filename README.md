# RUST Driver Matrix

## Prerequisites
* Rust (nightly build)
* Python3.10
* pip
* docker
* git
* OpenJDK 11 
* CCM

#### Installing dependencies
Docker image include all needed dependencies

##### Repositories dependencies
All repositories should be under the **same base folder**
```bash
  git clone git@github.com:datastax/scylla-rust-driver.git &
  git clone git@github.com:scylladb/rust-driver-matrix.git &
  wait
```

Install CCM
```bash
pip3 install https://github.com/scylladb/scylla-ccm/archive/master.zip &
```

## Running locally

* Execute the main.py wrapper like:
  * Create and start Scylla cluster:
  ```bash
  ccm create -i 127.0.1. -n 3 --scylla -v release:5.2  scylla-cluster
  ccm start
  ```
  * Running with scylla-rust-driver: 
    * From `rust-driver-matrix`:
      ```bash
      # Run all standard tests on latest rust-driver tag (--versions 1)
      # Default rust-driver versions: v0.8.2,v0.7.0. To change it, use `--versions` argument 
      python3 python3 main.py /scylla-rust-driver --tests rust,serverless,tls --scylla-version 5.2 --version-size 1
      ```

  * Running with docker image: 
      ```bash
      ./scripts/run_test.sh python3 main.py /scylla-rust-driver --tests rust --scylla-version 5.2 --version-size 1
      ```

#### Uploading docker images
When doing changes to `requirements.txt`, or any other change to docker image, it can be uploaded like this:
```bash
    export MATRIX_DOCKER_IMAGE=scylladb/scylla-rust-driver-matrix:nightly-rust.2023-06-10-python3.11-$(date +'%Y%m%d')
    docker build ./scripts -t ${MATRIX_DOCKER_IMAGE}
    docker push ${MATRIX_DOCKER_IMAGE}
    echo "${MATRIX_DOCKER_IMAGE}" > scripts/image
```
**Note:** you'll need permissions on the scylladb dockerhub organization for uploading images

#!/bin/bash

TMP_DIR=$(mktemp -d)
LAMBDA_PACKAGE_NAME=event-listener-1.0.0.zip
LAMBDA_PACKAGE_PATH=${TMP_DIR}/${LAMBDA_PACKAGE_NAME}

echo "Creating AWS Lambda package in temporary directory '${TMP_DIR}'."
zip "${LAMBDA_PACKAGE_PATH}" event_listener.py
echo "AWS Lambda package created in '${LAMBDA_PACKAGE_PATH}'."

aws s3 --profile baptiste --region eu-west-3 cp "${LAMBDA_PACKAGE_PATH}" "s3://meetup-spot-instances/demo2/${LAMBDA_PACKAGE_NAME}"

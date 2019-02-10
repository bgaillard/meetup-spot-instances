#!/bin/bash

AWS_PROFILE=baptiste
CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

packer build -force -var aws_profile="${AWS_PROFILE}" "${CURRENT_DIR}/demo1/mapper/packer-template.json"
packer build -force -var aws_profile="${AWS_PROFILE}" "${CURRENT_DIR}/demo1/reducer/packer-template.json"
packer build -force -var aws_profile="${AWS_PROFILE}" "${CURRENT_DIR}/load-generator/packer-template.json"

#!/bin/bash

set -x

aws ec2 describe-spot-price-history --instance-types m5.large --product-description "Linux/UNIX (Amazon VPC)" --start-time 2019-02-06T09:00:00 --end-time 2019-02-06T15:00:00 | jq


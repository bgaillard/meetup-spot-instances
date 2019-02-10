#!/bin/bash

DNS_NAME=demo2-load-balancer-1072315318.eu-west-3.elb.amazonaws.com

CONCURRENCY=100
NUMBER_OF_REQUESTS=10000

ab -c ${CONCURRENCY} -n ${NUMBER_OF_REQUESTS} "http://${DNS_NAME}/"

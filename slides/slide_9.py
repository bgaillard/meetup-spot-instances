#!/usr/bin/env python3

from datetime import datetime
import json
import boto3

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

ec2_client = boto3.client('ec2')
response = ec2_client.describe_spot_price_history(
    InstanceTypes=[
        'm5.large'
    ],
    ProductDescriptions=[
        'Linux/UNIX (Amazon VPC)'
    ],
    StartTime=datetime(2019, 2, 6, 9, 0, 0),
    EndTime=datetime(2019, 2, 6, 15, 0, 0)
)

response.pop('NextToken', None)
response.pop('ResponseMetadata', None)
print(json.dumps(response, default=json_serial, indent=2))

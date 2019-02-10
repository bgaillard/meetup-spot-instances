"""Python module used to manager the Mapper or Reducer applications."""
#!/usr/bin/env python3

import argparse
import base64
import time
import boto3

class SpotRequestsManager:
    """Component used to manage the Mapper or Reduction application."""

    def __init__(self, ec2_client):
        self.app = None
        self.ec2_client = ec2_client
        self.instance_count = None
        self.instance_type = None
        self.spot_price = None

    def describe_active_spot_instance_requests(self):
        """Describe the active spot instance requests of the app."""
        return self.ec2_client.describe_spot_instance_requests(
            Filters=[
                self._create_name_filter(),
                {
                    'Name': 'state',
                    'Values': [
                        'active'
                    ]
                }
            ]
        )

    def get_image_id(self):
        """Gets the identifier of the Mapper or the Reducer AMI."""
        images = self.ec2_client.describe_images(Filters=[self._create_name_filter()])
        return images['Images'][0]['ImageId']

    def get_security_group_id(self):
        """Gets the name of the Mapper or the Reducer Security Group."""
        security_groups = self.ec2_client.describe_security_groups(Filters=[self._create_name_filter()])
        return security_groups['SecurityGroups'][0]['GroupId']

    def get_subnet_id(self):
        """Gets the identifie of the first private subnet."""
        subnets = self.ec2_client.describe_subnets(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [
                        'meetup-spot-instances-private-subnet-1a'
                    ]
                }
            ]
        )
        return subnets['Subnets'][0]['SubnetId']

    def set_app(self, app):
        """Sets the name of the app to work on, this can be 'mapper' or 'reducer'."""
        self.app = app

    def set_instance_count(self, instance_count):
        self.instance_count = instance_count

    def set_instance_type(self, instance_type):
        self.instance_type = instance_type

    def set_spot_price(self, spot_price):
        self.spot_price = spot_price

    def start(self):
        response = self.ec2_client.request_spot_instances(
            InstanceCount=self.instance_count,
            LaunchSpecification={
                'IamInstanceProfile': {
                    'Name': self._create_name_tag_value()
                },
                'ImageId': self.get_image_id(),
                'InstanceType': self.instance_type,
                'Monitoring': {
                    'Enabled': False
                },
                'Placement': {
                    'Tenancy': 'default'
                },
                'SecurityGroupIds': [
                    self.get_security_group_id()
                ],
                'SubnetId': self.get_subnet_id(),
                'UserData': self._create_user_data()
            },
            SpotPrice=self.spot_price,
            Type='one-time',
            InstanceInterruptionBehavior='terminate'
        )

        spot_instance_requests = response['SpotInstanceRequests']
        for spot_instance_request in spot_instance_requests:
            while True:
                try:
                    self.ec2_client.create_tags(
                        Resources=[
                            spot_instance_request['SpotInstanceRequestId']
                        ],
                        Tags=self._create_tags()
                    )
                except:
                    pass
                else:
                    break

        for spot_instance_request in spot_instance_requests:
            tagged = False
            while not tagged:
                time.sleep(5)
                response = self.ec2_client.describe_spot_instance_requests(
                    SpotInstanceRequestIds=[spot_instance_request['SpotInstanceRequestId']]
                )
                if 'InstanceId' in response['SpotInstanceRequests'][0]:
                    self.ec2_client.create_tags(
                        Resources=[
                            response['SpotInstanceRequests'][0]['InstanceId']
                        ],
                        Tags=self._create_tags()
                    )
                    tagged = True

    def stop(self):
        """Stop spot instance requests."""
        requests = self.describe_active_spot_instance_requests()
        request_ids = self._extract_spot_requests_ids(requests)

        if request_ids:
            instance_ids = self._extract_spot_requests_instance_ids(requests)
            self.ec2_client.cancel_spot_instance_requests(SpotInstanceRequestIds=request_ids)
            self.ec2_client.terminate_instances(InstanceIds=instance_ids)

    def _create_tags(self):
        return [
            {
                'Key': 'Name',
                'Value': self._create_name_tag_value()
            }
        ]

    def _create_name_filter(self):
        return {
            'Name': 'tag:Name',
            'Values': [
                self._create_name_tag_value()
            ]
        }

    def _create_name_tag_value(self):
        return 'meetup-spot-instances-demo1-' + self.app

    def _create_user_data(self):
        user_data = """#cloud-config
bootcmd:
 - python3 /home/ec2-user/""" + self.app + """.py &"""
        return base64.b64encode(user_data)

    @staticmethod
    def _extract_spot_requests_ids(spot_instance_requests_response):
        spot_instance_request_ids = []
        for spot_instance_request in spot_instance_requests_response['SpotInstanceRequests']:
            spot_instance_request_ids.append(spot_instance_request['SpotInstanceRequestId'])
        return spot_instance_request_ids

    @staticmethod
    def _extract_spot_requests_instance_ids(spot_instance_requests_response):
        spot_instance_request_ids = []
        for spot_instance_request in spot_instance_requests_response['SpotInstanceRequests']:
            spot_instance_request_ids.append(spot_instance_request['InstanceId'])
        return spot_instance_request_ids

def main():
    """The main entry of program."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Create Spot requests for the Mapper or the Reducer.')
    parser.add_argument('action', default=None, help='The action to execute')
    parser.add_argument('--app', default=None, help='The name of the application to work on')
    parser.add_argument('--instance-count', default=None, help='The number of EC2 instances to start')
    parser.add_argument('--profile', default=None, help='The name of an AWS profile to use')
    parser.add_argument('--region', default='eu-west-3', help='The name of an AWS region to use')
    args = parser.parse_args()

    # Create the AWS clients
    boto3.setup_default_session(profile_name=args.profile, region_name=args.region)
    ec2_client = boto3.client('ec2')

    # Create the Spot requests Manager
    manager = SpotRequestsManager(ec2_client)
    manager.set_app(args.app)
    manager.set_instance_count(int(args.instance_count))
    manager.set_instance_type('t2.micro')
    manager.set_spot_price('0.0041')

    if args.action == 'start':
        manager.start()
    elif args.action == 'stop':
        manager.stop()
    else:
        print('Unknown action \'%s\' !', args.action)

if __name__ == '__main__':
    main()

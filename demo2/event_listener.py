import boto3
import json

class EventListener:

    def __init__(self, autoscaling_client, ec2_client, elbv2_client):
        self.autoscaling_client = autoscaling_client
        self.ec2_client = ec2_client
        self.elbv2_client = elbv2_client

    def handle_event(self, event):
        if 'detail-type' in event and event['detail-type'] == 'EC2 Spot Instance Interruption Warning':
            self._handle_interruption_event(event)

    def _deregister_target(self, instance_id):
        self.elbv2_client.deregister_targets(
            TargetGroupArn='',
            Targets=[
                {
                    'Id': instance_id
                }
            ]
        )

    def _get_launch_template_id(self):
        launch_templates = self.ec2_client.describe_launch_templates(
            LaunchTemplateNames=[
                'demo2-launch-template'
            ]
        )
        return launch_templates['LaunchTemplates'][0]['LaunchTemplateId']

    def _get_load_balancer_arn(self):
        load_balancers = self.elbv2_client.describe_load_balancers(
            Names=[
                'demo2-load-balancer'
            ]
        )
        return load_balancers['LoadBalancers'][0]['LoadBalancerArn']

    def _get_number_of_not_terminated_instances(self):
        number_of_not_terminated_instances = 0
        instances = self.ec2_client.describe_instances(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values' : [
                        'demo2-instance'
                    ]
                }
            ]
        )
        for instance in instances['Reservations'][0]['Instances']:
            if instance['State'] != 'terminated':
                number_of_not_terminated_instances += 1

        return number_of_not_terminated_instances


    def _get_target_group_arn(self):
        target_groups = self.elbv2_client.describe_target_groups(
            LoacBalancerArn=self._get_load_balancer_arn()
        )
        return target_groups['TargetGroups'][0]['TargetGroupArn']

    def _get_spot_fleet_target_capacity(self):
        launch_template_id = self._get_launch_template_id()
        spot_fleet_request_config = None
        spot_fleet_request_id = None
        spot_fleet_requests = self.ec2_client.describe_spot_fleet_requests()

        for spot_fleet_request_config in spot_fleet_requests['SpotFleetRequestConfigs']:
            launch_template_config = spot_fleet_request_config['SpotFleetRequestConfig']['LaunchTemplateConfigs'][0]
            if launch_template_config['LaunchTemplateSpecification']['LaunchTemplateId'] == launch_template_id:
                spot_fleet_request_id = spot_fleet_request_config['SpotFleetRequestConfig']['SpotFleetRequestId']

        return spot_fleet_request_id

    def _increment_desired_on_backup_auto_scaling_group(self):
        auto_scaling_groups = self.autoscaling_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[
                'demo2-backup-auto-scaling-group'
            ]
        )
        backup_auto_scaling_group = auto_scaling_groups['AutoScalingGroups'][0]
        desired_capacity = backup_auto_scaling_group['DesiredCapacity'] + 1
        self.autoscaling_client.set_desired_capacity(
            AutoScalingGroupName='demo2-backup-auto-scaling-group',
            DesiredCapacity=desired_capacity
        )

    def _handle_interruption_event(self, event):
        """Handle an EC2 Spot Instance interruption event.

        The received event has the following structure.
            {
                "version": "0,
                "id": "3b23bf38-941e-465d-3a28-c5dc5e0d9e1a",
                "detail-type": "EC2 Spot Instance Interruption Warning",
                "source": "aws.ec2",
                "account": "XXXXXXXXXXXX",
                "time": "2019-02-17T15:07:40Z",
                "region": 'eu-west-3',
                "resources": [
                    "arn:aws:ec2:eu-west-3a:instance/i-0b68a1b007d411280"
                ],
                "detail": {
                    "instance-id": "i-0b68a1b007d411280",
                    "instance-action": "terminate"
                }
            }
        """

        # Deregister the instance from the Load Balancer Target Group. The instance then enters a 'draining' state
        self._deregister_target(event['detail']['instance-id'])

        # If the Spot Fleet Target Capacity is the same as the number of not terminated EC2 instances then the EC2
        # instance will be terminated abnormally (i.e not following a scale-in)
        number_of_not_terminated_instances = self._get_number_of_not_terminated_instances()
        spot_fleet_target_capacity = self._get_spot_fleet_target_capacity()
        if number_of_not_terminated_instances == spot_fleet_target_capacity:
            self._increment_desired_on_backup_auto_scaling_group()

def lambda_handler(event, context):
    """AWS Lambda handler function which intercepts Spot Instance interruption events.

    Args:
      - event  : dict, The Amazon ECS event received.
      - context: LambdaContext, An object which describes the runtime context.
    """

    print(context)
    print(event)

    profile_name = None
    region_name = 'eu-west-3'

    # Only used for testing purpose locally
    if context.client_context and context.client_context.custom:
        profile_name = context.client_context.custom['profile_name']

    session = boto3.session.Session(profile_name=profile_name)
    autoscaling_client = session.client(service_name='autoscaling', region_name=region_name)
    ec2_client = session.client(service_name='ec2', region_name=region_name)
    elbv2_client = session.client(service_name='elbv2', region_name=region_name)

    event_listener = EventListener(autoscaling_client, ec2_client, elbv2_client)
    event_listener.handle_event(event)

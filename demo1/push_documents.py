"""Python module used to push document messages in the 'document' SQS queue."""
#!/usr/bin/env python3

import argparse
import boto3

class Pusher:
    """Component used to push document message in the 'document' SQS queue."""

    def __init__(self, s3_bucket, sqs_client):
        self.account_id = None
        self.bucket_name = None
        self.region = None
        self.s3_bucket = s3_bucket
        self.sqs_client = sqs_client

    def push_documents(self):
        """Push document messages to the 'documents' SQS queue."""
        for s3_object in self.s3_bucket.objects.all():
            if s3_object.key.endswith('.txt'):
                self.sqs_client.send_message(
                    QueueUrl=self._create_documents_queue_url(),
                    MessageBody='{"s3Key": "' + s3_object.key + '"}'
                )

    def set_account_id(self, account_id):
        """Sets the current AWS acccount identifier."""
        self.account_id = account_id

    def set_region(self, region):
        """Sets the AWS region to work on."""
        self.region = region

    def _create_documents_queue_url(self):
        """Create the SQS URL of the 'documents' queue."""
        return 'https://sqs.' + self.region + '.amazonaws.com/' + self.account_id + '/documents'

def main():
    """The main entry of the program."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Push document messages in the \'documents\' SQS queue.')
    parser.add_argument('--profile', default=None, help='The name of an AWS profile to use')
    parser.add_argument('--region', default='eu-west-3', help='The name of an AWS region to use')
    args = parser.parse_args()

    # Create the AWS clients
    boto3.setup_default_session(profile_name=args.profile, region_name=args.region)
    account_id = boto3.client('sts').get_caller_identity().get('Account')
    s3_bucket = boto3.resource('s3').Bucket('aws-nantes-imdb')
    sqs_client = boto3.client('sqs')

    # Create the Pusher
    pusher = Pusher(s3_bucket, sqs_client)
    pusher.set_account_id(account_id)
    pusher.set_region(args.region)
    pusher.push_documents()

if __name__ == '__main__':
    main()

"""Python module which defines a Mapper to count words in documents."""
#!/usr/bin/env python

import argparse
import json
import logging
import signal
import boto3

class Reducer:
    """"""
    DOCUMENTS_BATCH_SIZE = 1000

    def __init__(self, sqs_words_queue, dynamodb_table):

        # Configure the logger
        handler = logging.StreamHandler()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

        # AWS clients
        self.sqs_words_queue = sqs_words_queue
        self.dynamodb_table = dynamodb_table

        # Variables
        self.current_batch_size = 0
        self.stop = False
        self.word_counts_cache = {}

        # Bind signal handlers
        signal.signal(signal.SIGINT, self.handle_sigterm)
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def add_word_counts(self, word_counts):
        for word, count in word_counts.items():
            if word in self.word_counts_cache:
                self.word_counts_cache[word] += count
            else:
                self.word_counts_cache[word] = count

    def handle_sigterm(self, received_signal, frame): # pylint: disable=unused-argument
        """Handle the SIGTERM signal to prepare the mapper to be stopped."""
        self.logger.info('Received signal %s.', received_signal)
        self.logger.info('Wait until 20 seconds to quit the program ...')
        self.stop = True

    def process_words_message(self, message):
        """Process one words message.

        :type message: boto3.SQS.Message
        :param message: The SQS message which describe the words to process.
        """
        json_body = json.loads(message.body)
        self.add_word_counts(json_body)
        self.sqs_words_queue.delete_messages(
            Entries=[
                {
                    'Id': message.message_id,
                    'ReceiptHandle': message.receipt_handle
                }
            ]
        )
        self.current_batch_size += 1
        if self.current_batch_size >= self.DOCUMENTS_BATCH_SIZE:
            self._update_dynamodb_words_table()
            self.word_counts_cache = {}

    def _update_dynamodb_words_table(self):
        for word, count in self.word_counts_cache.items():
            self.dynamodb_table.update_item(
                Key={
                    'word': word
                },
                UpdateExpression='add occurences :c',
                ExpressionAttributeValues={
                    ':c': count
                }
            )

    def start(self):
        """Starts the reducer."""
        self.logger.info('Starting reducer ...')
        self.logger.info('Enter <Ctrl+C> to stop.')
        while not self.stop:
            messages = self.sqs_words_queue.receive_messages(
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20
            )
            for message in messages:
                self.process_words_message(message)
        self.logger.info('Reducer gracefully stopped.')

def main():
    """The main entry of the Reducer program."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Count words in documents.')
    parser.add_argument('--profile', default=None, help='The name of an AWS region to use)')
    parser.add_argument('--region', default='eu-west-3', help='The name of an AWS profile to use)')
    args = parser.parse_args()

    # Create AWS clients
    boto3.setup_default_session(profile_name=args.profile, region_name=args.region)
    dynamodb_client = boto3.resource('dynamodb')
    dynamodb_table = dynamodb_client.Table('words')
    sqs_client = boto3.resource('sqs')
    sqs_words_queue = sqs_client.get_queue_by_name(QueueName='words')

    # Create an start the Mapper
    reducer = Reducer(sqs_words_queue, dynamodb_table)
    reducer.start()

if __name__ == '__main__':
    main()

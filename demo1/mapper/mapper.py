"""Python module which defines a Mapper to count words in documents."""
#!/usr/bin/env python

import argparse
import collections
import logging
import json
import re
import signal
import boto3

class Mapper:
    """Class whic defines a Mapper to extract and count words from documents."""

    STOP_WORDS = [
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd",
        'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
        'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
        'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
        'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
        'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off',
        'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
        'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
        'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've",
        'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't",
        'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn',
        "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't",
        'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"
    ]

    def __init__(self, s3_bucket, sqs_documents_queue, sqs_words_queue):

        # Configure the logger
        handler = logging.StreamHandler()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

        # AWS clients
        self.s3_bucket = s3_bucket
        self.sqs_documents_queue = sqs_documents_queue
        self.sqs_words_queue = sqs_words_queue

        # Variable used to stop the Mapper
        self.stop = False

        # Bind signal handlers
        signal.signal(signal.SIGINT, self.handle_sigterm)
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def count_words_in_document(self, document_path):
        """Count words inside a specific document.

        :type document_path: string
        :param document_path: The path to the text document for which one to count words.

        :return: A dictionay where keys represent each word found and value their number.
        :rtype: collections.defaultdict
        """
        word_counts = collections.defaultdict(int)

        with open(document_path) as document:
            for line in document.readlines():
                for word in line.strip().split():
                    word = self._cleanup_word(word)
                    if self._is_word_eligible(word):
                        word_counts[word] += 1

        return collections.OrderedDict(sorted(word_counts.items(), key=lambda x: x[1], reverse=True))

    def handle_sigterm(self, received_signal, frame): # pylint: disable=unused-argument
        """Handle the SIGTERM signal to prepare the mapper to be stopped."""
        self.logger.info('Received signal %s.', received_signal)
        self.logger.info('Wait until 20 seconds to quit the program ...')
        self.stop = True

    def process_document_message(self, message):
        """Process one document message.

        :type message: boto3.SQS.Message
        :param message: The SQS message which describe the document to process.
        """
        json_body = json.loads(message.body)
        document_path = '/tmp/document.txt'

        # TODO: Si la cle 's3Key' n'est pas la ne pas echouer et afficher un log clair.
        #       Voir si on peut logger dans CloudWatch ou un autre endroit pratique
        self.s3_bucket.download_file(json_body['s3Key'], document_path)
        word_counts = self.count_words_in_document(document_path)
        self.sqs_words_queue.send_message(
            MessageBody=json.dumps(word_counts)
        )
        self.sqs_documents_queue.delete_messages(
            Entries=[
                {
                    'Id': message.message_id,
                    'ReceiptHandle': message.receipt_handle
                }
            ]
        )

    def start(self):
        """Starts the mapper."""
        self.logger.info('Starting mapper ...')
        self.logger.info('Enter <Ctrl+C> to stop.')
        while not self.stop:
            messages = self.sqs_documents_queue.receive_messages(
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20
            )
            for message in messages:
                self.process_document_message(message)
        self.logger.info('Mapper gracefully stopped.')

    @staticmethod
    def _cleanup_word(word):

        # Remove punctuation
        cleaned_word = re.sub(r'[^a-zA-Z0-9]+', ' ', word)

        return cleaned_word.lower()

    def _is_word_eligible(self, word):
        eligible = True
        eligible = eligible and len(word) > 2
        eligible = eligible and word not in self.STOP_WORDS
        return eligible


def main():
    """The main entry of the Mapper program."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Count words in documents.')
    parser.add_argument('--profile', default=None, help='The name of an AWS profile to use)')
    parser.add_argument('--region', default='eu-west-3', help='The name of an AWS region to use)')
    args = parser.parse_args()

    # Create AWS clients
    boto3.setup_default_session(profile_name=args.profile, region_name=args.region)
    s3_bucket = boto3.resource('s3').Bucket('aws-nantes-imdb')
    sqs_client = boto3.resource('sqs')
    sqs_documents_queue = sqs_client.get_queue_by_name(QueueName='documents')
    sqs_words_queue = sqs_client.get_queue_by_name(QueueName='words')

    # Create an start the Mapper
    mapper = Mapper(s3_bucket, sqs_documents_queue, sqs_words_queue)
    mapper.start()

if __name__ == '__main__':
    main()

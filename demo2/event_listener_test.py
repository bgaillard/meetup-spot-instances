from event_listener import lambda_handler

class ClientContext(object):
    __slots__ = ['custom', 'env', 'client']

class LambdaContext(object):
    def __init__(self):
        self.client_context = ClientContext()
        self.client_context.custom = {'profile_name': 'preprod'}

lambda_handler({'source': 'aws.ecs'}, LambdaContext())

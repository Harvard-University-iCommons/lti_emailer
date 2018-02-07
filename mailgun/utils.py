import json
import time


def replace_non_ascii(s, replacement='_'):
        return ''.join(i if ord(i) < 128 else replacement for i in s)


class ApiRequestTimer(object):
    """
    Context manager for logging requests made to HTTP API endpoints
    """
    def __init__(self, logger, method, url, payload={}):
        self.logger = logger
        self.method = method
        self.url = url
        self.payload = payload
        self.status_code = 0

    def __enter__(self):
        self.logger.info(
            "Sending %s API request to %s with payload %s",
            self.method,
            self.url,
            json.dumps(self.payload)
        )
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.millis = (time.time() - self.start) * 1000
        self.logger.info(
            "Received %d response from %s API endpoint %s in %d",
            self.status_code,
            self.method,
            self.url,
            self.millis
        )


class Bunch:
    """
    Utility class for creating simple objects with attributes
    Ex. response = Bunch(status_code=400, json=lambda: {})
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

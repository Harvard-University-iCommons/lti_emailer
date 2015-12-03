class HttpResponseException(RuntimeError):
    def __init__(self, response):
        self.response = response

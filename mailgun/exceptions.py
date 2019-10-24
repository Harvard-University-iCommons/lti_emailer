from django.http import HttpResponse


class HttpResponseException(RuntimeError):
    '''Encapsulates a django.http.HttpResponse.  Intended to be caught at the
    top level of a view (or by a view decorator) to allow code within a view
    to immediately return a response.'''

    def __init__(self, response):
        if not isinstance(response, HttpResponse):
            raise TypeError(
                      'HttpResponseException expected an HttpResponse, got'
                      'a {}'.format(type(response)))
        self.response = response


    def __unicode__(self):
        return 'HttpResponseException<{} {}>: {}'.format(
                   type(self.response), self.response.status_code,
                   str(self.response))

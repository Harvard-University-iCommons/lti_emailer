import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1

'''
Point to local apache 
'''
bind = "127.0.0.1:8185"

pidfile = '/logs/lti_emailer/gunicorn.pid'

accesslog = '/logs/lti_emailer/gunicorn_access.log'

errorlog = '/logs/lti_emailer/gunicorn_error.log'

secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'https', 
    'X-FORWARDED-PROTO': 'https', 
    'X-FORWARDED-SSL': 'on'
}

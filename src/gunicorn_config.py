workers = 1
worker_class = 'gevent'
bind = '0.0.0.0:5000'
pidfile = '/tmp/gunicorn-csdh-api.pid'
debug = True
reload = True
loglevel = 'info'
errorlog = '/tmp/gunicorn_csdh_api_error.log'
accesslog = '/tmp/gunicorn_csdh_api_access.log'
daemon = False

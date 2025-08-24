import os

# Server socket
bind = f"{os.getenv('HOST', '127.0.0.1')}:{os.getenv('PORT', '8080')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WORKERS', '2'))
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '/var/www/perfmatters-api/logs/access.log'
errorlog = '/var/www/perfmatters-api/logs/error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'perfmatters-config-api'

# Server mechanics
daemon = False
pidfile = '/var/www/perfmatters-api/logs/gunicorn.pid'
tmp_upload_dir = None

# SSL (if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# Worker tmp directory
worker_tmp_dir = '/dev/shm'

# Preload app for better performance
preload_app = True

# Enable threading
threads = 1
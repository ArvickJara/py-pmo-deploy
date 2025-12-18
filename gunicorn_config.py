# Configuración de Gunicorn para Docker
import multiprocessing

# Bind
bind = "0.0.0.0:5001"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeouts
timeout = 300
keepalive = 5
graceful_timeout = 30

# Logging
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "pmo-python-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = "/app/temp"

# SSL (si lo necesitas)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"

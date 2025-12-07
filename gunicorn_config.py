# Gunicorn configuration for PakLegal ChatBot
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8001"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "paklegal_chatbot"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None

# Application
wsgi_app = "paklegal_chatbot.wsgi:application"
reload = False
reload_extra_files = []
reload_extra_dirs = []

# Environment
raw_env = [
    f"DJANGO_SETTINGS_MODULE=paklegal_chatbot.settings",
]

# Server hooks
def on_starting(server):
    print("Starting PakLegal ChatBot with Gunicorn...")

def when_ready(server):
    print("Gunicorn is ready. Spawning workers.")

def on_exit(server):
    print("Gunicorn shutting down...")

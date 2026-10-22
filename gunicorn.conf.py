"""Serve behind a TLS reverse proxy; keep instance/ on persistent storage."""
import os

bind = os.environ.get('BIND', '127.0.0.1:8000')
workers = int(os.environ.get('WEB_CONCURRENCY', '2'))
threads = 2
timeout = 30
# Only trust forwarding headers from explicitly configured proxy IPs.
forwarded_allow_ips = os.environ.get('FORWARDED_ALLOW_IPS', '127.0.0.1,::1')
# Avoid logging inquiry receipt URLs and submitted personal details.
accesslog = None
errorlog = '-'
capture_output = True

import multiprocessing
import os

# Binding
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Worker processes and threading
# Railway containers are often memory-constrained. PyTorch models are heavy.
# 1 worker process with 4 threads is much safer than multiple processes.
workers = 1
threads = 4
worker_class = "gthread"

# Timeout handling
timeout = 60
graceful_timeout = 30

# Memory management
preload_app = True
max_requests = 1000
max_requests_jitter = 50

# Railway filesystem optimization
# Uses memory-backed tmpfs instead of disk, which prevents Docker I/O stalls
worker_tmp_dir = "/dev/shm"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

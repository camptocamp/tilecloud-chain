###
# app configuration
# https://docs.gunicorn.org/en/stable/settings.html
###

import os

import gunicorn.arbiter
import gunicorn.workers.base
from c2cwsgiutils import get_config_defaults, get_logconfig_dict, get_paste_config, prometheus
from prometheus_client import multiprocess

bind = ":8080"

worker_class = "gthread"
workers = os.environ.get("GUNICORN_WORKERS", 2)
threads = os.environ.get("GUNICORN_THREADS", 10)

preload_app = True

paste = get_paste_config()
wsgi_app = paste

accesslog = "-"
access_log_format = os.environ.get(
    "GUNICORN_ACCESS_LOG_FORMAT",
    '%(H)s %({Host}i)s %(m)s %(U)s?%(q)s "%(f)s" "%(a)s" %(s)s %(B)s %(D)s %(p)s',
)

logconfig_dict = get_logconfig_dict(paste)
if os.environ.get("DEBUG_LOGCONFIG", "0") == "1":
    print("LOGCONFIG")
    print(logconfig_dict)

raw_paste_global_conf = ["=".join(e) for e in get_config_defaults().items()]


def on_starting(server: gunicorn.arbiter.Arbiter) -> None:
    """
    Will start the prometheus server.

    Called just before the master process is initialized.
    """

    del server

    prometheus.start()


def post_fork(server: gunicorn.arbiter.Arbiter, worker: gunicorn.workers.base.Worker) -> None:
    """
    Will cleanup the configuration we get from the main process.

    Called just after a worker has been forked.
    """

    del server, worker

    prometheus.cleanup()


def child_exit(server: gunicorn.arbiter.Arbiter, worker: gunicorn.workers.base.Worker) -> None:
    """
    Remove the metrics for the exited worker.

    Called just after a worker has been exited, in the master process.
    """

    del server

    multiprocess.mark_process_dead(worker.pid)  # type: ignore [no-untyped-call]

import logging

bind = "0.0.0.0:8000"
workers = 2
timeout = 60
accesslog = "-"
errorlog = "-"


def on_starting(server):
    """Runs once in the gunicorn master: apply the idempotent schema migration."""
    import db
    log = logging.getLogger("gunicorn.error")
    for attempt in range(1, 6):
        try:
            db.run_migrations()
            log.info("migrations applied")
            return
        except Exception as exc:
            log.warning("migration attempt %s failed: %s", attempt, exc)
            import time
            time.sleep(5)
    log.error("migrations did not complete; /health will report 503 until the DB is reachable")

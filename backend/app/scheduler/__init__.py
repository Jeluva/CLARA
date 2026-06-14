"""Scheduled ingestion jobs (APScheduler).

V1 uses a simple in-process BackgroundScheduler; the door is open to Airflow in
V2. Disabled by default (`SCHEDULER_ENABLED=false`) so dev runs and tests don't
mutate data in the background — enable it explicitly to run the cron jobs.
"""

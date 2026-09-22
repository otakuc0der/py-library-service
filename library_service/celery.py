import os

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "library_service.settings"
)

app = Celery("library_service")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.beat_schedule = {
    "check-overdue-borrowings-daily": {
        "task": (
            "notifications.tasks."
            "check_overdue_borrowings"
        ),
        "schedule": crontab(
            hour=9,
            minute=0,
        ),
    },
}

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

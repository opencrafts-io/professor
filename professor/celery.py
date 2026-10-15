import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "professor.settings")

app = Celery("professor")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

"""Celery application configuration for the Imara project.

This module sets up the Celery app, points it at Django's settings,
and discovers task modules in each installed app. The app is imported
in imara/__init__.py so Celery is initialised whenever Django starts.
"""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'imara.settings')

app = Celery('imara')

# Load Celery config from Django settings, using the CELERY_ namespace.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in each installed app's tasks.py.
app.autodiscover_tasks()
import os
import datetime
from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "converter.settings")
app = Celery("converter")
app.config_from_object("django.conf:settings", namespace="CELERY")
# app.conf.update(
#     task_routes={
#         'web_part.tasks.*': {'queue': 'xmlfileprocessing'},
#     },
# )
# app.conf.update(imports=['web_part.tasks'])
app.now = datetime.datetime.now
app.autodiscover_tasks()

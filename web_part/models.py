from django.core.files.storage import FileSystemStorage
from django.db import models


# Create your models here.
class Files(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    fileField = models.FileField(upload_to='', null=True, blank=True, verbose_name="Файл", storage=FileSystemStorage)
    task_id = models.CharField(max_length=255, null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    type = models.PositiveIntegerField()  # 1- excel 2-xml
    status = models.CharField(max_length=255, null=True, blank=True)
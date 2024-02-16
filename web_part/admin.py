from django.contrib import admin

# Register your models here.
from .models import Files


# Register your models here.
class FilesAdmin(admin.ModelAdmin):
    list_display = ['nameFile', 'data', 'idType']


admin.site.register(Files)

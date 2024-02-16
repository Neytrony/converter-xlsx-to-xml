from django.urls import path
from web_part.views import MainPage, upload_excel, create_xml

urlpatterns = [
    path('', MainPage, name='homepage'),
    path('upload_excel/', upload_excel, name='upload_excel'),
    path('create_xml/', create_xml, name='create_xml'),
]
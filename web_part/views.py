from django.shortcuts import render
import datetime
import pandas as pd
from celery.result import AsyncResult
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from web_part.decorators import log_clearMediaDirs
from web_part.tasks import read_excel, Files, create_xml_task


def get_session_message(request):
    try:
        message = request.session.get('message')
        try:
            del request.session['message']
        except KeyError:
            pass
    except BaseException:
        message = 'Error'
    return message


def MainPage(request):
    # Получение списков файлов, которые нужно отобразить(есть в базе данных)
    message = get_session_message(request)
    files = Files.objects.all()
    # excel = pd.read_excel(Files.objects.filter(type=1).first().fileField.path, None)['Рабочие места'].to_html(index=False)
    update_status(files.exclude(status='SUCCESS'))
    context = {'message': message, 'files': files.order_by('-createdAt')}
    return render(request, 'main.html',  context)


@log_clearMediaDirs('excel/')
def upload_excel(request):
    if request.method == 'POST':
        # Загрузка и сохранение файла
        try:
            uploaded_file = request.FILES['myfile']
            fileName = uploaded_file.name
            if fileName.split('.')[-1] in ['xlsx', 'xls']:
                FileSystemStorage().save(f'excel/{fileName}', uploaded_file)
                task = read_excel.delay(fileName)
                task_result = AsyncResult(task.id)
                Files.objects.create(name=fileName, type=1, fileField=f'excel/{fileName}', task_id=task.id, status=task_result.status)
                request.session['message'] = 'Началась обработка файла'
            else:
                request.session['message'] = 'Не верный формат файла'
        except BaseException:
            request.session['message'] = 'Ошибка. Файл не выбран'
    return HttpResponseRedirect('/')


@log_clearMediaDirs('xml/')
def create_xml(request):
    if request.method == 'POST':
        req_dict = dict(request.POST)
        a_filter = {
            'dopl': req_dict['dopl'][0],
            'dop_otpusk': req_dict['dop_otpusk'][0],
            'week': req_dict['week'][0],
            'lpo': req_dict['lpo'][0],
            'milk': req_dict['milk'][0],
            'medosm': req_dict['medosm'][0],
        }
        if any(a_filter.values()) == None:
            request.session['message'] = 'Не все значения заполнены'
            return HttpResponseRedirect('/')

        filename = Files.objects.filter(type=1).order_by('createdAt').last().name
        task = create_xml_task.delay(filename, a_filter)
        task_result = AsyncResult(task.id)
        Files.objects.create(name=f"{filename.split('.')[0]}.zip", type=2, task_id=task.id,
                             status=task_result.status)
        request.session['message'] = 'Началась обработка файла'
    return HttpResponseRedirect('/')
def update_status(files):
    for file in files:
        task_result = AsyncResult(file.task_id)
        file.status = task_result.status
        file.save()

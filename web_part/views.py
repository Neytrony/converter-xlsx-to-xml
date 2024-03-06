import datetime
import pandas as pd
import os
from celery.result import AsyncResult
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse

from web_part.decorators import log_clearMediaDirs
from web_part.tasks import read_excel, Files, create_xml_task
from web_part.forms import LoginForm


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


@login_required(login_url='web_part:login')
def MainPage(request):
    # Получение списков файлов, которые нужно отобразить(есть в базе данных)
    message = get_session_message(request)
    user = request.user
    files = Files.objects.filter(user=user)
    # excel = pd.read_excel(Files.objects.filter(type=1).first().fileField.path, None)['Рабочие места'].to_html(index=False)
    update_status(files.exclude(status='SUCCESS'))
    context = {'msg': message, 'files': files.order_by('-createdAt'), 'user': user}
    return render(request, 'main.html',  context)


@login_required(login_url='web_part:login')
@log_clearMediaDirs('excel/')
def upload_excel(request):
    if request.method == 'POST':
        # Загрузка и сохранение файла
        try:
            uploaded_file = request.FILES['myfile']
            fileName = uploaded_file.name
            if fileName.split('.')[-1] in ['xlsx', 'xls']:
                user = request.user
                username = user.username
                save_path = f'excel/{username}/'
                full_save_path = f'{save_path}/{fileName}'
                if not os.path.exists(f'mediafiles/{save_path}'):
                    # Если путь не существует, создаем папку
                    os.makedirs(f'mediafiles/{save_path}')
                FileSystemStorage().save(full_save_path, uploaded_file)
                task = read_excel.delay(full_save_path)
                task_result = AsyncResult(task.id)
                Files.objects.create(name=fileName, user=user, type=1, fileField=full_save_path, task_id=task.id, status=task_result.status)
                request.session['message'] = 'Началась обработка файла'
            else:
                request.session['message'] = 'Не верный формат файла'
        except BaseException:
            request.session['message'] = 'Ошибка. Файл не выбран'
    return HttpResponseRedirect('/')


@login_required(login_url='web_part:login')
@log_clearMediaDirs('xml/')
def create_xml(request):
    if request.method == 'POST':
        req_dict = dict(request.POST)
        a_filter = {
            'adress': int(req_dict['adress'][0]),
            'analog_rm': int(req_dict['analog_rm'][0]),
        }
        user = request.user
        filename = Files.objects.filter(type=1, user=user).order_by('createdAt').last()
        if filename is not None:
            filename = filename.name
            full_path = f'excel/{user.username}/{filename}'
            task = create_xml_task.delay(full_path, a_filter)
            task_result = AsyncResult(task.id)
            Files.objects.create(name=f"{filename.split('.')[0]}.zip", type=2, task_id=task.id,
                                 status=task_result.status, user=user)
            request.session['message'] = 'Началась обработка файла'
        else:
            request.session['message'] = 'Ошибка. Сначала загрузите excel файл'
    return HttpResponseRedirect('/')


def update_status(files):
    for file in files:
        task_result = AsyncResult(file.task_id)
        file.status = task_result.status
        file.save()


def delete_file(request, filename):
    file = Files.objects.filter(user=request.user, name=filename)
    if file.exists():
        file = file.first()
        try:
            file_path = file.fileField.path
            if os.path.exists(file_path):
                os.remove(file_path)
        except BaseException:
            pass
        file.delete()
        request.session['message'] = 'Файл успешно удален'
    else:
        request.session['message'] = 'Файл не найден'
    return redirect('web_part:homepage')


def LoginPage(request):
    msg = ''
    form_user = LoginForm(request.POST)
    if request.method == "POST":
        if form_user.is_valid():
            username = form_user.cleaned_data.get("username")
            password = form_user.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('web_part:homepage')
            else:
                msg = 'Неверное имя пользователя или пароль'
    context = {'msg': msg, 'form': form_user}
    return render(request, 'login.html', context)

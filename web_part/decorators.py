import os
import datetime
from functools import wraps
import fnmatch
from web_part.models import Files


def log_clearMediaDirs(path):
    def _logs(f):
        @wraps(f)
        def inner(request, *args, **kwargs):
            status, errors = clearMediaDir(f'{path}{request.user.username}/')
            if status:
                return f(request, *args, **kwargs)
            else:
                with open('mediafiles/logs/error.log', 'w') as g:
                    g.write('Вознили ошибки при удалении следующих файлов: \n')
                    for error in errors:
                        g.write(f'{error}\n')
        return inner
    return _logs


def clearMediaDir(path):
    errors = []
    with open('mediafiles/logs/error.log', 'w') as g:
        g.write(f'mediafiles/{path}')
    for r, dirs, files in os.walk(f'mediafiles/{path}'):
        for name in files:
            if fnmatch.fnmatch(name, "*.csv") or fnmatch.fnmatch(name, "*.xls*") or fnmatch.fnmatch(name, "*.zip") or fnmatch.fnmatch(name, "*.xml"):
                p = os.path.join(r, name)
                try:
                    os.remove(p)
                    Files.objects.filter(name=name).delete()
                except BaseException:
                    errors.append(p)
    if len(errors) != 0:
        return False, errors
    else:
        return True, None


def log_user_action():
    def _logs(f):
        @wraps(f)
        def inner(request, *args, **kwargs):
            result = f(request, *args, **kwargs)
            funcs_names = {
                "create_xml": "Запуск задачи создания xml файла",
                "upload_excel": "Запуск задачи загрузки excel файла",
                "delete_file": "Удаление файла",
                "MainPage": "Заход на главную страницу",
                "LoginPage": "Заход на страницу авторизации",
                "create_xml_task": "Задача загрузки xml завершена",
                "read_excel": "Задача загрузки excel завершена",
            }
            log_name = f'{datetime.datetime.now().strftime("%d-%m-%Y")}.log'
            log_path = f'mediafiles/logs/log_action/{log_name}'
            if not os.path.exists("/".join(log_path.split('/')[:-1])):
                os.makedirs("/".join(log_path.split('/')[:-1]))
            if type(request) != str:
                username = request.user.username
            else:
                username = request
            with open(log_path, 'a') as log:
                log.write(f'{datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")}----{username}----{funcs_names[f.__name__]}----{args}\n')
            return result
        return inner
    return _logs

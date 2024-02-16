import os
from functools import wraps
import fnmatch
from web_part.models import Files


def log_clearMediaDirs(path):
    def _logs(f):
        @wraps(f)
        def inner(*args, **kwargs):
            status, errors = clearMediaDir(path)
            if status:
                return f(*args, **kwargs)
            else:
                with open('mediafiles/logs/error.log', 'w') as g:
                    g.write('Вознили ошибки при удалении следующих файлов: \n')
                    for error in errors:
                        g.write(f'{error}\n')
        return inner
    return _logs


def clearMediaDir(path):
    errors = []
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

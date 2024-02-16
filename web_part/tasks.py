from converter.celery import app
import pandas as pd
import zipfile
import datetime
import time
import uuid
import xml.etree.ElementTree as Et
from web_part.models import Files


@app.task
def read_excel(filename):
    full_path = f'mediafiles/excel/{filename}'
    status = check_excel(full_path)


@app.task
def create_xml_task(filename, a_filter):
    filename_excel = f'mediafiles/excel/{filename}'
    write_xml(fill_models_dict(filename_excel, a_filter), filename_excel)



def check_excel(path):
    all_sheets = {
        'Реквизиты': ["Полное наименование организации", "ФИО руководителя", "Электронная почта", "Юр адрес", "ИНН",
                      "ОКПО", "ОКОГУ", "ОКВЭД", "ОКАТО", "КПП", "ОГРН"],
        'Рабочие места': ["Фактический адрес местонахождения", "Номер рабочего места",
                          "Наименование штатной единицы (должность)",
                          "График рабочих/выходных дней: 5/2 или 1/3 или 2/2",
                          "Выполняемая операция и время ее выполнения в % от смены",
                          "Краткое описание выполняемых работ", "Используемое оборудование в работе",
                          "Используемые материалы и сырье", "Название подразделения", "Отдел",
                          "Кол-во человек на рабочем месте"],
        'Сотрудники': ["Номер рабочего места", "Снилс сотрудника", "Фамилия сотрудника", "Имя сотрудника",
                       "Отчество сотрудника", "Пол сотрудника", "Группа инвалидности (при наличии)"],
        'Ранее проведенные СОУТ': ["Номер рабочего места", "Номер прошлой карты СОУТ",
                                   "Класс/подкласс условий труда (по результатам предыдущей АРМ/СОУТ) Если не проводилась, то написать НЕТ",
                                   "Доплата: да/нет", "Доп. отпуск: да/нет", "Сокр. раб. неделя: да/нет",
                                   "Досрочная пенсия: да (по какому списку)/нет", "Молоко: да/нет",
                                   "Медосмотр: да/нет"],
        'Комиссия': ["Фио члена комиссии", "Должность члена комиссии"],
    }
    status = True
    df = pd.read_excel(path, None)
    for key, value in df.items():
        columns = [col.replace('\n', '').replace('  ', ' ').replace('\\', '/') for col in value.columns]
        for a_sheet in all_sheets[key]:
            if a_sheet not in columns:
                status = False
                df = f'Неправильная структура Excel: {key}, {a_sheet}'
                break
        if status is False:
            break
    return status, df


def fill_models_dict(filename, a_filter):
    excel = pd.read_excel(filename, None)
    req = excel['Реквизиты']
    rm = excel['Рабочие места'].sort_values(by='Название подразделения')
    employees = excel['Сотрудники']
    comission = excel['Комиссия']

    models_dict = {
        'struct_org': [],
        'struct_ceh': {},
        'struct_rm': [],
        'sout_rabs': [],
        'person': [],
        'sout_dop_info_fact': [],
    }

    ceh_count = 1
    rm_count = 1
    person_count = 1
    rabs_count = 1
    org_id = 1
    sout_dop_info_fact_count = 1
    ind_req = 0

    org_name = req['Полное наименование организации'][ind_req]

    for ind_rm in rm.index:
        rm_num = rm['Номер рабочего места'][ind_rm]

        empl = employees.copy()
        empl = empl[empl['Номер рабочего места'] == rm_num]
        colwom = 0
        ref_rm = 0
        rm_people_count = 0
        for ind_empl in empl.index:
            rm_people_count += 1
            models_dict['sout_rabs'].append({
                'id': rabs_count,
                'rm_id': rm_num,
                'fio': f'{empl["Фамилия сотрудника"][ind_empl]} {empl["Имя сотрудника"][ind_empl]} {empl["Отчество сотрудника"][ind_empl]}',
                'snils': empl["Снилс сотрудника"][ind_empl],
                'morder': rabs_count,
                'mguid': f'{uuid.uuid4()}'.replace('-', '').upper(),
            })
            if empl["Пол сотрудника"][ind_empl] == 'ж' or empl["Пол сотрудника"][ind_empl] == 'Ж':
                colwom += 1
            if empl["Группа инвалидности (при наличии)"][ind_empl] == 'Да':
                ref_rm += 1
            rabs_count += 1

        a_rm = {
            'id': rm_count,
            'caption': rm['Наименование штатной единицы (должность)'][ind_rm],
            #'caption2': None,
            #'short_code': None,
            'uch_id': 0,
            #'code': None,
            #'codeok': None,
            #'col_anal_rm': None,
            'colrab_rm': rm_people_count,
            #'colrab_all': None,
            'colwom': colwom,
            #'col18': None,
            #'etks': 'Отсутствует',
            #'file': None,
            #'result': -1,
            #'kut': None,
            #'tb': -1,
            #'siz': -1,
            #'dopl': 0,
            'ind_code': rm_num,
            #'deleted': 0,
            'm_order': rm_count,
            'timesmena': rm['График рабочих/\nвыходных дней: \n5\\2 или 1\\3 или 2\\2'][ind_rm],
            #'param': None,
            'mguid': f'{uuid.uuid4()}'.replace('-', '').upper(),
            #'etks_memo': None,
            #'att_num': 0,
            'ref_rm': ref_rm,
            'savedate': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            #'kut1': None,
            #'kut2': None,
            #'file_sout': None,
        }

        models_dict['sout_dop_info_fact'].append({
            'id': sout_dop_info_fact_count,
            'rm_id': rm_count,
            'oborud': rm['Используемое оборудование в работе'][ind_rm],
            'material': rm['Используемые материалы и сырье'][ind_rm],
            'dopl': a_filter['dopl'],
            #'dopl_txt': None,
            'dop_otpusk': a_filter['dop_otpusk'],
            #'dop_otpusk_txt': None,
            'week': a_filter['week'],
            #'week_txt': None,
            'milk': a_filter['milk'],
            #'milk_txt': None,
            #'profpit': 0,
            #'profpit_txt': None,
            'lpo': a_filter['lpo'],
            #'lpo_txt': None,
            'medosm': 1,
            # 'medosm_txt': None,
            # 'operac_t': 'Физические нагрузки',
            # 'operac_n': None,
            # 'pevm': None,
            # 'dop_shum': None,
            # 'dop_vibr': None,
            # 'dop_infr': None,
            # 'dop_ultr': None,
            # 'dop_vibr_loc': None,
            # 'dop_him': None,
            #'dop_apfd': None,
            #'dop_bio': 'Физические нагрузки',
        })
        sout_dop_info_fact_count += 1
        rm_count += 1

        ceh_name = rm['Название подразделения'][ind_rm]
        struct_ceh = models_dict['struct_ceh'].get(ceh_name, None)
        if struct_ceh:
            struct_ceh['struct_rm'].append(a_rm)
        else:
            models_dict['struct_ceh'][ceh_name] = {
                'id': ceh_count,
                'org_id': org_id,
               # 'prg_id': 1,
                'caption': ceh_name,
                #'short_caption': None,
                #'code': None,
                'adr': rm['Фактический адрес местонахождения'][ind_rm],
                #'deleted': 0,
                'm_order': ceh_count,
                #'param': None,
                'mguid': f'{uuid.uuid4()}'.replace('-', '').upper(),
                #'caption2': None,
                'struct_rm': [a_rm]
            }
            ceh_count += 1

    models_dict['struct_org'].append({
        'id': org_id,
        'caption': org_name,
        'short_caption': req['ОГРН'][ind_req],
        #'code': None,
        'kod1': req['ОКПО'][ind_req],
        'kod2': req['ОКОГУ'][ind_req],
        'kod3': req['ОКВЭД'][ind_req],
        'kod4': req['ОКАТО'][ind_req],
        'org': req['ОГРН'][ind_req],
        'adr': req['Юр адрес'][ind_req],
        'm_order': org_id,
        #'deleted': 0,
        #'param': None,
        'inn': req['ИНН'][ind_req],
        'fio': req['ФИО руководителя'][ind_req],
        #'contact': None,
        #'kom_flag': 0,
        'mguid': f'{uuid.uuid4()}'.replace('-', '').upper(),
        #'adr2': None,
        #'need_update': 0,
        'last_update': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        #'caption2': None,
        'struct_ceh': models_dict['struct_ceh'],
    })

    for ind_com in comission.index:
        models_dict['person'].append({
            'id': person_count,
            'org_id': org_id,
            #'ceh_id': 0,
            #'uch_id': 0,
            'proff': comission['Должность члена комиссии'][ind_com],
            'name': comission['Фио члена комиссии'][ind_com],
            #'chlen_type': 1,
        })
        person_count += 1

    return models_dict


def write_xml(models_dict, filename):
    status = True
    now = datetime.datetime.now()
    nsmap = {
        "xmlns:od": "urn:schemas-microsoft-com:officedata",
        'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
        # 'xsi:noNamespaceSchemaLocation': "struct_org.xsd",
        'generated': now.strftime('%Y-%m-%dT%H:%M:%S'),
    }

    for key, value in nsmap.items():
        Et.register_namespace(key, value)

    xml = Et.Element('dataroot', attrib=nsmap)

    struct_org = Et.SubElement(xml, 'struct_org')
    for elem in models_dict['struct_org']:
        for key, value in elem.items():
            if value is not None:
                if key != 'struct_ceh':
                    subxml = Et.SubElement(struct_org, key)
                    subxml.text = f'{value}'
                else:
                    for a_struct, a_struct_data in value.items():
                        struct_ceh = Et.SubElement(struct_org, 'struct_ceh')
                        for struct_key, struct_value in a_struct_data.items():
                            if struct_value is not None:
                                if struct_key != 'struct_rm':
                                    subxml = Et.SubElement(struct_ceh, struct_key)
                                    subxml.text = f'{struct_value}'
                                else:
                                    for a_rm in struct_value:
                                        struct_rm = Et.SubElement(struct_ceh, 'struct_rm')
                                        for rm_key, rm_value in a_rm.items():
                                            if rm_value is not None:
                                                subxml = Et.SubElement(struct_rm, rm_key)
                                                subxml.text = f'{rm_value}'
                                            if rm_key == 'code':
                                                subxml = Et.SubElement(struct_rm, rm_key)
    for pers in models_dict['person']:
        person_ = Et.SubElement(xml, 'person')
        for key, value in pers.items():
            if value is not None:
                subxml = Et.SubElement(person_, key)
                subxml.text = f'{value}'

    for sout_rab in models_dict['sout_rabs']:
        sout_rab_ = Et.SubElement(xml, 'sout_rabs')
        for key, value in sout_rab.items():
            if value is not None:
                subxml = Et.SubElement(sout_rab_, key)
                subxml.text = f'{value}'

    for dop_info_fact in models_dict['sout_dop_info_fact']:
        dop_info_fact_ = Et.SubElement(xml, 'sout_dop_info_fact')
        for key, value in dop_info_fact.items():
            if value is not None:
                subxml = Et.SubElement(dop_info_fact_, key)
                subxml.text = f'{value}'

    tree = Et.ElementTree(xml)
    Et.indent(tree, '  ')
    filename = filename.split('/')[-1].split('.')[0]
    tree.write(f'mediafiles/xml/{filename}.xml', encoding='utf-8', xml_declaration=True, short_empty_elements=False)
    with zipfile.ZipFile(f'mediafiles/xml/{filename}.zip', 'w') as zip_file:
        zip_file.write(f'mediafiles/xml/{filename}.xml', f'{filename}.xml',
                       compress_type=zipfile.ZIP_DEFLATED)

    time.sleep(0.5)

    file = Files.objects.get(name=f'{filename}.zip')
    file.fileField = f'xml/{filename}.zip'
    file.save()
    return status, 'success'

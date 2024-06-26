from converter.celery import app
import pandas as pd
import numpy as np
import os
import zipfile
import datetime
import time
import uuid
import xml.etree.ElementTree as Et
from web_part.models import Files
from web_part.decorators import log_user_action


@app.task
@log_user_action()
def read_excel(request, filename):
    full_path = f'mediafiles/{filename}'
    status = check_excel(full_path)


@app.task
@log_user_action()
def create_xml_task(request, filename, a_filter):
    filename_excel = f'mediafiles/{filename}'
    write_xml(fill_models_dict(filename_excel, a_filter), filename_excel)
    return True



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
                          "Кол-во человек на рабочем месте", "Код ОК", "ЕТКС", "Идентификация", "Аналогия", "Источник вредного фактора"],
        'Сотрудники': ["Номер рабочего места", "Снилс сотрудника", "ФИО сотрудника", "Кол-во женщин на рабочем месте", "Группа инвалидности (при наличии)"],
        'Ранее проведенные СОУТ': ["Номер рабочего места", "Номер прошлой карты СОУТ",
                                   "Класс/подкласс условий труда (по результатам предыдущей АРМ/СОУТ) Если не проводилась, то написать НЕТ",
                                   "Доплата: да/нет", "Доп. отпуск: да/нет", "Сокр. раб. неделя: да/нет",
                                   "Досрочная пенсия: да (по какому списку)/нет", "Молоко: да/нет",
                                   "Медосмотр: да/нет"],
        'Комиссия': ["Фио члена комиссии", "Должность члена комиссии"],
        'Рабочие зоны': ["Номер рабочего места", "Название зоны", "Учёт времени в %", "Факторы"]
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
    excel = pd.read_excel(filename, sheet_name=None, dtype=str)
    req = excel['Реквизиты'].replace(np.nan, '')
    rm = excel['Рабочие места'].replace(np.nan, '')
    employees = excel['Сотрудники'].replace(np.nan, '')
    comission = excel['Комиссия'].replace(np.nan, '')
    sout_dop_info_fact = excel['Ранее проведенные СОУТ'].replace(np.nan, '')
    per_rzona = excel['Рабочие зоны'].replace(np.nan, '')

    models_dict = {
        'struct_org': [],
        'struct_ceh': {},
        'struct_rm': {},
        'sout_rabs': [],
        'person': [],
        'sout_ident': [],
        'struct_uch': {},
        'struct_uch_info': {},
        'sout_dop_info_fact': [],
        'analog_rm': {},
        'per_rzona': {},
        'per_gigfactors': [],
        'per_genfactors': [],
    }

    ceh_count = 1
    rm_count = 1
    person_count = 1
    rabs_count = 1
    indent_count = 1
    uch_count = 1
    org_id = 1
    sout_dop_info_fact_count = 1
    ind_req = 0
    analog_rm_count = 1
    analog_rm_group = 1
    per_rzona_count = 1
    per_gigfactors_count = 1
    per_genfactors_count = 1

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
                'rm_id': rm_count,
                'fio': empl["ФИО сотрудника"][ind_empl],
                'snils': empl["Снилс сотрудника"][ind_empl],
                'morder': rabs_count,
                'mguid': f'{uuid.uuid4()}'.replace('-', '').upper(),
            })
            if empl["Кол-во женщин на рабочем месте"][ind_empl] == '1':
                colwom += 1
            if empl["Группа инвалидности (при наличии)"][ind_empl] == 'Да':
                ref_rm += 1
            rabs_count += 1
        if a_filter['adress'] in [2, 3]:
            short_code = rm['Фактический адрес местонахождения'][ind_rm]
        else:
            short_code = None
        caption = rm['Наименование штатной единицы (должность)'][ind_rm]
        operation = rm['Выполняемая операция и время ее выполнения в % от смены'][ind_rm]
        short_discription = rm['Краткое описание выполняемых работ'][ind_rm]
        oborud = rm['Используемое оборудование в работе'][ind_rm]
        material = rm['Используемые материалы и сырье'][ind_rm]
        timesmena = '480'
        ceh_name = rm['Название подразделения'][ind_rm]
        code_ok = rm['Код ОК'][ind_rm]
        ETKC = rm['ЕТКС'][ind_rm]
        uch_caption = rm['Отдел'][ind_rm]
        unique_analog_str = f'{short_code}{caption}{timesmena}{operation}{short_discription}{oborud}{material}{ceh_name}{uch_caption}{code_ok}{ETKC}'
        a_rm = {
            'id': rm_count,
            'caption': caption,
            #'caption2': None,
            'short_code': short_code,
            'uch_id': 0,
            #'code': None,
            'codeok': rm['Код ОК'][ind_rm],
            #'col_anal_rm': None,
            'colrab_rm': rm_people_count,
            #'colrab_all': None,
            'colwom': colwom,
            #'col18': None,
            'etks': rm['ЕТКС'][ind_rm],
            #'file': None,
            #'result': -1,
            #'kut': None,
            #'tb': -1,
            #'siz': -1,
            #'dopl': 0,
            'ind_code': rm_num,
            #'deleted': 0,
            'm_order': rm_count,
            'timesmena': timesmena,
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
        models_dict['struct_rm'][rm_num] = rm_count

        if a_filter['analog_rm'] not in [3]:
            if a_filter['analog_rm'] in [1]:
                analog_rm = models_dict['analog_rm'].get(unique_analog_str)
                if analog_rm is None:
                    models_dict['analog_rm'][unique_analog_str] = {'analog_rms': [], 'count': 1, 'main': rm_count}
                else:
                    a_count = analog_rm['count']
                    main = analog_rm['main']
                    if a_count == 1:
                        analog_rm['analog_rms'].append({
                            'id': analog_rm_count,
                            'group_id': analog_rm_group,
                            'rm_id': main,
                            'main': main
                        })

                        analog_rm['group_id'] = analog_rm_group
                        analog_rm_count += 1
                        analog_rm_group += 1

                    group_id = analog_rm.get('group_id')
                    analog_rm['analog_rms'].append({
                        'id': analog_rm_count,
                        'group_id': group_id,
                        'rm_id': rm_count,
                        'main': main
                    })

                    analog_rm['count'] = a_count + 1
                    analog_rm_count += 1
            elif a_filter['analog_rm'] in [2]:
                group_id = rm['Аналогия'][ind_rm]
                if group_id != '':
                    analog_rm = models_dict['analog_rm'].get(group_id)
                    if analog_rm is None:
                        models_dict['analog_rm'][group_id] = {'analog_rms': [], 'count': 1, 'main': rm_count}
                    else:
                        a_count = analog_rm['count']
                        main = analog_rm['main']
                        if a_count == 1:
                            analog_rm['analog_rms'].append({
                                'id': analog_rm_count,
                                'group_id': group_id,
                                'rm_id': main,
                                'main': main
                            })
                            analog_rm_count += 1

                        analog_rm['analog_rms'].append({
                            'id': analog_rm_count,
                            'group_id': group_id,
                            'rm_id': rm_count,
                            'main': main
                        })
                        analog_rm_count += 1
                        analog_rm['count'] = a_count + 1

        sout_dop_info_fact_ = sout_dop_info_fact.copy()
        sout_dop_info_fact_ = sout_dop_info_fact_[sout_dop_info_fact_['Номер рабочего места'] == rm_num]
        dopl_ = sout_dop_info_fact_['Доплата: да/нет'].values[0]
        dop_otpusk_ = sout_dop_info_fact_['Доп. отпуск: да/нет'].values[0]
        week_ = sout_dop_info_fact_['Сокр. раб. неделя: да/нет'].values[0]
        milk_ = sout_dop_info_fact_['Досрочная пенсия: да (по какому списку)/нет'].values[0]
        lpo_ = sout_dop_info_fact_['Молоко: да/нет'].values[0]
        medosm_ = sout_dop_info_fact_['Медосмотр: да/нет'].values[0]
        yes_no_dict = {
            'Да': 1,
            'да': 1,
            'Нет': 0,
            'нет': 0,
            '': None
        }

        models_dict['sout_dop_info_fact'].append({
            'id': sout_dop_info_fact_count,
            'rm_id': rm_count,
            'oborud': oborud,
            'material': material,
            'dopl': yes_no_dict[dopl_],
            #'dopl_txt': None,
            'dop_otpusk': yes_no_dict[dop_otpusk_],
            #'dop_otpusk_txt': None,
            'week': yes_no_dict[week_],
            #'week_txt': None,
            'milk': yes_no_dict[milk_],
            #'milk_txt': None,
            #'profpit': 0,
            #'profpit_txt': None,
            'lpo': yes_no_dict[lpo_],
            #'lpo_txt': None,
            'medosm': yes_no_dict[medosm_],
            # 'medosm_txt': None,
            'operac_t': rm['Краткое описание выполняемых работ'][ind_rm],
            # 'operac_n': None,
            # 'pevm': None,
            # 'dop_shum': None,
            # 'dop_vibr': None,
            # 'dop_infr': None,
            # 'dop_ultr': None,
            # 'dop_vibr_loc': None,
            # 'dop_him': None,
            #'dop_apfd': None,
            'dop_bio': rm['Источник вредного фактора'][ind_rm],
        })
        sout_dop_info_fact_count += 1
        sout_indent_kut_ = sout_dop_info_fact_['Класс/подкласс условий труда (по результатам предыдущей АРМ/СОУТ) Если не проводилась, то написать НЕТ'].values[0]
        if sout_indent_kut_ is None:
            sout_indent_kut_ = 'Нет'
        is_ident_dict = {
            '0': '0',
            '1': '1',
            '2': '2',
            '3': '3',
        }
        models_dict['sout_ident'].append({
            'id': indent_count,
            'rm_id': rm_count,
            'is_ident': is_ident_dict.get(rm['Идентификация'][ind_rm], -1),
            'is_travma': '0',
            'is_profzab': '0',
            'kut': sout_indent_kut_,
            'is_rab': '1',
            'rab_descr': None,
            'is_pk6': '0',
            'is_dop1': '0',
            'is_dop2': '0',
            'dop1': '0',
            'dop2': '0~~~~~~~~~~',
        })

        tajest = rm['Тяжесть труда'][ind_rm]
        if tajest in ['Да', 'ДА', 'да', '1']:
            models_dict['per_genfactors'].append({
                'id': per_genfactors_count,
                'tabl4_id': rm_count,
                'caption': 'Тяжесть труда',
                'time': 0,
                'time2': 0,
                'factor_id': 13,
            })
            per_genfactors_count += 1

        napriajonost = rm['Напряженность труда'][ind_rm]
        if napriajonost in ['Да', 'ДА', 'да', '1']:
            models_dict['per_genfactors'].append({
                'id': per_genfactors_count,
                'tabl4_id': rm_count,
                'caption': 'Напряженность труда',
                'time': 0,
                'time2': 0,
                'factor_id': 14,
            })
            per_genfactors_count += 1

        indent_count += 1
        rm_count += 1


        struct_ceh = models_dict['struct_ceh'].get(ceh_name, None)
        if struct_ceh:
            uch_ceh_id = struct_ceh['id']
            a_rm['ceh_id'] = struct_ceh['id']
            struct_ceh['struct_rm'].append(a_rm)
        else:
            a_rm['ceh_id'] = ceh_count
            if a_filter['adress'] in [1, 3]:
                adr = rm['Фактический адрес местонахождения'][ind_rm]
            else:
                adr = None
            models_dict['struct_ceh'][ceh_name] = {
                'id': ceh_count,
                'org_id': org_id,
               # 'prg_id': 1,
                'caption': ceh_name,
                #'short_caption': None,
                #'code': None,
                'adr': adr,
                #'deleted': 0,
                'm_order': ceh_count,
                #'param': None,
                'mguid': f'{uuid.uuid4()}'.replace('-', '').upper(),
                #'caption2': None,
                'struct_rm': [a_rm]
            }
            uch_ceh_id = ceh_count
            ceh_count += 1

        uch_caption = rm['Отдел'][ind_rm]
        if uch_caption != '':
            if a_filter['adress'] in [1, 3]:
                adr = rm['Фактический адрес местонахождения'][ind_rm]
            else:
                adr = None

            # par_id = 0
            # nod_id = 0
            # uch_caption_split = uch_caption.split('\\')
            struct_uch_ = models_dict['struct_uch'].get(uch_ceh_id, None)
            # Если нет подразделения(ceh), то создаем пустой славарь для него
            if struct_uch_ is None:
                models_dict['struct_uch'][uch_ceh_id] = {}
                struct_uch_ = models_dict['struct_uch'][uch_ceh_id]

            struct_uch_, uch_count = uch_creation(uch_caption, struct_uch_, uch_count, uch_ceh_id, adr, 0, 0)
            rm_uch_id = uch_count - 1
            models_dict['struct_ceh'][ceh_name]['struct_rm'][-1]['uch_id'] = rm_uch_id

    models_dict['struct_org'].append({
        'id': org_id,
        'caption': req['Полное наименование организации'][ind_req],
        'short_caption': req['ОГРН'][ind_req],
        #'code': None,
        'kod1': req['ОКПО'][ind_req],
        'kod2': req['ОКОГУ'][ind_req],
        'kod3': f"{req['ОКВЭД'][ind_req]}",
        'kod4': req['ОКАТО'][ind_req],
        'org': req['Полное наименование организации'][ind_req],
        'adr': req['Юр адрес'][ind_req],
        'm_order': org_id,
        #'deleted': 0,
        #'param': None,
        'inn': req['ИНН'][ind_req],
        'fio': req['ФИО руководителя'][ind_req],
        'contact': req['Электронная почта'][ind_req],
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
            'chlen_type': 1,
        })
        person_count += 1
    models_dict['person'][0]['chlen_type'] = 0

    for ind_per in per_rzona.index:
        pzone = models_dict['per_rzona']
        pz_tabl4_id = models_dict['struct_rm'][per_rzona['Номер рабочего места'][ind_per]]
        pz_caption = per_rzona['Название зоны'][ind_per]
        pz = pzone.get(f'{pz_tabl4_id}_{pz_caption}')
        if pz is None:
            pzone[f'{pz_tabl4_id}_{pz_caption}'] = {
                "id": per_rzona_count,
                "tabl4_id": pz_tabl4_id,
                "caption": pz_caption,
                "time": per_rzona['Учёт времени в %'][ind_per],
                "morder": 0,
                "mintime": 0,
            }
            rzona_id = per_rzona_count
            per_rzona_count += 1
        else:
            rzona_id = pz['id']
        gigfactors = per_rzona['Факторы'][ind_per].replace(' ', '').split(',')
        gigfactor_dict = {
            'ХИМ': ('Химический', 1),
            'БИО': ('Биологический', 2),
            'АПФД': ('Аэрозоли ПФД', 3),
            'ШУМ': ('Шум', 4),
            'ИНФР': ('Инфразвук', 5),
            'УЗ': ('Ультразвук', 6),
            'ВИО': ('Вибрация общая', 7),
            'ВИЛ': ('Вибрация локальная', 8),
            'ЭМП': ('ЭМП', 9),
            'РАД': ('Ионизирующие излучения', 10),
            'МИКР': ('Микроклимат', 11),
            'ОСВ': ('Освещение', 12),
            'УФИ': ('Ультрафиолетовое излучение', 26),
            'ЛИ': ('Лазерное излучение', 41),
        }

        for gigfactor in gigfactors:
            if gigfactor != '':
                gigfactor = gigfactor.upper()
                models_dict['per_gigfactors'].append({
                    "id": per_gigfactors_count,
                    "rzona_id": rzona_id,
                    "factor_id": gigfactor_dict[gigfactor][1],
                    "caption": gigfactor_dict[gigfactor][0],
                    "proctime": 0,
                    "mintime": 0,
                })
                per_gigfactors_count += 1

    return models_dict


def uch_creation(uch_caption, models_dict_uch, uch_count, uch_ceh_id, adr, par_id, nod_id):
    uch_caption_split = uch_caption.split('\\')
    uch_caption_first = uch_caption_split[0]
    sub_uch = '\\'.join(uch_caption_split[1::])
    if models_dict_uch.get(uch_caption_first) is None:
        models_dict_uch[uch_caption_first] = {
            'uch': {
                'id': uch_count,
                'par_id': par_id,
                'ceh_id': uch_ceh_id,
                'node_level': nod_id,
                'caption': uch_caption_first,
                'code': None,
                'adr': adr,
                'deleted': '0',
                'm_order': uch_count,
                'mguid': f'{uuid.uuid4()}'.replace('-', '').upper(),
            },
            'sub': {}
        }
        uch_count += 1
    if sub_uch:
        a_dict, uch_count = uch_creation(sub_uch, models_dict_uch[uch_caption_first]['sub'], uch_count, uch_ceh_id, adr, models_dict_uch[uch_caption_first]['uch']['id'], 1)
    return models_dict_uch, uch_count


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

    for sout_indent in models_dict['sout_ident']:
        sout_indent_ = Et.SubElement(xml, 'sout_ident')
        for key, value in sout_indent.items():
            if value is not None:
                subxml = Et.SubElement(sout_indent_, key)
                subxml.text = f'{value}'


    for struct_uch in models_dict['struct_uch'].values():
        uch_write(struct_uch, xml)
    # for struct_uch_key, struct_uch_value in models_dict['struct_uch'].items():
    #     for key, value in struct_uch_value.items():
    #         struct_uch_ = Et.SubElement(xml, 'struct_uch')
    #         for key_, value_ in value.items():
    #             if value_ is not None:
    #                 subxml = Et.SubElement(struct_uch_, key_)
    #                 subxml.text = f'{value_}'

    for analog_rm_value in models_dict['analog_rm'].values():
        if analog_rm_value['count'] > 1:
            for analog_rm in analog_rm_value['analog_rms']:
                    analog_rm_ = Et.SubElement(xml, 'anal_group')
                    for key_, value_ in analog_rm.items():
                        if value_ is not None:
                            subxml = Et.SubElement(analog_rm_, key_)
                            subxml.text = f'{value_}'

    for per_rzona in models_dict['per_rzona'].values():
        per_rzona_ = Et.SubElement(xml, 'per_rzona')
        for key_, value_ in per_rzona.items():
            if value_ is not None:
                subxml = Et.SubElement(per_rzona_, key_)
                subxml.text = f'{value_}'

    for per_gigfactors in models_dict['per_gigfactors']:
        per_gigfactors_ = Et.SubElement(xml, 'per_gigfactors')
        for key_, value_ in per_gigfactors.items():
            if value_ is not None:
                subxml = Et.SubElement(per_gigfactors_, key_)
                subxml.text = f'{value_}'

    for per_genfactor in models_dict['per_genfactors']:
        per_genfactor_ = Et.SubElement(xml, 'per_genfactors')
        for key, value in per_genfactor.items():
            if value is not None:
                subxml = Et.SubElement(per_genfactor_, key)
                subxml.text = f'{value}'

    tree = Et.ElementTree(xml)
    Et.indent(tree, '  ')
    file_dir, filename = filename.split('/')[-2::]
    filename = filename.split('.')[0]
    save_path = f'mediafiles/xml/{file_dir}/'
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    tree.write(f'{save_path}{filename}.xml', encoding='utf-8', xml_declaration=True, short_empty_elements=False)
    with zipfile.ZipFile(f'{save_path}{filename}.zip', 'w') as zip_file:
        zip_file.write(f'{save_path}{filename}.xml', f'{filename}.xml',
                       compress_type=zipfile.ZIP_DEFLATED)

    time.sleep(0.5)

    file = Files.objects.get(name=f'{filename}.zip')
    file.fileField = f'xml/{file_dir}/{filename}.zip'
    file.save()
    return status, 'success'


def uch_write(struct_uch, xml):
    for key, value in struct_uch.items():
        for key_, value_ in value.items():
            if key_ == 'uch':
                struct_uch_ = Et.SubElement(xml, 'struct_uch')
                for key__, value__ in value_.items():
                    if value__ is not None:
                        subxml = Et.SubElement(struct_uch_, key__)
                        subxml.text = f'{value__}'
            elif key_ == 'sub':
                uch_write(value_, xml)

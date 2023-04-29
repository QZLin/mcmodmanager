import enum
import json
import logging as log
import os
import re
import shutil
import zipfile
from enum import Enum
from os.path import join, exists, islink
from typing import *

import yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from click import echo

import datautils as du
import str_version

j = join

root_dir = os.path.abspath(os.curdir)
mods_available = join(root_dir, 'mods-available')
mods_enabled = root_dir

dir_metadata = join(root_dir, 'metadata')
dir_conf = join(root_dir, 'conf')
dir_runvar = join(root_dir, 'var')
dir_rules_d = join(dir_conf, 'rules.d')
dir_mixin_d = join(dir_conf, 'mixin.d')

#
file_metadata_cache = j(dir_metadata, 'metadata.json')
file_mapping = j(dir_conf, 'maps.json')

init_required_dirs = (mods_available, mods_enabled,
                      dir_conf, dir_metadata, dir_runvar,
                      dir_rules_d, dir_mixin_d)


class ConfigType:
    YAML = enum.auto()
    JSON = enum.auto()


load_order = [ConfigType.YAML, ConfigType.JSON]
suffixes = ['yaml', 'yml', 'json']


def config(path, type_):
    result = None
    if type_ == ConfigType.YAML:
        with open(path) as f:
            result = yaml.load(f, Loader)
            # if type(r) == list:
    elif type_ == ConfigType.JSON:
        with open(path) as f:
            result = json.load(f)
    return result


def config_suffix(full_path, suffix):
    match suffix:
        case 'yaml' | 'yml':
            return config(full_path, ConfigType.YAML)
        case 'json':
            return config(full_path, ConfigType.JSON)


def cfg_all_type(path_key):
    cfgs = []
    for x in suffixes:
        if not exists(full_path := f'{path_key}.{x}'):
            continue
        if (r := config_suffix(full_path, x)) is not None:
            cfgs.extend(r)

    return cfgs


def get_cfgs(path):
    result = []

    result.extend(cfg_all_type(path))

    if not os.path.isdir(cfg_dir := path + '.d'):
        return result
    files = [(x, ext, ext_i) for x in next(os.walk(cfg_dir))[2]
             if (ext := x[(ext_i := x.rfind('.')) + 1:]) in suffixes]
    for x in files:
        name, ext, ext_i = x
        result.extend(config_suffix(join(cfg_dir, name), ext))
    return result


__dir_heap = []


def push_d(path):
    global __dir_heap
    __dir_heap.append(os.curdir)
    os.chdir(path)


def pop_d():
    global __dir_heap
    path = __dir_heap.pop()
    os.chdir(path)


def nerd_dict_get(dict_: dict, *keys, obj=None):
    if obj is None:
        obj = []
    next_obj = dict_
    for i, key in enumerate(keys):
        if key in next_obj.keys():
            next_obj = next_obj[key]
            continue
        if i == len(keys) - 1:
            next_obj[key] = obj
            next_obj = obj
        else:
            next_obj[key] = {}
            next_obj = next_obj[key]
    return next_obj


def nerd_get(obj: dict, *pairs: Tuple[Any, Any]):
    next_obj = obj
    for pair in pairs:
        key, value = pair
        if key in obj.keys():
            next_obj = obj[key]
        else:
            next_obj[key] = value
    return next_obj


def get_mixin():
    return get_cfgs(join(dir_conf, 'mixin'))


def gen_metadata(library_dir=None, output_dir=None):
    if library_dir is None:
        library_dir = mods_available
    if output_dir is None:
        output_dir = dir_metadata
    # clean cached metadata
    cached_files = (x for x in next(os.walk(dir_metadata))[2] if x.endswith('.json'))
    for x in cached_files:
        os.remove(j(dir_metadata, x))

    files = next(os.walk(library_dir))[2]
    mixin_data = get_mixin()
    mixin_data_files = [x['file'] for x in mixin_data]
    mixin_data = {x.pop('file'): x for x in mixin_data}

    jars = []
    for file in files:
        if file in mixin_data_files:
            data = mixin_data[file]
            with open(join(output_dir, f'{file}.json'), 'w') as f:
                json.dump(data, f)
                log.info(f'mixin {file} {data}')
            jars.append(file)
            continue
        try:
            archive_file = zipfile.ZipFile(join(library_dir, file))
            file_info = archive_file.read('fabric.mod.json')
        except zipfile.BadZipFile:
            log.info(f'NotZip {file}')
            continue
        except KeyError:
            log.warning(f'NoInfo {file}')
            continue
        with open(join(output_dir, f'{file}.json'), 'wb') as f:
            f.write(file_info)
            jars.append(file)
    return jars


def read_metadata(dir_=dir_metadata, cache=None, rebuild=False):
    if cache is None:
        cache = file_metadata_cache
    if (not rebuild) and exists(cache):
        with open(cache) as f:
            return json.load(f)

    metadata = {}
    files = (x for x in next(os.walk(dir_))[2] if x.endswith('.json'))
    # for root, dirs, filenames in os.walk(dir_):
    #     files.extend([x for x in filenames if x.lower().endswith('.json')])
    #     break
    for x in files:
        with open(join(dir_, x), encoding='utf-8') as f:
            content = json.load(f)
            metadata[x] = content
    with open(cache, 'w') as f:
        json.dump(metadata, f)

    return metadata


class RuleMode(Enum):
    APPEND = enum.auto()
    EXCEPT = enum.auto()


def read_rules(rule_file=join(dir_conf, 'rules.json')) -> dict:
    if not exists(rule_file):
        write_rules({}, rule_file)
        return {}
    with open(rule_file) as f:
        return json.load(f)


def write_rules(rule: dict, rule_file=join(dir_conf, 'rules.json')):
    with open(rule_file, 'w') as f:
        json.dump(rule, f, indent=2)


def get_lib_info(metadata: dict):
    versions_data = {}
    for filename, data in metadata.items():
        name = filename.removesuffix('.json')
        if 'id' not in data.keys():
            log.warning(f'id not found in {data.keys()}')
            continue
        if data['id'] not in versions_data.keys():
            versions_data[data['id']] = []
        versions_data[data['id']].append(name)
    return versions_data


def init_dir():
    for dir_ in init_required_dirs:
        if not exists(dir_):
            os.makedirs(dir_)
        elif os.path.isdir(dir_):
            log.debug(f'skip existed dir {dir_}')
        else:
            log.error(f'file {dir_} existed, can\'t create dir')


def get_version(mod_id, index=None, auto=False):
    versions_data = list_mods()
    if mod_id not in versions_data.keys():
        raise RuntimeError(f'mod `{mod_id}` not found')
    versions = versions_data[mod_id]
    str_version.sort_versions(versions)
    if index is not None and index < len(versions):
        return (versions[index],)
    elif auto:
        return (versions[0],)
    return versions


def enable(file, id_, mapping: du.Data = None):
    if mapping is None:
        mapping = du.Data(file_mapping)
    link_name = f'{id_}.jar'
    if exists(link_name) or islink(link_name):
        os.remove(link_name)
        log.info(f'Existed {link_name} Removed')
    os.symlink(join(mods_available, file), join(mods_enabled, link_name))
    mapping[link_name] = file
    echo(f'[Enable]: {link_name} -> {file}')


def enable_auto(mod_id, versions_data=None, mapping: du.Data = None):
    if versions_data is None:
        versions_data = list_mods()
    # if mod_id not in versions_data.keys():
    #     raise RuntimeError(f'{mod_id} not found')
    versions = get_version(mod_id)
    rules = read_rules()
    blocked = nerd_get(rules, ('mods', {}), (mod_id, {}), ('block', []))

    for x in blocked:
        if x not in versions:
            continue
        versions.remove(x)
        log.info(f'[Skip blocked]: {x}')
    str_version.sort_versions(versions)
    mod_file = versions[0] if len(versions) > 0 else None
    if mod_file is None:
        log.error(f'No available mod of {mod_id} except block list {blocked}')
        return

    enable(mod_file, mod_id, mapping)


def disable(file):
    if exists(file) or islink(file):
        os.remove(file)
        log.info(f'[Unlink]: {file}')
    else:
        log.warning(f'NotFound {file}')


def list_mods():
    meta = read_metadata(dir_metadata)
    versions_data = get_lib_info(meta)
    return versions_data


def ls_mods(path=None):
    if path is None:
        path = os.curdir
    jars = [x for x in next(os.walk(path))[2] if x.endswith('.jar')]
    return jars


def readlink(path):
    os.path.relpath(path)


def apply(ruleset, pre_add_all=True):
    versions_data = list_mods()
    ids = [x for x in versions_data.keys()] if pre_add_all else []
    clean(os.curdir)
    for rule in ruleset:
        mode = rule['mode']
        rules = rule['rule']
        if mode == RuleMode.APPEND:
            for x in rules:
                if x not in ids:
                    ids.append(x)
        elif mode == RuleMode.EXCEPT:
            for x in rules:
                if x in ids:
                    ids.remove(x)
    mapping = du.Data('maps.json', True)
    for x in ids:
        enable_auto(x, versions_data, mapping)
    mapping.write()
    return ids


def clean(path):
    push_d(path)
    files = []
    for root, dirs, filenames in os.walk(path):
        files.extend(filenames)
        break
    mapping = get_map()
    for x in files:
        if islink(x):
            os.unlink(x)
            mapping.pop(x)
            echo(f'[Unlink]: {x}')
        else:
            log.warning(f'file {x} not symbolic link')
    mapping.write()
    pop_d()


def select(pattern):
    versions_data = list_mods()
    return [x for x in versions_data.keys() if re.match(pattern, x)]


def is_disabled(name):
    return re.match(r'(.*\.jar)(\.(old|disabled))$', name)
    # example.jar.disabled
    # ('example.jar', '.disabled', 'disabled')


def archive(path: str) -> Tuple[List[str], List[str]]:
    files: List[str] = next(os.walk(path))[2]  # ls -File

    push_d(path)
    unlink_list = []
    archive_list = []

    mapping = get_map()
    for file_name in files:
        # old link
        if islink(file_name):
            if is_disabled(file_name):
                unlink_list.append(file_name)
                os.unlink(file_name)
                mapping.pop(file_name)
                log.debug(f'[unlink] {file_name}')
        # unknown file
        elif r := is_disabled(file_name):
            restored_name = file_name.removesuffix(r.groups()[1])
            if not os.path.exists(target := j(mods_available, restored_name)):
                archive_list.append(file_name)
                shutil.move(file_name, target)
                mapping.pop(file_name)
            else:
                log.error(f'Conflict Name {file_name} -> {restored_name}')
        # new file
        elif re.match(r'.*\.jar', file_name):
            archive_list.append(file_name)
            shutil.move(file_name, join(mods_available, file_name))
            mapping.pop(file_name)
            log.info(f'[move] {file_name} to [mods_available]')
    mapping.write()

    gen_metadata(mods_available, dir_metadata)
    read_metadata(dir_metadata, rebuild=True)
    pop_d()
    return unlink_list, archive_list


def get_map():
    return du.Data(file_mapping, delay_write=True)


def prune():
    pass

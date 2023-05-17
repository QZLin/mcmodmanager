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
file_rule = j(dir_conf, 'rules.json')

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


pattern_cfg = re.compile(r'.*\b(.+)\.(yaml|yml|json)')


def mload(path, suffix_type=None) -> dict:
    if suffix_type is None:
        r = re.match(pattern_cfg, path)
        suffix_type = r.groups()[1]
    with open(path) as f:
        match suffix_type:
            case 'yaml' | 'yml':
                return yaml.load(f, Loader)
            case 'json':
                return json.load(f)


def mix_cfg(config_files: List[str]) -> dict:
    result = {}
    for x in config_files:
        result.update(mload(x))
    return result


def all_cfg(path, name=None) -> List[str]:
    result = []
    for file in next(os.walk(path))[2]:
        if (r := re.match(pattern_cfg, file)) is None:
            continue
        if name is None or r.groups()[0] == name:
            result.append(j(path, file))
    return result


def get_cfgs(directory, name) -> dict:
    """
    get named cfg and all cfg in {name}.d
    :param name:
    :param directory:
    :return:
    """
    result = {}
    result.update(mix_cfg(all_cfg(directory, name)))
    if os.path.isdir(d := f'{directory}/{name}.d'):
        result.update(mix_cfg(all_cfg(d)))
    return result


__dir_heap = []


def push_d(path):
    global __dir_heap
    __dir_heap.append(os.curdir)
    os.chdir(path)


def pop_d():
    global __dir_heap
    os.chdir(__dir_heap.pop())


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
    return get_cfgs(dir_conf, 'mixin')


def get_metadata(file) -> bytes | None:
    try:
        archive_file = zipfile.ZipFile(file)
        file_info = archive_file.read('fabric.mod.json')
        return file_info
    except zipfile.BadZipFile:
        log.warning(f'Not a zip {file}')
        return
    except KeyError:
        log.warning(f'fabric.mod.json not found {file}')
        return


def extract_metadata(library_dir=mods_available, output_dir=dir_metadata) -> List[str]:
    # clean cached metadata
    cached_files = (x for x in next(os.walk(dir_metadata))[2] if x.endswith('.json'))
    for x in cached_files:
        os.remove(j(dir_metadata, x))

    files = next(os.walk(library_dir))[2]
    mixin_data = get_mixin()['metadata']
    mixin_data_files = [x['file'] for x in mixin_data]
    mixin_data = {x.pop('file'): x for x in mixin_data}

    jars = []
    for file in files:
        file_o = j(output_dir, f'{file}.json')
        if file in mixin_data_files:
            data = mixin_data[file]
            with open(file_o, 'w') as f:
                json.dump(data, f)
                log.info(f'mixin {file} {data}')
            jars.append(file)
            continue
        md = get_metadata(j(library_dir, file))
        if md is None:
            continue
        with open(file_o, 'wb') as f:
            f.write(md)
            jars.append(file)
    return jars


def parse_metadata(dir_=dir_metadata, cache=file_metadata_cache, rebuild=False) -> Dict[str, Any]:
    if (not rebuild) and exists(cache):
        with open(cache) as f:
            return json.load(f)

    metadata = {}
    files = (x for x in next(os.walk(dir_))[2] if x.endswith('.json'))
    for x in files:
        with open(j(dir_, x), encoding='utf-8') as f:
            content = json.load(f)
            metadata[x] = content
    with open(cache, 'w') as f:
        json.dump(metadata, f, indent=2)

    return metadata


def get_mod_versions_all(metadata: dict) -> Dict[str, List[str]]:
    versions_data = {}
    for filename, data in metadata.items():
        name = filename.removesuffix('.json')
        if 'id' not in data.keys():
            log.warning(f'id not found in #{filename}')
            continue
        mod_id = data['id']
        if mod_id not in versions_data.keys():
            versions_data[mod_id] = []
        versions_data[mod_id].append(name)
    return versions_data


def get_version(mod_id, index=None, auto=False, versions_data=None) -> Tuple[str] | List[str]:
    if versions_data is None:
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


def init_dir():
    for dir_ in init_required_dirs:
        if not exists(dir_):
            os.makedirs(dir_)
        elif os.path.isdir(dir_):
            log.debug(f'skip existed dir {dir_}')
        else:
            log.error(f'file {dir_} existed, can\'t create dir')


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
    versions = get_version(mod_id, versions_data)
    rules = read_rules()
    blocked = nerd_get(rules, ('mods', {}), (mod_id, {}), ('block', []))

    for x in blocked:
        if x not in versions:
            continue
        versions.remove(x)
        log.info(f'[Skip blocked]: {x}')
    str_version.sort_versions(versions)
    if len(versions) < 1:
        log.error(f'No available mod of {mod_id} except block list {blocked}')
        return

    enable(versions[0], mod_id, mapping)


def disable(file):
    if exists(file) or islink(file):
        os.remove(file)
        echo(f'[Unlink]: {file}')
    else:
        log.warning(f'NotFound {file}')


def list_mods():
    meta = parse_metadata(dir_metadata)
    all_jar_mod = get_mod_versions_all(meta)
    return all_jar_mod


def ls_mods(path=None):
    if path is None:
        path = os.curdir
    jars = [x for x in next(os.walk(path))[2] if x.endswith('.jar')]
    return jars


# def readlink(path):
#     os.path.relpath(path)


def apply(ruleset, pre_add_all=True):
    versions_data = list_mods()
    ids = [x for x in versions_data.keys()] if pre_add_all else []
    clean(os.curdir)
    for rule in ruleset:
        mode = rule['mode']
        rules = rule['rule']
        if mode == RuleMode.APPEND:
            ids.extend(x for x in rules if x not in ids)
        elif mode == RuleMode.EXCEPT:
            for x in rules:
                if x not in ids:
                    continue
                ids.remove(x)
    mapping = get_map()
    for x in ids:
        enable_auto(x, versions_data, mapping)
    mapping.write()
    return ids


def clean(path):
    push_d(path)
    files = next(os.walk(path))[2]
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


pattern_disabled = re.compile(r'(.*\.jar)(\.(old|disabled))$')
pattern_jar = re.compile(r'(.*)\.jar$')


def archive(path: str) -> Tuple[List[str], List[str]]:
    files: List[str] = next(os.walk(path))[2]  # ls -File

    push_d(path)
    unlink_list = []
    archive_list = []

    mapping = get_map()
    for file_name in files:
        # old link
        if islink(file_name):
            if re.match(pattern_disabled, file_name):
                unlink_list.append(file_name)
                os.unlink(file_name)
                mapping.pop(file_name)
                log.debug(f'unlink {file_name}')
        # unknown file
        elif r := re.match(pattern_disabled, file_name):
            restored_name = file_name.removesuffix(r.groups()[1])
            if not os.path.exists(target := j(mods_available, restored_name)):
                archive_list.append(file_name)
                shutil.move(file_name, target)
                mapping.pop(file_name)
            else:
                log.error(f'Conflict Name {file_name} -> {restored_name}')
        # new file
        elif re.match(pattern_jar, file_name):
            archive_list.append(file_name)
            shutil.move(file_name, join(mods_available, file_name))
            mapping.pop(file_name)
            log.info(f'move {file_name} to [mods_available]')
    mapping.write()

    extract_metadata(mods_available, dir_metadata)
    parse_metadata(dir_metadata, rebuild=True)
    pop_d()
    return unlink_list, archive_list


def get_map():
    return du.Data(file_mapping, delay_write=True)


def prune():
    pass


class RuleMode(Enum):
    APPEND = enum.auto()
    EXCEPT = enum.auto()


def write_rules(rule: dict, rule_file=file_rule):
    with open(rule_file, 'w') as f:
        json.dump(rule, f, indent=2)


def read_rules(rule_file=file_rule) -> dict:
    if not exists(rule_file):
        write_rules({}, rule_file)
        return {}
    with open(rule_file) as f:
        return json.load(f)

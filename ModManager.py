import enum
import json
import logging
import os
import re
import shutil
import zipfile
from enum import Enum
from os import PathLike
from os.path import join, exists, islink, relpath, abspath, normpath
from pathlib import PurePath
from typing import Dict, List, Any, Tuple

import yaml
from click import echo

import DataUtil
import StrVersion
from DataUtil import ModFileInfo
from MixConfig import Config
from RuntimeConfig import get_env

try:
    from yaml import CLoader as YamlLoader, CDumper as YamlDumper
except ImportError:
    from yaml import Loader as YamlLoader, Dumper as YamlDumper

j = join
ENCODING = 'utf-8'

_root = os.getcwd()
_env = None
_env_path = PurePath(_root, 'mcm.yaml')
if exists(_env_path):
    with open(_env_path) as _env_file:
        _env = yaml.load(_env_file, YamlLoader)
env_dir, env_file = get_env(_root, _env)
__dir_heap = []


def push_d(path):
    global __dir_heap
    __dir_heap.append(os.curdir)
    os.chdir(path)


def pop_d():
    global __dir_heap
    os.chdir(__dir_heap.pop())


def nerd_dict_get(dict_: dict, *keys, fallback=None):
    if fallback is None:
        fallback = []
    next_obj = dict_
    for i, key in enumerate(keys):
        if key in next_obj.keys():
            next_obj = next_obj[key]
            continue
        if i == len(keys) - 1:
            next_obj[key] = fallback
            next_obj = fallback
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


def __zip_has(zip_, path):
    r = next((x for x in zip_.filelist if x.filename == path), None)
    return r is not None


def mod_metadata(file) -> Tuple[str | None, str | None]:
    try:
        archive_file = zipfile.ZipFile(file)
    except zipfile.BadZipFile:
        logging.warning(f'not a zip {file}')
        return None, None
    if __zip_has(archive_file, 'fabric.mod.json'):
        mod_type = 'fabric'
        content = archive_file.read('fabric.mod.json').decode()
    elif __zip_has(archive_file, 'quilt.mod.json'):
        mod_type = 'quilt'
        file_orig = json.loads(archive_file.read('quilt.mod.json'))
        file_orig.update(file_orig['quilt_loader'])
        content = json.dumps(file_orig)
    else:
        logging.error(f'unknown zip mod {file}')
        return None, None
    return content, mod_type


def mixin(filename, mixin_data=None):
    if mixin_data is None:
        mixin_data = Config.mixed_config(env_dir.conf, 'mixin.d', 'mixin')['metadata']
    r = [x for x in mixin_data if x['file'] == filename]
    if len(r) == 1:
        data = r[0]
        logging.info(f'mixin {filename} {data}')
        return json.dumps(data)
    return


# def get_files(path):
#     pass


def extract_metadata(library_dir=None, output_dir=None) -> List[PathLike]:
    """
    extract all metadata that already at library folder
    :param library_dir:
    :param output_dir:
    :return:
    """
    library_dir = env_dir.mods_available if library_dir is None else library_dir
    output_dir = env_dir.metadata if output_dir is None else output_dir
    # clean cached metadata
    cached_files = (x for x in next(os.walk(env_dir.metadata))[2] if x.endswith('.json'))
    for x in cached_files:
        os.remove(j(env_dir.metadata, x))

    mixin_data = Config.mixed_config(env_dir.conf, 'mixin.d', 'mixin')['metadata']
    mixin_data_files = [x['file'] for x in mixin_data]
    # mixin_data = {x.pop('file'): x for x in mixin_data}

    jars = []
    for filename in next(os.walk(library_dir))[2]:
        file = PurePath(library_dir, filename)
        file_cache = PurePath(output_dir, f'{filename}.json', )
        if file.name in mixin_data_files:
            data = mixin(filename, mixin_data)
        else:
            data, type_ = mod_metadata(file)
        if data is None:
            continue
        with open(file_cache, 'w', encoding=ENCODING) as f:
            f.write(data)
        jars.append(file)
    return jars


def meta_cache(cache_file=None) -> dict:
    if cache_file is None:
        cache_file = env_file.metadata_cache
    if not exists(cache_file):
        return {}
    try:
        with open(cache_file, 'r') as f:
            result = json.load(f)
        return {PurePath(env_dir.metadata, k): v for k, v in result.items()}
    except json.JSONDecodeError:
        return {}


def parse_metadata(dir_=None, file_all_cache=None, rebuild_=False) -> Dict[PurePath, Any]:
    if dir_ is None:
        dir_ = env_dir.metadata
    if file_all_cache is None:
        file_all_cache = env_file.metadata_cache

    if not rebuild_:
        return meta_cache(file_all_cache)

    metadata = {}
    all_cache = (x for x in next(os.walk(dir_))[2] if x.endswith('.json'))
    for name in all_cache:
        cache_file = PurePath(dir_, name)
        with open(cache_file, encoding=ENCODING) as f:
            content = json.load(f)
            metadata[cache_file.name] = content
    with open(file_all_cache, 'w') as f:
        json.dump(metadata, f, indent=2)

    return {PurePath(env_dir.metadata, k): v for k, v in metadata.items()}


def rebuild():
    extract_metadata()
    parse_metadata(rebuild_=True)


def get_all(all_metadata: dict[PurePath, dict]) -> Dict[str, List[DataUtil.ModFileInfo]]:
    versions_data = {}
    for file, metadata in all_metadata.items():
        if 'id' not in metadata.keys():
            logging.error(f'key#id not found at #{file.stem}')
            continue
        mod_id = metadata['id']
        info = DataUtil.ModFileInfo(mod_id, PurePath(env_dir.mods_available, file.stem))
        if mod_id not in versions_data.keys():
            versions_data[mod_id] = []
        versions_data[mod_id].append(info)

        if 'name' in metadata.keys():
            info.name = metadata['name']

    return versions_data


def get_version(mod_id, index=None, auto=False, versions_data=None) -> tuple[ModFileInfo] | list[ModFileInfo]:
    if versions_data is None:
        versions_data = list_library()
    if mod_id not in versions_data.keys():
        raise RuntimeError(f'mod#{mod_id} not found')
    versions = versions_data[mod_id]
    StrVersion.sort_versions(versions)
    if index is not None and index < len(versions):
        return (versions[index],)
    elif auto:
        return (versions[0],)
    return versions


def enable(file: PurePath, id_, mapping: DataUtil.Data = None):
    mapping = DataUtil.Data(env_file.mapping) if mapping is None else mapping

    target = None
    if env_dir.use_relative:
        try:
            rel = relpath(start=env_dir.mods_enabled, path=env_dir.mods_available)
            target = PurePath(rel, file.name)
        except ValueError:
            target = None
    if target is None and not file.is_absolute():
        target = abspath(file)

    link = PurePath(env_dir.mods_enabled, f'{id_}.jar')
    if exists(link) or islink(link):
        os.remove(link)
        logging.info(f'Existed {link.name} Removed')
    os.symlink(normpath(target), link)
    mapping[link.name] = str(target)
    logging.info(f'{link.name}#{link} -> {target}')
    return link, target


def enable_auto(mod_id, versions_data=None, mapping: DataUtil.Data = None):
    versions = get_version(mod_id, versions_data)
    rules = read_rules()
    blocked = nerd_get(rules, ('mods', {}), (mod_id, {}), ('block', []))

    for x in blocked:
        if x not in versions:
            continue
        versions.remove(x)
        logging.info(f'[Skip blocked]: {x}')
    StrVersion.sort_versions(versions)
    if len(versions) < 1:
        logging.error(f'No available mod of {mod_id} except block list {blocked}')
        return

    return enable(versions[0].file, mod_id, mapping)


def disable(file, mapping=None):
    mapping = DataUtil.Data(env_file.mapping) if mapping is None else mapping

    if exists(file) or islink(file):
        os.remove(file)
        echo(f'[Unlink]: {file}')
        mapping.pop(file)
    else:
        logging.warning(f'NotFound {file}')


def list_library():
    meta = parse_metadata(env_dir.metadata)
    all_jar_mod = get_all(meta)
    return all_jar_mod


def is_mod(path):
    return path.endswith('.jar')


def ls_mods(path=None):
    if path is None:
        path = env_dir.mods_enabled
    jars = [x for x in next(os.walk(path))[2] if is_mod(x)]
    return jars


def apply(ruleset, pre_add_all=True):
    versions_data = list_library()
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
            logging.info(f'[Unlink]: {x}')
        else:
            logging.warning(f'file {x} not symbolic link')
    mapping.write()
    pop_d()


def select(pattern):
    versions_data = list_library()
    return [x for x in versions_data.keys() if re.match(pattern, x)]


PT_DISABLE = re.compile(r'(.*\.jar)(\.(?:old|disabled))$')
PT_JAR = re.compile(r'(.*)\.jar$')


def archive(path: str) -> Tuple[List[str], List[str]]:
    files: List[str] = next(os.walk(path))[2]  # ls -File

    push_d(path)
    unlinked = []
    archived = []

    mapping = get_map()
    for file_name in files:
        # old link
        if islink(file_name):
            r = re.match(PT_DISABLE, file_name)
            if r is not None:
                origin_name = r.groups()[0]
                unlinked.append(file_name)
                os.unlink(file_name)
                if origin_name in mapping:
                    mapping.pop(origin_name)
                logging.debug(f'unlink {file_name}')
        # unknown file
        elif r := re.match(PT_DISABLE, file_name):
            restored_name = file_name.removesuffix(r.groups()[1])
            if not os.path.exists(target := j(env_dir.mods_available, restored_name)):
                archived.append(file_name)
                shutil.move(file_name, target)
                mapping.pop(file_name)
            else:
                logging.error(f'Conflict Name {file_name} -> {restored_name}')
        # new file
        elif re.match(PT_JAR, file_name):
            archived.append(file_name)
            shutil.move(file_name, join(env_dir.mods_available, file_name))
            if file_name in mapping.keys():
                mapping.pop(file_name)
            logging.info(f'move {file_name} to [mods_available]')
    mapping.write()

    extract_metadata()
    parse_metadata(env_dir.metadata, rebuild_=True)
    pop_d()
    return unlinked, archived


def get_map():
    return DataUtil.Data(env_file.mapping, delay_write=True)


def prune():
    pass


class RuleMode(Enum):
    APPEND = enum.auto()
    EXCEPT = enum.auto()


def write_rules(rule: dict, rule_file=env_file.rule):
    with open(rule_file, 'w') as f:
        json.dump(rule, f, indent=2)


def read_rules(rule_file=env_file.rule) -> dict:
    if not exists(rule_file):
        write_rules({}, rule_file)
        return {}
    with open(rule_file) as f:
        return json.load(f)

# def init_dir():
#     return None

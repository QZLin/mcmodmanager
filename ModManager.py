import enum
import json
import logging
import os
import re
import shutil
import zipfile
from enum import Enum
from os.path import join, exists, islink, relpath, abspath
from typing import Dict, List, Any, Tuple

import yaml
from click import echo

import DataUtil
import StrVersion
from MixConfig import Config
from RuntimeConfig import EnvDirs, EnvFiles, get_env

try:
    from yaml import CLoader as YamlLoader, CDumper as YamlDumper
except ImportError:
    from yaml import Loader as YamlLoader, Dumper as YamlDumper

j = join
ENCODING = 'utf-8'

root = os.getcwd()
env = None
env_conf = join(root, 'mcm.yaml')
if exists(env_conf):
    with open(env_conf) as file1:
        env = yaml.load(file1, YamlLoader)
env_dir, env_file = get_env(root, env)
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


def _zip_has(zip_, path):
    return len([x for x in zip_.filelist if x.filename == path]) == 1


def mod_metadata(file) -> Tuple[str, str] | Tuple[None, None]:
    try:
        archive_file = zipfile.ZipFile(file)
    except zipfile.BadZipFile:
        logging.warning(f'not a zip {file}')
        return None, None
    if _zip_has(archive_file, 'fabric.mod.json'):
        mod_type = 'fabric'
        content = archive_file.read('fabric.mod.json').decode()
    elif _zip_has(archive_file, 'quilt.mod.json'):
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


def extract_metadata(library_dir=None, output_dir=None) -> List[str]:
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
    for file in next(os.walk(library_dir))[2]:
        out_path = j(output_dir, f'{file}.json')
        if file in mixin_data_files:
            metadata_ = mixin(file, mixin_data)
        else:
            metadata_, mod_type = mod_metadata(j(library_dir, file))
        if metadata_ is None:
            continue
        with open(out_path, 'w', encoding=ENCODING) as f:
            f.write(metadata_)
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
    except json.JSONDecodeError:
        result = {}
    return result


def parse_metadata(dir_=None, cache_file=None, rebuild=False) -> Dict[str, Any]:
    if dir_ is None:
        dir_ = env_dir.metadata
    if cache_file is None:
        cache_file = env_file.metadata_cache

    if not rebuild:
        return meta_cache(cache_file)

    metadata = {}
    files = (x for x in next(os.walk(dir_))[2] if x.endswith('.json'))
    for filename in files:
        with open(j(dir_, filename), encoding='utf-8') as f:
            content = json.load(f)
            metadata[filename] = content
    with open(cache_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    return metadata


def get_library(metadata: dict) -> Dict[str, List[str]]:
    versions_data = {}
    for filename, data in metadata.items():
        name = filename.removesuffix('.json')
        if 'id' not in data.keys():
            logging.warning(f'key#id not found at #{filename}')
            continue
        mod_id = data['id']
        if mod_id not in versions_data.keys():
            versions_data[mod_id] = []
        versions_data[mod_id].append(name)
    return versions_data


def get_version(mod_id, index=None, auto=False, versions_data=None) -> Tuple[str] | List[str]:
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


def enable(filename, id_, mapping: DataUtil.Data = None):
    mapping = DataUtil.Data(env_file.mapping) if mapping is None else mapping

    # target = join(env_dir.mods_available, filename)
    target = None
    if env_dir.use_relative:
        try:
            rel = relpath(start=env_dir.mods_enabled, path=env_dir.mods_available)
            target = join(rel, filename)
        except ValueError:
            pass
    if target is None:
        target = abspath(join(env_dir.mods_available, filename))

    link_name = f'{id_}.jar'
    link = join(env_dir.mods_enabled, link_name)
    if exists(link) or islink(link):
        os.remove(link)
        logging.info(f'Existed {link_name} Removed')
    os.symlink(target, link)
    mapping[link_name] = target
    logging.info(f'{link_name}#{link} -> {target}')
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

    return enable(versions[0], mod_id, mapping)


def disable(file):
    if exists(file) or islink(file):
        os.remove(file)
        echo(f'[Unlink]: {file}')
    else:
        logging.warning(f'NotFound {file}')


def list_library():
    meta = parse_metadata(env_dir.metadata)
    all_jar_mod = get_library(meta)
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
    parse_metadata(env_dir.metadata, rebuild=True)
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

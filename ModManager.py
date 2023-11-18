import enum
import json
import logging
import os
import re
import shutil
import zipfile
from dataclasses import dataclass
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
else:
    raise RuntimeError('init first')
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


'''
mods -> mods-enabled
var
mods-lib
-- mods-available
-- metadata
-- conf
-- -- mixin
-- -- rule

'''


def mod_metadata(file, dict_first=False) -> Tuple[str | None, str | None]:
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
        file_dict = json.loads(archive_file.read('quilt.mod.json'))
        file_dict.update(file_dict['quilt_loader'])
        content = file_dict if dict_first else json.dumps(file_dict)
    else:
        logging.error(f'unknown zip mod {file}')
        return None, None
    return content, mod_type


def get_mixin() -> Tuple[dict[str, Any], List[str]]:
    mixin_data = Config.mixed_config(env_dir.conf, 'mixin.d', 'mixin')['metadata']
    mixin_data_files = [x['file'] for x in mixin_data]
    mixin_data = {x['file']: x for x in mixin_data}
    return mixin_data, mixin_data_files


def do_mixin(filename, orig_data, mixin_data):
    if orig_data is None:
        return mixin_data
    # if mixin_data is None:
    #     mixin_data = Config.mixed_config(env_dir.conf, 'mixin.d', 'mixin')['metadata']
    r = [x for x in mixin_data if x['file'] == filename]
    if len(r) == 1:
        data = r[0]
        logging.info(f'mixin {filename} {data}')
        return json.dumps(data)
    else:
        raise RuntimeError('Multiple mixin set for single file')


def get_files(path, contain_subdir=False, file_type=None):
    if contain_subdir:
        raise NotImplementedError
    result = [PurePath(path, filename) for filename in next(os.walk(path))[2]]
    if file_type is not None:
        return [x for x in result if x.suffix == file_type]
    return result


def extract_metadata(files, mixin_data):
    """
    extract all metadata that already at library folder
    :return:
    """
    m_data, m_names = mixin_data
    mixin_hit = []
    all_cache = {}
    for file in files:
        if file in m_names:
            metadata, type_ = mod_metadata(file)
            if type_ is None:
                continue
            if type_ != 'quilt':
                metadata = json.loads(metadata)
            metadata = do_mixin(file, metadata, m_data)
            mixin_hit.append(file)
            metadata = json.dumps(metadata)
        else:
            metadata, type_ = mod_metadata(file)
        if type_ is None:
            continue

        file_meta_cache = PurePath(env_dir.metadata, f'{file.name}.json')
        with open(file_meta_cache, 'w', encoding=ENCODING) as f:
            f.write(metadata)
        all_cache[file_meta_cache] = metadata
    for name, data in m_data.items():
        if name not in mixin_hit:
            file_meta_cache = PurePath(env_dir.metadata, f'{name}.json', )
            with open(file_meta_cache, 'w', encoding=ENCODING) as f:
                json.dump(data, f)
            all_cache[file_meta_cache] = data
    return all_cache

    # library_dir = env_dir.mods_available if library_dir is None else library_dir
    # output_dir = env_dir.metadata if output_dir is None else output_dir
    # clean cached metadata
    # cached_files = (x for x in next(os.walk(env_dir.metadata))[2] if x.endswith('.json'))
    # for x in cached_files:
    #     os.remove(j(env_dir.metadata, x))

    # mixin_data = {x.pop('file'): x for x in mixin_data}

    # jars = []
    # for filename in next(os.walk(library_dir))[2]:
    # file = PurePath(library_dir, filename)
    # file_cache = PurePath(output_dir, f'{file}.json', )
    # if file.name in mixin_data_files:
    #     data = do_mixin(filename, mixin_data)
    # else:
    #     data, type_ = mod_metadata(file)
    # if data is None:
    #     return
    # with open(file_cache, 'w', encoding=ENCODING) as f:
    #     f.write(data)
    # jars.append(file)
    # return jars


def parse_metadata(dir_=None, file_all_cache=None, rebuild_=False) -> Dict[PurePath, Any]:
    if dir_ is None:
        dir_ = env_dir.metadata
    if file_all_cache is None:
        file_all_cache = env_file.metadata_cache
    cache = MetaCache()

    if rebuild_:
        cache.rebuild()
        cache.save()

    # all_meta = {}
    # all_mata_caches = (x for x in next(os.walk(dir_))[2] if x.endswith('.json'))
    # for name in all_mata_caches:
    #     cache_file = PurePath(dir_, name)
    #     with open(cache_file, encoding=ENCODING) as f:
    #         content = json.load(f)
    #         all_meta[cache_file.name] = content
    # with open(file_all_cache, 'w') as f:
    #     json.dump(all_meta, f, indent=2)

    # return {PurePath(env_dir.metadata, k): v for k, v in all_meta.items()}

    return cache.cache


class MetaCache:
    """
    cache for all metadata
    ---------- -> metadata.json (global cache)
    a.jar.json
    b.jar.json
    c.jar.json
    """

    def __init__(self, global_cache=None, cache_dir=None, late_init=False):
        if global_cache is None:
            global_cache = env_file.metadata_cache
        if cache_dir is None:
            cache_dir = env_dir.metadata
        self.global_cache = global_cache
        self.cache_dir = cache_dir

        self._indexes = []

        self.cache = {}
        if not late_init:
            self.load()

    def load(self) -> dict:
        if not exists(self.global_cache):
            self.cache.clear()
            return self.cache
        try:
            with open(self.global_cache, 'r') as f:
                result = json.load(f)
            self.cache = {PurePath(env_dir.metadata, name): data for name, data in result.items()}
            self._indexes.clear()
            self._indexes.extend((x.name for x in self.cache.keys()))
        except json.JSONDecodeError:
            self.cache.clear()
        return self.cache

    def rebuild(self):
        self.clear()
        meta_files = (x for x in next(os.walk(self.cache_dir))[2] if x.endswith('.json'))
        for file in meta_files:
            with open(j(self.cache_dir, file), encoding=ENCODING) as f:
                self.cache[PurePath(self.cache_dir, file)] = json.load(f)
        self._indexes.clear()
        self._indexes.extend((x.name for x in self.cache.keys()))
        self.save()

    def save(self):
        with open(self.global_cache, 'w') as f:
            json.dump({k.name: v for k, v in self.cache.items()}, f, indent=2)

    def clear(self):
        self.cache.clear()
        if exists(self.global_cache):
            os.remove(self.global_cache)

    def hit(self, v) -> bool:
        return f'{v.name}.json' in self._indexes


def update_mode(rebuild_=False):
    files = get_files(env_dir.mods_available)
    m_data, m_names = get_mixin()

    cache = MetaCache(late_init=True)
    if rebuild_:
        cache.clear()
        for x in get_files(env_dir.metadata, file_type='.json'):
            os.remove(x)
    else:
        cache.rebuild()
        for file in files.copy():
            if cache.hit(file):
                files.remove(file)

    extract_metadata(files, (m_data, m_names))
    cache.rebuild()


def get_all(all_metadata: dict[PurePath, dict]) -> Dict[str, List[DataUtil.ModFileInfo]]:
    versions_data = {}
    for file, metadata in all_metadata.items():
        if 'id' not in metadata.keys():
            logging.error(f'key=id not found at #{file.name}')
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
    else:
        target = abspath(file)
    # if target is None and not file.is_absolute():
    #     target = abspath(file)

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
        mapping.pop(file.name, None)
    else:
        logging.warning(f'NotFound {file}')


def list_library():
    cache = MetaCache()
    all_jar_mod = get_all(cache.cache)
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


def archive(file: PurePath, archive_name=None, del_source=True, allow_override=False):
    if archive_name is None:
        archive_name = file.name
    archived = PurePath(env_dir.mods_available, archive_name)
    logging.debug(f'archive {file}->{archived}')
    if allow_override:
        if exists(archived):
            os.remove(archived)
    else:
        if exists(archived):
            logging.error(f'{archived} existed and override is not allowed')

    if del_source:
        shutil.move(file, archived)
    else:
        shutil.copy(file, archived)


def archive_dir(path: str, ignore_disabled=True):
    # files: List[str] = next(os.walk(path))[2]  # ls -File
    dis_list = []
    old_list = []
    new_list = []

    # push_d(path)
    for file in get_files(path, file_type='.jar'):
        if not islink(file):
            logging.info(f'archive {file}')
            archive(file, allow_override=True)
            new_list.append(file)
    for file in get_files(path, file_type='.old'):
        old_list.append(file)
        if islink(file):
            logging.info(f'unlink {file}')
            os.remove(file)
        else:
            logging.info(f'archive {file}')
            archive(file, file.stem)
    for file in get_files(path, file_type='.disabled'):
        dis_list.append(file)
        if islink(file):
            logging.info(f'unlink {file}')
            os.remove(file)
        elif ignore_disabled:
            logging.info(f'ignore disabled {file}')
        else:
            logging.info(f'archive {file}')
            archive(file, file.stem)

    # for file_name in files:
    #     file = PurePath(path, file_name)
    #     if islink(file):
    #         if file.suffix == '.jar':
    #             pass
    #         elif file.suffix == '.old':
    #             old_list.append(file)
    #             os.remove(file)
    #         elif file.suffix == '.disabled':
    #             disabled.append(file)
    #             os.remove(file)
    #         else:
    #             logging.info(f'skipped unknown {file}')
    #     else:
    #         if file.suffix == '.jar':
    #             archive_(file, allow_override=True)
    #         elif file.suffix == '.old':
    #             archive_(file, file.stem)
    #             old_list.append(file)
    #         elif file.suffix == '.disabled':
    #             archive_(file, file.stem, allow_override=False)
    #             disabled.append(file)
    #         else:
    #             logging.info(f'skipped unknown {file}')
    return dis_list, old_list, new_list


def get_map():
    return DataUtil.Data(env_file.mapping, delay_write=True)


def prune():
    pass


def check_env():
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

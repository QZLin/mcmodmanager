import enum
import json
import logging
import os
import re
import shutil
import zipfile
from enum import Enum
from os.path import join, exists, islink, relpath, abspath, normpath
from pathlib import PurePath
from typing import Dict, List, Any, Tuple

from UtilLib import StrVersion, Data
from UtilLib.Dict import nerd_get
from UtilLib.MixConfig import Config
from UtilLib.RuntimeConfig import get_env

try:
    import yaml
    from yaml import CLoader as YamlLoader, CDumper as YamlDumper
except ImportError:
    import yaml
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

notice = print


def push_d(path):
    global __dir_heap
    __dir_heap.append(os.curdir)
    os.chdir(path)


def pop_d():
    global __dir_heap
    os.chdir(__dir_heap.pop())


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


def mod_metadata(file, to_dict=False) -> Tuple[str | dict | None, str | None]:
    try:
        archive_file = zipfile.ZipFile(file)
    except zipfile.BadZipFile:
        logging.warning(f'not a zip {file}')
        return None, None
    if __zip_has(archive_file, 'fabric.mod.json'):
        mod_type = 'fabric'
        binary_content = archive_file.read('fabric.mod.json')
        if to_dict:
            content = json.loads(binary_content)
        else:
            content = binary_content.decode()
    elif __zip_has(archive_file, 'quilt.mod.json'):
        mod_type = 'quilt'
        file_dict = json.loads(archive_file.read('quilt.mod.json'))
        file_dict.update(file_dict['quilt_loader'])
        content = file_dict if to_dict else json.dumps(file_dict)
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
        notice(f'mixin {filename} {data}')
        return json.dumps(data)
    else:
        raise RuntimeError('Multiple mixin set for single file')


def get_files(path, ext=None, contain_subdir=False, symlink: bool | None = None) -> List[PurePath]:
    if contain_subdir:
        raise NotImplementedError
    result = [PurePath(path, filename) for filename in next(os.walk(path))[2]]
    if symlink is not None:
        raise NotImplementedError
    if ext is not None:
        return [x for x in result if x.suffix == ext]
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


def parse_metadata(dir_=None, file_all_cache=None, rebuild_=False) -> Dict[PurePath, Any]:
    if dir_ is None:
        dir_ = env_dir.metadata
    if file_all_cache is None:
        file_all_cache = env_file.metadata_cache
    cache = MetaCache()

    if rebuild_:
        cache.rebuild()
        cache.save()

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


def update_mod(rebuild_=False):
    files = get_files(env_dir.mods_available, ext='.jar')
    file_names = [x.name for x in files]
    m_data, m_names = get_mixin()

    global_cache = MetaCache(late_init=True)
    if rebuild_:
        global_cache.clear()
        for meta_file in get_files(env_dir.metadata, ext='.json'):
            os.remove(meta_file)
    else:
        global_cache.rebuild()
        for meta_file in get_files(env_dir.metadata, ext='.json'):
            if meta_file.stem not in file_names:
                os.remove(meta_file)
                notice(f'outdated {meta_file} removed')
        for file in files.copy():
            if global_cache.hit(file):
                files.remove(file)
            else:
                notice(f'{file.name} updated')

    extract_metadata(files, (m_data, m_names))
    global_cache.rebuild()


def get_all(all_metadata: dict[PurePath, dict]) -> Dict[str, List[Data.ModFileInfo]]:
    versions_data = {}
    for file, metadata in all_metadata.items():
        if 'id' not in metadata.keys():
            logging.error(f'key=id not found at #{file.name}')
            continue
        mod_id = metadata['id']
        info = Data.ModFileInfo(mod_id, PurePath(env_dir.mods_available, file.stem))
        if mod_id not in versions_data.keys():
            versions_data[mod_id] = []
        versions_data[mod_id].append(info)

        if 'name' in metadata.keys():
            info.name = metadata['name']

    return versions_data


def get_version(mod_id, index=None, auto=False, versions_data=None) -> (
        tuple[Data.ModFileInfo] | list[Data.ModFileInfo]):
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


def get_spec_mod(filename, id_=None, data=None):
    if data is None:
        data = list_library()
    if id_ is not None:
        versions = data[id_]
        r = [x for x in versions if x.file.name == filename]
        assert len(r) == 1
        return r[0]
    else:
        for id_, versions in data.items():
            r = [x for x in versions if x.file.name == filename]
            assert len(r) <= 1
            if len(r) == 1:
                return r[0]


def enable(file: PurePath, id_, mapping: Data.Data = None):
    mapping = Data.Data(env_file.mapping) if mapping is None else mapping

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
        notice(f'Existed {link.name} Removed')
    os.symlink(normpath(target), link)
    mapping[link.name] = str(target)
    notice(f'{link.name}#{link} -> {target}')
    return link, target


def enable_auto(mod_id, versions_data=None, mapping: Data.Data = None):
    versions = get_version(mod_id, versions_data)
    rules = read_rules()
    blocked = nerd_get(rules, ('mods', {}), (mod_id, {}), ('block', []))

    for x in blocked:
        if x not in versions:
            continue
        versions.remove(x)
        notice(f'[Skip blocked]: {x}')
    StrVersion.sort_versions(versions)
    if len(versions) < 1:
        logging.error(f'No available mod of {mod_id} except block list {blocked}')
        return

    return enable(versions[0].file, mod_id, mapping)


def disable(file, mapping=None):
    mapping = Data.Data(env_file.mapping) if mapping is None else mapping

    if exists(file) or islink(file):
        os.remove(file)
        notice(f'[Unlink]: {file}')
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
    files = [PurePath(path, x) for x in next(os.walk(path))[2]]
    mapping = get_map()
    for x in files:
        logging.debug(f'{x}')
        if islink(x):
            os.unlink(x)
            mapping.pop(x.name)
            notice(f'[Unlink]: {x.name}')
        else:
            logging.warning(f'file {x.name} not symbolic link')
    mapping.write()


def select(pattern):
    versions_data = list_library()
    return [x for x in versions_data.keys() if re.match(pattern, x)]


PT_DISABLE = re.compile(r'(.*\.jar)(\.(?:old|disabled))$')
PT_JAR = re.compile(r'(.*)\.jar$')


def archive(file: PurePath, archive_name=None, del_source=True, allow_override=False) -> PurePath | None:
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
            return

    if del_source:
        shutil.move(file, archived)
    else:
        shutil.copy(file, archived)
    return archived


def archive_dir(path: str, ignore_disabled=True):
    # files: List[str] = next(os.walk(path))[2]  # ls -File
    dis_list = []
    old_list = []
    new_list = []

    # push_d(path)
    for file in get_files(path, ext='.jar'):
        if not islink(file):
            notice(f'archive {file}')
            archived = archive(file, allow_override=True)
            metadata, type_ = mod_metadata(archived, to_dict=True)
            enable(archived, metadata['id'])
            new_list.append(file)
    for file in get_files(path, ext='.old'):
        old_list.append(file)
        if islink(file):
            notice(f'unlink {file}')
            os.remove(file)
        else:
            notice(f'archive {file}')
            archive(file, file.stem)
    for file in get_files(path, ext='.disabled'):
        dis_list.append(file)
        if islink(file):
            notice(f'unlink {file}')
            os.remove(file)
        elif ignore_disabled:
            notice(f'ignore disabled {file}')
        else:
            notice(f'archive {file}')
            archive(file, file.stem)

    return dis_list, old_list, new_list


def get_map():
    return Data.Data(env_file.mapping, delay_write=True)


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

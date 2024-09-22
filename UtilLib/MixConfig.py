import enum
import json
import os
from os.path import join
from pathlib import PurePath

import yaml

try:
    from yaml import CLoader as YamlLoader, CDumper as YamlDumper
except ImportError:
    from yaml import Loader as YamlLoader, Dumper as YamlDumper


class CFGType:
    YAML = enum.auto()
    JSON = enum.auto()


def get_cfg_type(file: PurePath):
    if file.suffix in ('.yaml', '.yml'):
        return CFGType.YAML
    elif file.suffix in ('.json',):
        return CFGType.JSON


class Mixed:
    @staticmethod
    def load(path, type_=None):
        if type_ is None:
            type_ = get_cfg_type(path)
        if type_ == CFGType.YAML:
            with open(path, 'r') as f:
                return yaml.load(f, YamlLoader)
        elif type_ == CFGType.JSON:
            with open(path, 'r') as f:
                return json.load(f)
        else:
            raise NotImplementedError(f'unknown file type {path}#{type_}')

    @staticmethod
    def dump(path, content, type_=None):
        if type_ is None:
            type_ = get_cfg_type(path)
        if type_ == CFGType.YAML:
            with open(path, 'w') as f:
                return yaml.dump(content, f, YamlDumper)
        elif type_ == CFGType.JSON:
            with open(path, 'w') as f:
                return json.dump(content, f)
        else:
            raise NotImplementedError(f'unknown file type {path}#{type_}')


class Config:
    types = {'yaml': CFGType.YAML, 'yml': CFGType.YAML, 'json': CFGType.JSON}

    def __init__(self, root, name):
        self.root = root
        self.name = name
        self.subdir = join(root, f'{name}.d')

    @property
    def files(self):
        return self.config_files(self.root, self.subdir, self.name)

    @property
    def mixed(self):
        return self.mixed_config(self.root, self.subdir, self.name)

    @staticmethod
    def config_files(root, subdir_name, name=None):
        subdir = PurePath(root, subdir_name)
        result = []
        # root/config.xxx
        if name is not None:
            for ext in Config.types.keys():
                path_ = PurePath(root, f'{name}.{ext}')
                if os.path.exists(path_):
                    result.append((path_, get_cfg_type(path_)))
        # config.d/xxxx.xxx
        if os.path.isdir(subdir):
            for name in next(os.walk(subdir))[2]:
                file = PurePath(subdir, name)
                type_ = get_cfg_type(file)
                if type_ is not None:
                    result.append((file, type_))
        return result

    @staticmethod
    def mixed_config(root, subdir, name=None):
        result = {'metadata': []}
        for path_, type_ in Config.config_files(root, subdir, name):
            content = Mixed.load(path_, type_)
            if content is not None and 'metadata' in content.keys():
                for x in content['metadata']:
                    if x not in result['metadata']:
                        result['metadata'].append(x)
        return result

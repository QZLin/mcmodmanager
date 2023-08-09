import logging
import os
from os.path import exists, join
from typing import Tuple


class EnvDirs:
    rules_d: str
    mixin_d: str
    init_required_dirs = ('mods_available', 'mods_enabled',
                          'conf', 'rules_d', 'mixin_d',
                          'metadata', 'runvar')

    def __init__(self, root):

        self.mods_available = join(root, 'mods-available')
        self.mods_enabled = join(root, 'mods-enabled')
        self.metadata = join(root, 'metadata')

        self.conf = join(root, 'conf')

        self.runvar = join(root, 'var')

    @property
    def conf(self):
        return self._conf

    @conf.setter
    def conf(self, value):
        self._conf = value
        self.rules_d = join(self.conf, 'rules.d')
        self.mixin_d = join(self.conf, 'mixin.d')

    def init_dir(self):
        for name in self.init_required_dirs:
            if not hasattr(self, name):
                continue
            dir_ = self.__getattribute__(name)
            if not exists(dir_):
                os.makedirs(dir_)
            elif os.path.isdir(dir_):
                logging.debug(f'skip existed dir {dir_}')
            else:
                raise RuntimeError(f'can\'t create dir when file existed: {dir_}')


class EnvFiles:
    def __init__(self, dirs: EnvDirs):
        self.metadata_cache = join(dirs.metadata, 'metadata.json')
        self.mapping = join(dirs.runvar, 'maps.json')
        self.rule = join(dirs.conf, 'rules.json')


def get_env(root: str, env=None) -> Tuple[EnvDirs, EnvFiles]:
    dirs = EnvDirs(root)
    if env is not None:
        if 'root' in env.keys():
            dirs = EnvDirs(env['root'])
        for key in env.keys():
            if key in dirs.__dict__.keys():
                dirs.__setattr__(key, env[key])
        if 'conf' in env.keys():
            dirs.conf = env['conf']
        logging.debug(env)

    files = EnvFiles(dirs)
    return dirs, files

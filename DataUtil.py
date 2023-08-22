import json
import os.path
from dataclasses import dataclass
from os import PathLike
from pathlib import PurePath
from typing import Literal, List


class Data(dict):
    def __init__(self, file: str, delay_write=False):
        super().__init__()
        self.delay_write = delay_write
        self.file = file
        if os.path.exists(self.file):
            self.read()
        else:
            self.write()

    def __getitem__(self, y):
        if y not in self.keys():
            return None
        return super().__getitem__(y)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if not self.delay_write:
            self.write()

    def __delitem__(self, key):
        super().__delitem__(key)
        if not self.delay_write:
            self.write()

    def read(self):
        with open(self.file, 'r',encoding='utf-8') as f:
            try:
                self.update(json.load(f))
            except json.JSONDecodeError:
                # raise RuntimeError(f'Parse {self.file} fail')
                self.write()

    def write(self):
        with open(self.file, 'w') as f:
            json.dump(self, f)


@dataclass
class File:
    filename: str
    directory: str
    ext: str = ""

    @property
    def fullpath(self):
        return os.path.join(self.filename, self.directory)


@dataclass
class ModFileInfo:
    id: str
    file: PurePath
    name: str = ""
    version: str = ""
    mcver: str = ""
    launcher: Literal['fabric', 'quilt', 'forge', None] = 'fabric'

    @staticmethod
    def from_json(dir_, filename, data, launcher=None) -> 'ModFileInfo':
        r = ModFileInfo(data['id'], filename, dir_, launcher)
        if 'version' in data.keys():
            r.version = data['version']
        try:
            r.mcver = data['depends']['minecraft']
        except KeyError:
            pass

        return r


@dataclass
class ModVerInfo:
    id: str
    mods: List[ModFileInfo]

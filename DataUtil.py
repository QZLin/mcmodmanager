import json
import os.path


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
        with open(self.file, 'r') as f:
            self.update(json.load(f))

    def write(self):
        with open(self.file, 'w') as f:
            json.dump(self, f)

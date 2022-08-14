import os
import json
import threading
from os.path import join

MOD_DIR = '../'
SPLIT_CHAR = ':'
TYPE_JAR = '.jar'
TYPE_DISABLED = '.disabled'

ERR_LOST = 0
ENABLE = 1
DISABLE = 2


class ModManager:
    def __init__(self, root='.'):
        self.root = root

    def get_jars(self, publish=False):
        jars, disables = [], []

        def _handle(file_name):
            if not len(file_name) < 4 and file_name[-4:] == TYPE_JAR:
                jars.append(file_name)
            elif not len(file_name) < 9 and file_name[-9:] == TYPE_DISABLED:
                disables.append(file_name)

        for root, dirs, files in os.walk(self.root, topdown=True):
            if root == root:
                for name in files:
                    _handle(name)
            break
        return jars if publish else (jars, disables)

    @staticmethod
    def encode(jars):
        data = {'jars': jars}
        return json.dumps(data)

    @staticmethod
    def decode(code):
        data = json.loads(code)
        result = data['jars']
        return result

    @staticmethod
    def handle_file(action, file, **files):
        def _run():
            if action == ERR_LOST:
                print('lost', file)
            elif action == ENABLE:
                print('enable', file)
                try:
                    os.rename(file + TYPE_DISABLED, file)
                except FileNotFoundError as err:
                    print(err)
                except FileExistsError as err:
                    print(err)
            elif action == DISABLE:
                print('disable', file)
                try:
                    os.rename(file, file + TYPE_DISABLED)
                except FileNotFoundError as err:
                    print(err)
                except FileExistsError as err:
                    print(err)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    @staticmethod
    def compare(targe_jar_rules, local_jar_files):
        local_jars, disables = local_jar_files
        lost = []
        for jar in targe_jar_rules:
            # (jar in code) in local or not
            if jar in local_jars:
                pass
            else:
                if jar + TYPE_DISABLED in disables:
                    ModManager.handle_file(ENABLE, jar)
                else:
                    ModManager.handle_file(ERR_LOST, jar)
                    lost.append(jar)
        for jar in local_jars:
            # local jars contain unexpected jar or not
            if jar in targe_jar_rules:
                pass
            else:
                ModManager.handle_file(DISABLE, jar)
        if len(lost) >= 1:
            return lost

        # class Flags:
        #     def __init__(self, type_):
        #         self.type = type_

    def get_flag(self):
        with open(join(self.root, 'flag.json'), 'r'):
            pass


if __name__ == '__main__':
    try:
        mode = int(input('select mode:\n0 load[default]\n1 publish\nmode:'))
    except ValueError:
        mode = 0
    except TypeError:
        mode = 0

    manager = ModManager()
    if mode == 0:
        txt = input('code:')
        ModManager.compare(ModManager.decode(txt), manager.get_jars())
    elif mode == 1:
        txt = ModManager.encode(manager.get_jars(publish=True))
        print(txt)

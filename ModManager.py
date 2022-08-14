import os
import json
import threading
from os.path import join

MOD_DIR = '../'
SPLIT_CHAR = ':'
TYPE_JAR = '.jar'
TYPE_DISABLED = '.disabled'

ERR_LOST = 0


class Action:
    ENABLE = 1
    DISABLE = 2


class ModManager:
    def __init__(self, root='.'):
        self.root = root
        self.modlist = []  # jar name
        self.filelist = []  # file name
        self.mod_status = {}  # jar name : bool
        self.scan()

    @staticmethod
    def match_ext(name, extension, match_case=False):
        if len(name) < len(extension):
            return False
        if match_case:
            if name[-len(extension):].lower() == extension.lower():
                return True
        else:
            if name[-len(extension):] == extension:
                return True
        return False

    @staticmethod
    def ext_replace(name, ext, target_ext='') -> str:
        length = len(ext)
        if len(name) >= length and name[-length:] == ext:
            return name[:-length] + target_ext

    @staticmethod
    def ext_name(name, active=True):
        if not active and len(name) >= len(TYPE_JAR) \
                and name[-len(TYPE_JAR):] == TYPE_JAR:
            return name + TYPE_DISABLED
        elif active and len(name) >= len(TYPE_DISABLED) \
                and name[-len(TYPE_DISABLED):] == TYPE_DISABLED:
            return name[:-len(TYPE_DISABLED)]
        return name

    def switch_active(self, name):
        self.mod_status[name] = not self.mod_status[name]

    def scan(self):
        a, b = self.get_files()
        a.sort()
        b.sort()

        self.filelist = a.copy()
        self.filelist.extend(b)

        self.modlist = a.copy()
        self.modlist.extend([self.ext_name(x, True) for x in b])

        self.mod_status = {x: True for x in a}
        self.mod_status.update({self.ext_name(x, True): False for x in b})

    def get_files(self, publish=False) -> (list, list):
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
        return jars, disables

    # def mod_names(self):
    #     names = []
    #     a, b = self.get_files()
    #     names.extend(a)
    #
    #     # return [x[-len(TYPE_JAR):] for x in a], [x[-len(TYPE_DISABLED):] for x in b]
    #     return names

    @staticmethod
    def encode(jars):
        data = {'jars': jars}
        return json.dumps(data)

    @staticmethod
    def decode(code):
        data = json.loads(code)
        result = data['jars']
        return result

    def handle_mod(self, activate, mod_index):
        name = self.filelist[mod_index]
        self.handle_file(activate, name)
        # if rescan:
        #     self.mod_status[name] = not self.mod_status[name]
        #     self.filelist[mod_index] = self.ext_name(name, activate)

    def handle_file(self, activate: bool, file_name, rescan=True, **files):
        file = os.path.join(self.root, file_name)

        def _run():
            # if action == ERR_LOST:
            #     print('lost', file)
            if activate:
                print('enable', file)
                try:
                    os.rename(file, ModManager.ext_name(file, True))
                except FileNotFoundError as err:
                    print(err)
                except FileExistsError as err:
                    print(err)
            else:
                print('disable', file)
                try:
                    os.rename(file, ModManager.ext_name(file, False))
                except FileNotFoundError as err:
                    print(err)
                except FileExistsError as err:
                    print(err)
            if rescan:
                self.scan()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def compare(self, targe_jar_rules, local_jar_files):
        local_jars, disables = local_jar_files
        lost = []
        for jar in targe_jar_rules:
            # (jar in code) in local or not
            if jar in local_jars:
                pass
            else:
                if jar + TYPE_DISABLED in disables:
                    self.handle_file(True, jar)
                else:
                    self.handle_file(True, jar)
                    lost.append(jar)
        for jar in local_jars:
            # local jars contain unexpected jar or not
            if jar in targe_jar_rules:
                pass
            else:
                self.handle_file(False, jar)
        if len(lost) >= 1:
            return lost

        # class Flags:
        #     def __init__(self, type_):
        #         self.type = type_

    def get_flag(self):
        with open(join(self.root, 'flag.json'), 'r'):
            pass

    def load_rules(self, code):
        rules = json.loads(code)
        self.compare(rules['jars'], self.get_files())


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
        ModManager.compare(ModManager.decode(txt), manager.get_files())
    elif mode == 1:
        txt = ModManager.encode(manager.get_files(publish=True))
        print(txt)

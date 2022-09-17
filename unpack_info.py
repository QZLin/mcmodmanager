import os
import zipfile
import json
from os.path import join, exists, islink

mod_library = r'C:\vmo\minecraft\.minecraft-fabric\mods\ModFiles'
lib_info = join(mod_library, 'info')
target_dir = r'C:\vmo\minecraft\.minecraft-fabric\mods'


def gen_metadata(library_dir):
    files = []
    for root, dirs, filenames in os.walk(library_dir):
        files.extend(filenames)
        break

    jars = []
    for x in files:
        try:
            archive = zipfile.ZipFile(x)
            info = archive.read('fabric.mod.json')
        except zipfile.BadZipFile:
            print(f'NotZip:{x}')
            continue
        except KeyError:
            print(f'NoInfo:{x}')
            continue
        with open(join('./info', f'{x}.json'), 'wb') as f:
            f.write(info)
            jars.append(x)


def read_metadata(lib_info_dir):
    metadata = {}
    files = []
    for root, dirs, filenames in os.walk(lib_info_dir):
        files.extend([x for x in filenames if x.lower().endswith('.json')])
        break
    for x in files:
        with open(join(lib_info_dir, x)) as f:
            content = json.load(f)
            metadata[x] = content
    return metadata


def get_lib_info(metadata: dict):
    mod_map = {}
    for filename, data in metadata.items():
        name = filename.strip('.json')
        if data['id'] not in mod_map.keys():
            mod_map[data['id']] = []
        mod_map[data['id']].append(name)
    return mod_map


def deploy(target_directory):
    files = []

    for root, dirs, filenames in os.walk('info'):
        files.extend([x.rstrip('.json') for x in filenames])
        break
    mods = {}
    for x in files:
        with open(f'info/{x}.json') as f:
            data = json.load(f)
            if data['id'] not in mods.keys():
                mods[data['id']] = []
            mods[data['id']].append(x)
            if exists(symbolic := join(target_dir, f'{data["id"]}.jar')) or \
                    islink(symbolic):
                os.unlink(symbolic)
            os.symlink(join(mod_library, x), symbolic)

    json.dump(mods, open('map.json', 'w'))
    print(mods)


def read_rules() -> dict:
    with open('info/rules.json') as f:
        return json.load(f)


def write_rules(rule):
    with open('info/rules.json', 'w') as f:
        json.dump(rule, f)


def enable(name):
    data = read_rules()
    data.update({name: {'enable': True}})
    write_rules(data)


def disable(name):
    data = read_rules()
    data.update({name: {'enable': False}})
    write_rules(data)


if __name__ == '__main__':
    meta = read_metadata(mod_library + '/info')
    m = get_lib_info(meta)
    print()

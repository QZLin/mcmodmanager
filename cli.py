import enum
import json
import logging as log
import os
import re
import shutil
import sys
import zipfile
from enum import Enum
from os.path import join, exists, islink

import argparse
import click as cl
from click import echo

# root_dir = r'C:\vmo\mcserver\1.19\mods'
root_dir = os.curdir
mods_available = join(root_dir, 'mods-available')
mods_enabled = root_dir
dir_metadata = join(root_dir, 'metadata')
dir_conf = join(root_dir, 'conf')


@cl.group()
@cl.option('--debug/--no-debug', default=False)
@cl.pass_context
def cli(ctx, debug):
    pass


def dict_safe_get(dictionary, *keys, obj=None):
    if obj is None:
        obj = []
    next_obj = dictionary
    for i, key in enumerate(keys):
        if key in next_obj.keys():
            next_obj = next_obj[key]
            continue
        if i == len(keys) - 1:
            next_obj[key] = obj
            next_obj = obj
        else:
            next_obj[key] = {}
            next_obj = next_obj[key]
    return next_obj


# def confirm_key_obj(dictionary, obj, keys: list):
#     key = keys[0]
#     if key not in dictionary.keys():
#         next_obj = dictionary[key] = obj if len(keys) == 1 else {}
#     else:
#         next_obj = dictionary[key]
#     if len(keys) <= 1:
#         return next_obj
#     else:
#         return confirm_key_obj(next_obj, obj, keys[1:])


def gen_metadata(library_dir, output_dir):
    for root, dirs, filenames in os.walk(dir_metadata):
        for file in filenames:
            if file.endswith('.json'):
                os.remove(join(dir_metadata, file))
        break

    files = []
    for root, dirs, filenames in os.walk(library_dir):
        files.extend(filenames)
        break

    jars = []
    for file in files:
        try:
            archive_file = zipfile.ZipFile(join(library_dir, file))
            file_info = archive_file.read('fabric.mod.json')
        except zipfile.BadZipFile:
            print(f'NotZip:{file}')
            continue
        except KeyError:
            print(f'NoInfo:{file}')
            continue
        with open(join(output_dir, f'{file}.json'), 'wb') as f:
            f.write(file_info)
            jars.append(file)
    return jars


def read_metadata(dir_, cache=join(dir_conf, 'metadata.json'), rebuild=False):
    if (not rebuild) and exists(cache):
        with open(cache) as f:
            return json.load(f)
    metadata = {}
    files = []
    for root, dirs, filenames in os.walk(dir_):
        files.extend([x for x in filenames if x.lower().endswith('.json')])
        break
    for x in files:
        with open(join(dir_, x)) as f:
            content = json.load(f)
            metadata[x] = content
    with open(cache, 'w') as f:
        json.dump(metadata, f)

    return metadata


class RuleMode(Enum):
    APPEND = enum.auto()
    EXCEPT = enum.auto()


def read_rules(rule_file=join(dir_conf, 'rules.json')) -> dict:
    if not exists(rule_file):
        write_rules({}, rule_file)
        return {}
    with open(rule_file) as f:
        return json.load(f)


def write_rules(rule: dict, rule_file=join(dir_conf, 'rules.json')):
    with open(rule_file, 'w') as f:
        json.dump(rule, f, indent=2)


def get_lib_info(metadata: dict):
    mod_map = {}
    for filename, data in metadata.items():
        name = filename.rstrip('.json')
        if 'id' not in data.keys():
            print(f'Error: id not found in {data.keys()}')
            continue
        if data['id'] not in mod_map.keys():
            mod_map[data['id']] = []
        mod_map[data['id']].append(name)
    return mod_map


@cli.command('init')
def init_():
    init_dir()


def init_dir():
    dirs = [mods_available, mods_enabled, dir_conf, dir_metadata]
    for x in dirs:
        if not exists(x):
            os.makedirs(x)


@cli.command('rebuild')
def rebuild_():
    gen_metadata(mods_available, dir_metadata)
    read_metadata(dir_metadata, rebuild=True)


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
            if exists(symbolic := join(mods_enabled, f'{data["id"]}.jar')) or \
                    islink(symbolic):
                os.unlink(symbolic)
            os.symlink(join(mods_available, x), symbolic)

    json.dump(mods, open('map.json', 'w'))
    print(mods)


def enable_(file, id_):
    link_name = f'{id_}.jar'
    if exists(link_name) or islink(link_name):
        os.remove(link_name)
    os.symlink(join(mods_available, file), join(mods_enabled, link_name))
    echo(f'Enable {link_name} <- {file}')


@cli.command()
@cl.argument('mod_id', metavar='name')
@cl.argument('index', required=False, type=int, default=-1)
@cl.option('--auto', '-a', is_flag=True)
def enable(mod_id, index, auto):
    # if exists(name):
    #     log.info(f'SkipExisted:{name}')
    map_data = list_()
    versions = map_data[mod_id]
    if len(versions) != 1:
        if index != -1:
            mod_file = versions[index]
        elif auto:
            rules = read_rules()
            blocked = dict_safe_get(rules, mod_id, 'block')
            i = len(versions) - 1
            while True:
                mod_file = versions[i]
                if mod_file not in blocked:
                    if len(blocked) > 0:
                        echo(f'Skip blocked {versions[i + 1:]}')
                    break
                i -= 1
                if i < 0:
                    echo(f'No available mod of {mod_id} except block list{blocked}')
                    return
        else:
            print('\n'.join([f'{i} -- {x}' for i, x in enumerate(versions)]))
            return
    else:
        mod_file = versions[0]

    enable_(mod_file, mod_id)


@cli.command()
@cl.argument('name')
def disable(name):
    if exists(name) or islink(name):
        os.remove(name)
        echo(f'Unlink {name}')
    else:
        log.warning(f'NotFound:{name}')


@cli.command()
@cl.argument('file')
def block(file):
    map_data = list_()
    name = None
    for k, v in map_data.items():
        if file in v:
            name = k
            break
    if name is None:
        log.warning(f'Not Found {file}')
        return
    echo(f'Block {file} of [{name}]')
    data = read_rules()

    obj = dict_safe_get(data, name, 'block')
    if file not in obj:
        obj.append(file)
    write_rules(data)


@cli.command()
@cl.argument('id_', metavar='id', required=False)
@cl.option('-p', '--pattern')
@cl.option('-s', '--server', is_flag=True)
@cl.option('-c', '--client', is_flag=True)
@cl.option('-f', '--flag', multiple=True)
def mark(id_, pattern, server, client, flag):
    ids = []
    if id_:
        ids.append(id_)
    if pattern:
        ids.extend(select(pattern))
    flags = []
    if server:
        flags.append('server')
    if client:
        flags.append('client')
    if flag is not None:
        flags.extend(flag)
    echo('Flags:' + ' '.join(flags))
    echo('\t' + '\n\t'.join(ids))
    rules = read_rules()
    for fl in flags:
        obj = dict_safe_get(rules, 'ruleset', fl, obj=[])
        obj.extend([x for x in ids if x not in obj])
    write_rules(rules)


def list_():
    meta = read_metadata(dir_metadata)
    map_data = get_lib_info(meta)
    return map_data


@cli.command('list')
@cl.option('--tree', '-t', is_flag=True)
@cl.option('--min', '-m', 'min_info', is_flag=True)
def list_mods(tree, min_info):
    map_data = list_()

    if tree:
        for k, v in map_data.items():
            if min_info and len(v) <= 1:
                continue
            print(k)
            for x in v:
                print(f'\t{x}')
    else:
        echo('\n'.join(map_data.keys()))
        return map_data


@cli.command('versions')
@cl.argument('name')
def versions_(name):
    data = list_()
    echo(data[name])


@cli.command('apply')
@cl.argument('rules_with_mode', metavar='rules', nargs=-1)
# @cl.option('-a', '--rules-append', multiple=True)
# @cl.option('-x', '--rules-except', multiple=True)
# @cl.option('-n', '--pre-add-all', is_flag=True)
def apply_(rules_with_mode):
    rules_data = read_rules()
    ruleset = []
    print(' '.join(rules_with_mode))
    for rule_name in rules_with_mode:
        if rule_name == '_all' or rule_name == '+all':
            continue
        ruleset.append({
            'mode': RuleMode.EXCEPT if rule_name[0] == '_' else RuleMode.APPEND,
            'rule': rules_data['ruleset'][rule_name[1:]]
        })
    print(ruleset)
    apply(ruleset, '_all' not in rules_with_mode)


def apply(ruleset, pre_add_all=True):
    map_data = list_()
    ids = [x for x in map_data.keys()] if pre_add_all else []
    for rule in ruleset:
        mode = rule['mode']
        rules = rule['rule']
        if mode == RuleMode.APPEND:
            for x in rules:
                if x not in ids:
                    ids.append(x)
        elif mode == RuleMode.EXCEPT:
            for x in rules:
                if x in ids:
                    ids.remove(x)
    print(ids)


# --add -r client --except -r server
def parse_rule_statement(statements):
    for statement in statements:
        pass


class OrderedArgsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        arg_list = getattr(namespace, 'ordered_args', None)
        if arg_list is None:
            arg_list = []
            setattr(namespace, 'ordered_args', arg_list)
        arg_list.append({'option': option_string, 'value': values})


def gen_rule(args):
    map_data = list_()
    result = []
    result.extend(map_data.keys())
    rule_data = read_rules()

    parsar1 = argparse.ArgumentParser()
    parsar1.add_argument('-a', '--append', nargs='?', action=OrderedArgsAction, const=str)
    parsar1.add_argument('-e', '--exclude', nargs='?', action=OrderedArgsAction, const=str)
    parsar1.add_argument('-c', '--current', nargs='?', action=OrderedArgsAction, const=str)
    parsar1.add_argument('-n', '--name')
    args1 = parsar1.parse_args(args[0])
    print(args1)
    for args_ in args1.ordered_args:
        match args_['option']:
            case '-a' | '--append':
                rule = rule_data['ruleset'][args_['value']]
                result.extend(y for y in rule if y not in result)
            case '-e' | '--exclude':
                rule = rule_data['ruleset'][args_['value']]
                for y in rule:
                    if y not in result:
                        continue
                    result.remove(y)
            case '-c' | '--current':
                mods = []
                for root, dirs, filenames in os.walk('.'):
                    mods.extend([x.rstrip('.jar') for x in filenames if x.endswith('.jar')])
                    break
                result.extend(y for y in mods if y not in result)

    echo(result)


def save(rule_name):
    mods = []
    for root, dirs, filenames in os.walk('.'):
        mods.extend([x.rstrip('.jar') for x in filenames if x.endswith('.jar')])
        break
    rules = read_rules()
    mod_rule = dict_safe_get(rules, 'ruleset', rule_name)
    mod_rule.clear()
    mod_rule.extend(mods)
    write_rules(rules)
    print(f'{rule_name}:{mods}')


@cli.command('save')
@cl.argument('rule_name')
def save_(rule_name):
    save(rule_name)


@cli.command()
@cl.option('-p', '--path', default='.')
def archive(path):
    last_loc = os.curdir
    os.chdir(path)
    files = []
    for root, dirs, filenames in os.walk(path):
        files.extend(filenames)
        break
    for file in files:
        if islink(file):
            if file.endswith('.old') or file.endswith('.disabled'):
                echo(f'[-] ({file})')
                os.unlink(file)
            continue
        if file.endswith('.jar') or file.endswith('.old') or file.endswith('.disabled'):
            echo(f'>>{file}')
            shutil.move(file, join(mods_available, file.rstrip('.old').rstrip('.disabled')))
    os.chdir(last_loc)


def select(pattern):
    map_data = list_()
    return [x for x in map_data.keys() if re.match(pattern, x)]


@cli.command('select')
@cl.argument('pattern')
def select_(pattern):
    print('\n'.join(select(pattern)))


if __name__ == '__main__':
    log.getLogger()

    pre_parser = argparse.ArgumentParser()
    pre_parser.add_argument('command', default=None)
    pre_args = pre_parser.parse_known_args()
    if pre_args[0].command == 'gen-rule':
        gen_rule(pre_args[1:])
    else:
        cli(obj={})

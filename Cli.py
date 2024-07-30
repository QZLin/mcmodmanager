import argparse
import json
import logging
import os
from os.path import join
from pathlib import PurePath
from typing import Dict, Literal, List, Any

import click
from click import echo

import DataUtil
import ModManager as Mn
import StrVersion
from DictUtil import nerd_get, nerd_dict_get, kv_print


class CustomCliGroup(click.Group):
    def command(self, *args, **kwargs):
        def decorator(f):
            aliases = kwargs.pop('aliases', None)
            if aliases and isinstance(aliases, list):
                name = kwargs.pop('name', None)
                if not name:
                    raise click.UsageError('name command argument is required when using aliases.')

                base_command = super(CustomCliGroup, self).command(name, *args, **kwargs)(f)

                for alias in aliases:
                    cmd = super(CustomCliGroup, self).command(alias, *args, **kwargs)(f)
                    cmd.help = f'Alias for "{name}".\n\n{cmd.help}'
                    cmd.params = base_command.params

                # return cmd
            else:
                # return \
                super(CustomCliGroup, self).command(*args, **kwargs)(f)

        return decorator


@click.group(cls=CustomCliGroup)
@click.option('--debug', '-d', is_flag=True, default=False)
@click.pass_context
def cli(ctx, debug):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug(ctx)


@cli.command()
def init():
    Mn.env_dir.init_dir()


@cli.command()
def env():
    kv_print(Mn.env_dir.__dict__)
    print()
    kv_print(Mn.env_file.__dict__)


@cli.command()
def rebuild():
    """
    completely rebuild mod library
    :return:
    """
    Mn.update_mode(rebuild_=True)


@cli.command()
def update():
    """
    only try to analyse new file, will not rebuild
    :return:
    """
    Mn.update_mode()


@cli.command()
@click.argument('file')
def add(file):
    pass


@cli.command(name='delete', aliases=['del', 'rm'])
@click.argument('name')
def delete(name):
    echo(name)
    mod = Mn.get_spec_mod(name)
    print(f'delete {mod.file.name} {mod.file}')
    os.remove(mod.file)


@cli.command()
@click.argument('path', required=False)
def fix(path=None):
    """
    try to fix broken symlink via link target
    :return:
    """
    if path is None:
        path = Mn.env_dir.mods_enabled
    jar_list = Mn.get_files(path, '.jar')
    link_list = [x for x in jar_list if x.is_symlink()]
    target_list = [x.readlink() for x in link_list]
    library = Mn.list_library()
    for link, mod in zip(link_list, target_list):
        versions = library[link.stem]
        version = [x for x in versions if x.file.name == mod.name]
        if len(version) != 1:
            logging.error(f'{link.name} not matched in {versions}')
            continue
        fixed_target = version[0].file
        Mn.enable(fixed_target, link.stem)


@cli.command(name='enable', aliases=['e'])
@click.argument('mod_id', metavar='name')
@click.argument('index', required=False, type=int, default=None)
@click.option('--auto', '-a', is_flag=True)
def enable(mod_id, index, auto):
    versions = Mn.get_version(mod_id, index, auto)
    if len(versions) != 1:
        echo('Select a version')
        format_print('versions', versions)
        return
    else:
        r = Mn.enable(versions[0].file, mod_id)
        if r is not None:
            echo(r)


@cli.command()
@click.argument('mod_id', metavar='name')
def disable(mod_id):
    file = join(Mn.env_dir.mods_enabled, f'{mod_id}.jar' if not mod_id.endswith('.jar') else mod_id)
    file = PurePath(file)
    Mn.disable(file)


@cli.command()
@click.argument('file')
def block(file):
    map_data = Mn.list_library()
    name = None
    for k, v in map_data.items():
        if file in v:
            name = k
            break
    if name is None:
        logging.warning(f'Not Found {file}')
        return
    echo(f'[Block] {file} of "{name}"')
    data = Mn.read_rules()

    obj = nerd_dict_get(data, name, 'block')
    if file not in obj:
        obj.append(file)
    Mn.write_rules(data)


@cli.command()
@click.argument('id_', metavar='id', required=False)
@click.option('-p', '--pattern')
@click.option('-s', '--server', is_flag=True)
@click.option('-c', '--client', is_flag=True)
@click.option('-f', '--flag', multiple=True)
def mark(id_, pattern, server, client, flag):
    ids = []
    if id_:
        ids.append(id_)
    if pattern:
        ids.extend(Mn.select(pattern))

    flags = []
    if server:
        flags.append('server')
    if client:
        flags.append('client')
    if flag is not None:
        flags.extend(flag)
    echo('Flags:' + ' '.join(flags))
    echo('\t' + '\n\t'.join(ids))
    all_rules = Mn.read_rules()
    for fl in flags:
        obj = nerd_dict_get(all_rules, 'ruleset', fl, fallback=[])
        obj.extend([x for x in ids if x not in obj])
    Mn.write_rules(all_rules)


def info_complete():
    pass


def format_print(data_type: Literal['mod_list', 'mod_lib', 'versions', 'map'],
                 data: Any, format_: Literal[None, 'strip', 'freeze', 'id'] = None):
    logging.debug(data)
    if data_type == 'mod_lib':
        data: Dict[str, List[str]]
        if format_ == 'id':
            format_print('mod_list', data.keys())
        else:
            for k in data.keys():
                StrVersion.sort_versions(data[k])
            for k, v in data.items():
                echo(k)
                for x in v:
                    echo(f'\t{x}')
    elif data_type == 'mod_list':
        data: List[str]
        if format_ == 'freeze':
            mapping = DataUtil.Data(Mn.env_file.mapping)
            echo('\n'.join(f'{x}=={mapping[x]}' for x in data))
            pass
        elif format_ == 'strip':
            echo('\n'.join((x.removesuffix('.jar') for x in data)))
        elif format_ == 'id':
            pass
        else:
            echo('\n'.join(data))
    elif data_type == 'versions':
        data: List[DataUtil.ModFileInfo]
        echo('\n'.join([f'{i} -- {x.file.name}' for i, x in enumerate(data)]))
    elif data_type == 'map':
        data: dict
        for k, v in data.items():
            echo(f'{k}=={v}')


@cli.command(name='list', aliases=['ls'])
@click.option('format_', '-f', metavar='format', type=click.Choice(('simple', 'strip', 'tree', 'freeze', 'id')))
# @click.option('--tree', '-t', is_flag=True)
@click.option('--all-mods', '-a', is_flag=True)
# @click.option('--min', '-m', 'min_info', is_flag=True)
def list_mods_(format_, all_mods):
    if all_mods:
        mods = Mn.list_library()
        format_print('mod_lib', mods, format_)
    else:
        mods = Mn.ls_mods()
        format_print('mod_list', mods, format_)


@cli.command(name='versions', aliases=['v'])
@click.argument('name')
def versions_(name):
    format_print('versions', Mn.get_version(name))


@cli.command()
@click.argument('rules_with_mode', metavar='rules', nargs=-1)
# @cl.option('-a', '--rules-append', multiple=True)
# @cl.option('-x', '--rules-except', multiple=True)
# @cl.option('-n', '--pre-add-all', is_flag=True)
def apply(rules_with_mode):
    """
    If version select property not specify, latest version will selected
    :param rules_with_mode:
    :return:
    """
    rules_data = Mn.read_rules()
    ruleset = []
    echo(' '.join(rules_with_mode))
    for rule_name in rules_with_mode:
        if rule_name == '_all' or rule_name == '+all':
            continue
        ruleset.append({
            'mode': Mn.RuleMode.EXCEPT if rule_name[0] == '_' else Mn.RuleMode.APPEND,
            'rule': rules_data['ruleset'][rule_name[1:]]
        })
    logging.debug(ruleset)
    echo(Mn.apply(ruleset, '_all' not in rules_with_mode))


# --add -r client --except -r server
def parse_rule_statement(statements):
    for statement in statements:
        pass


class OrderedArgsAction(argparse.Action):
    NAME = 'ordered_args'

    def __call__(self, parser, namespace, values, option_string=None):
        arg_list = getattr(namespace, self.NAME, None)
        if arg_list is None:
            arg_list = []
            setattr(namespace, self.NAME, arg_list)
        arg_list.append({'option': option_string, 'value': values})


def gen_rule(args):
    map_data = Mn.list_library()
    result = []
    result.extend(map_data.keys())
    rule_data = Mn.read_rules()

    parsar1 = argparse.ArgumentParser()

    parsar1.add_argument('-a', '--append', nargs='?', action=OrderedArgsAction, const=str)
    parsar1.add_argument('-e', '--exclude', nargs='?', action=OrderedArgsAction, const=str)
    parsar1.add_argument('-c', '--current', nargs='?', action=OrderedArgsAction, const=str)
    parsar1.add_argument('-n', '--name')
    args1 = parsar1.parse_args(args[0])
    logging.debug(args1)
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
                mods = (x for x in next(os.walk('.'))[2] if x.endswith('.jar'))
                result.extend(y for y in mods if y not in result)
    if args1.name:
        obj = nerd_dict_get(rule_data, 'ruleset', args1.name)
        obj.extend(result)
        Mn.write_rules(rule_data)

    echo(result)


def save(rule_name, preview=False):
    mods = Mn.get_files(Mn.env_dir.mods_available)
    if preview:
        echo('\n'.join(mods))
        return mods
    rules = Mn.read_rules()
    mod_rule = nerd_get(rules, ('ruleset', {}), (rule_name, []))
    mod_rule.clear()
    mod_rule.extend(mods)
    Mn.write_rules(rules)
    echo(f'{rule_name}:{mods}')
    return mods


@cli.command('save')
@click.argument('rule_name')
@click.option('-l', '--list-only', is_flag=True, required=False)
def save_(rule_name, list_only):
    save(rule_name, preview=list_only)


@cli.command()
def clean():
    Mn.clean(os.curdir)


@cli.command('import')
@click.argument('path')
@click.option('--read-only', '-R', is_flag=True)
def import_(path, read_only):
    """
    Import mods config from a mods folder

    :param read_only:
    :param path:
    :return:
    """
    mods = Mn.ls_mods(path)
    id_list = []
    for x in mods:
        data, type_ = Mn.mod_metadata(join(path, x))
        if data is None:
            continue
        data = json.loads(data)
        id_list.append(data['id'])
    format_print('mod_list', id_list)


@cli.command()
@click.option('-i', '--interactive', default=False)
@click.option('-p', '--path', default=None)
@click.option('-u', '--upgrade', is_flag=True)
def archive(path, upgrade=True, interactive=False):
    if path is None:
        path = Mn.env_dir.mods_enabled
    dis, old, new = Mn.archive_dir(path)
    print(' '.join([x.stem for x in old]))


@cli.command(name='select', aliases=['sl'])
@click.argument('pattern')
def select(pattern):
    format_print('mod_list', Mn.select(pattern))


@cli.command('rules')
def rules_():
    print(Mn.read_rules())


if __name__ == '__main__':
    logging.getLogger()
    logging.basicConfig(format='[%(asctime)s %(levelname)s] [%(funcName)s]: %(message)s', datefmt='%H:%M:%S')

    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('command', default=None, nargs='?')
    pre_parser.add_argument('-d', '--debug', action='store_true')
    pre_parser.add_argument('--ide-debug', action='store_true')
    pre_args = pre_parser.parse_known_args()
    dbg_args = None
    if pre_args[0].ide_debug:
        logging.getLogger().setLevel(logging.DEBUG)
        dbg_args = input("input args:").split(' ')
        if 'mcm' in dbg_args:
            dbg_args.remove('mcm')
    if pre_args[0].debug:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.debug('Pre-Parsing finished')
    if pre_args[0].command == 'gen-rule':
        gen_rule(pre_args[1:])
    else:
        if dbg_args is not None:
            cli(args=dbg_args)
        else:
            cli(obj={})

import argparse

import click

from ModManager import *


@click.group()
@click.option('--debug', '-d', is_flag=True, default=False)
@click.pass_context
def cli(ctx, debug):
    if not debug:
        return
    log.getLogger().setLevel(log.DEBUG)
    log.debug(ctx)
    # input('Attach debugger to process and press enter...')
    # import sys, threading, importlib.abc
    #
    # class NotificationFinder(importlib.abc.MetaPathFinder):
    #     def find_spec(self, fullname, _path, _target=None):
    #         if 'pydevd' in fullname:
    #             with t:
    #                 t.notify()
    #
    # t = threading.Condition()
    # sys.meta_path.insert(0, NotificationFinder())

    # with t:
    #     t.wait()


@cli.command('init')
def init_():
    init_dir()


@cli.command('rebuild')
def rebuild_():
    gen_metadata(mods_available, dir_metadata)
    read_metadata(dir_metadata, rebuild=True)


@cli.command('enable')
@click.argument('mod_id', metavar='name')
@click.argument('index', required=False, type=int, default=None)
@click.option('--auto', '-a', is_flag=True)
def enable_(mod_id, index, auto):
    versions = get_version(mod_id, index, auto)

    if len(versions) != 1:
        echo('Select a version')
        echo('\n'.join([f'{i} -- {x}' for i, x in enumerate(versions)]))
        return
    else:
        enable(versions[0], mod_id)


@cli.command('disable')
@click.argument('mod_id')
def disable_(mod_id):
    file = f'{mod_id}.jar' if not mod_id.endswith('.jar') else mod_id
    disable(file)


@cli.command()
@click.argument('file')
def block(file):
    map_data = list_mods()
    name = None
    for k, v in map_data.items():
        if file in v:
            name = k
            break
    if name is None:
        log.warning(f'Not Found {file}')
        return
    echo(f'[Block] {file} of "{name}"')
    data = read_rules()

    obj = nerd_dict_get(data, name, 'block')
    if file not in obj:
        obj.append(file)
    write_rules(data)


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
        obj = nerd_dict_get(rules, 'ruleset', fl, obj=[])
        obj.extend([x for x in ids if x not in obj])
    write_rules(rules)


@cli.command('list')
@click.option('format_', '-f', metavar='format', type=click.Choice(('tree', 'freeze')))
# @click.option('--tree', '-t', is_flag=True)
@click.option('--min', '-m', 'min_info', is_flag=True)
def list_mods_(format_, min_info):
    map_data = list_mods()

    if format_ == 'tree':
        for k, v in map_data.items():
            if min_info and len(v) <= 1:
                continue
            print(k)
            for x in v:
                print(f'\t{x}')
    elif format_ == 'freeze':
        pass
    else:
        echo('\n'.join(map_data.keys()))
        return map_data


@cli.command()
@click.option('format_', '-f', metavar='format', type=click.Choice(('tree', 'freeze')))
def ls(format_):
    mods = ls_mods()
    if format_ == 'freeze':
        print('\n'.join(mods))
    else:
        print('\n'.join(mods))


@cli.command('versions')
@click.argument('name')
def versions_(name):
    versions = get_version(name)
    echo('\n'.join([f'{i} -- {x}' for i, x in enumerate(versions)]))


@cli.command('apply')
@click.argument('rules_with_mode', metavar='rules', nargs=-1)
# @cl.option('-a', '--rules-append', multiple=True)
# @cl.option('-x', '--rules-except', multiple=True)
# @cl.option('-n', '--pre-add-all', is_flag=True)
def apply_(rules_with_mode):
    """
    If version select property not specify, latest version will selected
    :param rules_with_mode:
    :return:
    """
    rules_data = read_rules()
    ruleset = []
    echo(' '.join(rules_with_mode))
    for rule_name in rules_with_mode:
        if rule_name == '_all' or rule_name == '+all':
            continue
        ruleset.append({
            'mode': RuleMode.EXCEPT if rule_name[0] == '_' else RuleMode.APPEND,
            'rule': rules_data['ruleset'][rule_name[1:]]
        })
    log.debug(ruleset)
    echo(apply(ruleset, '_all' not in rules_with_mode))


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
    map_data = list_mods()
    result = []
    result.extend(map_data.keys())
    rule_data = read_rules()

    parsar1 = argparse.ArgumentParser()

    parsar1.add_argument('-a', '--append', nargs='?', action=OrderedArgsAction, const=str)
    parsar1.add_argument('-e', '--exclude', nargs='?', action=OrderedArgsAction, const=str)
    parsar1.add_argument('-c', '--current', nargs='?', action=OrderedArgsAction, const=str)
    parsar1.add_argument('-n', '--name')
    args1 = parsar1.parse_args(args[0])
    log.debug(args1)
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
                    mods.extend([x.removesuffix('.jar') for x in filenames if x.endswith('.jar')])
                    break
                result.extend(y for y in mods if y not in result)
    if args1.name:
        obj = nerd_dict_get(rule_data, 'ruleset', args1.name)
        obj.extend(result)
        write_rules(rule_data)

    echo(result)


def save(rule_name, preview=False):
    mods = []
    for root, dirs, filenames in os.walk('.'):
        mods.extend([x.removesuffix('.jar') for x in filenames if x.endswith('.jar')])
        break
    if preview:
        echo('\n'.join(mods))
        return mods
    rules = read_rules()
    mod_rule = nerd_dict_get(rules, 'ruleset', rule_name)
    mod_rule.clear()
    mod_rule.extend(mods)
    write_rules(rules)
    echo(f'{rule_name}:{mods}')
    return mods


@cli.command('save')
@click.argument('rule_name')
@click.option('-l', '--list-only', is_flag=True, required=False)
def save_(rule_name, list_only):
    save(rule_name, preview=list_only)


@cli.command('clean')
def clean_():
    clean(os.curdir)


@cli.command('archive')
@click.option('-p', '--path', default='.')
@click.option('-u', '--upgrade', is_flag=True)
def archive_(path, upgrade=True):
    a, b = archive(path)
    echo('[UNLINK]:')
    echo('\n'.join(a))
    echo('[ARCHIVE]:')
    echo('\n'.join(b))
    if upgrade:
        echo('[Upgrade]:')
        mods = [x.removesuffix('.old').removesuffix('.disabled').removesuffix('.jar') for x in b]
        gen_metadata(mods_available, dir_metadata)
        read_metadata(dir_metadata, rebuild=True)
        map_data = list_mods()
        for x in mods:
            enable_auto(x, map_data)


@cli.command('select')
@click.argument('pattern')
def select_(pattern):
    echo('\n'.join(select(pattern)))


if __name__ == '__main__':
    log.getLogger()
    log.basicConfig(format='[%(asctime)s %(levelname)s] [%(funcName)s]: %(message)s', datefmt='%H:%M:%S')

    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('command', default=None, nargs='?')
    pre_parser.add_argument('-d', '--debug', action='store_true')
    pre_args = pre_parser.parse_known_args()
    if pre_args[0].debug:
        log.getLogger().setLevel(log.DEBUG)
    log.debug('Pre-Parsing finished')
    if pre_args[0].command == 'gen-rule':
        gen_rule(pre_args[1:])
    else:
        cli(obj={})

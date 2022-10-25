import argparse

import click

from ModManager import *


@click.group()
@click.option('--debug', '-d', is_flag=True, default=False)
@click.pass_context
def cli(ctx, debug):
    if debug:
        log.getLogger().setLevel(log.DEBUG)
        log.debug(ctx)


@cli.command('init')
def init_():
    init_dir()


@cli.command('rebuild')
def rebuild_():
    gen_metadata(mods_available, dir_metadata)
    read_metadata(dir_metadata, rebuild=True)


@cli.command('enable')
@click.argument('mod_id', metavar='name')
@click.argument('index', required=False, type=int, default=-1)
@click.option('--auto', '-a', is_flag=True)
def enable_(mod_id, index, auto):
    map_data = list_mods()
    versions = map_data[mod_id]
    str_version.sort_versions(versions)
    if len(versions) != 1:
        if index != -1:
            mod_file = versions[index]
        elif auto:
            enable_auto(mod_id, map_data)
            return
        else:
            echo('\n'.join([f'{i} -- {x}' for i, x in enumerate(versions)]))
            return
    else:
        mod_file = versions[0]
    enable(mod_file, mod_id)


@cli.command('disable')
@click.argument('mod_id')
def disable_(mod_id):
    file = f'{mod_id}.jar' if not mod_id.endswith('.jar') else mod_id
    if exists(file) or islink(file):
        os.remove(file)
        echo(f'[Unlink]: {file}')
    else:
        log.warning(f'NotFound {file}')


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


@cli.command('ls')
@click.option('--tree', '-t', is_flag=True)
@click.option('--min', '-m', 'min_info', is_flag=True)
def list_mods_(tree, min_info):
    map_data = list_mods()

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
@click.argument('name')
def versions_(name):
    data = list_mods()
    str_version.sort_versions(data[name])
    echo(data[name])


@cli.command('apply')
@click.argument('rules_with_mode', metavar='rules', nargs=-1)
# @cl.option('-a', '--rules-append', multiple=True)
# @cl.option('-x', '--rules-except', multiple=True)
# @cl.option('-n', '--pre-add-all', is_flag=True)
def apply_(rules_with_mode):
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
def archive_(path):
    a, b = archive(path)
    echo('[UNLINK]:')
    echo('\n'.join(a))
    echo('[ARCHIVE]:')
    echo('\n'.join(b))


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
    log.debug('Pre-Parser end')
    if pre_args[0].command == 'gen-rule':
        gen_rule(pre_args[1:])
    else:
        cli(obj={})

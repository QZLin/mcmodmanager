from os import walk, rename


def _handle(list1, list2, file):
    length = len(file)
    if length < 4:
        return
    if file[-4:] == '.jar':
        list1.append(file)
        return
    if length < 9:
        return
    if file[-9:] == '.disabled':
        list2.append(file)
        return
    return


def get_jars(publish=False):
    jars = []
    disables = []
    for root, dirs, files in walk(".", topdown=True):
        for name in files:
            if root == '.':
                _handle(jars, disables, name)
        # for name in dirs:
        #     print(os.path.join(root, name))
    if publish:
        return jars
    else:
        return jars, disables


def encode(jars):
    code = ''
    for jar in jars:
        code += jar + ':'
    return code


def decode(code):
    result = code.split(':')
    result.remove('')
    return result


ERR_LOST = 0
ENABLE = 1
DISABLE = 2


def handle_file(err_type, file):
    if err_type == ERR_LOST:
        print('lost', file)
    elif err_type == ENABLE:
        print('enable', file)
        try:
            rename(file + '.disabled', file)
        except FileNotFoundError:
            print('err', 'rename %s->%s' % (file + '.disabled', file))
        except FileExistsError:
            print('File:%s exist' % file)
    elif err_type == DISABLE:
        print('disable', file)
        try:
            rename(file, file + '.disabled')
        except FileNotFoundError:
            print('err', 'rename %s->%s' % (file, file + '.disabled'))
        except FileExistsError:
            print('File:%s exist' % file + '.disabled')


def compare(jars, jars_local):
    local, disables = jars_local
    lost = []
    for jar in jars:
        if jar in local:
            pass
        else:
            if jar + '.disabled' in disables:
                handle_file(ENABLE, jar)
            else:
                handle_file(ERR_LOST, jar)
                lost.append(jar)
    for jar in local:
        if jar in jars:
            pass
        else:
            handle_file(DISABLE, jar)
    if len(lost) >= 1:
        return lost


if __name__ == '__main__':
    try:
        mode = int(input('select mode:\n0 load[default]\n1 publish\nmode:'))
    except ValueError:
        mode = 0
    except TypeError:
        mode = 0

    if mode == 0:
        txt = input('code:').replace('\n', '')
        compare(decode(txt), get_jars())
    elif mode == 1:
        txt = encode(get_jars(publish=True))
        # i = 1
        # out = ''
        # for x in txt:
        #     out += x
        #     if i % 30 == 0:
        #         out += '\n'
        #     i += 1
        # txt = out
        print(txt)

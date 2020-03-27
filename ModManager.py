from os import walk, rename

jar_path = '../'
SPLIT_CHAR = ':'
TYPE_JAR = '.jar'
TYPE_DISABLED = '.disabled'


def _handle(list1, list2, file):
    # list1,list2 (share) <- jars,disables
    length = len(file)
    if length < 4:
        return
    if file[-4:] == TYPE_JAR:
        list1.append(file)
        return

    if length < 9:
        return
    if file[-9:] == TYPE_DISABLED:
        list2.append(file)
        return

    return


def set_root(path):
    global jar_path
    jar_path = path


def get_jars(publish=False):
    jars, disables = [], []
    for root, dirs, files in walk(jar_path, topdown=True):
        if root == root:
            for name in files:
                _handle(jars, disables, name)
        break
    return jars if publish else (jars, disables)


def encode(jars):
    code = SPLIT_CHAR.join(jars)
    return code


def decode(code):
    result = code.split(SPLIT_CHAR)
    try:
        result.remove('')
    except ValueError:
        pass

    return result


ERR_LOST = 0
ENABLE = 1
DISABLE = 2


def handle_file(handle_type, file):
    if handle_type == ERR_LOST:
        print('lost', file)
    elif handle_type == ENABLE:
        print('enable', file)
        try:
            rename(file + TYPE_DISABLED, file)
        except FileNotFoundError:
            print('err', 'rename %s->%s' % (file + TYPE_DISABLED, file))
        except FileExistsError:
            print('File:%s exist' % file)
    elif handle_type == DISABLE:
        print('disable', file)
        try:
            rename(file, file + TYPE_DISABLED)
        except FileNotFoundError:
            print('err', 'rename %s->%s' % (file, file + TYPE_DISABLED))
        except FileExistsError:
            print('File:%s exist' % file + TYPE_DISABLED)


def compare(jars, jars_local):
    local_jars, disables = jars_local
    lost = []
    for jar in jars:
        # (jar in code) in local or not
        if jar in local_jars:
            pass
        else:
            if jar + TYPE_DISABLED in disables:
                handle_file(ENABLE, jar)
            else:
                handle_file(ERR_LOST, jar)
                lost.append(jar)
    for jar in local_jars:
        # local jars contain unexpected jar or not
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
        txt = input('code:')
        compare(decode(txt), get_jars())
    elif mode == 1:
        txt = encode(get_jars(publish=True))
        print(txt)

from typing import Any, Tuple


def nerd_dict_get(dict_: dict, *keys, fallback=None):
    if fallback is None:
        fallback = []
    next_obj = dict_
    for i, key in enumerate(keys):
        if key in next_obj.keys():
            next_obj = next_obj[key]
            continue
        if i == len(keys) - 1:
            next_obj[key] = fallback
            next_obj = fallback
        else:
            next_obj[key] = {}
            next_obj = next_obj[key]
    return next_obj


def nerd_get(obj: dict, *pairs: Tuple[Any, Any]):
    next_obj = obj
    for pair in pairs:
        key, value = pair
        if key in obj.keys():
            next_obj = obj[key]
        else:
            next_obj[key] = value
    return next_obj


def kv_print(data: dict, end='\n'):
    print('\n'.join(f'{k}: {v}' for k, v in data.items()), end=end)

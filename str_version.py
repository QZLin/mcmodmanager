import re
from operator import itemgetter


def version2nums(name):
    r = re.findall('\\d+', name)
    return [int(x) for x in r]


def sort_versions(versions):
    nums_list = []
    version_nums = {}
    for x in versions:
        nums_list.append(nums := version2nums(x))
        version_nums[x] = nums

    min_len = min([len(x) for x in nums_list])
    nums_list.sort(key=itemgetter(*[x for x in range(min_len)]), reverse=True)
    versions.sort(key=lambda y: nums_list.index(version_nums[y]))

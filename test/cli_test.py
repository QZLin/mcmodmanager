import os
import unittest
import cli
from ModManager import *
from str_version import *

if __name__ == '__main__':
    push_d(r'C:\vmo\minecraft\.minecraft-fabric\mods')
    print(get_cfgs('conf/mixin'))
    pop_d()

    la = ['sodium-extra-0.4.10+mc1.19.2-build.64.jar', 'sodium-extra-0.4.11+mc1.19.2-build.68.jar',
          'sodium-extra-0.4.7+mc1.19.2-build.52.jar', 'sodium-extra-0.4.9+mc1.19.2-build.60.jar']
    sort_versions(la)
    print('\n'.join(la))

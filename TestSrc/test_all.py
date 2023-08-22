import unittest
from os.path import join

res_root = 'res'


class MyTestCase(unittest.TestCase):
    def test_mixconfig(self):
        import MixConfig
        res = join(res_root, 'mix')
        r = MixConfig.Config.mixed_config(res, res + '/mix.d', 'mix')
        print(r)
        self.assertEqual(r, {'a': 1, 'b': 1, 'c': 1, 'd': 1, 'e': 1})

    def test_rule_exp(self):
        import rule_expression as exp
        test = '((a+b-c)+a1)+b_1+$TestSrc'
        ast = exp.to_ast(test)
        print(exp.debug_tokens(ast))

        rules1 = {'a': [1, 2, 3], 'b': [4, 5, 6], 'c': [2, 4, 6], 'a1': [2], 'b_1': [4], '$TestSrc': [0]}
        r = exp.execute(ast, rules1)
        print(r)
        r.sort()
        self.assertEqual(r, [x for x in range(0, 6)])

    def test_read_mod(self):
        import ModManager
        ModManager.mod_metadata(r'C:\vmo\minecraft\.minecraft-fabric\mods\MouseTweaks-fabric-mc1.20-2.25.jar')
        return self.assertTrue(True)

    def test_mix_config(self):
        import MixConfig
        print(MixConfig.Mixed.load('TestSrc/res/mix/mix.yaml'))
        return self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

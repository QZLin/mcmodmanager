from UtilLib.DataUtil import Data

a = Data('a.json', delay_write=True)
print(a)
a['ab'] = True
a['cd'] = True
a['ef'] = True
a.write()

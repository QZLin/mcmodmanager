import zipfile

# 默认模式r,读
azip = zipfile.ZipFile('BetterFps-1.4.8.jar')  # ['bb/', 'bb/aa.txt']
# 返回所有文件夹和文件
print(azip.namelist())
# # 返回该zip的文件名
print(azip.filename)
'''
# 压缩文件里bb文件夹下的aa.txt
azip_info = azip.getinfo('bb/aa.txt')
# 原来文件大小
print(azip_info.file_size)
# 压缩后大小
print(azip_info.compress_size)

# 这样可以求得压缩率，保留小数点后两位
print('压缩率为{:.2f}'.format(azip_info.file_size/azip_info.compress_size))
'''

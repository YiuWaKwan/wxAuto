import subprocess

import pymysql
import subprocess
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis

app_name='CopyFile-v1.5.apk'
BASEDIR = os.getcwd()

# 初始化logger
logger = getLogger('./log/installApp.log')
# # 初始化config
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)

DEV_ID = confAllItems.getOneOptions('devInfo', 'dev')

db = pymysql.connect(host = '103.203.1.179', port = 49606, user = 'wxAuto', passwd = '^B93kU)>k8', db = 'wxAuto', charset="utf8")
#db = pymysql.connect(host = '121.11.152.185', port = 8001, user = 'wxAuto', passwd = 'b2PI2vD&FFSL', db = 'wxAuto', charset="utf8")

cursor = db.cursor()
cursor.execute("select devport from wx_machine_info where clientId='%s'" % DEV_ID)
data = cursor.fetchall()

#打印获取到的数据
if data is not None:
    portList = [i.split('\t')[0] for i in
     subprocess.check_output("adb devices").decode(encoding="utf-8").split('\r\n')
     if ':' in i and 'device' in i]
    print(portList)
    for machinfo in data:

        if '127.0.0.1:%s'%machinfo[0] in portList:
            print('adb -s  127.0.0.1:%s install -r data/%s' % (machinfo[0], app_name))
            # print('adb connect 127.0.0.1:%s' % machinfo[0])
            # subprocess.check_output('adb connect 127.0.0.1:%s' % machinfo[0])
            subprocess.check_output('adb -s  127.0.0.1:%s install -r data/%s' % (machinfo[0],app_name))
#关闭游标和数据库的连接
cursor.close()
db.close()



#

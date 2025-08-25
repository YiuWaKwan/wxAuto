# -*- coding: utf-8 -*-

# @Time    : 2018/7/25 19:25
# @Author  : xiaoguobiao
# @File    : scheduleTask.py

import os
import re
import subprocess
import time
import schedule
from lib.FinalLogger import getLogger
from lib.ModuleConfig import ConfAnalysis
from tools import MysqlDbPool,Monitor
from actionModule import wxDataClear

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/scheduleTask.log')
# 初始化config
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)

user_list = confAllItems.getOneOptions("alarm", "user_list1")
alarm_server = confAllItems.getOneOptions("alarm", "alarm_server")
dev_id = confAllItems.getOneOptions("devInfo", "dev")

BASEDIR = os.getcwd()

def main(mySqlUtil):
    logger.info("begin monitor task..")
    # 获取当前adb 进程号
    adbInitPort = [re.split(r" +", i.strip())[1]
                   for i in subprocess.check_output("tasklist|findstr adb",
                                                    shell=True)
                       .decode(encoding="utf-8")
                       .split("K\r\n") if i]
    if len(adbInitPort) != 1 :
        logger.warn("adb 进程数量异常，请先进行清理，确保只有一个adb进程")
        return
    else:
        logger.info("adb init Port :%s" %adbInitPort[0])
    # taskMonitor
    # schedule.every(1).minutes.do(taskMonitor.start_monitor,mySqlUtil)
    # schedule.every(5).seconds.do(taskMonitor.logMonitor,"multiTaskAction.log")

    # getGroupHeadPic every 10 mins
    # schedule.every(10).minutes.do(getGroupHeadPic.scanGroupInfo, mySqlUtil)

    # tools.Monitor
    hdMonitor = Monitor.hdMonitor(logger, BASEDIR)
    monitorServer = Monitor.monitorServer(logger, BASEDIR, adbInitPort[0])

    # 好友添加信息汇报,每天九点半进行信息汇报
    schedule.every().day.at("09:30").do(Monitor.friendSummaryMonitor, dev_id,mySqlUtil,logger,alarm_server,user_list)

    # 清理微信数据
    schedule.every().day.at("01:30").do(wxDataClear.dbClearEntry, mySqlUtil, logger)
    schedule.every().day.at("02:30").do(wxDataClear.taskGenerate, mySqlUtil, logger)
    schedule.every().day.at("07:30").do(wxDataClear.wxDataTaskMsg, mySqlUtil, logger)


    while True:
        schedule.run_pending()
        hdMonitor.run()
        monitorServer.run()
        time.sleep(5)


if __name__ == '__main__':
    mySqlUtil = MysqlDbPool.MysqlDbPool()
    main(mySqlUtil)

    # wxDataClear.taskGenerate(mySqlUtil, logger)
    # wxDataClear.wxDataTaskMsg(mySqlUtil, logger)

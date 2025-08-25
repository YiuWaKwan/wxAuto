# -*- coding: utf-8 -*-

# @Time    : 2018/7/25 17:09
# @Author  : xiaoguobiao
# @File    : taskMonitor.py

import datetime
import random
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
from tools import MysqlDbPool
import urllib.request

os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.AL32UTF8'

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/taskMonitor.log')
# 初始化config
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)

user_list = confAllItems.getOneOptions("alarm", "user_list")
alarm_server = confAllItems.getOneOptions("alarm", "alarm_server")
dev_id = confAllItems.getOneOptions("devInfo", "dev")

def start_monitor(mySqlUtil):
    logger.info("开始扫描任务执行情况")
    try:
        type_dict = {}
        get_type_sql = "select name,value from wx_dictionary where type = 'task_type'"
        type_info = mySqlUtil.getData(get_type_sql)
        if type_info and len(type_info) > 0:
            for item in type_info:
                type_dict[item[1]] = item[0]

        get_task_list_sql = "SELECT a.taskSeq, a.actionType, a.startTime,a.endTime,b.wx_name,b.client_id, now() " \
                            " FROM wx_task_manage a LEFT JOIN wx_account_info b ON " \
                            " a.uuid = b.uuid WHERE DATE_FORMAT(createTime, '%Y%m%d') = DATE_FORMAT(NOW(), '%Y%m%d') " \
                            " and alarm = '0' and a.actionType !='19' "

        task_list_result = list(mySqlUtil.getData(get_task_list_sql))
        if len(task_list_result) > 0:
            for item in task_list_result:
                taskSeq = item[0]
                actionType = item[1]
                startTime = item[2]
                endTime = item[3]
                wx_name = item[4]
                client_id = item[5]
                now_time = item[6]
                if str(actionType) in type_dict :
                    if startTime is not None:
                        if endTime is not None:
                            # run_time = (endTime - startTime).seconds
                            # if run_time > 60:
                            #     msg = "客户机%s上，昵称：%s，完成 %s 任务耗时超过1分钟，请关注" % (client_id, wx_name, type_dict[str(actionType)])
                            #     alarm(msg)
                            #     update_alarm_sql = "update wx_task_manage set alarm = '2' where taskSeq = '%s' " % taskSeq
                            #     logger.info(update_alarm_sql)
                            #     mySqlUtil.excSql(update_alarm_sql)
                            # else:
                            update_alarm_sql = "update wx_task_manage set alarm = '1' where taskSeq = '%s' " % taskSeq
                            logger.info(update_alarm_sql)
                            mySqlUtil.excSql(update_alarm_sql)
                        elif endTime is None:
                            if now_time > startTime + datetime.timedelta(seconds=300):
                                msg = "客户机%s上，昵称：%s，%s 任务已执行超过5分钟，请检查重启" % (client_id, wx_name, type_dict[str(actionType)])
                                alarm(msg)
                                update_alarm_sql = "update wx_task_manage set alarm = '2',status='3' where taskSeq = '%s' " % taskSeq
                                mySqlUtil.excSql(update_alarm_sql)

        # 关联不上虚拟机的微信账号
        sql = "select wx_name from wx_account_info where (client_id = '' or devId = '') and wx_status='1'"
        machineErrInfoList = list(mySqlUtil.getData(sql))
        if len(machineErrInfoList) > 0:
            for item in machineErrInfoList:
                msg = "微信模拟器信息为空： 微信[%s] " % (item[0])
                alarm(msg)
        # 关联虚拟机信息有误
        sql = "select wx_name,client_id,devId from wx_account_info a where wx_status='1' and not exists (select uuid from wx_machine_info i where clientid = a.client_id and devId = a.devId) and client_id <> '' and devId<>'' "
        machineErrInfoList = list(mySqlUtil.getData(sql))
        if len(machineErrInfoList) > 0:
            for item in machineErrInfoList:
                msg = "微信模拟器信息有误，找不到对应模拟器： 微信[%s] clientid[%s] devId[%s] " % (item[0], item[1], item[2])
                alarm(msg)
        # 微信UUID与虚拟机UUID不匹配的微信号
        sql = "select wx_name,uuid from wx_account_info a where wx_status='1' and uuid not in (select uuid from wx_machine_info i where clientid = a.client_id and devId = a.devId) "
        machineErrInfoList = list(mySqlUtil.getData(sql))
        if len(machineErrInfoList) > 0:
            for item in machineErrInfoList:
                msg = "微信模拟器信息有误，UUID不匹配： 微信[%s] uuid[%s] " % (item[0], item[1])
                alarm(msg)

        #消息接收模拟器停止运行
        sql="select a.wx_id,a.wx_name,a.uuid from wx_status_check c, wx_account_info a where c.wx_main_id=a.wx_id and c.state='1' and a.wx_status='1' and a.if_start = 1 and last_heartbeat_time < SUBDATE(now(),interval 3 minute)"
        appStopInfoList = list(mySqlUtil.getData(sql))
        if len(appStopInfoList) > 0:
            for item in appStopInfoList:
                #msg="微信["+item[1]+"]对应的消息接收程序停止运行，目前尝试恢复"
                #alarm(msg)
                #生成任务信息
                sql = "INSERT INTO wx_task_manage(taskSeq,uuid,actionType,createTime,status,priority)VALUES(%d,'%s',26,now(),1,1)" % (
                    round(time.time() * 1000 + random.randint(100, 999)), item[2])
                mySqlUtil.excSql(sql)
                #改变告警状态
                sql = "update wx_status_check set state='2' where wx_main_id='%s'" % item[0]
                mySqlUtil.excSql(sql)
    except(Exception) as error:
        logger.exception(error)
    finally:
        logger.info("扫描任务执行情况结束")

def alarm(msg):
    msg = urllib.parse.quote(msg)
    warn_msg = "%s?msg=%s&type=2&user=%s&creator=maizq" % (alarm_server, msg, user_list)
    logger.info(warn_msg)
    warning(warn_msg)

def warning(url):
    http_client=urllib.request.urlopen(url, timeout = 5)
    print(http_client.read())
    return http_client.read()

#监控multi运行日志的进程，判断最后一条日志与当前时间的差距是否超过30秒
def logMonitor(log_file):
    try:
        import time
        today = time.strftime("%Y-%m-%d")
        logFilePath=os.path.join("log",str(log_file)+"."+today)
        last_line=""
        if os.path.exists(logFilePath):
            with open(logFilePath, 'r',encoding='utf8') as f:
                lines = f.readlines()  # 读取所有行
                last_line = lines[-1]  # 取最后一行
                f.close()
            if last_line:
                last_time_str=last_line.split(",")[0]
                time = datetime.datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')#2018-11-16 10:25:36
                Intervals=(datetime.datetime.now() - time).seconds
                if Intervals and int(Intervals)>30:
                    msg=str(dev_id)+":"+str(log_file)+"日志超过30秒没刷新，请检查程序是否异常！"
                    logger.info(msg)
                    alarm(msg)
    except Exception as e:
        logger.info("监控程序异常："+str(e))
if __name__ == '__main__':
    mysqlPool = MysqlDbPool.MysqlDbPool()
    start_monitor(mysqlPool)

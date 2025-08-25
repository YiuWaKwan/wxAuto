#!/usr/bin/python
# -*- coding: UTF-8 -*-
import json
import os
import traceback
import pymysql
import time
import signal
import logging
import logging.handlers
import logging.config
from logging.handlers import TimedRotatingFileHandler
import requests
from DBUtils.PooledDB import PooledDB
dev_name="服务器：121.11.152.188"
log_file_name='./logs/sendMsgTaskMonitor.log'
# MysqlConfig = {
#     'host': '103.203.1.179',
#     'port':49606 ,
#     'user': 'wxAuto',
#     'password': '^B93kU)>k8',
#     'db': 'wxAuto',
#     'charset': 'utf8mb4',
# }
# MysqlConfig = {
#     'host': '172.51.82.19',
#     'port':8001 ,
#     'user': 'wxAuto',
#     'password': 'b2PI2vD&FFSL',
#     'db': 'wxAuto',  # TODO
#     'charset': 'utf8mb4',
# }
errmsgsenduser = "shijx|luol|yangy|xiaogb|maizq|yinlw|ouzhiyong"
errmsgsenduser_dev = "luol"
errmsgsendurl = "http://124.172.189.98/wechat/send_err_msg/?msg=%s&type=NETWORK&user=%s&creator=netCheck99&jobid=123"

# os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'
processRunFlag = 1
def programExit(signalFlag, local_pid):
    global processRunFlag
    if processRunFlag != None:
        processRunFlag = 0
    logger.info("接收到退出信号，进程(%s)准备退出！" % os.getpid())
# 信号触发函数。SIGTERM = 2 ；SIGINT = 15
signal.signal(signal.SIGTERM, programExit)  # program terminate
signal.signal(signal.SIGINT, programExit)  # control+c

#创建数据库连接池
def get_pool(logger):
    db_pool=None
    while processRunFlag:
        try:
            db_pool = PooledDB(creator=pymysql,
                                    mincached=1,  # 启动时开启的空连接数
                                    maxcached=5,  # 连接池最大可用连接数量
                                    host=MysqlConfig['host'],
                                    port=MysqlConfig['port'],
                                    user=MysqlConfig['user'],
                                    passwd=MysqlConfig['password'],
                                    db=MysqlConfig['db'],
                                    charset='utf8mb4')
            break
        except Exception as e:
            msg=dev_name+"数据库连接失败，1分钟后重连"
            sendErrMsg_by_weixin(msg,logger,errmsgsenduser_dev)
            time.sleep(60)
    return db_pool
def getLogger(fileName,timeType='d',backupCount=10,console=True):
    MSG_FORMAT = logging.Formatter("%(asctime)s %(levelname)s %(filename)s %(funcName)s (line:%(lineno)d)[%(process)d][%(threadName)s][%(message)s]")
    logger = logging.Logger("")
    log_path = os.path.split(fileName)[0]
    if not os.path.exists(log_path+'/'):
        os.makedirs(log_path)
    log_handler = ConcurrentTRFileHandler(fileName, when=timeType, interval=1,backupCount=backupCount,encoding='utf8',delay=True)
    log_handler.setLevel(logging.INFO)
    log_handler.setFormatter(MSG_FORMAT)
    logger.addHandler(log_handler)
    if console:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(MSG_FORMAT)
        logger.addHandler(console)
    logger.handlers[0].baseFilename += ('.'+time.strftime("%Y-%m-%d", time.localtime()))
    return logger

class ConcurrentTRFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False,
                 atTime=None):
        TimedRotatingFileHandler.__init__(self, filename, when, interval, backupCount, encoding, delay, utc)

        self.origin_filename = filename

    def getFilesToDelete(self):
        """
        Determine the files to delete when rolling over.
        More specific than the earlier method, which just used glob.glob().
        """
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix = self.origin_filename + "."  # 这里就不能用 baseName 了
        plen = len(prefix)
        for fileName in fileNames:
            if fileName[:plen] == prefix:
                suffix = fileName[plen:]
                if self.extMatch.match(suffix):
                    result.append(os.path.join(dirName, fileName))
        result.sort()
        if len(result) < self.backupCount:
            result = []
        else:
            result = result[:len(result) - self.backupCount]
        return result

    def doRollover(self):
        """
        do a rollover; in this case, a date/time stamp is appended to the filename
        when the rollover happens.  However, you want the file to be named for the
        start of the interval, not the current time.  If there is a backup count,
        then we have to get a list of matching filenames, sort them and remove
        the one with the oldest suffix.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        # get the time that this sequence started at and make it a TimeTuple
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        if self.utc:
            timeTuple = time.gmtime()
        else:
            timeTuple = time.localtime()

        # 以追加方式打开新的日志文件，没有改名和删除操作就不会冲突报错了。
        self.baseFilename = self.rotation_filename(os.path.abspath(self.origin_filename) + "." +
                                                   time.strftime(self.suffix, timeTuple))
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        # If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                    addend = -3600
                else:  # DST bows out before next rollover, so we need to add an hour
                    addend = 3600
                newRolloverAt += addend
        self.rolloverAt = newRolloverAt
#发消息模块
def sendErrMsg_by_weixin(msg, logger,user):
    logger.info(msg)
    req = requests.get(errmsgsendurl % (msg,user))
    data = json.loads(req.text)
    logger.info(data)

#遍历task_manage表
# 1、每次获取crontime大于上次crontime 且小于当前时间或者next_list指定的taskseq
#     (第一次启动获取crontime小于当前时间  且  crontime大于10分钟前的所有定时任务)
# 2、状态为3的直接告警
# 3、状态为4的直接跳过
# 4、剩下的判断crontime，超过15秒直接告警，没超过15秒的，taskseq写进next_list
# 5、把最大的crontime记录下来
# 6、crontime可继承
def taskCheck(logger):
    db_pool = get_pool(logger)
    last_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()-0*60))
    taskSeqListStr=""
    taskSeqList=[]
    index=0
    last_day = time.strftime("%Y-%m-%d", time.localtime())
    logger.info("last_day:" + str(last_day))
    while processRunFlag:
        today = time.strftime("%Y-%m-%d", time.localtime())
        if today != last_day:
            last_day = today
            logger = getLogger(log_file_name)
            logger.info("today:" + str(last_day))
        if index==4:
            logger.info("监控程序运行中,(监控时间范围起点时间:"+str(last_time)+")")
            index=0
        else:
            index+=1
        try:
            conn=None
            try:
                conn = db_pool.connection()
            except:
                logger.info("无法获取连接，将开始尝试重连。")
            if not conn:
                db_pool = get_pool(logger)
                continue
            else:
                my_cur=conn.cursor()
                sql="select taskSeq,endTime,remarks,status,cronTime,TIMESTAMPDIFF(SECOND,cronTime,now()) diffTime,now(),actionType from wx_task_manage where " \
                    " actionType in (6,23,24) and ((cronTime>str_to_date('"\
                    +last_time+"', '%Y-%m-%d %H:%i:%s') and cronTime<now()) or taskSeq in ('"+str(taskSeqListStr)+\
                    "')) order by cronTime desc"
                logger.debug("上一次任务执行时间:"+str(last_time))
                logger.debug("sql:"+str(sql))
                my_cur.execute(sql)
                rs = my_cur.fetchall()
                if len(rs) > 0:
                    logger.info("查询到新的发消息任务："+str(rs))
                    taskSeqList,last_time_new = dealWithTaskList(rs,logger,taskSeqList)#判断消息状态，发送消息，返回未超时的任务seq
                    if last_time_new:
                        last_time=last_time_new
                    taskSeqListStr = "','".join(taskSeqList)
                else:
                    taskSeqListStr=""#如果没有消息，则清空seq列表
        except Exception as e:
            msg = e
            logger.info(traceback.format_exc())
            sendErrMsg_by_weixin(msg, logger,errmsgsenduser_dev)
        finally:
            index_count=10
            while index_count>0 and processRunFlag:
                time.sleep(0.5)
                index_count-=1
#监控未发送成功的消息
def dealWithTaskList(taskList,logger,taskSeqList_old):
    taskSeqList=[]
    lastTime=None
    for result in taskList:
        taskSeq, endTime, remarks, status, cronTime,diffTime,now_time,actionType=result
        if endTime and str(status) in ['3','4']:
            if cronTime<now_time:
                diffTime=(endTime-cronTime).seconds
            else:
                diffTime = (endTime - cronTime).seconds + 24 * 60 * 60  # cronTime已经加一天，所以算出来的差值应该加一天
        if (lastTime is None) and (taskSeq not in taskSeqList_old):
            lastTime=cronTime.strftime('%Y-%m-%d %H:%M:%S')
        if str(status)=='3':
            msg=dev_name+"|taskSeq:"+str(taskSeq)+"|发消息失败（remark:"+str(remarks)+"）"
            sendErrMsg_by_weixin(msg,logger,errmsgsenduser)
        elif str(status)=='4':
            if int(diffTime)>15:
                msg = dev_name+"|taskSeq:" + str(taskSeq) + "|发消息"+str(diffTime)+"秒完成"
                sendErrMsg_by_weixin(msg, logger,errmsgsenduser)
            else:
                continue
        else:
            if endTime and cronTime>now_time:
                diffTime = (endTime - cronTime).seconds + 24 * 60 * 60  # cronTime已经加一天，所以算出来的差值应该加一天
            if int(diffTime)>15 :
                msg = dev_name+"|taskSeq:" + str(taskSeq) + "|发消息"+str(diffTime)+"秒未完成"
                sendErrMsg_by_weixin(msg, logger,errmsgsenduser)
            elif cronTime<now_time:
                taskSeqList.append(str(taskSeq))
    return taskSeqList,lastTime


if __name__ == '__main__':
    logger = getLogger(log_file_name)  # 加载日志
    logger.info("监控程序启动成功！")
    with open('kill.sh', 'w+') as file:
        file.write("kill -s SIGTERM "+str(os.getpid())+"\nrm kill.sh")
        file.close()
    taskCheck(logger)
    logger.info("监控程序退出！")
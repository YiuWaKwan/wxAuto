import random
import re
import subprocess
import traceback
import urllib

from tools import oracleDPool,MysqlDbPool
import os
import time
import linecache
from lib.ModuleConfig import ConfAnalysis
import requests
import psutil

class monitorAgent():
    def __init__(self,moduleName):
        __moduleName = moduleName.split('.')[0]
        __baseDir = os.getcwd()
        self.monitorFile = "%s\data\heartBeat\%s_monitorAgent.txt" %(__baseDir,__moduleName)
    def run(self):
        timeStamp = str(int(time.time()))
        fileRoot = os.path.split(self.monitorFile)[0]
        if not os.path.exists(fileRoot + '/'):
            os.makedirs(fileRoot)
        with open(self.monitorFile, 'w') as pidFile:
            pidFile.write(timeStamp)

class monitorServer():
    def __init__(self,logger,BASEDIR, adbPort):
        self.moduleAlertDict = {}
        self.logger = logger
        self.baseDir = BASEDIR
        self.adbPort = adbPort
        self.mySqlUtil = MysqlDbPool.MysqlDbPool(1, 5)
        self.oracleAction = oracleDPool.oracleDbAction(self.logger)
        __configFile = '%s/conf/moduleConfig.conf' % BASEDIR
        __confAllItems = ConfAnalysis(self.logger, __configFile)
        self.DevId = __confAllItems.getOneOptions('devInfo', 'dev')
        __Module_ID = __confAllItems.getOneOptions('actionModuleName', 'moduleName')
        __Web_Url = __confAllItems.getOneOptions('actionModuleName', 'webUrl')
        self.userListAlert = __confAllItems.getOneOptions("alarm", "user_list")
        self.moduleList = ""
        if __Module_ID:
            self.moduleList = __Module_ID.split(',')
        self.webList = ""
        if __Web_Url:
            self.webList = __Web_Url.split(',')

    def processMonitor(self):
        '''
        # 主要程序监控
        # 采用进程嵌入agent进行文件输入心跳信息监控，一旦心跳信息对比当前超过阈值时间进行告警 : Search -> processMonitorGate
        # 设置告警间隔时长，避免短时间内频繁告警 : Search -> processMonitorTime
        :return:
        '''
        if self.moduleList:
            for moduleName in self.moduleList:
                try:
                    errType = -1
                    if not os.path.exists("%s\data\heartBeat\\" % (self.baseDir)):
                        os.makedirs("%s\data\heartBeat" % (self.baseDir))
                    monitorFile = "%s\data\heartBeat\%s_monitorAgent.txt" % (
                        self.baseDir, moduleName)
                    if not os.path.exists(monitorFile):
                        errType = 2
                    else:
                        with open(monitorFile, 'r', ) as f:
                            modTimeStampTmp = f.readlines()
                        if modTimeStampTmp:
                            modTimeStamp = modTimeStampTmp[0]
                            currentTimeStamp = int(time.time())
                            if currentTimeStamp - int(modTimeStamp) >= 60 * 10:   # 主程序监控告警触发间隔时长 [processMonitorGate]
                                errType = 1
                            elif currentTimeStamp - int(modTimeStamp) >= 60 * 0.8: # 尝试杀死adb
                                adbInitPort = [re.split(r" +", i.strip())[1]
                                               for i in subprocess.check_output("tasklist|findstr adb",
                                                                                shell=True)
                                                   .decode(encoding="utf-8")
                                                   .split("K\r\n") if i]
                                if len(adbInitPort) > 1:
                                    if self.adbPort in adbInitPort:
                                        for adbKillPort in adbInitPort:
                                            if adbKillPort != self.adbPort :
                                                subprocess.check_output("taskkill /f /pid %s" % adbKillPort, shell=True)
                                    else:
                                        for adbKillPort in adbInitPort[1:]:
                                            subprocess.check_output("taskkill /f /pid %s" % adbKillPort, shell=True)

                                    # adbStart = "adb start-server"
                                    # subprocess.check_call(adbStart)
                        # else:
                        #     # 空异常，预估是读取的时候，刚好有值写进去，无法读取/20081205屏蔽
                        #     errType = 0

                    if errType != -1:
                        runFlag = False
                        if moduleName not in self.moduleAlertDict:
                            self.moduleAlertDict[moduleName] = int(time.time())
                            runFlag = True
                        else:
                            if int(time.time()) - self.moduleAlertDict[moduleName] >= 60 * 5: # 每次监控告警间隔时长 [processMonitorTime]
                                runFlag = True
                        if runFlag:
                            self.moduleAlertDict[moduleName] = int(time.time())
                            self.wxErrAlert(moduleName, errType)
                    else:
                        if moduleName in self.moduleAlertDict:
                            self.moduleAlertDict.pop(moduleName)
                except Exception as e:
                    self.logger.warn(e)
        else:
            self.logger.warn("无配置监控模块名称（moduleName）")

    def webMonitor(self):
        '''
        # 页端监控
        # 采用对django服务进行get请求，返回状态是否200判断服务状态 : Search -> webMonitorGate
        # 设置告警间隔时长，避免短时间内频繁告警 : Search -> webMonitorTime
        :return:
        '''
        codeRet = ""
        if self.webList:
            for webUrl in self.webList:
                status = -1
                try:
                    webStatus = requests.get(webUrl, timeout=2)
                    if webStatus.status_code == 200: # 主程序监控告警触发条件 [webMonitorGate]
                        status = 1
                    else:
                        codeRet = webStatus.status_code
                except Exception as e:
                    codeRet = '-1'
                    status = -1
                finally:
                    if status == -1:
                        if webUrl not in self.moduleAlertDict:
                            self.moduleAlertDict[webUrl] = int(time.time())
                            webRunFlag = True
                        elif int(time.time()) - self.moduleAlertDict[webUrl] >= 60 * 5: # 每次监控告警间隔时长 [webMonitorTime]
                                webRunFlag = True
                        else:
                            webRunFlag = False

                        if webRunFlag:
                            self.moduleAlertDict[webUrl] = int(time.time())
                            self.wxErrAlert(webUrl, 3,codeRet)
        else:
            self.logger.warn("无配URL监控项目（webUrl）")

    def adbMonitor(self):
        '''
        # 模拟器监控
        # 以设备状态为非device为触发条件，正常则更新心跳时间，否则不更新，一旦不更新超过阈值时间进行告警 : Search -> adbMonitorGate
        # 设置告警间隔时长，避免短时间内频繁告警 : Search -> adbMonitorGateTime
        :return:
        '''

        adbStartList = self.adbInfoGet()
        if adbStartList:
            adbDevAction = subprocess.check_output('adb devices').decode(encoding="utf-8")
            for adbItem in adbStartList:
                adbPort = adbItem[0]
                adbName = adbItem[1]
                if "%s_%s" % (adbName, adbPort) not in self.moduleAlertDict:
                    self.moduleAlertDict["%s_%s" % (adbName, adbPort)] = int(time.time())

                if '%s\tdevice' % (adbPort) in adbDevAction:
                    self.moduleAlertDict["%s_%s" % (adbName, adbPort)] = int(time.time()) # 正常情况下更新时间 [adbMonitorGate]

                if int(time.time()) - self.moduleAlertDict["%s_%s" % (adbName, adbPort)] >= 60 * 5 : # 告警触发条件 [adbMonitorGateTime]
                    try:
                        # 减少认为disconnect导致触发告警，尝试重连
                        adbConnect = "adb connect 127.0.0.1:%s" % (adbPort)
                        subprocess.check_call(adbConnect)
                    except Exception as e:
                        self.logger.warn(traceback.format_exc())
                    finally:
                        reAdbDevAction = subprocess.check_output('adb devices').decode(encoding="utf-8")
                        if '%s\tdevice' % (adbPort) not in reAdbDevAction:
                            self.wxErrAlert(adbName, 4)
                            self.moduleAlertDict["%s_%s" % (adbName, adbPort)] = int(time.time())

    def run(self):
        '''
        # 当前监控程序自监控，采用向远端db发送心跳包，监控程序当前设置为在db端  'ps -ef|grep Monitor.py'
        # 触发条件 search -> svrHearbeatGate
        :return:
        '''
        self.processMonitor()
        self.webMonitor()
        # self.adbMonitor()
        # heartbeatSql = """REPLACE INTO wx_services_monitor(clientId,`timestamp`) VALUES (\'%s\',now())""" %(self.DevId)
        # self.mySqlUtil.excSql(heartbeatSql)

    def adbInfoGet(self):
        getSql = """select A.devPort,A.devName from wx_machine_info A
                        join wx_account_info B on A.uuid = B.uuid
                        where B.if_start = 1
                        and A.clientId = \'%s\'""" %(self.DevId)
        adbInfoList = self.mySqlUtil.getData(getSql)
        return adbInfoList

    def wxErrAlert(self,moduleName,alertType,alertAdditon=''):
        taskSeq = round(time.time() * 1000 + random.randint(100, 999))
        if alertType == 1:
            alarmMsg = "主机:%s %s 模块10分钟无心跳信息" % (self.DevId,moduleName)
        elif alertType == 0:
            alarmMsg = "主机:%s %s 模块心跳信息为空异常" % (self.DevId,moduleName)
        elif alertType == 2:
            alarmMsg = "主机:%s %s 模块心跳文件异常" % (self.DevId,moduleName)
        elif alertType == 3:
            alarmMsg = "%s 页端服务异常,异常码:%s" % (moduleName,alertAdditon)
        elif alertType == 4:
            alarmMsg = "主机:%s %s 设备异常" % (self.DevId, moduleName)
        else:
            alarmMsg = "主机:%s %s 模块心跳异常" % (self.DevId,moduleName)
        # weixinAlarmSql = """insert into weixin.wxerrmsg (msgid, msgcontent, msgtype, msgtime, targetuser,status, createuser)
        #                         values ('%s','%s','21',sysdate,'%s','0','edent')""" % (
        #                         taskSeq, alarmMsg, self.userListAlert)
        # self.logger.info(weixinAlarmSql)
        # self.oracleAction.insertData(weixinAlarmSql)
        weixinAlarmRequest = """http://124.172.189.98/wechat/send_err_msg/?msg=%s&type=21&user=%s&creator=edent&jobid=123""" % (
            alarmMsg, self.userListAlert)
        req = requests.get(weixinAlarmRequest)

class dbMonitor():
    def __init__(self,logger,BASEDIR):
        self.moduleAlertDict = {}
        self.logger = logger
        self.baseDir = BASEDIR
        self.mySqlUtil = MysqlDbPool.MysqlDbPool(1, 10)
        self.oracleAction = oracleDPool.oracleDbAction(self.logger)
        __configFile = '%s/conf/moduleConfig.conf' % BASEDIR
        __confAllItems = ConfAnalysis(self.logger, __configFile)
        self.userListAlert = __confAllItems.getOneOptions("alarm", "user_list")
        self.dbHost = __confAllItems.getOneOptions("database", "host")

    def svrHeartbeatMonitor(self):
        '''
        # 对服务端监控程序进行监控，触条件为服务端阈值时间内为更新心跳信息 search -> svrHearbeatGate
        # 设置告警间隔时长，避免短时间内频繁告警 : Search -> svrHeartbeatTime
        :return:
        '''
        monitorHeartbeatSql  = """SELECT clientId from wx_services_monitor A
                                    where unix_timestamp(now()) - unix_timestamp(A.`timestamp`) >= 60 * 5
                                    and A.`status` = 1;"""
        monitorServerHeratbeatOut = self.mySqlUtil.getData(monitorHeartbeatSql)  # [svrHearbeatGate]
        if monitorServerHeratbeatOut:
            for monitorItem in monitorServerHeratbeatOut:
                # monitorAlertFlag = False
                clientId = monitorItem[0]
                if clientId not in self.moduleAlertDict:
                    self.moduleAlertDict[clientId] = int(time.time())
                    monitorAlertFlag = True
                elif int(time.time()) - self.moduleAlertDict[clientId] >= 60 * 5: # [svrHeartbeatTime]
                    self.moduleAlertDict[clientId] = int(time.time())
                    monitorAlertFlag = True
                else:
                    monitorAlertFlag = False

                if monitorAlertFlag:
                    self.wxErrAlert(clientId, 1)
                    # updateTimestampSql = """update  wx_services_monitor
                    #                             set `timestamp` = now()
                    #                             where clientId = \'%s\'""" %(clientId)
                    # self.mySqlUtil.excSql(updateTimestampSql)

    def dbConnectMonitor(self):
        '''
        # 数据库连接数监控，根据当前将结束与最大连接数比例进行阈值监控  search -> dbConnectGate
        # 设置告警间隔时长，避免短时间内频繁告警 : Search -> dbConnectTime
        :return:
        '''
        dbConnectedSql = "show status like 'Threads_connected'"
        dbMaxConnectedSql = "show variables like 'max_connections'"
        dbConnectedCount = self.mySqlUtil.getData(dbConnectedSql)[0][1]
        dbMaxConnectedCount = self.mySqlUtil.getData(dbMaxConnectedSql)[0][1]
        monitorGate = int(dbConnectedCount) / int(dbMaxConnectedCount) * 100
        infoDict = {'dbConnectedCount': dbConnectedCount, 'dbMaxConnectedCount': dbMaxConnectedCount}
        if monitorGate >= 80: # [dbConnectGate]
            if self.dbHost not in self.moduleAlertDict:
                monitorAlertFlag = True
                self.moduleAlertDict[self.dbHost] = int(time.time())
            elif int(time.time()) - self.moduleAlertDict[self.dbHost] >= 60 * 5: #[dbConnectTime]
                monitorAlertFlag = True
                self.moduleAlertDict[self.dbHost] = int(time.time())
            else:
                monitorAlertFlag = False

            if monitorAlertFlag:
                self.wxErrAlert(self.dbHost, 2, **infoDict)



    def wxErrAlert(self,moduleName,alertType,*tupleArg,**kwargs):
        dbConnectedCount = kwargs['dbConnectedCount']
        dbMaxConnectedCount = kwargs['dbMaxConnectedCount']

        taskSeq = round(time.time() * 1000 + random.randint(100, 999))
        if alertType == 1:
            alarmMsg = "主机:%s 监控脚本异常" % (moduleName)
        elif alertType == 2:
            alarmMsg = "db: %s 连接数阈值超80%%（%s / %s）" % (moduleName,dbConnectedCount,dbMaxConnectedCount)
        else:
            alarmMsg = ""
        weixinAlarmRequest = """http://124.172.189.98/wechat/send_err_msg/?msg=%s&type=21&user=%s&creator=edent&jobid=123""" % (
        alarmMsg, self.userListAlert)
        req = requests.get(weixinAlarmRequest)
        # weixinAlarmSql = """insert into weixin.wxerrmsg (msgid, msgcontent, msgtype, msgtime, targetuser,status, createuser)
        #                         values ('%s','%s','21',sysdate,'%s','0','edent')""" % (
        #                         taskSeq, alarmMsg, self.userListAlert)
        # self.logger.info(weixinAlarmSql)
        # self.oracleAction.insertData(weixinAlarmSql)

class hdMonitor():
    def __init__(self,logger, BASEDIR, cpuGate = 80, memGate = 80, netGate = 4000):
        self.moduleAlertDict = {}
        self.logger = logger
        self.baseDir = BASEDIR
        self.mySqlUtil = MysqlDbPool.MysqlDbPool(1, 10)
        self.oracleAction = oracleDPool.oracleDbAction(self.logger)
        __configFile = '%s/conf/moduleConfig.conf' % BASEDIR
        __confAllItems = ConfAnalysis(self.logger, __configFile)
        self.userListAlert = __confAllItems.getOneOptions("alarm", "user_list")
        self.svrHost = __confAllItems.getOneOptions("devInfo", "dev")
        self.cpuGate = cpuGate
        self.memGate = memGate
        self.netGate = netGate

    def cpuMonitor(self):
        cpuLoadPercentCur = psutil.cpu_percent()
        # 阈值超过0.8则告警，
        if cpuLoadPercentCur >= self.cpuGate: # [cpuGate]
            if 'cpuMonitor' not in self.moduleAlertDict:
                monitorAlertFlag = True
                self.moduleAlertDict['cpuMonitor'] = int(time.time())
            elif int(time.time()) - self.moduleAlertDict['cpuMonitor'] >= 60 * 5: #[cpuGateTime]
                monitorAlertFlag = True
                self.moduleAlertDict['cpuMonitor'] = int(time.time())
            else:
                monitorAlertFlag = False

            if monitorAlertFlag:
                self.wxErrAlert('cpuMonitor', 1)

        if not os.path.exists("%s\data\heartBeat\\" % (self.baseDir)):
            os.makedirs("%s\data\heartBeat" % (self.baseDir))
        monitorFile = "%s\data\heartBeat\%s_monitorAgent_%s.txt" % (
            self.baseDir, 'cpu',time.strftime('%Y%m%d',time.localtime(time.time())))

        with open(monitorFile, 'a+') as f:
            f.write('%s|%s' %(time.strftime('%H%M%S',time.localtime(time.time())),cpuLoadPercentCur))
            f.write('\n')

    def memMonitor(self):
        memLoadPercentCur = psutil.virtual_memory().percent
        # 阈值超过0.8则告警，
        if memLoadPercentCur >= self.memGate: # [cpuGate]
            if 'memMonitor' not in self.moduleAlertDict:
                monitorAlertFlag = True
                self.moduleAlertDict['memMonitor'] = int(time.time())
            elif int(time.time()) - self.moduleAlertDict['memMonitor'] >= 60 * 5: #[cpuGateTime]
                monitorAlertFlag = True
                self.moduleAlertDict['memMonitor'] = int(time.time())
            else:
                monitorAlertFlag = False

            if monitorAlertFlag:
                self.wxErrAlert('memMonitor', 2)

        if not os.path.exists("%s\data\heartBeat\\" % (self.baseDir)):
            os.makedirs("%s\data\heartBeat" % (self.baseDir))
        monitorFile = "%s\data\heartBeat\%s_monitorAgent_%s.txt" % (
            self.baseDir, 'mem',time.strftime('%Y%m%d',time.localtime(time.time())))

        with open(monitorFile, 'a+') as f:
            f.write('%s|%s' %(time.strftime('%H%M%S',time.localtime(time.time())),memLoadPercentCur))
            f.write('\n')

    def netMonitor(self):
        netSentLoad1 = psutil.net_io_counters().bytes_sent
        netRecvLoad1 = psutil.net_io_counters().bytes_recv
        time.sleep(1)
        netSentLoad2 = psutil.net_io_counters().bytes_sent
        netRecvLoad2 = psutil.net_io_counters().bytes_recv

        netSentLoad = (netSentLoad2 - netSentLoad1) / 1024 * 8
        netRecvLoad = (netRecvLoad2 - netRecvLoad1) / 1024 * 8

        if netSentLoad >= self.netGate: # [netGate]
            monitorAlertFlag = False
            if 'netSentMonitor' not in self.moduleAlertDict:
                monitorAlertFlag = True
                self.moduleAlertDict['netSentMonitor'] = int(time.time())
            elif int(time.time()) - self.moduleAlertDict['netSentMonitor'] >= 60 * 5: #[netGateTime]
                monitorAlertFlag = True
                self.moduleAlertDict['netSentMonitor'] = int(time.time())
            else:
                monitorAlertFlag = False

            if monitorAlertFlag:
                self.wxErrAlert('netSentMonitor', 3)

        if netRecvLoad >= self.netGate: # [netGate]
            monitorAlertFlag = False
            if 'netRecvMonitor' not in self.moduleAlertDict:
                monitorAlertFlag = True
                self.moduleAlertDict['netRecvMonitor'] = int(time.time())
            elif int(time.time()) - self.moduleAlertDict['netRecvMonitor'] >= 60 * 5: #[netGateTime]
                monitorAlertFlag = True
                self.moduleAlertDict['netRecvMonitor'] = int(time.time())
            else:
                monitorAlertFlag = False

            if monitorAlertFlag:
                self.wxErrAlert('netRecvMonitor', 4)


        if not os.path.exists("%s\data\heartBeat\\" % (self.baseDir)):
            os.makedirs("%s\data\heartBeat" % (self.baseDir))
        monitorFile = "%s\data\heartBeat\%s_monitorAgent_%s.txt" % (
            self.baseDir, 'netSent',time.strftime('%Y%m%d',time.localtime(time.time())))

        with open(monitorFile, 'a+') as f:
            f.write('%s|%s' %(time.strftime('%H%M%S',time.localtime(time.time())),netSentLoad))
            f.write('\n')

        if not os.path.exists("%s\data\heartBeat\\" % (self.baseDir)):
            os.makedirs("%s\data\heartBeat" % (self.baseDir))
        monitorRecvFile = "%s\data\heartBeat\%s_monitorAgent_%s.txt" % (
            self.baseDir, 'netRecv',time.strftime('%Y%m%d',time.localtime(time.time())))

        with open(monitorRecvFile, 'a+') as f:
            f.write('%s|%s' %(time.strftime('%H%M%S',time.localtime(time.time())),netRecvLoad))
            f.write('\n')

    def run(self):
        self.cpuMonitor()
        self.memMonitor()
        # self.netMonitor()

    def wxErrAlert(self,moduleName,alertType,*tupleArg,**kwargs):

        taskSeq = round(time.time() * 1000 + random.randint(100, 999))
        if alertType == 1:
            alarmMsg = "%s主机: CPU 当前使用率超过 %s %%" % (self.svrHost,self.cpuGate )
        elif alertType == 2:
            alarmMsg = "%s主机: 内存 当前使用率超过 %s %%" % (self.svrHost, self.memGate)
        elif alertType == 3:
            alarmMsg = "%s主机: 网络发送流量 当前超过 %s kbps %%" % (self.svrHost, self.netGate)
        elif alertType == 4:
            alarmMsg = "%s主机: 网络接收流量 当前超过 %s kbps %%" % (self.svrHost, self.netGate)
        else:
            alarmMsg = ""
        weixinAlarmRequest = """http://124.172.189.98/wechat/send_err_msg/?msg=%s&type=21&user=%s&creator=edent&jobid=123"""%(alarmMsg, self.userListAlert)
        req = requests.get(weixinAlarmRequest)
        # weixinAlarmSql = """insert into weixin.wxerrmsg (msgid, msgcontent, msgtype, msgtime, targetuser,status, createuser)
        #                         values ('%s','%s','21',sysdate,'%s','0','edent')""" % (
        #                         taskSeq, alarmMsg, self.userListAlert)
        # self.logger.info(weixinAlarmSql)
        # self.oracleAction.insertData(weixinAlarmSql)

def alarm(msg,logger,alarm_server,user_list):
    msg = urllib.parse.quote(msg)
    warn_msg = "%s?msg=%s&type=2&user=%s&creator=maizq" % (alarm_server, msg, user_list)
    http_client=urllib.request.urlopen(warn_msg, timeout = 5)
    print(http_client.read())
    return http_client.read()

def friendSummaryMonitor(devId,mySqlUtil,logger,alarm_server,user_list):
    # print(devId)
    # devId = '124.172.188.65'
    getInfoSql = """SELECT
                        concat(
                            '%s测试环境wx户数：',
                            count(t1.wx_main_id),
                            '，昨日新wx户数：',
                            sum(t1.new_tag),
                            '，好友总数：',
                            sum(all_fl),
                            '，昨日新增好友数：',
                            sum(IF(t1.new_tag = 1, 0, new_fl)),
                            '；昨日加人任务数：',
                            sum(ifnull(t2.totle, 0)),
                            '，昨天加人任务未执行数：',
                            sum(ifnull(t2.fail_num, 0)),
                            '，昨天加人实际发送数：',
                            sum(ifnull(t2.fact_send_num, 0)),
                            '，昨天加人统计成功数：',
                            sum(ifnull(t3.add_succ, 0))
                        ) AS content
                    FROM
                        (
                            SELECT
                                a.wx_main_id,
                                b.wx_name,
                    
                            IF (
                                date_format(b.register_time, '%%Y-%%m-%%d') = date_sub(curdate(), INTERVAL 1 DAY),
                                1,
                                0
                            ) new_tag,
                            count(DISTINCT a.wx_id) all_fl,
                            sum(
                    
                                IF (
                                    date_format(a.add_time, '%%Y-%%m-%%d') = date_sub(curdate(), INTERVAL 1 DAY),
                                    1,
                                    0
                                )
                            ) new_fl
                        FROM
                            wx_friend_rela a
                        JOIN wx_account_info b ON a.wx_main_id = b.wx_id
                        WHERE
                            a.wx_id NOT LIKE '%%@%%'
                        AND b.if_start = 1
                        AND b.client_id = \'%s\'
                        GROUP BY
                            a.wx_main_id
                        ) t1
                    LEFT JOIN (
                        SELECT
                            b.wx_user,
                            count(wx_code) totle,
                            sum(IF(a.send_code IS NULL or a.send_code = '6', 1, 0)) fail_num,
                            sum(
                    
                                IF (
                                    a.SEND_CODE in ('1','3','4'),
                                    1,
                                    0
                                )
                            ) fact_send_num
                        FROM
                            OKAY_TASK_LIST a
                        LEFT JOIN OKAY_TASK_INFO b ON a.task_id = b.task_id
                        WHERE
                            date_format(a.task_pre_exec, '%%Y-%%m-%%d') = date_sub(curdate(), INTERVAL 1 DAY)
                        GROUP BY
                            b.wx_user
                    ) t2 ON t1.wx_main_id = t2.wx_user
                    LEFT JOIN (
                        SELECT
                            a.wx_user,
                            count(a.wx_user) add_succ
                        FROM
                            OKAY_TASK_INFO a
                        INNER JOIN OKAY_TASK_LIST b ON a.TASK_ID = b.TASK_ID
                        INNER JOIN wx_friend_rela c ON a.WX_USER = c.wx_main_id
                        AND CASE
                        WHEN IFNULL(b.TARGET_WX_ID, '') <> '' THEN
                            b.TARGET_WX_ID
                        ELSE
                            b.TARGET_WX_NAME
                        END = CASE
                        WHEN IFNULL(b.TARGET_WX_ID, '') <> '' THEN
                            c.wx_id
                        ELSE
                            c.remark
                        END
                        WHERE
                            date_format(b.task_pre_exec, '%%Y-%%m-%%d') = date_sub(curdate(), INTERVAL 1 DAY)
                        AND c.add_time > a.create_time
                        GROUP BY
                            a.wx_user
                    ) t3 ON t1.wx_main_id = t3.wx_user""" %(devId.split('.')[-1],devId)
    # print(getInfoSql)
    getInfo = mySqlUtil.getData(getInfoSql)
    # print(getInfoSql)
    alertMsg = getInfo[0][0].decode(encoding="utf-8")
    alarm(alertMsg, logger, alarm_server, user_list)
    # print(getInfo)

if __name__ == '__main__':
    c = monitorAgent()
    # c.run()

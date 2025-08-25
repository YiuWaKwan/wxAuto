import multiprocessing
import subprocess
import time
import os
import traceback
import uiautomator2 as u2
import requests

from lib.FinalLogger import getLogger
from lib.ModuleConfig import ConfAnalysis
import random
from tools import MysqlDbPool
import signal
from tools import Monitor
import win32gui, win32con

from tools.machinInfo import vmsInit

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/randomChatDispatch.log')
# 初始化config
configFile =  '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)

RETRYNUM = 1
# 设备编号
DEV_ID = confAllItems.getOneOptions('devInfo','dev')
loopGate = int(confAllItems.getOneOptions('addFriend', 'loopGate'))
userListAlert = confAllItems.getOneOptions("alarm", "user_list")
randomChatSleepMin = int(confAllItems.getOneOptions('randomChat', 'randomChatSleepMin'))
randomChatSleepMax = int(confAllItems.getOneOptions('randomChat', 'randomChatSleepMax'))
clientId = confAllItems.getOneOptions("buildVM", "clientId")
devName = int(confAllItems.getOneOptions("buildVM", "devName"))
wechat = confAllItems.getOneOptions("buildVM", "wechat")
copyfile = confAllItems.getOneOptions("buildVM", "copyfile")
xposed = confAllItems.getOneOptions("buildVM", "xposed")

logNum = 0
RunFlag=1
devStatus = {}

build_flag = multiprocessing.Value("i", 1) #是否启动检测模拟器方法
def programExit(signalFlag,local_pid):
    global RunFlag
    if RunFlag != None :
        RunFlag=0
    logger.info("接收到退出信号，进程(%s)准备退出！" % os.getpid())
#信号触发函数。SIGTERM = 2 ；SIGINT = 15
signal.signal(signal.SIGTERM, programExit)  # program terminate
signal.signal(signal.SIGINT, programExit)  # control+c


def main(mySqlUtil):
    logger.info("程序启动")
    # 获取当前pid
    pid = os.getpid()
    # 获取ppid
    ppid = os.getppid()
    # 当前 pid 落地
    with open('conf/randomChatDispatchpid.conf', 'w') as pidFile:
        pidFile.write(str(pid))
    moduleName = os.path.basename(__file__).split('.')[0]
    monitorAgent = Monitor.monitorAgent(moduleName)
    randomChaStart = time.time()
    randomChatGate = 0
    while RunFlag:
        monitorAgent.run()
        # 检测是否新建模拟器
        global build_flag
        if build_flag.value == 1:
            build_flag.value = 0
            buildVM(mySqlUtil)

        # 定时任务调度
        scheduleDispatch(mySqlUtil)


        # 通讯录加好友调度
        addFriendContractDispatch(mySqlUtil)

        # 模拟器监控启动
        devMonitor(mySqlUtil, logger)

        # 养好聊天调度
        if int(time.strftime('%H', time.localtime(time.time()))) < 1 or int(time.strftime('%H', time.localtime(time.time()))) > 7:
            if time.time() - randomChaStart > randomChatGate * 30:
                randomChatDispatch(mySqlUtil)
                randomChatGate = random.randint(2, 5)
                randomChaStart = time.time()
            # timeSleep = random.randint(randomChatSleepMin, randomChatSleepMax)
            # # logger.info("sleep: %s" % timeSleep)
            # time.sleep(timeSleep)
        elif int(time.strftime('%H', time.localtime(time.time()))) >= 1 and int(time.strftime('%H', time.localtime(time.time()))) <= 6:
            logger.info("1点 - 7点限制时间限制养号功能，当前： %s ,睡眠一小时"%(int(time.strftime('%H', time.localtime(time.time())))))

        time.sleep(10)


def devMonitor(mySqlUtil,logger):
    devFindSql = """ SELECT B.devName,B.devDir, A.uuid, B.devPort, A.if_start from wx_account_info A
                        join wx_machine_info B on A.uuid = B.uuid 
                        where  B.clientId = "%s" and B.is_phone = 0""" %(DEV_ID)
    devFindList = mySqlUtil.getData(devFindSql)
    for devItem in devFindList:
        devName = devItem[0]
        devDir = devItem[1]
        if '_' in devDir:
            devIndex = devDir.split('_')[1]
        else:
            devIndex = 0
        devUuid = devItem[2]
        devPort = devItem[3]
        ifStart = int(devItem[4])

        hwnd = win32gui.FindWindow(None, devName)
        if ifStart == 0:
            if hwnd != 0:
                pass # TODO
                # logger.info("%s:%s ifStart=0,进行关闭" %(DEV_ID, devName))
                # stopCom = "memuc stop -i %s" %(devIndex)
                # subprocess.check_call(stopCom)
                # hwnd = win32gui.FindWindow(None, devName)
            continue

        if hwnd == 0:

            if devName not in devStatus.keys():
                devStatus[devName] = {"actTime" : int(time.time()),"actCount": 1}
            else:
                actTime = devStatus[devName]["actTime"]
                actCount = devStatus[devName]["actCount"]
                if int(time.time()) - actTime >= 5 * 60:
                    devStatus[devName]["actTime"] = int(time.time())
                    devStatus[devName]["actCount"] = 1
                else:

                    if actCount >= 2:
                        devStatus[devName]["actTime"] = int(time.time())
                        devStatus[devName]["actCount"] = 1
                        alarmMsg = "%s : %s 5分钟内多次重启，需要人工干预" % (DEV_ID, devName)
                        alarm(alarmMsg)
                        return
                    else:
                        devStatus[devName]["actCount"] += 1

            logger.info("%s:%s 关闭，ifStart=1 需启动" % (DEV_ID, devName))
            try:
                restartFlag = False
                startTime = time.time()
                startDeadLine = startTime + 600
                outTimeLoop = 1
                reconnectLoop = 0
                reConnectFlag = False
                devRestartFlag = False

                while True:
                    try:
                        adbDevAction = subprocess.check_output('adb devices').decode(encoding="utf-8")
                    except Exception as e:
                        print(traceback.format_exc())
                        break
                    if time.time() >= startDeadLine:
                        break
                    hwnd = win32gui.FindWindow(None, devName)
                    # adb断连已连上
                    if '%s\tdevice' % (devPort) in adbDevAction:
                        # 进行adb初始化
                        statusDevCheckCommand = """adb -s 127.0.0.1:%s shell dumpsys activity activities""" % (devPort)
                        try:
                            statusDevCheck = [i for i in
                                              subprocess.check_output(statusDevCheckCommand).decode(
                                                  encoding="utf-8").split(
                                                  '\r\r\n')
                                              if "idle=true" in i and "visible=true" in i]
                        except Exception as e:
                            statusDevCheck = []

                        if len(statusDevCheck) > 0:
                            logger.info("%s 初始化正常" % devName)
                            restartFlag = True
                            break
                        else:
                            time.sleep(3)
                    elif hwnd != 0 and not devRestartFlag:  # adb断连，需要重连
                        logger.info("%s 设备开启，adb 重连" % devName)
                        adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                        subprocess.check_call(adbReconnectCommand)
                        time.sleep(2)
                    elif hwnd == 0:  # 模拟器未启动
                        logger.info("%s 设备未开启，即将启动" % devName)
                        subprocess.check_call("MEmuConsole.exe %s" % devDir)
                        devRestartFlag = True
                        time.sleep(5)
                    elif '%s\toffline' % (
                    devPort) in adbDevAction and not reConnectFlag and not devRestartFlag:  # adb offline
                        logger.info("%s 设备 offline，adb 重连" % devName)
                        adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                        subprocess.check_call(adbReconnectCommand)
                        reconnectLoop += 1
                        if reconnectLoop > 3:
                            logger.info("%s 设备adb重连失败" % devName)
                            reConnectFlag = True
                        time.sleep(1)
                    elif reConnectFlag:  # 重连失败，重启模拟器
                        logger.info("%s 设备重启" % devName)
                        hwnd = win32gui.FindWindow(None, devName)
                        if hwnd != 0:
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        subprocess.check_call("MEmuConsole.exe %s" % devDir)
                        devRestartFlag = True
                        reConnectFlag = False
                        time.sleep(5)
                    elif (time.time() - startTime) / (120 * outTimeLoop) > 1:  # 50秒内无响应，重连adb
                        logger.info("%s 模拟器重启后120s内连不上adb，尝试重连" % devName)
                        adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                        subprocess.check_call(adbReconnectCommand)
                        outTimeLoop += 1
                        time.sleep(1)
                    else:
                        logger.info("%s 设备启动中" % devName)
                        time.sleep(5)

                if restartFlag:
                    u2Con = u2.connect("127.0.0.1:%s"%devPort)
                    u2Con.press("home")
                    u2Con(text=u"CopyFile").click(3)
                    time.sleep(2)
                    startTime = time.time()
                    while True:
                        if time.time() - startTime >= 30:
                            break
                        if u2Con(resourceId="com.gz.pbs.copyfile:id/checkCondition").exists:
                            break

                    startTime = time.time()
                    while True:
                        if time.time() - startTime >= 30:
                            break
                        if u2Con(text=u"微信").exists:
                            u2Con(text=u"微信").click_exists(3)
                            break
                        else:
                            u2Con.press("home")

            except Exception as e:
                restartFlag = False
                logger.warn(traceback.format_exc())
            finally:
                if restartFlag:
                    alarmMsg = "%s : %s 设备退出，重启成功" %(DEV_ID, devName)
                    logger.info(alarmMsg)
                else:
                    alarmMsg = "%s : %s 设备退出，重启失败，需人工干预"%(DEV_ID, devName)
                    alarm(alarmMsg)

def alarm(alarmMsg):
    weixinAlarmRequest = """http://124.172.189.98/wechat/send_err_msg/?msg=%s&type=21&user=%s&creator=edent&jobid=123""" % (
        alarmMsg, userListAlert)
    req = requests.get(weixinAlarmRequest)

def addFriendContractDispatch(mySqlUtil):
    getTaskSeqSql = """SELECT
                            taskSeq
                        FROM
                            wx_task_manage A
                        JOIN wx_machine_info B ON A.uuid = B.uuid
                        WHERE
                            A.taskSeq IN (
                                SELECT DISTINCT
                                    (A.TASK_SEQ)
                                FROM
                                    OKAY_TASK_LIST A
                                JOIN wx_add_friend B ON A.TASK_SEQ = B.taskSeq
                                WHERE
                                    A.TASK_ID IN (
                                        SELECT
                                            TASK_ID
                                        FROM
                                            OKAY_TASK_INFO
                                        WHERE
                                            TASK_STATE = 1
                                    )
                                AND B.notLoadTimes <= 3
                            )
                        AND A. STATUS = 3
                        AND B.clientId = \"%s\"
                        AND B.uuid IS NOT NULL
                        UNION ALL
                            SELECT
                                taskSeq
                            FROM
                                wx_task_manage A
                            JOIN wx_machine_info B ON A.uuid = B.uuid
                            WHERE
                                A.taskSeq IN (
                                    SELECT
                                        subTaskSeq
                                    FROM
                                        wx_add_friend
                                    WHERE
                                        taskSeq IN (
                                            SELECT DISTINCT
                                                (A.TASK_SEQ)
                                            FROM
                                                OKAY_TASK_LIST A
                                            JOIN wx_add_friend B ON A.TASK_SEQ = B.taskSeq
                                            WHERE
                                                A.TASK_ID IN (
                                                    SELECT
                                                        TASK_ID
                                                    FROM
                                                        OKAY_TASK_INFO
                                                    WHERE
                                                        TASK_STATE = 1
                                                )
                                            AND B.notLoadTimes <= %s
                                        )
                                    AND subTaskSeq != ""
                                    AND freindIdListRecover != ""
                                )
                            AND A. STATUS = 3
                            AND B.clientId = \"%s\"
                            AND B.uuid IS NOT NULL""" %(DEV_ID, loopGate, DEV_ID)
    taskSeqList = mySqlUtil.getData(getTaskSeqSql)
    if taskSeqList:
        tmpCondi = ""
        for taskSeqItem in taskSeqList:
            tmpCondi += str(taskSeqItem[0]) + ','
        logger.info("加好友任务失败重新调度 taskSeq:%s" %tmpCondi[:-1])
        updateSql = """UPDATE wx_task_manage
                            SET STATUS = 1, ifKill=0, cronTime = DATE_ADD( now(), INTERVAL 5 MINUTE )
                            WHERE
                                taskSeq IN (%s)"""%tmpCondi[:-1]
        mySqlUtil.excSql(updateSql)

def scheduleDispatch(mySqlUtil):
    # 将任务中定时时间超过1个小时的，状态置为3，失效任务
    disableTaskSql = """UPDATE wx_task_manage
                            SET STATUS = 3,
                             remarks = "任务时间超时失效"
                            WHERE
                                TIMESTAMPDIFF(SECOND,cronTime,now()) >= 60 * 60
                            AND STATUS IN (1, 2)
                            AND actionType IN (24)
                            AND uuid IN (
                                SELECT DISTINCT
                                    (uuid)
                                FROM
                                    wx_machine_info
                                WHERE
                                    uuid != ""
                                AND uuid != '0'
                                AND uuid REGEXP '^[0-9a-zA-Z]'
                                AND clientId = \'%s\'
                            )""" %(DEV_ID)
    mySqlUtil.excSql(disableTaskSql)
    # 定时调度，taskType=2（每天），且状态为3或4的任务进行定时时间加一天
    scheduleDict = {}
    scheduleTaskCheckSql = """SELECT A.taskSeq,B.createTime,B.actionMaxNum from wx_task_manage A 
                                join wx_schedule_task B on A.taskSeq = B.taskSeq
                                join wx_machine_info C on A.uuid = C.uuid
                                where B.`status` = 1
                                and C.clientId = \'%s\'
                                and B.taskType = 2
                                and A.`status` in (3,4)""" %(DEV_ID)
    scheduleTaskInfo = mySqlUtil.getData(scheduleTaskCheckSql)
    if scheduleTaskInfo:
        for info in scheduleTaskInfo:
            scheduleDict[info[0]] = (info[1],info[2])

    # allScheduleChechSql = """SELECT taskSeq,createTime,actionMaxNum from wx_schedule_task
    #                             where taskType = 2
    #                             and `status` = 1"""
    # allScheduleTask = mySqlUtil.getData(allScheduleChechSql)
    # if allScheduleTask:
    #     for taskInfo in allScheduleTask:
    #         if taskInfo[0] not in scheduleDict:
    #             scheduleDict[taskInfo[0]] = (taskInfo[1], taskInfo[2])
    if scheduleDict:
        for taskSeq in scheduleDict:
            taskSeqHere = taskSeq
            createTime = str(scheduleDict[taskSeqHere][0])
            outLoop = scheduleDict[taskSeqHere][1]
            if int(outLoop) == 0 :
                updateActionFlagSql = """ update wx_schedule_task
                                        set actionTimeFlag = DATE_ADD(actionTimeFlag,INTERVAL datediff(now(),actionTimeFlag)+1 DAY)
                                        where taskSeq = "%s" """%(taskSeq)
                logger.debug(updateActionFlagSql)
                mySqlUtil.excSql(updateActionFlagSql)

                randomCount = random.randint(-60,60)
                updateActionSql = """update wx_task_manage A, wx_schedule_task B
                                    set A.cronTime = DATE_ADD(B.actionTimeFlag,INTERVAL %s SECOND),
                                    B.actionTime = DATE_ADD(B.actionTimeFlag,INTERVAL %s SECOND),
                                    A.status  = 1
                                    where A.taskSeq = "%s"
                                    and B.taskSeq = "%s" """ %(randomCount,randomCount,taskSeq,taskSeq)
                logger.debug(updateActionSql)
                logger.info("定时任务调度taskSeq:%s"%(taskSeq))
                mySqlUtil.excSql(updateActionSql)


                # updateManageSql = """UPDATE `wx_task_manage` SET `status`='1', cronTime = DATE_ADD(cronTime,INTERVAL datediff(now(),cronTime)+1 DAY)
                #                       WHERE (`taskSeq`=\'%s\')
                #                       """ %taskSeqHere
                # logger.info(" %s 定时任务wx_task_manage调度sql：%s" %(taskSeqHere,updateManageSql))
                # mySqlUtil.excSql(updateManageSql)
                # updateScheduleSql = """update wx_schedule_task A inner join(select taskSeq,cronTime from wx_task_manage
                #                         where taskSeq = \'%s\') c
                #                         on A.taskSeq = c.taskSeq set A.actionTime = c.cronTime;
                #                         """ %(taskSeqHere)
                # logger.info("%s 定时任务wx_schedule_task调度sql：%s" % (taskSeqHere,updateScheduleSql))
                # mySqlUtil.excSql(updateScheduleSql)
                #写发送通知记录
                # writeMessageNotice(mySqlUtil, taskSeqHere)
            else:
                nowTimestamp = time.time()
                ts = time.strptime(createTime, "%Y-%m-%d %H:%M:%S")
                createTimestamp = time.mktime(ts)
                if nowTimestamp - createTimestamp > int(outLoop) * 24 * 60 * 60:
                    outTimeTaskSql = """UPDATE `wx_schedule_task` SET `status`='0' WHERE (`taskSeq`=\'%s\')""" %(taskSeqHere)
                    logger.info(" %s 定时任务wx_schedule_task失效调度sql：%s" % (taskSeqHere,outTimeTaskSql))
                    mySqlUtil.excSql(outTimeTaskSql)
                    updateManageSql1 = """UPDATE `wx_task_manage` SET `status`='6'
                                                      WHERE (`taskSeq`=\'%s\')
                                                      """ % taskSeqHere
                    logger.info("%s  定时任务wx_task_manage 失效调度sql：%s" % (taskSeqHere,updateManageSql1))
                    # 写发送通知记录
                    # writeMessageNotice(mySqlUtil, taskSeqHere)


def writeMessageNotice(mySqlUtil, taskSeqHere):
    sql = "select content, type from wx_chat_task where taskseq=%s" % taskSeqHere
    contentInfo = mySqlUtil.getData(sql)
    if contentInfo is not None and len(contentInfo) > 0:
        content = contentInfo[0][0]
        if contentInfo[0][1] == "2" and "|" in content:  # 图片
            content = content.split(u"|")[1]
        sql = "insert into wx_chat_info(wx_main_id, wx_id, send_time, type, content, send_type, status)" \
              "select wx_main_id, wx_id, now(), type, '%s', '1', '0' from wx_chat_task where taskseq=%s" % (
              content, taskSeqHere)
        mySqlUtil.excSql(sql)

def randomChatDispatch(mySqlUtil):

    # NOTICE: 正确情况下，select_valid_uuid_sql 返回比find_T2_UUID_L_1_sql返回 大于或等于
    global logNum
    # 查找现有机器有效的随机聊天任务uuid
    select_valid_uuid_sql = """SELECT A.uuid FROM `wx_randomChat_task` A
                                    join wx_machine_info B
                                    on (A.uuid = B.uuid)
                                    and B.clientId = \'%s\'
                                    and A.`status` = 1""" %DEV_ID
    selectUuidRet = mySqlUtil.fetchData(select_valid_uuid_sql)
    select_valid_uuid = ""
    if selectUuidRet[0] == 1:
        if  selectUuidRet[1]:
            for uuidItem in selectUuidRet[1]:
                select_valid_uuid += "\'%s\',"%uuidItem
            if logNum >= 20:
                logger.info("[##randomChatDispatch##]有效UUID: %s" %select_valid_uuid)
                logNum = 1
            logNum += 1

    # 如果存在有效uuid
    if select_valid_uuid:
        # 筛选有效uuid中大于两条任务的uuid
        find_T2_UUID_L_1_sql = """SELECT A.uuid,count(1) AS count from wx_task_manage A
                                    JOIN wx_machine_info B
                                    on (A.uuid = B.uuid)
                                    where A.uuid in ( %s )
                                    and B.clientId = \'%s\'
                                    and actionType = 2
                                    and (A.status = 3 or A.status = 4)
                                    group by A.uuid;""" %(select_valid_uuid[:-1],DEV_ID)
        findUuidRet = mySqlUtil.fetchData(find_T2_UUID_L_1_sql)
        uuidTmp = ""
        if findUuidRet[0] == 1:
            for uuidItem in findUuidRet[1]:
                if int(uuidItem[1]) > 1:
                    uuidTmp += "\'%s\',"%uuidItem[0]

        # 将重复的uuid任务删除，保留最大taskSeq
        if uuidTmp:
            # logger.info("[##randomChatDispatch##]删除重复任务 UUID：%s" % uuidTmp)
            delTaskseqSql = """ select max(taskSeq) as T from wx_task_manage 
                                                        where uuid in ( %s )
                                                        and actionType = 2 """ % uuidTmp[:-1]
            delTaskSeq = mySqlUtil.getData(delTaskseqSql)
            uuidList = ""
            for taskSeqItem in delTaskSeq:
                uuidList += "%s," % (taskSeqItem)
            uuidList = uuidList[:-1]

            del_T2_UUID_L_1_sql = """delete FROM `wx_task_manage` 
                                        where uuid in ( %s )
                                        and taskSeq not in (%s) and (status = 3 or status = 4)
                                        and actionType = 2""" %(uuidTmp[:-1],uuidList)
            # logger.info("[##randomChatDispatch##]删除重复项sql： %s" %del_T2_UUID_L_1_sql)
            delUuidRet =  mySqlUtil.execSql(del_T2_UUID_L_1_sql)

        updateUuidSql = """SELECT A.T from (
                                    select max(taskSeq) as T from wx_task_manage 
                                    where uuid in ( %s )
                                    and actionType = 2
                                    group by uuid
                                    ) A""" %select_valid_uuid[:-1]
        updateUuid = mySqlUtil.fetchData(updateUuidSql)

        if updateUuid[0] == 1:
            updateUuidTar = updateUuid[1]
            if updateUuidTar:
                # 对全部有效的uuid中已经完成或失败的 进行状态更新为1 ，等待执行
                maxTaskseqSql = """ select max(taskSeq) as T from wx_task_manage 
                                            where uuid in ( %s )
                                            and actionType = 2 """ %select_valid_uuid[:-1]
                maxTaskSeq = mySqlUtil.getData(maxTaskseqSql)
                uuidList = ""
                for taskSeqItem in maxTaskSeq:
                    uuidList += "%s," % (taskSeqItem)
                uuidList = uuidList[:-1]
                T2_UUID_sql = """update wx_task_manage
                                            set STATUS = 1,createTime = now(),cronTime = now()
                                            where taskSeq in ( %s ) and (status = 4 or status = 3)
                                            and actionType = 2""" %(uuidList)
            else:
                createTaskValue = ""
                for uuidItem in select_valid_uuid[:-1].split(","):
                    taskSeq = round(time.time() * 1000 + random.randint(100, 999))
                    createTaskValue += "(\'%s\',%s,2,now(),'99','1')," % (taskSeq,uuidItem)
                T2_UUID_sql = """INSERT INTO `wx_task_manage` (`taskSeq`, `uuid`, `actionType`, `createTime`,`priority`,`status`) VALUES %s""" % (createTaskValue[:-1])
            updateUuidRet = mySqlUtil.execSql(T2_UUID_sql)
        # logger.info("[##randomChatDispatch##]调度sql: %s"%update_T2_UUID_sql)
        if updateUuidRet[0] == 1:
            return True
    else:
        return False

#检测是否新建模拟器
def buildVM(mySqlUtil):
    global build_flag
    MAXNUM = 60 #一台主机最大资源数值,目前为理论值
    FREENUM = 5 #空闲模拟器值
    try:
        check_sql = """select count(1) as exist from wx_task_manage where uuid = '%s' and actionType=38 and status=2"""%(clientId)
        exist = mySqlUtil.getData(check_sql)
        if exist[0][0] == 0:
            sql = """select count(1) as totality,sum(case when status = 0 and if_ready ='1' then 1 else 0 end) as available from wx_machine_info where clientid  = '%s'"""%(clientId)
            result = mySqlUtil.getData(sql) # 检测可用模拟器是否小于5个
            if result and int(result[0][1]) < FREENUM:
                if int(result[0][0]) < (MAXNUM-FREENUM):
                    buildNum = FREENUM-int(result[0][1])
                    taskSeq = round(time.time() * 1000 + random.randint(100, 999))
                    task_sql = """insert into wx_task_manage(taskSeq,uuid,actionType,createTime,startTime,priority,remarks,status)value(%d,'%s','38',now(),now(),'5','新建模拟器%d个',2)"""\
                               %(taskSeq, clientId, buildNum)
                    ret = mySqlUtil.execSql(task_sql)
                    if ret[0] == 1:
                        p = multiprocessing.Process(target=vmsInit,
                                                    args=(taskSeq, clientId, buildNum, devName, wechat, copyfile, xposed, build_flag))
                        p.start()
                        p.join()
                else:
                    alarmMsg = "主机系统资源不足，不能再建模拟器"
                    logger.info(alarmMsg)
                    alarm(alarmMsg)

    except Exception as e:
        alarmMsg = "检测新建模拟器程序报错！"
        logger.info(alarmMsg)
        alarm(alarmMsg)

if __name__ == '__main__':
    mySqlUtil = MysqlDbPool.MysqlDbPool(1, 4)
    main(mySqlUtil)
    # # dispatch()
    # # scheduleDispatch(mySqlUtil)
    # # addFriendContractDispatch(mySqlUtil).
    # randomChatDispatch(mySqlUtil)



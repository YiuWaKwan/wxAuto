import signal
import socket
from multiprocessing import Pool
import multiprocessing
import datetime
import traceback
import redis
import win32gui
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
import time
from actionModule import addFriend, appManager, getWxFriendList, groupAction, login, momentsNew, \
    randomChat, sendWxMessage, transpondRuleManager, fileLoad, transpond, groupSent, wxDataClear
from tools import machinInfo, MysqlDbPool, taskStatusRecorder, wxUtil
from tools import Monitor,common,wxUtil, redisUtil

BASEDIR = os.getcwd()
# 忽略重试列表
reTryIgnoreList = [9, 19, 20,27,21,22, 30]
# 初始化logger
logger = getLogger('./log/multiTaskAction.log')
# # 初始化config
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)

# 初始化redis
redis_ip = confAllItems.getOneOptions('redis', 'ip')
redis_port = confAllItems.getOneOptions('redis', 'port')
redis_db = confAllItems.getOneOptions('redis', 'db')
redis_pwd = confAllItems.getOneOptions('redis', 'pwd')

#
DEV_ID = confAllItems.getOneOptions('devInfo', 'dev')
TIMEOUT = int(confAllItems.getOneOptions('taskOption', 'timeout'))
RunFlag=1
def programExit(signalFlag,local_pid):
    global RunFlag
    if RunFlag != None :
        RunFlag=0
    logger.info("接收到退出信号，进程(%s)准备退出！" % os.getpid())
#信号触发函数。SIGTERM = 2 ；SIGINT = 15
signal.signal(signal.SIGTERM, programExit)  # program terminate
signal.signal(signal.SIGINT, programExit)  # control+c

TIMEOUTDICT = { # 秒
    9 : int(confAllItems.getOneOptions('taskOption', 'timeout_refresh')),
    19 : int(confAllItems.getOneOptions('taskOption', 'timeout_login')),
    20 : int(confAllItems.getOneOptions('taskOption', 'timeout_login')),
    6 : 120,
    27 : 120,
    98 : 60 * 5,
    99 : 240,
    30 : 1800,
    32 : 1800,
    37 : 60 * 30
}
S_T_TIMEOUT = { # 秒
    30 : 60 * 30,
    32 : 60 * 30,
    20 : 60 * 1,
    99 : 60 * 1,
    'max' : 60 * 3
}
taskNameDict = {}

def sleepAction99(logger, u2ConStart, taskItemInfo, mySqlUtil):
    try:
        taskSeq = taskItemInfo[0]
        while True:
            taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新
            print("99 test|" * 10)
            time.sleep(1)

    except KeyboardInterrupt:
        logger.warn(traceback.format_exc())
    except Exception as e:
        logger.warn(traceback.format_exc())
    except RuntimeError:
        logger.warn(traceback.format_exc())
    finally:
        logger.debug('99 Final Finish')
    return (4, '#')


def sleepAction98(logger, u2ConStart, taskItemInfo):
    try:
        logger.debug("睡眠5秒钟")
        time.sleep(5)
        logger.debug("睡眠5秒钟")
        print("8" * 100)
    except KeyboardInterrupt:
        logger.warn(traceback.format_exc())
    except Exception as e:
        logger.warn(traceback.format_exc())
    except RuntimeError:
        logger.warn(traceback.format_exc())
    finally:
        logger.debug('98 Final Finish')
    return (4, '#')


# --
def taskGet(mySqlUtil_main, checkStartTime):
    '''

    :return: A.taskSeq, A.uuid, A.actionType, B.devIp, B.devPort,B.devDir,B.devName
    '''
    # maxInfo = int(confAllItems.getOneOptions('taskPool', 'maxTask'))
    taskFetchRetList = []
    taskFetchListSql = """SELECT
                                taskSeq,
                                uuid,
                                actionType,
                                devIp,
                                devPort,
                                devDir,
                                devName,
                                operViewName,
                                cronTime,
                                if_start
                            FROM
                                (
                                    SELECT
                                        taskSeq,
                                        uuid,
                                        actionType,
                                        devIp,
                                        devPort,
                                        devDir,
                                        devName,
                                        operViewName,
                                        cronTime,
                                        if_start,
                                        @rownum :=@rownum + 1,

                                    IF (
                                        @pdept = uuid ,@rank :=@rank + 1 ,@rank := 1
                                    ) AS rank,
                                    -- 分组字段
                                    @pdept := uuid
                                FROM
                                    (
                                        SELECT
                                            A.taskSeq,
                                            A.uuid,
                                            A.actionType,
                                            B.devIp,
                                            B.devPort,
                                            B.devDir,
                                            B.devName,
                                            A.operViewName,
                                            A.cronTime,
                                            C.if_start
                                        FROM
                                            -- `wx_task_manage_copy` A 
                                            `wx_task_manage` A
                                        JOIN wx_machine_info B ON (A.uuid = B.uuid)
                                   JOIN wx_account_info C ON (A.uuid = C.uuid)
                                        WHERE
                                            B.clientId = \'%s\'
                                        AND A.`status` = 1
                                        AND B.`status` = 1
                                        AND B.`is_phone` = 0
                                        AND C.`wx_status` = 1
                                        AND A.actionType not in (7 , 5)
                                        AND unix_timestamp(now()) >= unix_timestamp(A.cronTime)
                                        ORDER BY
                                            A.priority,
                                            A.uuid,
                                            A.createTime -- 分组字段，排序字段
                                            
                                    ) heyf_tmp,
                                    (
                                        SELECT
                                            @rownum := 0 ,@pdept := NULL ,@rank := 0
                                    ) a
                                ) a
                            WHERE
                                rank = 1""" %(DEV_ID)
    taskFetchList = mySqlUtil_main.fetchData(taskFetchListSql)
    for taskFetchItem in taskFetchList[1]:
        taskSeqHere = taskFetchItem[0]
        actionType = taskFetchItem[2]
        ifStart = taskFetchItem[9]
        infoItem = list(taskFetchItem)[:-2] # 截断 cronTime 和 ifStart
        taskSeqHere = taskFetchItem[0]
        cronTime = taskFetchItem[8]

        # if actionType == 6:
        #     logger.info("")
        #     redisDb = 3
        #     expireTime = 60*60*24
        #     firstRunFlag = redisUtil.taskSeqGet(taskSeqHere,redisDb)
        #     if firstRunFlag is not None:
        #         redisUtil.taskSeqSet(taskSeqHere,redisDb,expireTime)
        #         lastTimeRun = firstRunFlag.decode("utf-8")
        #         logger.warn("%s 重复执行, 上次执行时间：%s, 当前时间：%s"%(taskSeqHere,
        #                                                     time.strftime("%Y--%m--%d %H:%M:%S", time.localtime(int(lastTimeRun))),
        #                                                     time.strftime("%Y--%m--%d %H:%M:%S", time.localtime(int(time.time()))))
        #                                                     )
        #         #重复执行
        #         statusRecordAction(taskSeqHere, 8, mySqlUtil_main, taskFetchItem, '#')
        #         continue

        # 增加if_start判断
        if actionType in [30, 32] and ifStart != 0:
            taskFetchRetList.append(infoItem)
        else:
            if ifStart != 0 or actionType in [19]:
                cronTimeTimestamp = int(time.mktime(cronTime.timetuple()))
                nowTimestamp = int(time.time())
                if nowTimestamp - cronTimeTimestamp <= 60 * 20:
                    taskFetchRetList.append(infoItem)
                else:
                    taskStatusRecorder.taskDisable(mySqlUtil_main,taskSeqHere)

    if time.time() - checkStartTime >= 60 * 5 :
        checkStartTimeRet = time.time()
    else:
        checkStartTimeRet = None

    return (taskFetchRetList,checkStartTimeRet)

def statusRecordAction( taskSeq, status, mySqlUtil_main, taskInfo, remarks="" ):
    '''
    进行状态记录
    :param taskSeq:
    :param status:
    :return:
    '''
    operViewName = taskInfo[7]
    actType = taskInfo[2]
    devName = taskInfo[6]
    if not isinstance(taskSeq, int):
        if "actionType_7" in taskSeq:
            return
    # 一键加好友超时退出，记录回填
    taskDelayFlag = False
    if remarks == "#":
        remarks = "程序记录:%s" % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elif status == 3 :
        try:
            if "#" in remarks and isinstance(remarks,str) and int(actType) in [30, 32]:
                if remarks.count("#") == 2:
                    taskDelayFlag = True
                    status = 1
        except Exception:
            pass
    elif "atx-agent is not running" in remarks: # 更改U2报错内容
        remarks = "U2 ERROR"

    remarks = str(remarks).replace("'", " ").replace('\n',' ').replace("\""," ") # 转化字符
    if len(remarks) >= 255: # 限制超长
        remarks = remarks[:250]

    actionName = ""
    if actType in taskNameDict.keys():
        actionName = taskNameDict[actType]
    else:
        actionName = actType

    if actType in [23,24]:
        status = 4

    logger.info("%s | %s | %s | %s | 状态记录 status: %s | remark: %s" % (operViewName, taskSeq, devName, actionName, status, remarks))


    try:
        if int(status) == 2:
            sql = """UPDATE wx_task_manage
                set status = %s,startTime = now(),remarks = \"%s\" ,ifKill = 0
                where taskSeq = %s""" % (status, remarks, taskSeq)
        elif int(status) in [3, 4, 5]:
            sql = """UPDATE wx_task_manage
                set status = %s,endTime = now(),remarks = \"%s\"
                where taskSeq = %s""" % (status, remarks, taskSeq)
        elif status == 1 and taskDelayFlag:
            interTime = remarks.split("#")[1]
            remarksD = remarks.split("#")[2]
            sql = """update wx_task_manage
                        set STATUS= %s , cronTime = DATE_ADD(now(), INTERVAL %s HOUR),remarks = \"%s\",ifKill = 0
                        where taskSeq = \'%s\' """ %(status, interTime, remarksD,taskSeq)
        else:
            sql = """update wx_task_manage
                        set STATUS= %s 
                        where taskSeq = \'%s\' """ %(status, taskSeq)

        if sql:
            try:
                mySqlUtil_main.execSql(sql)
            except (Exception) as e:
                # 只考虑报错任务的remarks，其他任务remarks不存在异常符号或者超长状态
                if status == 3:
                    sql = """UPDATE wx_task_manage
                            set status = %s,endTime = now(),remarks = "程序异常"
                            where taskSeq = %s""" % (status, taskSeq)
                    mySqlUtil_main.execSql(sql)
    except (Exception) as e:
        logger.warn(traceback.format_exc())


def taskAction(taskItem,taskPidQueue,taskNameDict):
    '''
    : 各任务类型执行入口
    :param taskItem: eg: (1531202787842, '417b5701-5cd2-11e8-83ff-000e1e4932e0', 6, '127.0.0.1', '21533', 'MEmu_3', '13112926341')
    :return: (retStatus,remarks)
    '''
    # 返回指标初始化
    retStatus = False # 返回状态初始化
    remarks = "#"
    taskSeq = taskItem[0]
    actionType = taskItem[2]
    uuid = taskItem[1]
    devName = taskItem[6]
    operViewName = taskItem[7]
    pid = multiprocessing.current_process().pid
    name = multiprocessing.current_process().name
    taskPidQueue.put((uuid,pid))

    # 初始化mysql
    mySqlUtil = MysqlDbPool.MysqlDbPool(1, 20)
    try:
        #logger.debug("%s 队列insert (%s,%s)" % (taskSeq, taskSeq, pid))
        # taskStartQueue.put((taskSeq,int(pid)))
        # logger.debug("%s_PID : %s | TASK%s" % (name, pid, taskItem))
        # logger.info("%s 模拟器任务执行" % devName)

        actionName = ""
        if actionType in taskNameDict.keys():
            actionName = taskNameDict[actionType]
        else:
            actionName = actionType

        logger.info("%s | %s | %s | %s 任务开始" % (operViewName, taskSeq, devName, actionName ))
        # 模拟器各项指标初始化
        logger.debug("%s | %s | %s | %s | 设备初始化" % (operViewName, taskSeq, devName, actionName ))
        machineStartStatus = machinInfo.machineInit(taskItem, mySqlUtil)  # True or False ：adb 与 模拟器初始化判定完毕  ######MAIN######

        if machineStartStatus:
            taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil) # 心跳更新
            hwnd = win32gui.FindWindow(None, devName)
            if hwnd != 0:
                # 微信检查初始化
                if actionType in [28]:
                    # 过滤初始化，往列表添加类型即可
                    wxStart = (True, "type", 1)
                else:
                    # 执行初始化流程
                    sql = "select if_start from wx_account_info where uuid='%s'" % taskItem[1]
                    startInfo = mySqlUtil.getData(sql)
                    if startInfo:
                        if startInfo[0][0] == '0' and taskItem[2] not in [19, 20]:
                            remarks = "微信号已下线"
                            retStatus = False

                    logger.debug("%s | %s | %s | %s | 微信初始化" % (operViewName, taskSeq, devName, actionName))
                    wxStart = machinInfo.findWxApp(taskItem, logger, mySqlUtil)  ######MAIN######

                    taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新

                if wxStart[2] == 0:
                    remarks = "微信号已下线"
                    retStatus = False
                elif wxStart[0]:
                    # logger.info("%s : %s 任务调度开始" % (devName, actionType))
                    u2Connect = wxStart[1]
                    # 开始任务调度

                    logger.debug("%s | %s | %s | %s | 任务分发开始" % (operViewName, taskSeq, devName, actionName))
                    taskRunStatus = taskDispatch(taskItem, mySqlUtil, taskNameDict, u2ConStart=u2Connect)
                    if taskRunStatus[0] == 4:
                        retStatus = True
                        logger.debug(
                            "%s | %s | %s | %s | 完成 " % (operViewName, taskSeq, devName, actionName))
                    elif taskRunStatus[0] == 8:
                        retStatus = True
                        logger.debug(
                            "%s | %s | %s | %s | 聊天任务重复，忽略 " % (operViewName, taskSeq, devName, actionName))
                    elif taskRunStatus[0] == 3 and taskItem[2] in reTryIgnoreList:
                        remarks = taskRunStatus[1]
                        logger.warn("%s | %s | %s | %s | 失败 | %s" % (operViewName, taskSeq, devName, actionName, remarks))
                        # logger.info("任务类型-%s 失败退出" % (taskItem[2]))

                    else:
                        remarks = taskRunStatus[1]
                        logger.debug(
                            "%s | %s | %s | %s | 失败 | %s" % (operViewName, taskSeq, devName, actionName, remarks))
                        # logger.info("taskSeq:%s, 任务类型-%s 执行失败, remarkds:%s。" % (taskSeq, taskItem[2], remarks))
                else:
                    logger.debug("%s | %s | %s | %s | 失败 | %s" % (operViewName, taskSeq, devName, actionName, remarks))
                    # logger.info("taskSeq:%s, 任务类型-%s 执行失败, remarkds:%s。" % (taskSeq, taskItem[2], remarks))
            else:
                retStatus = False
                remarks = "设备初始化失败"
        else:
            logger.warn("%s | %s | %s | %s | 失败 | 模拟器初始化失败" % (operViewName, taskSeq, devName, actionName))
            retStatus = False
            remarks = "设备初始化失败"
    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())

    return (retStatus, remarks)


def taskDispatch(taskItemInfo, mySqlUtil, taskNameDict, u2ConStart=''):
    '''
    任务分发
    :param taskItemInfo:
    :return:
    '''
    # taskItem (1529744171645, '4129412c-6df1-11e8-951d-246e9664fac5', 7, '127.0.0.1', '21513')
    # 任务类型分发
    taskSeq = taskItemInfo[0]
    taskType = taskItemInfo[2]

    devName = taskItemInfo[6]
    operViewName = taskItemInfo[7]
    taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新

    actionName = ""
    if taskType in taskNameDict.keys():
        actionName = taskNameDict[taskType]
    else:
        actionName = taskType
    logger.debug("%s | %s | %s | 执行 %s " % (operViewName, taskSeq, devName, actionName))
    if taskType == 1:

        status = addFriend.action(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 2:

        # logger.info("执行随机聊天")
        status = randomChat.action(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 3:

        # logger.info("执行转发朋友圈功能-转发链接")
        status = momentsNew.forwardMomentsDB(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 4:

        # logger.info("发朋友圈功能表-发文字图片")
        status = momentsNew.sendMomentsDB(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType in [6,23,24]:

        # 判断是否重复
        taskSeqRunFlag = redisUtil.taskSeqGet(taskSeq,3)
        if taskSeqRunFlag is not None and taskType == 6:
            status = (8,"#") # 重复不执行
        else:
            # redisDb = 3
            # expireTime = 60 * 60 * 24
            # redisUtil.taskSeqSet(taskSeq, redisDb, expireTime)
        # logger.info("执行聊天内容发送")
            if not common.isApkRunning(u2ConStart):#首次启动模拟器未启动apk，应先启动apk，否则会导致第一条消息发布出去
                wxUtil.appStart(u2ConStart, logger)
            status = sendWxMessage.action(logger, u2ConStart, taskItemInfo, mySqlUtil, taskType)

    elif taskType == 7:

        # logger.info("执行状态检查完毕")
        status = (4,"#")
    elif taskType == 9:

        # logger.info("执行好友信息更新")
        # if not common.isApkRunning(u2ConStart):#首次启动模拟器未启动apk，应先启动apk，否则会导致第一条消息发布出去
        #     wxUtil.appStart(u2ConStart, logger)
        # status = getWxFriendList.get_wx_friend_info(logger, u2ConStart, taskItemInfo, mySqlUtil)
        # 屏蔽刷好友逻辑，由即时任务替代
        status = (4, "#")
    elif taskType == 12:

        # logger.info("一键拉群")
        status = groupAction.actionCreate(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 13:

        # logger.info("群加好友")
        status = groupAction.actionAdd(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 14:

        # logger.info("群删好友")
        status = groupAction.actionDel(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 15:

        # logger.info("群解散")
        status = groupAction.groupDel(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 16:

        # logger.info("修改公告")
        status = groupAction.noticeModify(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 17:

        # logger.info("更换群主")
        status = groupAction.mainWxChange(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 18:

        # logger.info("修改群主昵称")
        status = groupAction.wxNameModify(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 19 or taskType == 20:

        # logger.info("微信登录/登出")
        status = login.main(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 21:

        # logger.info("修改好友备注")
        status = getWxFriendList.change_friend_remark(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 22:

        # logger.info("一键加好友")
        status = addFriend.OneKeyAction(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 25:

        # logger.info("转发规则生效")
        status = transpondRuleManager.action(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 26:

        # logger.info("app重启")
        status = appManager.action(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 27:

        # logger.info("聊天链接处理")
        status = fileLoad.chatRecordAction(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 28:

        # logger.info("机器关闭")
        status = machinInfo.machineClose(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 29:

        # logger.info("转发链接")
        status = transpond.transpondAction(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 30:
        # logger.info("通讯录加好友")
        status = addFriend.addFriendByContact(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 32:
        # logger.info("通讯录补充搜索")
        status = addFriend.addFriendConPlus(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 33:
        logger.info("重启模拟器wifi")
        status,u2ConStart = machinInfo.restartWifi(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 34:
        logger.info('删除模拟器')
        status = machinInfo.deleteVM(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 35:
        logger.debug("群发消息")
        status = groupSent.action(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 37:
        status = wxDataClear.action(logger, u2ConStart, taskItemInfo, mySqlUtil)
    elif taskType == 99:
        logger.debug("测试99")
        status = sleepAction99(logger, u2ConStart, taskItemInfo, mySqlUtil)
    else:
        logger.info("任务类型无效："+str(taskType))
        status=(3,"任务类型无效")

    # 最后检测是否中途挤下线
    loginOut = wxUtil.indexJudege(u2ConStart, logger)
    if loginOut:
        taskUuid = taskItemInfo[1]
        wxOffLineSql = """UPDATE wx_account_info SET if_start = 0  where uuid=\"%s\"""" % (taskUuid)
        mySqlUtil.excSql(wxOffLineSql)

    u2ConStart = None
    taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新
    return status

def specialTaskCheck(taskSeq,actType,mySqlUtil_main):

    taskInfoCheckSql = """SELECT TIMESTAMPDIFF(SECOND,heartBeatTime,now()),ifKill from wx_task_manage
                        where taskSeq = \"%s\""""%(taskSeq)
    taskInfoCheck = mySqlUtil_main.getData(taskInfoCheckSql)

    if taskInfoCheck:
        heartBeatCheckSec = taskInfoCheck[0][0]
        ifKill = taskInfoCheck[0][1]
    else:
        heartBeatCheckSec = 0
        ifKill = 0

    return (heartBeatCheckSec, ifKill)

def mulProcess(DP_Pool, resultsList, taskList, taskPidQueue,taskNameDict):
    try:
        for taskItem in taskList:
            taskSeq = taskItem[0]
            uuid = taskItem[1]
            statusRecordAction(taskSeq, 2, mySqlUtil_main, taskItem, "#")

            # 任务下发，执行主体taskAction，后续参数均以taskItem为传递信息
            result = DP_Pool.apply_async(taskAction, args=(taskItem,taskPidQueue,taskNameDict))

            # taskSeq 记录
            # ex: 过期时间（s）,一天 = 60 * 60 * 24
            # nx：如果设置为True，则只有name不存在时，当前set操作才执行
            # redisUtil.taskSeqSet(taskSeq, 3, 60 * 60 * 24)

            # 任务结果记录
            resultsList[uuid] = [result, taskItem, time.time()]
    except Exception as e:
        logger.warn(traceback.format_exc())

def ovetTimeProcessor(taskItem):
    taskSeq = taskItem[1][0]
    actionType = int(taskItem[1][2])
    actionUuid = taskItem[1][1]
    if actionType == 6:
        msgInfoGetSql = """SELECT wx_main_id, wx_id, type, content, msgId FROM `wx_chat_task`
                                                        where taskSeq = '%s'""" % (taskSeq)
        msgInfoGet = mySqlUtil_main.getData(msgInfoGetSql)[0]
        wxMainId = msgInfoGet[0]
        wxId = msgInfoGet[1]
        acType = msgInfoGet[2]
        msgContent = msgInfoGet[3]
        msgId = msgInfoGet[4]
        msgErrInfo = ""
        if int(acType) == 1:
            msgErrInfo = "信息发送失败（超时）：%s" %(msgContent)
        elif int(acType) == 2:
            msgErrInfo = "图片发送失败（超时）：%s" % (msgContent.split('|')[1])
        elif int(acType) == 3:
            msgErrInfo = "文件发送失败（超时）：%s" % (msgContent.split('|')[1])
    elif actionType == 27:
        msgInfoGetSql = """SELECT 
                            (select wx_id from wx_account_info where uuid = '%s'),
                            objectId, type, fileName, msgId 
                             from wx_fileLoad_task
                            where taskSeq = '%s'""" % (actionUuid,taskSeq)
        msgInfoGet = mySqlUtil_main.getData(msgInfoGetSql)[0]
        wxMainId = msgInfoGet[0]
        wxId = msgInfoGet[1]
        acType = msgInfoGet[2]
        msgContent = msgInfoGet[3]
        msgId = msgInfoGet[4]
        msgErrInfo = ""
        if int(acType) == 1:
            msgErrInfo = "文件下载失败（超时）：%s" % (msgContent)
        elif int(acType) == 2:
            msgErrInfo = "视频下载失败（超时）：%s" % (msgContent.split('|')[1])


    common.messageNotice(wxMainId, wxId, msgErrInfo, msgId, mySqlUtil_main)

def taskNameGet(mySqlUtil):
    global taskNameDict
    # taskNameDict = {}
    taskNameGetSql = """select value,name from wx_dictionary
                        where type="task_type" """
    taskNameGet = mySqlUtil.getData(taskNameGetSql)
    for taskName in taskNameGet:
        value = taskName[0]
        name = taskName[1]
        if value not in taskNameDict.keys():
            taskNameDict[value] = name
        if int(value) not in taskNameDict.keys():
            taskNameDict[int(value)] = name
    return taskNameDict


def main(mySqlUtil_main, logger):
    try:
        # 心跳包检测
        moduleName = os.path.basename(__file__).split('.')[0]
        monitorAgent = Monitor.monitorAgent(moduleName)

        taskNameDict = taskNameGet(mySqlUtil_main) # 填充任务名字信息
        logNum = 0
        devInfo = {} # 设备信息表
        resultsList = {}  # resultsList 作为多进程任务结果列表
        manager = multiprocessing.Manager()
        # 父进程创建Queue，并传给各个子进程：
        taskPidQueue = manager.Queue()
        # taskStopQueue = manager.Queue()
        # 模拟器检查状态初始化时间
        checkStartTime = time.time()
        monitorAgent.run()  # 心跳
        # 初始化进程池
        taskNum = int(confAllItems.getOneOptions('taskPool', 'maxTask'))
        logger.info("进程池初始化资源数:%s"%(taskNum))
        DP_Pool = Pool(taskNum)

        # 初始化redis
        # logger.info("初始化redis")
        # redisPool = redis.ConnectionPool(host=redis_ip, port=redis_port, db=3,password=redis_pwd)
        # redisCon = redis.Redis(connection_pool=redisPool)

        last_day=time.strftime("%Y-%m-%d", time.localtime())
        # global logger
        logger.debug("last_day:"+str(last_day))
        hrartBeatNum=0

        while RunFlag:
            monitorAgent.run()  # 心跳
            today = time.strftime("%Y-%m-%d", time.localtime())
            if today!=last_day:
                last_day=today
                logger = getLogger('./log/multiTaskAction.log')
                logger.debug("today:"+str(last_day))
            if hrartBeatNum==10:
                hrartBeatNum=0
                try:
                    sql="select * from wx_status_check where program_type=2 and  wx_main_id='%s'" % DEV_ID
                    rs=mySqlUtil_main.getData(sql)
                    if len(rs)>0:
                        mySqlUtil_main.execSqlWithCount("update wx_status_check set last_heartbeat_time=now(),state=1 where program_type=2 and wx_main_id='%s'" % DEV_ID )
                    else:
                        mySqlUtil_main.execSqlWithCount("insert into wx_status_check (wx_main_id,program_name,last_heartbeat_time,state,program_type)values ('%s','multiTaskAction',now(),'1','2')" % DEV_ID)
                except Exception as e:
                    logger.warn("心跳sql执行报错：%s" %e)
                finally:
                    monitorAgent.run()  # 心跳
            else:
                hrartBeatNum+=1
            monitorAgent.run() # 心跳
            try:
                taskGetListRet = taskGet(mySqlUtil_main, checkStartTime)  # 获取任务信息 ([tasklist],checkStartTime)
                taskGetList = taskGetListRet[0]
                if taskGetListRet[1] is not None:
                    checkStartTime = taskGetListRet[1]
                # 处理任务信息，当前已存在uuid的任务进行过滤
                taskList = []
                for taskInfo in taskGetList:
                    uuidItem = taskInfo[1]
                    devName = taskInfo[6]
                    # 组装设备信息
                    if uuidItem not in devInfo.keys():
                        devInfo[uuidItem] = devName
                    monitorAgent.run()  # 心跳
                    # 组装任务信息
                    if uuidItem not in resultsList:
                        taskList.append(taskInfo)

                # taskExists = True
                if taskList is not None and len(taskList) > 0:
                    #############################################环境检查#############################################
                    monitorAgent.run()  # 心跳
                    machinInfo.taskMachineCheck(taskList)
                    monitorAgent.run()  # 心跳
                    #############################################任务执行#############################################
                    logger.debug("当前新增任务数量 : %s" % (len(taskList)))
                    #logger.info("当前执行uuid:%s" % (resultsList.keys()))
                    monitorAgent.run()  # 心跳
                    mulProcess(DP_Pool, resultsList, taskList, taskPidQueue, taskNameDict)  # 主进程池运行，返回结果为resultsList       ##### MAIN #####
                    monitorAgent.run()  # 心跳
                else:
                    monitorAgent.run()  # 心跳
                    # 无有效任务
                    logNum += 1
                    if logNum >= 60:
                        logger.info("...")
                        if resultsList:
                            logger.info("当前执行设备:%s" % ( [ devInfo[i] for i in  resultsList.keys() ]))
                        logNum = 0
                        # taskExists = False

                #############################################任务处理#############################################
                if resultsList:
                    while True:
                        monitorAgent.run()  # 心跳
                        if not taskPidQueue.empty():
                            taskPidInfo = taskPidQueue.get(True)
                            taskUuid = taskPidInfo[0]
                            taskPid = taskPidInfo[1]
                            resultsList[taskUuid].append(taskPid)
                        else:
                            break

                    taskCompleteListTmp = []
                    for taskItemUuid  in resultsList:
                        monitorAgent.run()  # 心跳
                        taskItem = resultsList[taskItemUuid]
                        taskInfo = taskItem[1]
                        operViewName = taskInfo[7]
                        devName = taskInfo[6]

                        taskSeq = taskItem[1][0]
                        actionType = int(taskItem[1][2])
                        actionUuid = taskItem[1][1]
                        taskTimeout = taskItem[2]

                        actionName = ""
                        if actionType in taskNameDict:
                            actionName = taskNameDict[actionType]
                        else:
                            actionName = actionType

                        # 对S_T_TIMEOUT 类型进行检测，防止内部卡死，或者进行主动停止
                        if actionType in S_T_TIMEOUT.keys():
                            monitorAgent.run()  # 心跳
                            heartBeatCheckSec, ifKill = specialTaskCheck(taskSeq,actionType,mySqlUtil_main)
                            if int(S_T_TIMEOUT.get('max')) >= int(heartBeatCheckSec) >= int(S_T_TIMEOUT.get(actionType,TIMEOUT)) or ifKill != 0:
                                try:
                                    command = 'taskkill /F /PID %s' %int(resultsList[actionUuid][-1])
                                    os.system(command)
                                except Exception as e:
                                    logger.warn(traceback.format_exc())
                                finally:
                                    monitorAgent.run()  # 心跳

                                if ifKill != 0 :
                                    logger.warn("%s | %s | %s | %s | 主动停止，任务失败" % (operViewName, taskSeq, devName, actionName))
                                    statusRecordAction(taskSeq, 5, mySqlUtil_main, taskInfo, '主动停止，任务失败')
                                else:
                                    logger.warn(
                                        "%s | %s | %s | %s | 心跳异常，任务失败" % (operViewName, taskSeq, devName, actionName))
                                    # logger.info("%s 心跳异常，任务失败" % (taskSeq))
                                    statusRecordAction(taskSeq, 3, mySqlUtil_main, taskInfo, '心跳异常（%s s）' %(S_T_TIMEOUT.get(actionType,TIMEOUT)))
                                # 程序处理退出记录
                                taskCompleteListTmp.append(taskItemUuid)
                                monitorAgent.run()  # 心跳
                                continue
                        #
                        # taskItem -> (result,taskItem)
                        if taskItem[0].ready():  # 进程函数是否已经完成
                            monitorAgent.run()  # 心跳
                            if taskItem[0].successful():  # 进程函数是否执行成功
                                # 进程无报错返回
                                # 获取进程返回
                                returnInfo = taskItem[0].get(timeout=1)
                                status = returnInfo[0]  # 执行状态
                                remarks = returnInfo[1]  # 执行备注
                                #logger.debug("%s 执行完成 ：status-%s,remarks-%s" % (taskSeq, status, remarks))
                                if status is True or status == 4:
                                    logger.info(
                                        "%s | %s | %s | %s | 执行成功" % (operViewName, taskSeq, devName, actionName))
                                    # logger.info("%s 执行成功：remarks-%s" % (taskSeq, remarks))
                                    # if actionType not in [6,23,24]:
                                    statusRecordAction(taskSeq, 4, mySqlUtil_main, taskInfo, remarks)
                                # statusRecordAction()
                                elif status is False  or status == 3:
                                    logger.warn(
                                        "%s | %s | %s | %s | 执行异常 | %s" % (operViewName, taskSeq, devName, actionName, remarks))
                                    # logger.info("%s 执行异常 ：remarks-%s" % (taskSeq, remarks))
                                    # if actionType not in [6, 23, 24]:
                                    statusRecordAction(taskSeq, 3, mySqlUtil_main, taskInfo, remarks)
                                else:
                                    pass
                                monitorAgent.run()  # 心跳
                                # 程序处理退出记录
                                taskCompleteListTmp.append(taskItemUuid)
                            elif time.time() - taskTimeout >= int(TIMEOUTDICT.get(actionType,TIMEOUT)): # 判断任务是否超时
                                try:
                                    command = 'taskkill /F /PID %s' %int(resultsList[actionUuid][-1])
                                    os.system(command)
                                except Exception as e:
                                    logger.warn(traceback.format_exc())
                                finally:
                                    monitorAgent.run()  # 心跳
                                logger.warn("%s 执行超时，任务失败" % (taskSeq))
                                statusRecordAction(taskSeq, 3, mySqlUtil_main, taskInfo, '任务超时（%s s）' %(TIMEOUTDICT.get(actionType,TIMEOUT)))

                                # 程序处理退出记录
                                taskCompleteListTmp.append(taskItemUuid)
                                monitorAgent.run()  # 心跳
                            # 进程报错返回
                            else: # 任务在处理时间内，报错返回
                                # 进程无报错返回
                                taskSeq = taskItem[1][0]
                                # 获取进程返回
                                returnInfo = taskItem[0].wait(timeout=1)
                                status = returnInfo[0]  # 执行状态
                                remarks = returnInfo[1]  # 执行备注
                                logger.warn(
                                    "%s | %s | %s | %s | 执行异常 | %s | %s" % (operViewName, taskSeq, devName, actionName, status, remarks))
                                # logger.debug("%s 执行异常 ：status-%s,remarks-%s" % (taskSeq, status, remarks))
                                statusRecordAction(taskSeq, 3, mySqlUtil_main, taskInfo,  remarks)

                                # 程序处理退出记录
                                taskCompleteListTmp.append(taskItemUuid)
                                monitorAgent.run()  # 心跳
                        else:
                            # 6 , 27 需要进行处理
                            if time.time() - taskTimeout >= TIMEOUTDICT.get(actionType,TIMEOUT):
                                try:
                                    if actionType in [6, 27]:
                                        ovetTimeProcessor(taskItem) # 任务超时处理
                                    command = 'taskkill /F /PID %s' %int(resultsList[actionUuid][-1])
                                    os.system(command)
                                except Exception as e:
                                    logger.warn(traceback.format_exc())
                                finally:
                                    monitorAgent.run()  # 心跳
                                # taskItem[0].wait(timeout=1) # 采用等待超时结束任务 2
                                logger.warn(
                                    "%s | %s | %s | %s | 执行超时，任务失败" % (operViewName, taskSeq, devName,actionName))
                                # logger.info("%s 执行超时，任务失败" % (taskSeq))
                                statusRecordAction(taskSeq, 3, mySqlUtil_main, taskInfo, '任务超时（%s）' %(TIMEOUTDICT.get(actionType,TIMEOUT)))
                                # 程序处理退出记录
                                taskCompleteListTmp.append(taskItemUuid)
                                monitorAgent.run()  # 心跳

                    # 对已经进行处理的任务pop出 resultsList
                    if taskCompleteListTmp:
                        for taskUuid in taskCompleteListTmp:
                            resultsList.pop(taskUuid)
                        monitorAgent.run()  # 心跳

            except Exception as e:
                logger.warn(traceback.format_exc())
            finally:
                monitorAgent.run()  # 心跳
                time.sleep(0.5)
    except Exception as e:
        logger.warn("multi项目异常，正在退出")
        logger.warn(traceback.format_exc())
        DP_Pool.close()
        DP_Pool.terminate()
        DP_Pool.join()


if __name__ == '__main__':
    # multiprocessing.freeze_support()

    localIp = socket.gethostbyname(socket.getfqdn(socket.gethostname()))
    localIp = '60.206.107.173'

    # logger.info("当前主机IP:%s, 配置主机IP:%s"%(localIp,DEV_ID))
    mySqlUtil_main = MysqlDbPool.MysqlDbPool(1, 10)
    if localIp == DEV_ID:
        logger.info("multiTask 主程序启动")
        main(mySqlUtil_main, logger)
    else:
        logger.warn("主机配置错误 ，请检查,当前主机IP:%s, 配置主机IP:%s"%(localIp,DEV_ID))


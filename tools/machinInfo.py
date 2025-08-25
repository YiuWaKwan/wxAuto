# -*- coding:utf-8 -*-
import random
import traceback
import uiautomator2 as u2
import time
import linecache
import requests

from tools import wxUtil, MysqlDbPool
import win32gui, win32con
import os
import subprocess
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
import hashlib
import re
from tools import oracleDPool
from tools.common import alarm

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/machineInfo.log')
# 初始化config
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)
CLIENT_ID = confAllItems.getOneOptions('devInfo', 'dev')
TIMEOUT = int(confAllItems.getOneOptions('taskOption', 'timeout'))

def readMemuFileByKeyWord(filename, keyWord, colsPoint):
    for line in open(filename):
        if line.find(keyWord) != -1:
            fileContent = line.strip()
            cols = fileContent.split("\"")
            data = cols[colsPoint]
            return data
    return ""


def readMemuFileContent(filename, linenum, colsPoint):
    fileContent = linecache.getline(filename, linenum)
    fileContent = fileContent.strip()
    cols = fileContent.split("\"")
    data = cols[colsPoint]
    return data


def modifyFileContent(file, find_str, old_str, new_str):
    """ 替换文件中的字符串  file:文件名    find_str:标识字符串  old_str:就字符串  new_str:新字符串 """

    file_data = ""
    with open(file, "r") as f:
        for line in f:
            if find_str in line:
                line = line.replace(old_str, new_str)
            file_data += line
    with open(file, "w") as f:
        f.write(file_data)


def setMachinInfo(logger, u2Con, taskItemInfo, mySqlUtil):
    """任务7"""
    sql = "SELECT taskSeq,wx_id,clientId,devId,(select uuid from wx_account_info a where a.wx_id=t.wx_id) " \
          "FROM wx_machine_info_task t where taskSeq = %d " % taskItemInfo[0]
    result = mySqlUtil.fetchData(sql)
    if result[0] == 1 and len(result[1]) > 0:
        taskItem = result[1][0]
    else:
        logger.error("读任务信息出错")
        sql = "delete from wx_machine_info_task where taskSeq='%s'" % taskItemInfo[0]
        mySqlUtil.excSql(sql)
        return 3
    sql = "delete from wx_machine_info_task where taskSeq='%s'" % taskItemInfo[0]
    mySqlUtil.excSql(sql)
    path = os.environ['MEMUDATAPATH']
    if path == '':
        logger.error("环境变量MEMUDATAPATH没有配置，请配置模拟器的镜像路径！")
        return 3
    files = os.listdir(path)  # 得到文件夹下的所有文件名称
    devDir = None
    devIp = ''
    devPort = ''
    mac = ''
    devIp = ''
    devPort = ''
    memuImei = ''
    memuPhone = ''
    vm_manufacturer = ''
    vm_model = ''
    telecom = ''
    for file in files:  # 遍历文件夹
        if not file.startswith('.'):
            filename = path + os.path.sep + file + os.path.sep + file + ".memu"
            winName = readMemuFileByKeyWord(filename, "name_tag", 3)
            print("%s-%s-%s" % (taskItem[3], winName, winName == taskItem[3]))
            if (taskItem[3] == winName):
                devDir = file
                # mac ip port
                mac = readMemuFileContent(filename, 66, 5)
                devIp = readMemuFileContent(filename, 74, 5)
                devPort = readMemuFileContent(filename, 74, 7)
                memuImei = readMemuFileByKeyWord(filename, "imei", 3)
                memuPhone = readMemuFileByKeyWord(filename, "linenum", 3)
                vm_manufacturer = readMemuFileByKeyWord(filename, "microvirt_vm_manufacturer", 3)
                vm_model = readMemuFileByKeyWord(filename, "microvirt_vm_model", 3)
                telecom = readMemuFileByKeyWord(filename, "operator_network", 3)
                break

    if devDir is not None:
        sql = "SELECT id,uuid,clientId,devId,devName,devDir,devIp,devPort,status,create_time FROM wx_machine_info where clientId='%s' and devId='%s'" % (
        taskItem[2], taskItem[3])
        result = mySqlUtil.fetchData(sql)

        if result[0] == 1:
            # 获取返回结果
            if len(result[1]) > 0:
                sql = "update wx_machine_info set uuid='%s',devDir='%s',devIp='%s',devPort='%s',memu_imei='%s',memu_mac='%s'," \
                      "memu_phone='%s',telecom='%s',vm_manufacturer='%s',vm_model='%s' where clientId='%s' and devId='%s' " % \
                      (
                      taskItem[4], devDir, devIp, devPort, memuImei, mac, memuPhone, telecom, vm_manufacturer, vm_model,
                      taskItem[2], taskItem[3])
            else:
                sql = "insert into wx_machine_info(uuid,clientId,devId,devName,devDir,devIp,devPort,status," \
                      "create_time,memu_imei,memu_mac,memu_phone,telecom,vm_manufacturer,vm_model)values('%s','%s','%s','%s'," \
                      "'%s','%s','%s',0,now(),'%s','%s','%s','%s','%s','%s')" % (
                      taskItem[4], taskItem[2], taskItem[3], taskItem[3], devDir, devIp, devPort,
                      memuImei, mac, memuPhone, telecom, vm_manufacturer, vm_model)
            mySqlUtil.excSql(sql)
            statusRecord = 4
        else:
            statusRecord = 3
            logger.error("查询机器信息出错")
    else:
        statusRecord = 3
        logger.error("没有找到匹配的模拟器")

    return statusRecord


def modifyMachinInfo(logger, u2Con, taskItemInfo, mySqlUtil):
    """任务8"""
    try:
        machinfo = ()
        sql = "select devDir,memu_imei,memu_phone,vm_manufacturer,vm_model,telecom,memu_mac, devName, t.taskSeq " \
              "from wx_machine_info i ,wx_task_manage t  " \
              "where t.uuid =i.uuid and t.actionType=8 and t.status=2 and t.taskSeq=%d" % taskItemInfo[0]
        result = mySqlUtil.fetchData(sql)
        if result[0] == 1 and len(result[1]) > 0:
            machinfo = result[1][0]
        else:
            logger.error("读任务信息出错")
            return 3

        path = os.environ['MEMUDATAPATH']
        logger.debug(path)
        if path == '':
            logger.error("环境变量MEMUDATAPATH没有配置，请配置模拟器的镜像路径！")
            return False

        filename = path + os.path.sep + machinfo[0] + os.path.sep + machinfo[0] + ".memu"
        memuImei = readMemuFileByKeyWord(filename, "imei", 3)
        memuPhone = readMemuFileByKeyWord(filename, "linenum", 3)
        vm_manufacturer = readMemuFileByKeyWord(filename, "microvirt_vm_manufacturer", 3)
        vm_model = readMemuFileByKeyWord(filename, "microvirt_vm_model", 3)
        telecom = readMemuFileByKeyWord(filename, "operator_network", 3)
        mac = readMemuFileContent(filename, 66, 5)

        server_start = False
        hwnd = win32gui.FindWindow(None, machinfo[7])
        if hwnd != 0:  # 先退出模拟器，防止文件修改冲突
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            server_start = True
            time.sleep(2)

        if memuImei != machinfo[1]:
            modifyFileContent(filename, 'imei', memuImei, machinfo[1])
        if memuPhone != machinfo[2]:
            modifyFileContent(filename, 'linenum', memuPhone, machinfo[2])
        if vm_manufacturer != machinfo[3]:
            modifyFileContent(filename, 'microvirt_vm_brand', vm_manufacturer, machinfo[3])
            modifyFileContent(filename, 'microvirt_vm_manufacturer', vm_manufacturer, machinfo[3])
        if vm_model != machinfo[4]:
            modifyFileContent(filename, 'microvirt_vm_model', vm_model, machinfo[4])
        if telecom != machinfo[5]:
            modifyFileContent(filename, 'operator_network', telecom, machinfo[5])
        if mac != machinfo[6]:
            modifyFileContent(filename, machinfo[6], mac, machinfo[6])
        if server_start:  # 启动模拟器
            cmdCommand = "MEmuConsole.exe " + machinfo[0]
            os.system(cmdCommand)
    except (Exception) as e:
        logger.warn(e)
        return 3

    return 4


def startup(logger, u2Con, taskItemInfo, mySqlUtil):
    """任务10"""
    try:
        sql = "SELECT devName,devDir FROM wx_machine_info t where uuid = '%s' " % taskItemInfo[1]
        result = mySqlUtil.fetchData(sql)
        taskItem = ()
        if result[0] == 1 and len(result[1]) > 0:
            taskItem = result[1][0]
        else:
            logger.error("读机器信息出错")
            return 3

        hwnd = win32gui.FindWindow(None, taskItem[0])
        if hwnd != 0:  # 如果模拟器已经启动则不需要再启动
            logger.info("模拟器已经启动")
        else:
            cmdCommand = "MEmuConsole.exe " + taskItem[1]
            os.system(cmdCommand)
            logger.info("启动成功")
        time.sleep(3)  # 防止启动过快

        sql = "update wx_account_info set if_start='1' where uuid='%s'" % taskItemInfo[1]
        mySqlUtil.excSql(sql)
        return 4
    except (Exception) as e:
        logger.warn(e)
        return 3


def shutdown(logger, u2Con, taskItemInfo, mySqlUtil):
    """任务11"""
    try:
        sql = "SELECT devName,devDir FROM wx_machine_info t where uuid = '%s' " % taskItemInfo[1]
        result = mySqlUtil.fetchData(sql)
        taskItem = ()
        if result[0] == 1 and len(result[1]) > 0:
            taskItem = result[1][0]
        else:
            logger.error("读机器信息出错")
            return 3

        hwnd = win32gui.FindWindow(None, taskItem[0])
        if hwnd != 0:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            logger.info("关闭成功")
        else:  # 如果模拟器关闭则不需要再关闭
            logger.info("模拟器已经关闭")
        return 4
    except (Exception) as e:
        logger.warn(e)
        return 3


def stateCheck(logger, DEV_ID, mySqlUtil):
    """任务11"""
    try:
        sql = "SELECT t.devName, a.uuid, a.if_start FROM wx_machine_info t, wx_account_info a where t.uuid=a.uuid and clientId='%s'" % DEV_ID
        result = mySqlUtil.fetchData(sql)
        taskItem = ()
        if result[0] == 1 and len(result[1]) > 0:
            taskItem = result[1]
            for item in taskItem:
                hwnd = win32gui.FindWindow(None, item[0])
                if hwnd != 0:  # 状态不正确 模拟器已启动
                    if item[2] == 0:
                        sql = "update wx_account_info set if_start='1' where uuid='%s' " % item[1]
                        mySqlUtil.excSql(sql)
                elif item[2] == 1:  # 模拟器已关闭
                    sql = "update wx_account_info set if_start='0' where uuid='%s' " % item[1]
                    mySqlUtil.excSql(sql)
        else:
            logger.error("读机器信息出错")
    except (Exception) as e:
        logger.warn(e)


# 初始化当前机器所有的模拟器到数据库
def setAllMachineInfo(mySqlUtil):
    path = os.environ['MEMUDATAPATH']
    if path == '':
        logger.error("环境变量MEMUDATAPATH没有配置，请配置模拟器的镜像路径！")
        return 3
    files = os.listdir(path)  # 得到文件夹下的所有文件名称
    devDir = None
    devIp = ''
    devPort = ''
    mac = ''
    devIp = ''
    devPort = ''
    memuImei = ''
    memuPhone = ''
    vm_manufacturer = ''
    vm_model = ''
    telecom = ''
    for file in files:  # 遍历文件夹
        if not file.startswith('.'):
            devPort = "21503"
            if str(file)!="MEmu":
                devPort=str(21503+10*int(str(file).split("_")[1]))
            filename = path + os.path.sep + file + os.path.sep + file + ".memu"
            winName = subprocess.check_output("MEmuManage.exe guestproperty get \"%s\" \"name_tag\"" % str(file)).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]
            devDir = file
            # mac ip port
            mac = readMemuFileContent(filename, 58,5)
            # mac = subprocess.check_output("MEmuManage.exe guestproperty get \"%s\" \"hmac\"" % str(file)).decode(
            #     encoding="utf-8").split('\r\n')[0].split(': ')[1]
            devIp = "127.0.0.1"
            memuImei = subprocess.check_output("MEmuManage.exe guestproperty get \"%s\" \"imei\"" % str(file)).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]
            memuPhone = subprocess.check_output("MEmuManage.exe guestproperty get \"%s\" \"linenum\"" % str(file)).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]
            vm_manufacturer = subprocess.check_output("MEmuManage.exe guestproperty get \"%s\" \"microvirt_vm_manufacturer\"" % str(file)).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]
            vm_model =  subprocess.check_output("MEmuManage.exe guestproperty get \"%s\" \"microvirt_vm_model\"" % str(file)).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]
            telecom = subprocess.check_output("MEmuManage.exe guestproperty get \"%s\" \"microvirt_vm_brand\"" % str(file)).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]

            sql = "SELECT id,uuid,clientId,devId,devName,devDir,devIp,devPort,status,create_time FROM wx_machine_info where clientId='%s' and devId='%s'" % (
                CLIENT_ID, winName)
            result = mySqlUtil.fetchData(sql)

            if result[0] == 1:
                # 获取返回结果
                if len(result[1]) > 0:
                    sql = "update wx_machine_info set devDir='%s',devPort='%s',memu_imei='%s',memu_mac='%s'," \
                          "memu_phone='%s',telecom='%s',vm_manufacturer='%s',vm_model='%s' where clientId='%s' and devId='%s' " % \
                          (devDir, devPort, memuImei, mac, memuPhone, telecom, vm_manufacturer, vm_model, CLIENT_ID,
                           winName)
                else:
                    sql = "insert into wx_machine_info(uuid,clientId,devId,devName,devDir,devIp,devPort,status," \
                          "create_time,memu_imei,memu_mac,memu_phone,telecom,vm_manufacturer,vm_model,if_ready)values('','%s','%s','%s'," \
                          "'%s','%s','%s',0,now(),'%s','%s','%s','%s','%s','%s',1)" % (
                              CLIENT_ID, winName, winName, devDir, devIp, devPort,
                              memuImei, mac, memuPhone, telecom, vm_manufacturer, vm_model)
                logger.info(sql)
                mySqlUtil.excSql(sql)
            else:
                logger.error("查询机器信息出错")


def machineRestart(taskItem):
    returnStatus = False
    devName = taskItem[6]
    devDir = taskItem[5]
    try:
        hwnd = win32gui.FindWindow(None, devName)
        if hwnd != 0:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            cmdCommand = "MEmuConsole.exe " + devDir
            os.system(cmdCommand)
        else:
            cmdCommand = "MEmuConsole.exe " + devDir
            os.system(cmdCommand)
        returnStatus = True
    except Exception as e:
        logger.warn(e)

    return returnStatus

#根据devname来关闭模拟器并删除账号
def machineClose(logger, u2ConStart, taskItemInfo, mySqlUtil):
    uuid = taskItemInfo[1]
    remark="#"
    status=4
    try:
        devName=taskItemInfo[6]
        # uuid_str=taskItemInfo[1]
        hwnd = win32gui.FindWindow(None, devName)
        if hwnd != 0:
            logger.info("关闭模拟器："+str(devName))
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            updateSql = """update wx_machine_info set if_start = '0' where uuid='%s'""" %(uuid)# 更新模拟器状态为未启动
            mySqlUtil.excSql(updateSql)
        else:
            logger.info("模拟器（%s）已经关闭" % str(devName))
        # updateSql = "update wx_machine_info set uuid='' where uuid=('" + uuid_str + "')"
        # logger.info(updateSql)
        # mySqlUtil.excSql(updateSql)
        # delSql = """update wx_account_info set wx_status=0 where  wx_login_id = \'%s\' """ %(wxLoginId)
        # delSql = "DELETE FROM wx_account_info where uuid=('" + uuid_str + "')"
        # logger.info(delSql)
        # mySqlUtil.excSql(delSql)
    except Exception as e:
        logger.debug(e)
        remark="关闭模拟器失败"
        status=3
    return (status, remark)


def adbConnectInit(taskItem):
    logger.debug("adb连接初始化")
    devPort = taskItem[4]
    devName = taskItem[6]
    adbPortTransmitAction = -1
    connectDeviceAction = -1
    try:
        devicesInfoCurrentList = [i.split('\t')[0] for i in
                                  subprocess.check_output("adb devices").decode(encoding="utf-8").split('\r\n')
                                  if ':' in i]
    except Exception as e:
        devicesInfoCurrentList = "adbFail"
        logger.warn(traceback.format_exc())
        # logger.warn(e)
        # process = subprocess.check_output("netstat -ano | findstr \"127.0.0.1:5037\"|findstr \"LISTENING\"",
        #                                   shell=True).decode(encoding="utf-8")
        # adbUsePort = re.split(r" +", process.strip())[4]
        # processPort = subprocess.check_output("taskkill /f /pid %s" % adbUsePort, shell=True)
        # adbRestart = subprocess.check_output("adb start-server", shell=True)
        #
        # devicesInfoCurrentList = [i.split('\t')[0] for i in
        #                           subprocess.check_output("adb devices").decode(encoding="utf-8").split('\r\n') if
        #                           ':' in i]

    # 多并发disconnect操作下线 20180719
    # for devicesInfo in devicesInfoCurrentList:
    #     if "127.0.0.1:%s"%(devPort) != devicesInfo:
    #         subprocess.check_output('adb disconnect %s' % devicesInfo)
    try:
        if devicesInfoCurrentList == "adbFail":
            logger.info("%s adb connect 失败" % devName)
        elif "127.0.0.1:%s" % (devPort) not in devicesInfoCurrentList:
            logger.debug("%s adb connect" % (devName))
            connectDeviceAction = subprocess.check_output('adb connect %s:%s' % (taskItem[3], taskItem[4]))
            if b'unable' not in connectDeviceAction:
                logger.debug("%s  adb connect 成功" % (devName))
                connectDeviceActionFlag = 0
            else:
                logger.debug("%s adb connect 失败" % devName)
                connectDeviceActionFlag = -1
        else:
            logger.debug("%s adb connect 成功" % devName)
            connectDeviceActionFlag = 0
            connectDeviceAction = 0
        # adbPortTransmitAction = subprocess.check_call('adb forward tcp:7912 tcp:7912')
        adbPortTransmitAction = 0
    except Exception as e:
        logger.warn(e)
        # logger.debug(connectDeviceAction,connectDeviceActionFlag,adbPortTransmitAction)
    if connectDeviceAction == 0 and connectDeviceActionFlag == 0 and adbPortTransmitAction == 0:
        logger.debug("%s 全部初始化完成" % devName)
        retStatus = True
    else:
        retStatus = False

    return retStatus


def u2Init(taskItem, logger):
    # u2 初始化
    devName = taskItem[6]
    logger.debug("%s u2 初始化" % devName)
    initStatus = False
    u2ConStart = u2.connect('127.0.0.1:%s' % taskItem[4])
    try:
        while True:
            if u2ConStart.info:
                initStatus = True
            else:
                u2ConStart.healthcheck()
            if initStatus:
                break
    except(Exception):
        logger.debug("u2 初始化失败,进行重启")
        initNum = 0

        while True:
            if initNum >= 4:
                logger.warn("%s u2 初始化 失败" % devName)
                break
            try:
                # subprocess.check_call('python -m uiautomator2 init  --serial 127.0.0.1:%s' % (taskItem[4]))
                if u2ConStart.healthcheck():
                    u2ConStart.press("home")
                    time.sleep(0.5)
                    # subprocess.check_call('adb shell input keyevent 3')
                    initStatus = True
                    break
                else:
                    time.sleep(1)
                initNum += 1

            except Exception as e:
                initNum += 1

    return (initStatus, u2ConStart)


def findWxApp(taskItem, logger, mySqlUtil):
    '''
        :param taskItem: taskSeq, uuid, actionType, devIp, devPort,devName
        :return:
        '''
    devName = taskItem[6]
    taskActionType = taskItem[2]
    taskUuid = taskItem[1]
    logger.debug("%s findWxApp" % devName)
    retStatus = False
    ifStart = 1
    # u2 初始化
    initStatus = u2Init(taskItem, logger)  # return(status,u2)

    # 页面监控注册
    if initStatus[0]:
        wxUtil.watcherRegister(initStatus[1])

    if initStatus[0] and taskActionType not in [19, 20]:
        # 初始化成功
        u2ConStart = initStatus[1]
        # time.sleep(0.5)
        loopNum = 0
        while True:
            loopNum += 1
            # 模拟器故障
            logger.debug("模拟器故障检测")
            wxUtil.machineBrowSkip(u2ConStart, logger)
            # 判断当前是否为微信界面
            if u2ConStart.info.get('currentPackageName') == "com.tencent.mm":
                logger.debug("当前处于微信界面")
                # 查看更新页，忽略掉
                # wxUtil.wxUpdateSkip(u2ConStart, logger)
                # 忽略告警框
                wxUtil.pwModifySkip(u2ConStart, logger)
                # 判断微信是否被挤下线
                # loginOut = wxUtil.judge_logout(u2ConStart)
                # if loginOut:
                #     logger.info("%s 设备微信号已下线" % devName)
                #     wxOffLineSql = """UPDATE wx_account_info SET if_start = 0  where uuid=\"%s\"""" % (taskUuid)
                #     mySqlUtil.excSql(wxOffLineSql)
                #     return (False, u2ConStart, 0)
                # 判断微信是否登出
                loginOut = wxUtil.indexJudege(u2ConStart, logger)
                if loginOut:
                    logger.info("%s 设备微信号已下线" % devName)
                    wxOffLineSql = """UPDATE wx_account_info SET if_start = 0  where uuid=\"%s\"""" % (taskUuid)
                    mySqlUtil.excSql(wxOffLineSql)
                    return (False, u2ConStart, 0)
                # 判断微信是否登出
                # loginOut = wxUtil.indexJudege(u2ConStart, logger)
                # if loginOut:
                #     logger.info("%s 设备微信号已下线" % devName)
                #     wxOffLineSql = """UPDATE wx_account_info SET if_start = 0  where uuid=%s""" % (taskUuid)
                #     mySqlUtil.excSql(wxOffLineSql)
                #     return (False, u2ConStart, 0)
                else:
                    # 回到微信主界面
                    if taskActionType not in [6,23,24,27,29]: # 无需backToHome的任务
                        wxUtil.backToHome(u2ConStart)
                    retStatus = True
                    break
            else:
                if wxUtil.elementExistOnlyByText(u2ConStart, u"微信", 0.1):
                    wxUtil.clickOnlyByText(u2ConStart, u"微信")
                else:
                    u2ConStart.press("home")
            if loopNum >= 4:
                raise Exception(" %s 微信app查找失败" % (devName))
            time.sleep(1)
    elif initStatus[0] and taskActionType in [19, 20]:
        u2ConStart = initStatus[1]
        retStatus = True
    else:
        # 初始化失败
        u2ConStart = None

    if not retStatus:
        u2ConStart = None

    return (retStatus, u2ConStart, ifStart)


def adbRestart():
    pass

def wxErrAlert(logger,devName,alertType):
    devID = confAllItems.getOneOptions('devInfo', 'dev')
    taskSeq = round(time.time() * 1000 + random.randint(100, 999))
    userListAlert = confAllItems.getOneOptions("alarm", "user_list")
    alarmMsg = ""
    if alertType == 1:
        alarmMsg = " %s 主机：%s 初始化失败，请登陆主机查看" %(devID,devName)

    # 初始化oracle db
    oracleAction = oracleDPool.oracleDbAction(logger)
    weixinAlarmSql = """insert into weixin.wxerrmsg (msgid, msgcontent, msgtype, msgtime, targetuser,status, createuser) 
                                    values ('%s','%s','21',sysdate,'%s','0','edent')""" % (
        taskSeq, alarmMsg, userListAlert)
    oracleAction.insertData(weixinAlarmSql)

def machineInit(taskItem, mySqlUtil):
    try:
        taskSeq = taskItem[0]
        devName = taskItem[6]
        devPort = taskItem[4]
        devDir = taskItem[5]
        logger.debug("%s 机器初始化" % devName)
        machineStartStatus = False
        startTime = time.time()
        startDeadLine = startTime + TIMEOUT  # deadTime 为120s （TIMEOUT为120 20180724）
        outTimeLoop = 1
        reconnectLoop = 0
        reConnectFlag = False
        devRestartFlag = False

        while True:
            try:
                adbDevAction = subprocess.check_output('adb devices').decode(encoding="utf-8")
            except Exception as e:
                logger.warn(traceback.format_exc())
                break
            if time.time() >= startDeadLine:
                break
            hwnd = win32gui.FindWindow(None, devName)
            # adb断连已连上
            if '%s\tdevice' % (devPort) in adbDevAction:
                # 进行adb初始化
                statusDevCheckCommand = """adb -s 127.0.0.1:%s shell dumpsys activity activities"""%(devPort)
                try:
                    statusDevCheck = [i for i in
                                      subprocess.check_output(statusDevCheckCommand).decode(encoding="utf-8").split(
                                          '\r\r\n')
                                      if "idle=true" in i and "visible=true" in i]
                except Exception as e:
                    statusDevCheck = []

                if len(statusDevCheck) > 0:
                    logger.debug("%s 初始化正常" % devName)
                    machineStartStatus = True
                    break
                else:
                    time.sleep(3)
            elif hwnd != 0 and not devRestartFlag:#adb断连，需要重连
                logger.debug("%s 设备开启，adb 重连" % devName)
                adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                subprocess.check_call(adbReconnectCommand)
                time.sleep(2)
            elif hwnd == 0:#模拟器未启动
                logger.debug("%s 设备未开启，即将启动" % devName)
                subprocess.check_call("MEmuConsole.exe %s" % devDir)
                devRestartFlag = True
                try:
                    sql = "update wx_login_task set x_value='',state='0',remark='数据恢复中'  where taskSeq='%s'" \
                          % taskSeq
                    mySqlUtil.execSql(sql)
                except (Exception) as e:
                    logger.info(e)
                time.sleep(5)
            elif '%s\toffline' % (devPort) in adbDevAction and not reConnectFlag and not devRestartFlag:#adb offline
                logger.debug("%s 设备 offline，adb 重连" % devName)
                adbReconnectCommand = "adb connect 127.0.0.1:%s" %(devPort)
                subprocess.check_call(adbReconnectCommand)
                reconnectLoop += 1
                if reconnectLoop > 3:
                    logger.debug("%s 设备adb重连失败" % devName)
                    reConnectFlag = True
                time.sleep(1)
            elif reConnectFlag: #重连失败，重启模拟器
                logger.debug("%s 设备重启" % devName)
                hwnd = win32gui.FindWindow(None, devName)
                if hwnd != 0:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                subprocess.check_call("MEmuConsole.exe %s" % devDir)
                devRestartFlag = True
                reConnectFlag = False
                time.sleep(5)
            elif (time.time() - startTime) / (50 * outTimeLoop) > 1:#50秒内无响应，重连adb
                logger.warn("%s 模拟器重启后50s内连不上adb，尝试重连"% devName)
                adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                subprocess.check_call(adbReconnectCommand)
                outTimeLoop += 1
                time.sleep(1)
            else:
                logger.debug("%s 设备下一轮查验" % devName)
                time.sleep(5)
    except Exception as e:
        logger.warn(traceback.format_exc())

    return machineStartStatus


def machineLoginInOut(taskItem, mySqlUtil):
    logger.debug('machineLoginInOut')
    '''

    :param taskItem: taskSeq, uuid, actionType, devIp, devPort,devName
    :return:
    '''
    actioType = taskItem[2]
    devName = taskItem[6]
    retStatus = False
    if actioType == 19:
        time.sleep(1)
        hwnd = win32gui.FindWindow(None, devName)
        if hwnd != 0:
            logger.debug("2 已经开启模拟器")
            devDirGetSql = """SELECT devDir FROM wx_machine_info t where devName = \'%s\'""" % (devName)
            devDir = mySqlUtil.getData(devDirGetSql)[0][0]
            ## 3分钟内判断设备启动状态
            machineStartStatus = machineInit(taskItem, devDir)
            ##

            if machineStartStatus:
                deadline = time.time() + 60
                while time.time() < deadline:
                    # print(1)
                    hwnd = win32gui.FindWindow(None, devName)
                    if hwnd != 0:
                        # print(2)
                        wxStart = findWxApp(taskItem)
                        if wxStart[0]:
                            retStatus = True
                            u2ConStart = wxStart[1]
                            break
                        else:
                            retStatus = False
                            u2ConStart = None
                    else:
                        time.sleep(5)
            else:
                logger.warn("模拟器初始化失败")
                retStatus = False
                u2ConStart = None
        else:
            logger.debug("未开启模拟器")
            # 启动模拟器
            devDirGetSql = """SELECT devDir FROM wx_machine_info t where devName = \'%s\'""" % (devName)
            devDir = mySqlUtil.getData(devDirGetSql)[0][0]
            try:
                subprocess.check_call("MEmuConsole.exe %s" % devDir)
            except Exception as e:
                logger.warn(e)

            ## 3分钟内判断设备启动状态
            machineStartStatus = machineInit(taskItem, devDir)
            ##
            # 判断主界面是否存在微信
            if machineStartStatus:
                deadline = time.time() + 60
                while time.time() < deadline:
                    # print(1)
                    hwnd = win32gui.FindWindow(None, devName)
                    if hwnd != 0:
                        # print(2)
                        wxStart = findWxApp(taskItem)
                        if wxStart[0]:
                            retStatus = True
                            u2ConStart = wxStart[1]
                            break
                        else:
                            retStatus = False
                            u2ConStart = None
                    else:
                        time.sleep(5)
            else:
                logger.warn("模拟器初始化失败")
                retStatus = False
                u2ConStart = None
    elif actioType == 20:
        hwnd = win32gui.FindWindow(None, devName)
        if hwnd != 0:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            retStatus = True
        else:
            retStatus = True
        u2ConStart = None

    return (retStatus, u2ConStart)


def machineLoginInit(u2, uuid, mySqlUtil):
    uin = None
    final_pwd = None
    try:
        xmlRes = u2.shell("cat /data/data/com.tencent.mm/shared_prefs/system_config_prefs.xml")
        if xmlRes[1] == 0:
            for xmlStr in xmlRes[0].split('\n'):
                if "default_uin" in xmlStr:
                    uin = xmlStr.split("\"")[3]
                    # if uin[0] == '-' and len(uin) == 10:
                    sql = "select memu_imei from wx_machine_info where uuid='" + str(uuid) + "'"
                    imei = mySqlUtil.getData(sql)[0][0]
                    uin_imei = imei + uin
                    hl = hashlib.md5()
                    hl.update(uin_imei.encode(encoding='utf-8'))
                    md5_pwd = hl.hexdigest()
                    final_pwd = md5_pwd[0:7]
                    sql = "update wx_account_info set uin='" + str(uin) + "',db_passwd='" + str(
                        final_pwd) + "' where uuid='" + str(uuid) + "'"
                    mySqlUtil.execSql(sql)
    except Exception as e:
        logger.info(traceback.format_exc())
    return uin, final_pwd


def vmsInit(taskSeq,devId, maxNum, name, wx_name, app_name, xPose_name, build_flag):
    try:
        success = True #全部新建成功标识
        status = 4 #先把任务状态置为完成
        mySqlUtil = MysqlDbPool.MysqlConn()
        for i in range(0, maxNum):
            currentMachine = subprocess.check_output("MEmuManage.exe list vms")
            currentMachineListOld = [str(i.split(" ")[0].replace("\"", "").replace("\'", "")) for i in
                                     subprocess.check_output("MEmuManage.exe list vms").decode(encoding="utf-8").split(
                                         '\r\n')
                                     if i]
            currentMachineOldLen = len(currentMachineListOld)
            createMachine = subprocess.check_call("MEmuConsole create")
            while True:
                currentMachineListNew = [str(i.split(" ")[0].replace("\"", "").replace("\'", "")) for i in
                                         subprocess.check_output("MEmuManage.exe list vms").decode(encoding="utf-8").split(
                                             '\r\n')
                                         if i]
                currentMachineNewLen = len(currentMachineListNew)
                if currentMachineNewLen > currentMachineOldLen:
                    break
            newMachine = list(set(currentMachineListNew) - set(currentMachineListOld))[0]
            time.sleep(5)
            newMachineSeq = (newMachine.split('_')[1])




            nameMachineSet = subprocess.check_call(
                "MEmuManage.exe guestproperty set \"MEmu_%s\" \"name_tag\" %s%s" % (newMachineSeq, name, newMachineSeq))
            fpsMachineSet = subprocess.check_call(
                "MEmuManage.exe guestproperty set \"MEmu_%s\" \"fps\" 30" % (newMachineSeq))
            cusMachineSet = subprocess.check_call(
                "MEmuManage.exe guestproperty set \"MEmu_%s\" \"is_customed_resolution\" 1" % (newMachineSeq))
            widMachineSet = subprocess.check_call(
                "MEmuManage.exe guestproperty set \"MEmu_%s\" \"resolution_width\" 380" % (newMachineSeq))
            heiMachineSet = subprocess.check_call(
                "MEmuManage.exe guestproperty set \"MEmu_%s\" \"resolution_height\" 580" % (newMachineSeq))
            dpiMachineSet = subprocess.check_call(
                "MEmuManage.exe guestproperty set \"MEmu_%s\" \"vbox_dpi\" 150" % (newMachineSeq))
            startMachine = subprocess.check_call("MEmuConsole.exe %s" % newMachine)

            time.sleep(5)
            portMachineGet = ""
            while True:
                try:
                    portMachineGet = [i.split("=")[1].split(",")[3] for i in subprocess.check_output(
                        "MEmuManage.exe showvminfo --details --machinereadable \"MEmu_%s\"" % (newMachineSeq)).decode(
                        encoding="gbk").split('\r\n') if "Forwarding(0)" in i][0]
                    if portMachineGet != '21503':
                        break
                    else:
                        time.sleep(2)
                except Exception as e:
                    break

            devPort = portMachineGet
            devName = "%s%s" % (name, newMachineSeq)
            devDir = "MEmu_%s" % newMachineSeq
            devIndex = newMachineSeq
            # startTime = time.time()
            # startDeadLine = startTime + 240  # deadTime 为100s （TIMEOUT为120 20180724）
            # allFalseStatus = False
            # print("adb port : %s"%(portMachineGet))
            # while time.time() <= startDeadLine:
            #     # print(time.time() - startTime)
            #     adbDevAction = subprocess.check_output('adb devices').decode(encoding="utf-8")
            #     if '%s\tdevice' % (portMachineGet) in adbDevAction:
            #         print("%s%s 成功启动" % (name, newMachineSeq))
            #         break
            #     elif '%s\toffline' % (portMachineGet) in adbDevAction or allFalseStatus:
            #         print("%s%s 启动失败" % (name, newMachineSeq))
            #         hwnd = win32gui.FindWindow(None, "%s%s" % (name, newMachineSeq))
            #         if hwnd != 0:
            #             win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            #         subprocess.check_call("MEmuConsole.exe %s" % newMachine)
            #         time.sleep(5)
            #     else:
            #         print("%s%s 设备下一轮查验" % (name, newMachineSeq))
            #         time.sleep(5)
            try:
                startTime = time.time()
                startDeadLine = startTime + TIMEOUT
                outTimeLoop = 1
                reconnectLoop = 0
                machineStartStatus = False
                reConnectFlag = False
                devRestartFlag = False
                adbOnceConnectFlag = False

                while True:
                    try:
                        adbDevAction = subprocess.check_output('adb devices').decode(encoding="utf-8")
                    except Exception as e:
                        # print(traceback.format_exc())
                        logger.info(traceback.format_exc())
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
                                              subprocess.check_output(statusDevCheckCommand).decode(encoding="utf-8").split(
                                                  '\r\r\n')
                                              if "idle=true" in i and "visible=true" in i]
                        except Exception as e:
                            statusDevCheck = []

                        if len(statusDevCheck) > 0:
                            logger.info("%s 初始化正常" % devName)
                            machineStartStatus = True
                            break
                        else:
                            time.sleep(3)
                    elif hwnd != 0 and not devRestartFlag and not adbOnceConnectFlag:  # adb断连，需要重连
                        logger.info("%s 设备开启，adb 重连" % devName)
                        adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                        subprocess.check_call(adbReconnectCommand)
                        adbOnceConnectFlag = True
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
                    elif (time.time() - startTime) / (120 * outTimeLoop) > 1:  # 120秒内无响应，重连adb
                        logger.info("%s 模拟器重启后120s内连不上adb，尝试重连" % devName)
                        adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                        subprocess.check_call(adbReconnectCommand)
                        outTimeLoop += 1
                        time.sleep(1)
                    else:
                        logger.info("%s 设备启动中" % devName)
                        time.sleep(5)
            except Exception as e:
                machineStartStatus = False
                logger.warn(traceback.format_exc())



            memu_imei = \
            subprocess.check_output("MEmuManage.exe guestproperty get \"MEmu_%s\" \"imei\"" % newMachineSeq).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]
            memu_mac = \
            subprocess.check_output("MEmuManage.exe guestproperty get \"MEmu_%s\" \"hmac\"" % newMachineSeq).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]
            memu_phone = \
            subprocess.check_output("MEmuManage.exe guestproperty get \"MEmu_%s\" \"linenum\"" % newMachineSeq).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1][1:]
            telecom = subprocess.check_output(
                "MEmuManage.exe guestproperty get \"MEmu_%s\" \"microvirt_vm_brand\"" % newMachineSeq).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]
            vm_manufacturer = subprocess.check_output(
                "MEmuManage.exe guestproperty get \"MEmu_%s\" \"microvirt_vm_manufacturer\"" % newMachineSeq).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]
            vm_model = subprocess.check_output(
                "MEmuManage.exe guestproperty get \"MEmu_%s\" \"microvirt_vm_model\"" % newMachineSeq).decode(
                encoding="utf-8").split('\r\n')[0].split(': ')[1]

            # u2 init

            # subprocess.check_call("adb -s 127.0.0.1:%s shell input keyevent 3" % (portMachineGet))
            startTIme = time.time()
            while True:
                if time.time() - startTIme >= 60 * 2:
                    break
                try:
                    backHomeFlag = subprocess.check_call("memuc -i %s adb  shell input keyevent 3" % (devIndex))
                    if backHomeFlag == 0:
                        break
                    else:
                        time.sleep(3)
                except Exception as e:
                    pass
            #a = time.time()

            #print(time.time() - a)
            # 安装Xpose
            # print('%s 安装xpose：adb -s 127.0.0.1:%s install -r data/%s' % (str(name)+str(newMachineSeq), portMachineGet, xPose_name))
            try:
                subprocess.check_output('adb -s  127.0.0.1:%s install -r data/%s' % (portMachineGet, xPose_name))
            except Exception as e:
                logger.info(e)
            time.sleep(1)
            # 安装APP copyfile
            # print('%s 安装copyfile: adb -s 127.0.0.1:%s install -r data/%s' % (str(name)+str(newMachineSeq), portMachineGet, app_name))
            try:
                subprocess.check_output('adb -s  127.0.0.1:%s install -r data/%s' % (portMachineGet, app_name))
            except Exception as e:
                logger.info(e)
            time.sleep(1)

            # print(
            #     '%s 安装微信： adb -s 127.0.0.1:%s install data/%s' % (str(name) + str(newMachineSeq), portMachineGet, wx_name))
            subprocess.check_output('adb -s  127.0.0.1:%s install data/%s' % (portMachineGet, wx_name))

            # print("%s 初始化U2" % str(name)+str(newMachineSeq))
            is_install_xpose = False      #xpose 是否安装成功
            is_install_tongxulun = False  #通讯录是否安装成功
            while True:
                try:
                    subprocess.check_call('python -m uiautomator2 init  --serial 127.0.0.1:%s' % portMachineGet)
                    u2Con = u2.connect('127.0.0.1:%s' % portMachineGet)
                    if u2Con.info:
                    # if u2Con.healthcheck():
                        # 执行点击启动操作
                        wxUtil.appStart(u2Con, logger)
                        time.sleep(2)
                        u2Con.press("home")
                        time.sleep(2)
                        #激活xpose
                        wxUtil.clickOnlyByText(u2Con, u"Xposed Installer")
                        time.sleep(2)
                        #通知弹出，勾掉不再显示
                        if wxUtil.elementExistById(u2Con,"de.robv.android.xposed.installer:id/md_promptCheckbox", 1): #不再显示选项
                            wxUtil.clickById(u2Con,"de.robv.android.xposed.installer:id/md_promptCheckbox")
                        if wxUtil.elementExistById(u2Con,"de.robv.android.xposed.installer:id/md_buttonDefaultPositive", 1): # 确定按钮
                            wxUtil.clickById(u2Con,"de.robv.android.xposed.installer:id/md_buttonDefaultPositive")
                        #安装模块激活xpose
                        # print("%s 开始设置xpose" % str(name)+str(newMachineSeq))
                        time.sleep(2)
                        if wxUtil.elementExistByText(u2Con, "android:id/title", u"Version 89"):
                            wxUtil.clickByText(u2Con, "android:id/title", u"Version 89")
                            if wxUtil.elementExistByText(u2Con, "de.robv.android.xposed.installer:id/md_title", u"Install", 1):
                                wxUtil.clickByText(u2Con, "de.robv.android.xposed.installer:id/md_title", u"Install")
                                if wxUtil.elementExistById(u2Con, "de.robv.android.xposed.installer:id/cancel", 60):
                                    wxUtil.clickById(u2Con, "de.robv.android.xposed.installer:id/cancel")
                                    if wxUtil.elementExistByDesc(u2Con, u"打开导航抽屉", 1):
                                        wxUtil.clickByDesc(u2Con, u"打开导航抽屉")
                                        if wxUtil.elementExistByText(u2Con,"de.robv.android.xposed.installer:id/design_menu_item_text", u"模块", 1):
                                            wxUtil.clickByText(u2Con, "de.robv.android.xposed.installer:id/design_menu_item_text", u"模块")
                                            if wxUtil.elementExistById(u2Con, "de.robv.android.xposed.installer:id/checkbox", 1):
                                                wxUtil.clickById(u2Con, "de.robv.android.xposed.installer:id/checkbox")
                                                is_install_xpose = True
                                                # print("%s xpose安装成功" % str(name)+str(newMachineSeq))

                        if is_install_xpose:
                            # print("%s 开始安装通讯录" % str(name)+str(newMachineSeq))
                            time.sleep(1)
                            u2Con.press("home")
                            time.sleep(2)
                            if wxUtil.elementExistByDesc(u2Con, u"文件夹：内置应用"):
                                wxUtil.clickByDesc(u2Con, u"文件夹：内置应用")
                                if wxUtil.elementExistOnlyByText(u2Con, u"谷歌安装器"):
                                    wxUtil.clickOnlyByText(u2Con, u"谷歌安装器")
                                    if wxUtil.elementExistByResIdClassInstence(u2Con,
                                                                               "com.microvirt.installer:id/xy_app_select",
                                                                               "android.widget.CheckBox", 4):
                                        wxUtil.clickByClassAndNum(u2Con, "com.microvirt.installer:id/xy_app_select",
                                                                  "android.widget.CheckBox", 4)
                                        wxUtil.clickById(u2Con, "com.microvirt.installer:id/xyDoAction")
                                        wxUtil.clickById(u2Con, "com.microvirt.installer:id/xyu_update_btn")
                                        time.sleep(5)
                                        # 重启模拟器
                                        if wxUtil.elementExistById(u2Con, "com.microvirt.installer:id/xyu_update_btn", 60):
                                            wxUtil.clickById(u2Con, "com.microvirt.installer:id/xyu_update_btn")
                                            time.sleep(10)
                                            is_install_tongxulun = True
                                            # print("%s 通信录安装成功，并重启了模拟器" % str(name)+str(newMachineSeq))
                        break
                    else:
                        subprocess.check_call('python -m uiautomator2 init  --serial 127.0.0.1:%s' % portMachineGet)
                except Exception as e:
                    try:
                        subprocess.check_call('python -m uiautomator2 init  --serial 127.0.0.1:%s' % portMachineGet)
                    except Exception as e:
                        pass



            machineInfoRecordSql = """INSERT INTO wx_machine_info ( uuid, clientId, devId, devName, 
                                      devDir, devIp, devPort, status, create_time, memu_imei, memu_mac, 
                                      memu_phone, telecom, vm_manufacturer, vm_model, if_start, if_ready)
                                    VALUES('','%s','%s','%s','%s','127.0.0.1','%s',' 0 ',now(),
                                    '%s','%s','%s','%s','%s','%s',NULL,'1')""" % (
                                    devId, str(name)+str(newMachineSeq), str(name)+str(newMachineSeq),
                                    newMachine, portMachineGet, memu_imei, memu_mac, memu_phone, telecom,
                                    vm_manufacturer, vm_model)
            # print(machineInfoRecordSql)
            if is_install_tongxulun:
                # print("初始化成功，注册模拟器到系统 %s" % machineInfoRecordSql)
                mySqlUtil.execSql(machineInfoRecordSql)
            else:
                # print("%s模拟器没有完全安装成功，禁用！" % str(name)+str(newMachineSeq))
                success = False
                status = 3 #任务失败
                alarmMsg = '模拟器新建任务%d失败' % (taskSeq)
                alarm(alarmMsg)
        if success:
            build_flag.value = 1
    except Exception as e:
        status = 3 #任务失败
        logger.debug(traceback.format_exc())
        alarmMsg = '模拟器新建任务%d失败'%(taskSeq)
        alarm(alarmMsg)
    finally:
        exec_sql ="""update wx_task_manage set status = %d,endTime = now() where taskSeq = %d""" %(status,taskSeq)
        ret = mySqlUtil.execSql(exec_sql)

def machineStateCheck(logger, u2ConStart, taskItemInfo, mySqlUtil):
    # pass
    # 模拟器开启状态
    devName = taskItemInfo[6]
    taskUuid = taskItemInfo[1]
    hwnd = win32gui.FindWindow(None, devName)
    if hwnd == 0:
        logger.info("%s 模拟器未开启,进行启动" % devName)
        machineRestart(taskItemInfo)
    # adb检查
    machineInit(taskItemInfo)

    # 上下线检查
    loginOut = wxUtil.indexJudege(u2ConStart, logger)
    if loginOut:
        logger.warn("微信号已下线")
        wxLoginOutFlag = True
        wxOffLineSql = """UPDATE `wx_account_info` SET if_start = 0  where `uuid`=\'%s\'""" % (taskUuid)
    # 分辨率


def taskMachineCheck(taskList):
    try:
        subprocess.check_output("adb devices")
    except Exception as e:
        logger.warn(traceback.format_exc())
        process = subprocess.check_output("netstat -ano | findstr \"127.0.0.1:5037\"|findstr \"LISTENING\"",
                                          shell=True).decode(encoding="utf-8")
        adbUsePort = re.split(r" +", process.strip())[4]
        subprocess.check_output("taskkill /f /pid %s" % adbUsePort, shell=True)
        subprocess.check_output("adb start-server", shell=True)
    finally:
        devicesInfoCurrentList = [i.split('\t')[0] for i in
                                  subprocess.check_output("adb devices").decode(encoding="utf-8").split('\r\n')
                                  if ':' in i]
        for infoItem in taskList:
            try:
                devName = infoItem[6]
                portDev = infoItem[4]
                if "127.0.0.1:%s" %(portDev) not in devicesInfoCurrentList:
                    hwnd = win32gui.FindWindow(None, devName)
                    if hwnd != 0:
                        logger.debug("127.0.0.1:%s adb 重连" % portDev)
                        adbconnectCommand = "adb connect 127.0.0.1:%s" %(portDev)
                        subprocess.check_call(adbconnectCommand)
                else:
                    logger.debug("127.0.0.1:%s adb 正常" %portDev)
            except Exception as e:
                pass
#根据devvir来重启模拟器wifi
def restartWifi(logger, u2ConStart, taskItemInfo, mySqlUtil):
    remark="#"
    status=4
    try:
        #memuc  connect -i 25   开启
        # memuc  disconnect -i 25   关闭
        dev_num=0
        devVir=taskItemInfo[5]
        devPort=taskItemInfo[4]
        if '_' in devVir:
            dev_num=str(devVir).split("_")[1]
        comm_close="memuc  disconnect -i "+str(dev_num)
        subprocess.check_output(comm_close)
        comm_start="memuc  connect -i "+str(dev_num)
        subprocess.check_output(comm_start)
        try:
            u2ConStart=u2.connect("127.0.0.1:%s" % str(devPort))
        except:
            pass
        u2ConStart = u2.connect("127.0.0.1:%s" % str(devPort))
    except Exception as e:
        logger.debug(e)
        remark="重启模拟器WIFI失败"
        status=3
    return ((status, remark),u2ConStart)

#根据devDir来删除模拟器
# def deleteVM(logger, u2ConStart, taskItemInfo, mySqlUtil):
#     devDir = taskItemInfo[5]
#     times = 0 #次数
#     close_flag = False #关闭标识
#     remark="#"
#     status=4
#     try:
#             while times <3: #循环3次
#                 command = "memuc stop -n %s" % (devDir)
#                 subprocess.check_call(command)  # 先把模拟器关闭,后才能删除
#                 time.sleep(10)
#                 command = "memuc isvmrunning -n %s" %(devDir)
#                 output = str(subprocess.check_output(command))
#                 if 'Not' in output:
#                     close_flag = True
#                     break
#                 else:
#                     times = times + 1
#             if close_flag:
#                 command = 'memuc remove -n %s' % (devDir)
#                 result = subprocess.check_call(command)  # 删除模拟器
#                 if result == 0:
#                     try:
#                         backups_table = ('wx_machine_info', 'wx_account_info', 'wx_firend_rela')
#                         for backup_table in backups_table:  # 循环删除备份表后重建
#                             exist_sql = """select ifnull(count(1),0) as eflag from information_schema.TABLES where table_name ='%s'""" % (
#                                 backup_table)
#                             ret = mySqlUtil.getData(exist_sql)
#                             if ret[0]['eflag'] != 0:  # 判断存在备份表则删除后新建
#                                 drop_sql = """drop table %s""" % (backup_table)
#                                 mySqlUtil.getData(drop_sql)
#                             backups_sql = """create table %s select * from %s""" % ((backup_table + '_bak'), backup_table)
#                             mySqlUtil.getData(backups_sql)  # 新建备份表
#                         dsql1 = """delete from wx_machine_info where uuid in (%s)""" % (devDir)
#                         mySqlUtil.getData(dsql1)  # 删除模拟器信息
#                         dsql2 = """delete from wx_account_info where uuid in (%s)""" % (devDir)
#                         mySqlUtil.getData(dsql2)  # 删除账号信息
#                         dsql3 = """delete from wx_firend_rela where wx_id in (%s) """ % (devDir)
#                         mySqlUtil.getData(dsql3)  # 删除该账号关系表信息
#                     except Exception as e:
#                         logger.debug(e)
#                         remark = "数据删除失败"
#                         status = 3
#             else:
#                 remark = "关闭模拟器失败"
#                 status = 3
#     except Exception as e:
#         logger.debug(e)
#         remark="删除模拟器失败"
#         status=3
#     return ((status, remark),u2ConStart)
if __name__ == '__main__':
    taskMachineCheck()
    a = machineInit([1,2,3,21513,'MEmu_1','17302'])
    print(a)
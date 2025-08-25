import datetime
import emoji
import requests

from tools import taskStatusRecorder
import random
from lib.WxElementConf import WxElementConf
from tools import wxUtil,taskStatusRecorder
from lib.FinalLogger import *
import os
import traceback
from lib.ModuleConfig import ConfAnalysis

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/addFriend.log')
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
wxElementConf = WxElementConf(logger)
confAllItems = ConfAnalysis(logger, configFile)
#
loopGate = int(confAllItems.getOneOptions('addFriend', 'loopGate'))
loadContractRetry = int(confAllItems.getOneOptions('addFriend', 'loadContractRetry'))
#创建tmp目录
def mkdir(path):
    # 去除首位空格
    path = path.strip()
    # 去除尾部 \ 符号
    path = path.rstrip("\\")

    # 判断路径是否存在
    # 存在     True
    # 不存在   False
    isExists = os.path.exists(path)

    # 判断结果
    if not isExists:
        # 如果不存在则创建目录
        # 创建目录操作函数
        os.makedirs(path)
        # print(path + ' 创建成功')
        return True
    else:
        # 如果目录存在则不创建，并提示目录已存在
        # print(path + ' 目录已存在')
        return False

def action(logger, u2Con, taskItemInfo, mySqlUtil):
    '''
    好友添加脚本
    :param u2Con:
    :param taskItemInfo:
    :return:
    '''
    # 信息初始化
    remarks = '#'
    status = 3
    try:
        wxUtil.backToHome(u2Con)

        addFriendInfoSql = """SELECT  frinedIdList,sayHi  from  `wx_add_friend` A
                            where A.taskSeq = \'%s\'""" % taskItemInfo[0]
        addFriendInfo = mySqlUtil.fetchData(addFriendInfoSql)
        if addFriendInfo[0] == 1:
            if addFriendInfo[1]:
                addFriendList = [i for i in addFriendInfo[1][0][0].split('#')]
                sayHi = addFriendInfo[1][0][1]
                status = 4
            else:
                remarks = "无法获取好友列表"
                status = 3
        else:
            addFriendList = []
            sayHi = ""
            status = 3

        if status != 3:
            # 主页：点击加好友功能
            wxUtil.clickByClassAndNum(u2Con, WxElementConf.AD_Index_Action, "android.widget.ImageView", 1)
            # wxUtil.clickById(u2Con, wxElementConf.AD_Index_Action)  # 点击微信主页+号按钮 # 7.0.0版本
            wxUtil.clickByText(u2Con, wxElementConf.AD_Add_Action, "添加朋友")  # 点击添加朋友按钮
            time.sleep(0.8)

            wxUtil.clickById(u2Con, wxElementConf.AD_Set_Text)  # 输入微信号/QQ号/手机号输入框
            for FrinedInfo in addFriendList:
                wxUtil.setTextById(u2Con, wxElementConf.AD_Set_Text, FrinedInfo)  # 输入微信号
                time.sleep(0.5)
                wxUtil.clickById(u2Con, wxElementConf.AD_Friend_Find_Info)  # 输入后点击搜索按钮
                time.sleep(0.5)
                if not wxUtil.elementExistById(u2Con, wxElementConf.AD_Friend_Not_Find):
                    if wxUtil.elementExistById(u2Con, wxElementConf.AD_Friend_Exists):  # AD_Friend_Exists
                        wxUtil.clickById(u2Con, wxElementConf.AD_Text_Back)  # 当前是好友
                    elif wxUtil.elementExistById(u2Con, wxElementConf.AD_Friend_Not_Find):
                        wxUtil.clickById(u2Con, wxElementConf.AD_Text_Back)
                    else:
                        time.sleep(1)
                        wxUtil.clickById(u2Con, wxElementConf.AD_Friend_Find)
                        time.sleep(1)
                        wxUtil.setTextById(u2Con, wxElementConf.AD_Say_Hi, sayHi)  # 输入打招呼语
                        time.sleep(1)
                        wxUtil.clickById(u2Con, wxElementConf.AD_Hi_Send)
                        while True:
                            wxUtil.pressBack(u2Con)
                            if wxUtil.elementExistById(u2Con, wxElementConf.AD_Set_Text):
                                break
                time.sleep(random.randint(2, 4))
            wxUtil.backToHome(u2Con)
            status = 4
    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())
        logger.warn(e)
        status = 3
    return (status, remarks)


def OneKeyAction(logger, u2Con, taskItemInfo, mySqlUtil):
    # 信息初始化
    remarks = '#'
    try:
        wxUtil.backToHome(u2Con)
        taskSeq = taskItemInfo[0]
        addFriendInfoSql = """SELECT  frinedIdList,sayHi  from  `wx_add_friend` A
                                where A.taskSeq = \'%s\'""" % taskSeq
        addFriendInfo = mySqlUtil.fetchData(addFriendInfoSql)

        if addFriendInfo[0] == 1:
            addFriendList = [i for i in addFriendInfo[1][0][0].split('#')]
            sayHi = addFriendInfo[1][0][1]
        else:
            addFriendList = []
            sayHi = ""

        # 主页：点击加好友功能
        addFlag = 1
        wx_friend_nickname = ""
        wx_friend_id = ""
        if addFriendList:
            wxUtil.clickByClassAndNum(u2Con, WxElementConf.AD_Index_Action, "android.widget.ImageView", 1)
            # u2Con(resourceId=wxElementConf.AD_Index_Action).click_exists(timeout=10.0)  # AD_Index_Action
            # u2Con(resourceId=wxElementConf.AD_Add_Action, text=u"添加朋友").click_exists(timeout=10.0)  # AD_Add_Action
            wxUtil.clickByText(u2Con, wxElementConf.AD_Add_Action, "添加朋友")
            time.sleep(0.8)

            wxUtil.clickById(u2Con, wxElementConf.AD_Set_Text)
            # u2Con(resourceId=wxElementConf.AD_Set_Text).click_exists(timeout=10.0)
            for addFrinedInfo in addFriendList:
                wxUtil.setTextById(u2Con, wxElementConf.AD_Set_Text, addFrinedInfo)  # 输入微信号
                # u2Con(resourceId=wxElementConf.AD_Set_Text).set_text('%s' % addFrinedInfo)  # AD_Set_Text
                time.sleep(0.5)
                wxUtil.clickById(u2Con, wxElementConf.AD_Friend_Find_Info)
                # u2Con(resourceId=wxElementConf.AD_Friend_Find_Info).click_exists(timeout=10.0)  # AD_Friend_Find_Info
                time.sleep(0.5)
                if not wxUtil.elementExistById(u2Con, wxElementConf.AD_Friend_Not_Find):  # AD_Friend_Not_Find
                    if wxUtil.elementExistById(u2Con, wxElementConf.AD_Friend_Exists):
                        # 当前是好友
                        addFlag = 4  # 当前以为好友，通过“发送信息”按钮来判别
                    else:
                        time.sleep(1)
                        # 获取微信昵称
                        wxNameFind = 0
                        while wxNameFind <= 10:
                            if wxUtil.elementExistById(u2Con,wxElementConf.wx_friend_remark):
                                wx_friend_nickname = wxUtil.getTextById(u2Con,wxElementConf.wx_friend_remark)
                                if wx_friend_nickname:
                                    break
                            wxNameFind += 1
                            time.sleep(0.5)

                        # 获取微信ID
                        if wxUtil.elementExistById(u2Con,wxElementConf.wx_friend_id):
                            wx_friend_id = wxUtil.getTextById(u2Con,wxElementConf.wx_friend_id).split(":")[1]
                        # u2Con(resourceId=wxElementConf.AD_Friend_Find).click_exists(timeout=10.0)
                        wxUtil.clickById(u2Con,wxElementConf.AD_Friend_Find)
                        time.sleep(2)
                        wxUtil.setTextById(u2Con,wxElementConf.AD_Say_Hi,sayHi)
                        # u2Con(resourceId=wxElementConf.AD_Say_Hi).set_text("%s" % sayHi)
                        wxUtil.clickById(u2Con,wxElementConf.AD_Hi_Send)
                        # u2Con(resourceId=wxElementConf.AD_Hi_Send).click_exists(timeout=10.0)
                        addFlag = 1  # 发送成功
                elif wxUtil.elementExistById(u2Con,wxElementConf.AD_Frequent_Operate):
                    if wxUtil.getTextById(u2Con,wxElementConf.AD_Frequent_Operate ) == "操作过于频繁，请稍后再试":
                        addFlag = 5  # 操作过于频繁
                elif wxUtil.elementExistById(u2Con,wxElementConf.AD_Exception_Tips):
                    if wxUtil.getTextById(u2Con,wxElementConf.AD_Exception_Tips) == "	被搜帐号状态异常，无法显示":
                        addFlag = 5  # 被搜帐号状态异常，无法显示
                else:
                    addFlag = 3  # 用户不存在
            status = 4
        else:
            addFlag = 2
            status = 7
            remarks = "未能找到任务指定信息"
    except Exception as e:
        remarks = e
        logger.warn(e)
        status = 3
        addFlag = 2
    finally:
        nowTimeSrt = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        recordTaskSql = """UPDATE `OKAY_TASK_LIST`
                                SET `SEND_CODE` = \'%s\',
                                 `SEND_CODE_TIME` = \'%s\',
                                 `TARGET_WX_ID` = \'%s\',
                                 `TARGET_WX_NAME` = \'%s\',
                                 `TASK_SEQ_FLAG` = \'%s\'
                                WHERE `TASK_SEQ` = \'%s\'""" % (
            addFlag, nowTimeSrt, wx_friend_id, wx_friend_nickname, status, taskSeq)
        mySqlUtil.excSql(recordTaskSql)
    return (status, remarks)

def screenUP(u2Con):
    toX = u2Con.window_size()[0] / 2
    toY = u2Con.window_size()[1] / 2
    fromX = u2Con.window_size()[0] / 2
    fromY = toY / 2
    u2Con.swipe(fromX, fromY, toX, toY, 0.1)

def screenDown(u2Con):
    fromX = u2Con.window_size()[0] / 2
    fromY = u2Con.window_size()[1] / 2
    toX = u2Con.window_size()[0] / 2
    toY = 0
    u2Con.swipe(fromX, fromY, toX, toY, 0.1)
    time.sleep(1)

def statusRecord(taskSeq,FrinedInfo, wechat_name, addFlag, task_seq_flag, mySqlUtil):
    try:
        if wechat_name != "":
            wechat_name = wechat_name.replace("'","\'")
    except Exception as e:
        wechat_name = ""
        pass

    try:
        nowTimeSrt = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        sql = """update OKAY_TASK_LIST set SEND_CODE ='%s',SEND_CODE_TIME='%s',
            TARGET_WX_ID='',TARGET_WX_NAME='%s',TASK_SEQ_FLAG='%s'  where TASK_SEQ='%s' and EXECUTE_TYPE='2' and WX_CODE='%s'""" % (
            addFlag, nowTimeSrt, wechat_name, task_seq_flag, taskSeq, FrinedInfo)
        mySqlUtil.excSql(sql)
        return True
    except Exception:
        try:
            nowTimeSrt = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            sql = """update OKAY_TASK_LIST set SEND_CODE ='%s',SEND_CODE_TIME='%s',
                        TARGET_WX_ID='',TARGET_WX_NAME='unknow',TASK_SEQ_FLAG='%s'  where TASK_SEQ='%s' and EXECUTE_TYPE='2' and WX_CODE='%s'""" % (
                addFlag, nowTimeSrt, task_seq_flag, taskSeq, FrinedInfo)
            mySqlUtil.excSql(sql)
            return True
        except Exception:
            nowTimeSrt = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            sql = """update OKAY_TASK_LIST set SEND_CODE ='%s',SEND_CODE_TIME='%s',
                                    TARGET_WX_ID='',TASK_SEQ_FLAG='%s'  where TASK_SEQ='%s' and EXECUTE_TYPE='2' and WX_CODE='%s'""" % (
                addFlag, nowTimeSrt, task_seq_flag, taskSeq, FrinedInfo)
            mySqlUtil.excSql(sql)
            return True

def freindIdListRecoverRecord(taskSeq,FrinedInfoList,mySqlUtil):
    if FrinedInfoList:
        FrinedInfoListRecover = "#".join(FrinedInfoList)
    else:
        FrinedInfoListRecover = ""
    recoverSql = """UPDATE `wx_add_friend` 
                        SET `freindIdListRecover`=\'%s\' 
                        where `taskSeq`=\'%s\'""" % (FrinedInfoListRecover, taskSeq)
    mySqlUtil.excSql(recoverSql)

def statusRecordByBatch(taskSeq,FrinedInfoList,mySqlUtil):
    for friendInfo in FrinedInfoList:
        nowTimeSrt = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        sql = """update OKAY_TASK_LIST set SEND_CODE ='6',SEND_CODE_TIME='%s',
            TARGET_WX_ID='',TARGET_WX_NAME='',TASK_SEQ_FLAG='1'  where TASK_SEQ='%s' and EXECUTE_TYPE='2' and WX_CODE='%s'""" % (
            nowTimeSrt,  taskSeq, friendInfo)
        mySqlUtil.excSql(sql)

def addFreiendInfoGet(taskSeq, mySqlUtil):
    addFriendInfoSql = """SELECT  frinedIdList, sayHi, freindIdListRecover  from  `wx_add_friend` A
                                        where A.taskSeq = \'%s\'""" % taskSeq
    addFriendInfo = mySqlUtil.fetchData(addFriendInfoSql)
    addFriendOtherInfoSql = """SELECT WX_CODE from OKAY_TASK_LIST
                                where SEND_CODE = '6'
                                and TASK_SEQ in (
                                 SELECT distinct(TASK_SEQ) from OKAY_TASK_LIST
                                where TASK_ID in (select DISTINCT(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ=\"%s\")
                                and TASK_SEQ !=  \"%s\")
                                    """ %(taskSeq,taskSeq)
    addFriendOtherInfo = mySqlUtil.getData(addFriendOtherInfoSql)

    if addFriendInfo[0] == 1 and addFriendInfo[1]:
        addFriendList = [i for i in addFriendInfo[1][0][0].split('#')]
        if addFriendInfo[1][0][2] :
            freindIdListRecover = [i for i in addFriendInfo[1][0][2].split('#')]
        else:
            freindIdListRecover = []
        sayHi = addFriendInfo[1][0][1]
        logger.debug("获取添加列表成功")
    else:
        freindIdListRecover = []
        addFriendList = []
        sayHi = ""
        logger.info("获取添加列表失败")
    if addFriendOtherInfo:
        addFriendOtherList = []
        for itemInfo in addFriendOtherInfo:
            addFriendOtherList.extend(itemInfo[0].split('#'))
    else:
        addFriendOtherList = []
    return (addFriendList,addFriendOtherList,sayHi,freindIdListRecover)

def contactsLoad(addFriendList,u2Con):
    fileSeq = random.randint(100, 999)
    dir = '%s/data/tmp' % (BASEDIR)
    mkdir(dir)
    filePath = '%s/data/tmp/00%s.vcf' % (BASEDIR, fileSeq)
    if os.path.exists(filePath):
        os.remove(filePath)
    with open(filePath, 'w+') as f:
        for FrinedInfo in addFriendList:
            contactPerson = FrinedInfo
            contactPerson1 = contactPerson[0]
            contactPerson2 = contactPerson[1:4]
            contactPerson3 = contactPerson[4:7]
            contactPerson4 = contactPerson[7:11]
            f.write('BEGIN:VCARD\n')
            f.write('VERSION:2.1\n')
            f.write("FN:" + FrinedInfo + "\n")   #联系人姓名为手机号码
            f.write('TEL;CELL:%s-%s-%s-%s\n' % (contactPerson1, contactPerson2, contactPerson3, contactPerson4))  #组装联系人的电话
            f.write('END:VCARD\n')
    # 组装完成通讯录

    # 通讯录导入
    u2Con.shell('pm clear com.android.providers.contacts')
    u2Con.shell('rm /storage/emulated/legacy/*.vcf')    #把文件清空
    #
    # try:
    #     u2Con.press('home')
    #     u2Con(text=u"微信").click_exists(timeout=10.0)
    #     wxUtil.backToHome(u2Con)
    #     # 主页：点击加好友功能
    #     wxUtil.clickById(u2Con, wxElementConf.AD_Index_Action)  # 点击微信主页+号按钮
    #
    #     wxUtil.clickByText(u2Con, wxElementConf.AD_Add_Action, "添加朋友")  # 点击添加朋友按钮
    #     time.sleep(0.5)
    #     wxUtil.clickByText(u2Con, wxElementConf.AD_Mail_List, "手机联系人")  # 点击手机联系人
    #     time.sleep(1)
    #     u2Con.press("back")
    #     time.sleep(1)
    #     wxUtil.clickByText(u2Con, wxElementConf.AD_Mail_List, "手机联系人")  # 点击手机联系人
    # except Exception:
    #     pass

    u2Con.push(filePath, '/storage/emulated/legacy/')   #导入联系人文件
    time.sleep(2)
    loding = 'am start -t "text/x-vcard" -d "file:/storage/emulated/legacy/00%s.vcf" -a android.intent.action.VIEW com.android.contacts'%(fileSeq)
    u2Con.shell(loding)
    time.sleep(4)
    return filePath

def stepToFreindList(u2Con):
    while True:
        #if u2Con(resourceId="com.tencent.mm:id/bc3").exists(timeout=3): # 联系号码
        if wxUtil.elementExistById(u2Con, wxElementConf.AD_Exist_Name):
            break
        elif wxUtil.elementExistById(u2Con,wxElementConf.home_page_wx):
            wxUtil.clickByClassAndNum(u2Con, WxElementConf.AD_Index_Action, "android.widget.ImageView", 1)  # 点击微信主页+号按钮
            wxUtil.clickByText(u2Con, wxElementConf.AD_Add_Action, "添加朋友")  # 点击添加朋友按钮
            time.sleep(0.5)
            wxUtil.clickByText(u2Con, wxElementConf.AD_Mail_List, "手机联系人")  # 点击手机联系人
        else:
            u2Con.press("back")
        time.sleep(2)
        # if u2Con(resourceId="android:id/title", text=u"手机联系人").exists(timeout=3):
        #     u2Con(resourceId="android:id/title", text=u"手机联系人").click_exists(timeout=10.0)
        # elif u2Con(resourceId="com.tencent.mm:id/gd").exists(timeout=3):
        #     u2Con(resourceId="com.tencent.mm:id/gd").click_exists(timeout=10.0)
        #     u2Con(resourceId="com.tencent.mm:id/ge", text=u"添加朋友").click_exists(timeout=10.0)

def otherSpecialTaskAction(logger, u2Con, taskItemInfo,mySqlUtil):
    pass

def taskInfoRemarkUpdate(mySqlUtil, taskSeq, remarkType):
    if remarkType == 1:
        updateSql = """UPDATE OKAY_TASK_INFO
                        set remark = %s
                        where task_id = (SELECT DISTINCT(task_id) from OKAY_TASK_LIST where TASK_SEQ = "%s")"""%(remarkType,taskSeq)
    else:
        updateSql = """UPDATE OKAY_TASK_INFO
                        set remark = %s, EXEC_TIME = %s
                        where task_id = (
                        SELECT DISTINCT(TASK_ID) from OKAY_TASK_LIST
                            where TASK_SEQ = "%s"
                            UNION 
                            SELECT DISTINCT(TASK_ID) from OKAY_TASK_LIST
                            where TASK_SEQ = (SELECT taskSeq from wx_add_friend where subTaskSeq = "%s")
                        )""" % (
                        remarkType, time.strftime('%Y%m%d%H%M%S', time.localtime(time.time())),taskSeq,taskSeq)
    mySqlUtil.excSql(updateSql)

def allTaskRefresh(taskSeq, mySqlUtil, actType):
    delaySql = ""
    if actType == 1:
        # 通讯录延迟 1 小时
        taskSeqFindSql = """  select distinct(TASK_SEQ) from OKAY_TASK_LIST
                        where TASK_ID = (select DISTINCT(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ = \'%s\')"""%(taskSeq)

        taskSeqFind = mySqlUtil.getData(taskSeqFindSql)
        if taskSeqFind:
            taskSeqCondi = ""
            for item in taskSeqFind:
                taskSeqCondi += " \"%s\"," % (item[0])

            delaySql = """update wx_task_manage
                            set cronTime = DATE_ADD( now(), INTERVAL 1 HOUR ),ifKill = 0, heartBeatTime=  DATE_ADD( now(), INTERVAL 1 HOUR )
                            where taskSeq in (
                            %s)
                            and status = 1
                            and taskSeq != \'%s\'"""%(taskSeqCondi[:-1],taskSeq)

    elif actType == 2:
        # 调度剩下批次任务进行执行，延迟 5 分钟，heartBeatTime 加一小时，防止误杀
        taskSeqFindSql = """ select distinct(TASK_SEQ) from OKAY_TASK_LIST A
                        JOIN wx_task_manage B on A.TASK_SEQ=B.taskSeq
                        where A.TASK_ID = (select DISTINCT(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ = '%s')
                        and A.TASK_SEQ_FLAG != '2'
                        and B.`status` = 1
                        UNION ALL
                        SELECT subTaskSeq from wx_add_friend A
                        JOIN wx_task_manage B on A.subTaskSeq=B.taskSeq
                        where A.taskSeq in (
                        SELECT DISTINCT(TASK_SEQ) from OKAY_TASK_LIST where TASK_ID=(SELECT DISTINCT(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ="%s")
                        )and B.`status` = 1""" % (taskSeq, taskSeq)

        taskSeqFind = mySqlUtil.getData(taskSeqFindSql)

        if taskSeqFind:
            taskSeqCondi = ""
            for item in taskSeqFind:
                taskSeqCondi += " \"%s\"," % (item[0])

            delaySql = """update wx_task_manage
                            set cronTime = DATE_ADD( now(), INTERVAL 5 MINUTE ),ifKill = 0, heartBeatTime=  DATE_ADD( now(), INTERVAL 1 HOUR )
                            where taskSeq in ( %s
                            ) 
                            and status = 1
                            and taskSeq != \'%s\'""" % (taskSeqCondi[:-1], taskSeq)
    elif actType == 3:
        # 搜索延迟
        taskSeqFindSql = """ SELECT
                                    subTaskSeq
                                FROM
                                    wx_add_friend
                                WHERE
                                    taskSeq IN (
                                        SELECT DISTINCT
                                            (TASK_SEQ)
                                        FROM
                                            OKAY_TASK_LIST
                                        WHERE
                                            TASK_ID = (
                                                SELECT DISTINCT
                                                    (TASK_ID)
                                                FROM
                                                    OKAY_TASK_LIST
                                                WHERE
                                                    TASK_SEQ = "%s"
                                            )
                                    )""" % (taskSeq)

        taskSeqFind = mySqlUtil.getData(taskSeqFindSql)
        if taskSeqFind:
            taskSeqCondi = ""
            for item in taskSeqFind:
                taskSeqCondi += " \"%s\"," % (item[0])

            delaySql = """ update wx_task_manage
                            set cronTime = DATE_ADD( now(), INTERVAL 1 HOUR ),ifKill = 0, heartBeatTime=  DATE_ADD( now(), INTERVAL 1 HOUR )
                            where taskSeq in (
                            %s
                            )
                            and  status = 1
                            and taskSeq != \"%s\" """%(taskSeqCondi[:-1], taskSeq)

    if delaySql:
        mySqlUtil.excSql(delaySql)

def taskInterruptAction(taskSeq, mySqlUtil):
    returnStatus = False
    taskStatusCheckSql = """select TASK_STATE from OKAY_TASK_INFO
                                where TASK_ID = (select DISTINCT(TASK_ID) from OKAY_TASK_LIST 
                                where TASK_SEQ = \'%s\' limit 1)""" % (taskSeq)

    taskStatus = int(mySqlUtil.getData(taskStatusCheckSql)[0][0])
    if taskStatus in (2,3):
        # 暂停
        returnStatus = True
    return returnStatus


def taskAdditionalDispatch_DEP(taskSeq, uuid, mySqlUtil):
    # 子任务的个数
    subtaskNumSql = """SELECT count(distinct(TASK_SEQ)) from OKAY_TASK_LIST
                            where TASK_ID = (select distinct(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ=\'%s\')""" % (
        taskSeq)
    # 完成的子任务个数
    comSubtaskNumSql = """select count(1) from wx_task_manage
                            where STATUS = 4
                            and taskSeq in (SELECT distinct(TASK_SEQ) from OKAY_TASK_LIST
                            where TASK_ID = (select distinct(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ=\'%s\'))""" % (
        taskSeq)

    subtaskNum = mySqlUtil.getData(subtaskNumSql)[0][0]
    comSubtaskNum = mySqlUtil.getData(comSubtaskNumSql)[0][0]

    allTaskComFlag = True
    if subtaskNum - comSubtaskNum == 1 or comSubtaskNum == subtaskNum:
        # 全部通讯录任务完成,查验是否需要搜索加好友

        # 剩下未执行数
        additionalSearchNumSql = """SELECT taskSeq,freindIdListRecover from wx_add_friend
                                        where freindIdListRecover is not null 
                                        and taskSeq in (SELECT distinct(TASK_SEQ) from OKAY_TASK_LIST
                                        where TASK_ID = (select distinct(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ=\'%s\'))""" % (
            taskSeq)
        additionalSearchList = mySqlUtil.getData(additionalSearchNumSql)
        if additionalSearchList:
            for item in additionalSearchList:  # 因是迭代的执行32任务检查insert，会存在部分任务空跑
                taskSeqItem = item[0]
                friendList = item[1]
                if friendList:
                    allTaskComFlag = False
                    taskStatusRecorder.taskInfoInsert(uuidMachine=uuid, actionType='32', priority='20', mysqlUtil=mySqlUtil, taskSeq=taskSeqItem)
    else:
        allTaskComFlag = False
        # 调度剩下批次任务进行执行
        allTaskRefresh(taskSeq, mySqlUtil, 2)

    if allTaskComFlag:
        taskStatus = 4
    else:
        taskStatus = 1

    alltaskStatusSql = """UPDATE `OKAY_TASK_INFO`
                            SET `TASK_STATE` = \'%s\'
                            WHERE `TASK_ID` = (select DISTINCT(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ = \'%s\') 
                            """ %(taskStatus,taskSeq)
    mySqlUtil.excSql(alltaskStatusSql)

def toastStatus(u2Con,logger):
    '''

    :param u2Con:
    :return: retStatus    0: 未获取；1 - 已发送； 2 - 频繁
    '''
    startTime = time.time()
    retStatus = 0
    while True:
        if time.time() - startTime >= 60:
            logger.warn("获取toast失败")
            break
        # [Args]
        # 5.0: max wait timeout. Default 10.0
        # 10.0: cache time. return cache toast if already toast already show up in recent 10 seconds. Default 10.0 (Maybe change in the furture)
        # "default message": return if no toast finally get. Default None
        toastMsg = u2Con.toast.get_message(10.0, 30.0, "notFind")
        if toastMsg != "notFind":
            logger.debug("toast:%s"%(toastMsg))
            if toastMsg == "已发送":
                retStatus = 1 # 已发送
            elif toastMsg == "你回复太快了，请休息一下稍后再试":
                retStatus = 2  # 频繁
            else:
                alarmMsg = "加好友发现新toast : %s" %(toastMsg)
                alarm(alarmMsg)
            u2Con.toast.reset()
            break

    return retStatus

def alarm(alarmMsg):
    userListAlert = "yinlw"
    weixinAlarmRequest = """http://124.172.189.98/wechat/send_err_msg/?msg=%s&type=21&user=%s&creator=edent&jobid=123""" % (
        alarmMsg, userListAlert)
    req = requests.get(weixinAlarmRequest)

def taskAdditionalDispatch(taskSeq, uuid, mySqlUtil, type=0):
    '''

    :param taskSeq:
    :param uuid:
    :param mySqlUtil:
    :param type:  0->正常。1-> 延迟。
    :return:
    '''
    taskStatusSql = """SELECT SUM(
                            case when TASK_SEQ_FLAG = '2' THEN 0
                            ELSE 1
                            END)
                            from OKAY_TASK_LIST 
                            where TASK_ID=(SELECT DISTINCT(TASK_ID) from OKAY_TASK_LIST
                            where TASK_SEQ = "%s")"""%(taskSeq)
    taskStatus = mySqlUtil.getData(taskStatusSql)[0][0]
    if taskStatus == 0:
        # 全部 okay_task_list 任务完成
        clearTaskSeqSql = """SELECT
                                    taskSeq
                                FROM
                                    wx_task_manage
                                WHERE
                                    taskSeq IN (
                                        SELECT
                                            TASK_SEQ
                                        FROM
                                            OKAY_TASK_LIST
                                        WHERE
                                            TASK_ID = (
                                                SELECT DISTINCT
                                                    (TASK_ID)
                                                FROM
                                                    OKAY_TASK_LIST
                                                WHERE
                                                    TASK_SEQ = "%s"
                                            )
                                    )
                                AND STATUS IN (1, 2, 3)
                                UNION ALL
                                    SELECT
                                        taskSeq
                                    FROM
                                        wx_task_manage
                                    WHERE
                                        taskSeq IN (
                                            SELECT
                                                subTaskSeq
                                            FROM
                                                wx_add_friend
                                            WHERE
                                                taskSeq IN (
                                                    SELECT
                                                        TASK_SEQ
                                                    FROM
                                                        OKAY_TASK_LIST
                                                    WHERE
                                                        TASK_ID = (
                                                            SELECT DISTINCT
                                                                (TASK_ID)
                                                            FROM
                                                                OKAY_TASK_LIST
                                                            WHERE
                                                                TASK_SEQ = "%s"
                                                        )
                                                )
                                            AND freindIdListRecover != ""
                                        )
                                    AND STATUS IN (1, 2, 3)""" %(taskSeq, taskSeq)
        clearTaskSeqList = mySqlUtil.getData(clearTaskSeqSql)
        if clearTaskSeqList:
            clearTaskSeqSql = """update wx_task_manage
                                set STATUS = 4
                                where 1=1 """
            taskList = ""
            for info in clearTaskSeqList:
                taskList += "'%s',"%(info[0])
            clearTaskSeqSql += "and taskSeq in (%s)" %(taskList[:-1])
            mySqlUtil.excSql(clearTaskSeqSql)

        alltaskStatusSql = """UPDATE `OKAY_TASK_INFO`
                                    SET `TASK_STATE` = 4
                                    WHERE `TASK_ID` = (select DISTINCT(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ = \'%s\') 
                                    """ % (taskSeq)
        mySqlUtil.excSql(alltaskStatusSql)

        # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
        taskInfoRemarkUpdate(mySqlUtil, taskSeq, 4)
    else:
        # 全部 okay_task_list 任务 未 完成

        # 查找freindIdListRecover 为空（即全部处理）的数量
        finishCountSql = """SELECT count(1) from wx_add_friend
                            where taskSeq in 
                            (
                            SELECT distinct(TASK_SEQ) FROM OKAY_TASK_LIST where task_id = (SELECT DISTINCT(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ="%s")
                            )
                            and freindIdListRecover = "" """%(taskSeq)
        finishCount = mySqlUtil.getData(finishCountSql)[0][0]

        # 需完成的全部数量
        taskCountSql = """SELECT count(distinct(TASK_SEQ)) FROM OKAY_TASK_LIST where task_id = (SELECT DISTINCT(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ="%s")
                           """ % (taskSeq)
        taskCount = mySqlUtil.getData(taskCountSql)[0][0]

        if finishCount == taskCount:
            # 则证明有部分 okay_task_list 任务存在异常，需补跑
            errTaskSeq = """SELECT TASK_SEQ, WX_CODE from OKAY_TASK_LIST
                                where TASK_ID=(SELECT DISTINCT(TASK_ID) from OKAY_TASK_LIST where TASK_SEQ="%s")
                                and TASK_SEQ_FLAG != 2"""%(taskSeq)
            errTask = mySqlUtil.getData(errTaskSeq)
            errTaskDict = {}
            for errItem in errTask:
                taskSeqItem = errItem[0]
                wxPhone = errItem[1]
                if taskSeqItem not in errTaskDict.keys():
                    errTaskDict[taskSeqItem] = []
                errTaskDict[taskSeqItem].append(wxPhone)
            errFixSql = """update wx_add_friend 
                            set freindIdListRecover = case %s
                            END"""
            caseWhenSql = ""
            for errItemKeys in errTaskDict.keys():
                caseWhenSql += "when taskSeq = '%s' then '%s'" %(errItemKeys, '#'.join(errTaskDict[errItemKeys]))
            errFixSqlMod =  errFixSql %(caseWhenSql)
            mySqlUtil.excSql(errFixSqlMod)

            for taskSeqItem in errTaskDict.keys():
                taskStatusRecorder.taskInfoInsert(uuidMachine=uuid, actionType='32', priority='20', mysqlUtil=mySqlUtil,
                                                  taskSeq=taskSeqItem)
        else:
            # 对当前任务进行调度处理
            subTaskExistSql = """SELECT freindIdListRecover from wx_add_friend
                                            where taskSeq = "%s" """ % (taskSeq)
            subTaskExist = mySqlUtil.getData(subTaskExistSql)[0][0]
            if subTaskExist:
                # 如果freindIdListRecover 存在，则调度补充搜索
                taskStatusRecorder.taskInfoInsert(uuidMachine=uuid, actionType='32', priority='20', mysqlUtil=mySqlUtil,
                                                  taskSeq=taskSeq)

        # 对所有待执行任务进行延后5分钟处理
        if type == 0:
            allTaskRefresh(taskSeq, mySqlUtil, 2)

def backToSearchPage(u2Con):
    while True:
        if wxUtil.elementExistById(u2Con, wxElementConf.AD_Set_Text):
            wxUtil.clickById(u2Con, wxElementConf.AD_Set_Text)  # 搜索框
            time.sleep(1)
            break
        elif wxUtil.elementExistByResIdClassInstence(u2Con,WxElementConf.AD_Index_Action,"android.widget.ImageView",1 )\
                and wxUtil.elementExistById(u2Con,WxElementConf.wo):
            wxUtil.clickByClassAndNum(u2Con, WxElementConf.AD_Index_Action, "android.widget.ImageView", 1)  # 主页 + 号功能页
            wxUtil.clickByText(u2Con, wxElementConf.AD_Add_Action, "添加朋友")
            time.sleep(0.8)
            wxUtil.clickById(u2Con, wxElementConf.AD_Set_Text)  # 搜索框
        else:
            u2Con.press("back")

def addFriendConPlus(logger, u2Con, taskItemInfo,mySqlUtil):
    # 信息初始化
    remarks = '#'
    taskSeq = taskItemInfo[0]
    uuidTask = taskItemInfo[1]
    taskType = taskItemInfo[2]
    devName = taskItemInfo[6]
    operViewName = taskItemInfo[7]
    try:
        wxUtil.backToHome(u2Con)

        addFriendInfoSql = """SELECT  frinedIdList,sayHi,freindIdListRecover,taskSeq  from  `wx_add_friend` A
                                    where A.subTaskSeq = \'%s\'""" % taskSeq
        addFriendInfo = mySqlUtil.fetchData(addFriendInfoSql)

        # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
        taskInfoRemarkUpdate(mySqlUtil, taskSeq, 1)

        if addFriendInfo[0] == 1 and addFriendInfo[1]:
            addFriendList = [i for i in addFriendInfo[1][0][0].split('#')]
            sayHi = addFriendInfo[1][0][1]
            freindIdListRecover = addFriendInfo[1][0][2]
            mainTaskSeq = addFriendInfo[1][0][3]
            if freindIdListRecover:
                freindIdListRecover = [i for i in freindIdListRecover.split('#')]
            else:
                freindIdListRecover = []
        else:
            addFriendList = []
            freindIdListRecover = []
            sayHi = ""
            mainTaskSeq = ""

        # 主页：点击加好友功能

        freindIdListRecoverCopy = freindIdListRecover.copy()
        wxName = ""
        tooFrequency = False
        if freindIdListRecover:

            wxUtil.clickByClassAndNum(u2Con, WxElementConf.AD_Index_Action, "android.widget.ImageView", 1) # 主页 + 号功能页
            # u2Con(resourceId=wxElementConf.AD_Index_Action).click_exists(timeout=10.0)  # AD_Index_Action
            # u2Con(resourceId=wxElementConf.AD_Add_Action, text=u"添加朋友").click_exists(timeout=10.0)  # AD_Add_Action
            wxUtil.clickByText(u2Con, wxElementConf.AD_Add_Action, "添加朋友")
            time.sleep(0.8)
            wxUtil.clickById(u2Con, wxElementConf.AD_Set_Text)  # 搜索框
            # u2Con(resourceId=wxElementConf.AD_Set_Text).click_exists(timeout=10.0)
            for addFrinedInfo in freindIdListRecover:
                addFlag = 0  # 1 成功 2 失败 3 用户不存在 4 已经是好友 5 异常（操作频繁）6 等待执行 7 被搜帐号状态异常
                taskSeqFlag = 0  # 0-未发送;1-已发送;2-已完成;3-失败
                wxName = ""
                if tooFrequency:
                    break # 频繁提醒，退出
                wxUtil.clearTextById(u2Con, wxElementConf.AD_Set_Text)
                time.sleep(0.5)
                wxUtil.setTextById(u2Con, wxElementConf.AD_Set_Text, addFrinedInfo)  # 输入微信号
                # u2Con(resourceId=wxElementConf.AD_Set_Text).set_text('%s' % addFrinedInfo)  # AD_Set_Text
                time.sleep(1)
                wxUtil.clickById(u2Con, wxElementConf.AD_Friend_Find_Info)
                # u2Con(resourceId=wxElementConf.AD_Friend_Find_Info).click_exists(timeout=10.0)  # AD_Friend_Find_Info
                actRun = True
                while actRun:
                    time.sleep(1)
                    try:
                        if not wxUtil.elementExistById(u2Con, wxElementConf.AD_Friend_Not_Find):  # AD_Friend_Not_Find

                            # 7.0 获取好友微信昵称
                            wxName = ""
                            wxUtil.clickById(u2Con, wxElementConf.AD_Mail_List)
                            time.sleep(0.5)
                            try:
                                if wxUtil.elementExistById(u2Con, wxElementConf.set_friend_remark, 3):
                                    wxName = wxUtil.getTextById(u2Con, wxElementConf.set_friend_remark)
                                    wxName = emoji.emojize(wxName)
                                else:
                                    wxName = wxUtil.getTextById(u2Con, wxElementConf.set_friend_remark_other)
                                    wxName = emoji.emojize(wxName)
                            except Exception as e:
                                pass

                            while True:
                                wxUtil.clickById(u2Con, wxElementConf.AD_Back)
                                if wxUtil.elementExistById(u2Con, wxElementConf.AD_Wechat_Name):
                                    break
                                if wxUtil.elementExistById(u2Con, wxElementConf.AD_Friend_Find_Info):
                                    wxUtil.clickById(u2Con, wxElementConf.AD_Friend_Find_Info)

                            if wxUtil.elementExistByText(u2Con, wxElementConf.AD_Friend_Exists,"发消息"):
                                # 当前是好友
                                addFlag = 4  # 当前已经好友，通过“发送信息”按钮来判别
                                taskSeqFlag = 2
                                actRun = False
                            else:
                                # 获取微信昵称
                                # 无法获取微信昵称
                                # wxNameFind = 0
                                # while wxNameFind <= 10:
                                #     if wxUtil.elementExistById(u2Con, wxElementConf.wx_friend_remark):
                                #         wx_friend_nickname = wxUtil.getTextById(u2Con, wxElementConf.wx_friend_remark)
                                #         if wx_friend_nickname != "" and wx_friend_nickname:
                                #             break
                                #     wxNameFind += 1
                                #     time.sleep(0.5)

                                # 获取微信ID
                                # if wxUtil.elementExistById(u2Con, wxElementConf.wx_friend_id):
                                #     wx_friend_id = wxUtil.getTextById(u2Con, wxElementConf.wx_friend_id).split(":")[1]
                                # u2Con(resourceId=wxElementConf.AD_Friend_Find).click_exists(timeout=10.0)
                                wxUtil.clickById(u2Con, wxElementConf.AD_Friend_Find)

                                # 增加对点添加到通讯录后，立马变成好友的情况
                                startTimr = time.time()
                                loadFlag = 0
                                while True:
                                    # 防止黑屏报错
                                    # if u2Con(resourceId="com.tencent.mm:id/hg").exists(timeout=3): # 发送键
                                    if wxUtil.elementExistById(u2Con, wxElementConf.AD_Hi_Send, 3):
                                        loadFlag = 1
                                        break  # 好友添加界面
                                    # if u2Con(resourceId="com.tencent.mm:id/ap1").exists(timeout=3): # 发送信息键
                                    if wxUtil.elementExistByText(u2Con, wxElementConf.AD_To_Mail_List, "发消息"):  # 发送信息键
                                        loadFlag = 2
                                        break  # 好友无需验证
                                    if time.time() - startTimr >= 10:  # 10秒内黑屏回退，重试
                                        # u2Con.press("back")
                                        stepToFreindList(u2Con)
                                        break  # 黑屏导致好友未刷出

                                if loadFlag == 2:
                                    addFlag = 1  # 发送成功
                                    taskSeqFlag = 2  # 已完成
                                    actRun = False
                                elif loadFlag == 1:
                                    wxUtil.setTextById(u2Con, wxElementConf.AD_Say_Hi, sayHi)
                                    # u2Con(resourceId=wxElementConf.AD_Say_Hi).set_text("%s" % sayHi)
                                    wxUtil.clickById(u2Con, wxElementConf.AD_Hi_Send)
                                    sendStatus = toastStatus(u2Con,logger)
                                    # sendStatus : 0  -> 跳过
                                    # sendStatus : 1  -> 已发送
                                    # sendStatus : 2  -> 频繁
                                    if sendStatus == 2:
                                    # if wxUtil.elementExistById(u2Con, wxElementConf.AD_Hi_Send):
                                        addFlag = 5  # 频繁
                                        taskSeqFlag = 1  # 已完成
                                        actRun = False
                                        tooFrequency = True
                                    elif sendStatus == 1:
                                    # u2Con(resourceId=wxElementConf.AD_Hi_Send).click_exists(timeout=10.0)
                                        addFlag = 1  # 发送成功
                                        taskSeqFlag = 2 # 已完成
                                        actRun = False
                                    else:
                                        addFlag = 7 # 跳过
                                        taskSeqFlag = 1  # 等待执行
                                        actRun = False
                        elif wxUtil.elementExistById(u2Con, wxElementConf.AD_Frequent_Operate):
                            if wxUtil.getTextById(u2Con, wxElementConf.AD_Frequent_Operate) == "操作过于频繁，请稍后再试":
                                addFlag = 5  # 操作过于频繁
                                tooFrequency = True
                                taskSeqFlag = 1  # 失败
                                actRun = False
                            elif wxUtil.getTextById(u2Con, wxElementConf.AD_Frequent_Operate) == "该用户不存在":
                                taskSeqFlag = 2
                                addFlag = 3  # 用户不存在
                                actRun = False
                            elif "被搜帐号状态异常" in wxUtil.getTextById(u2Con, wxElementConf.AD_Frequent_Operate):
                                taskSeqFlag = 2
                                addFlag = 7  # 用户不存在
                                actRun = False
                        elif wxUtil.elementExistById(u2Con, wxElementConf.AD_Exception_Tips): # 新增判断
                            if "被搜帐号状态异常" in wxUtil.getTextById(u2Con, wxElementConf.AD_Exception_Tips):
                                addFlag = 7  # 被搜帐号状态异常，无法显示
                                taskSeqFlag = 2  # 完成
                                actRun = False
                            else:
                                taskSeqFlag = 2
                                addFlag = 3  # 用户不存在
                                actRun = False
                        else:
                            taskSeqFlag = 2
                            addFlag = 3  # 用户不存在
                            actRun = False

                        # 返回搜索页
                        backToSearchPage(u2Con)

                    except Exception as e:
                        logger.warn(traceback.format_exc())
                    finally:
                        if not tooFrequency:
                            if addFlag != 0  and taskSeqFlag != 0:
                                if addFrinedInfo in freindIdListRecoverCopy:
                                    freindIdListRecoverCopy.remove(addFrinedInfo)
                                freindIdListRecoverRecord(mainTaskSeq, freindIdListRecoverCopy, mySqlUtil)
                                statusRecord(mainTaskSeq, addFrinedInfo, wxName, addFlag, taskSeqFlag, mySqlUtil)
                        else:
                            allTaskRefresh(taskSeq, mySqlUtil, 3)
                            break

            if tooFrequency:
                status = 3
                remarks = "#1#搜索频繁，延迟1小时执行"
            else:
                status = 4
        else:
            status = 7
            logger.info(
                "%s | %s | %s | %s | 未能找到任务指定信息" % (
                    operViewName, taskSeq, devName, taskType))
            # remarks = "未能找到任务指定信息"
    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())
        status = 3
    finally:
        if tooFrequency:
            # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
            taskInfoRemarkUpdate(mySqlUtil, taskSeq, 3)
        else:
            # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
            taskInfoRemarkUpdate(mySqlUtil, taskSeq, 2)

        if mainTaskSeq and not tooFrequency:
            taskAdditionalDispatch(mainTaskSeq, uuidTask, mySqlUtil)
    return (status, remarks)

def addFriendByContact(logger, u2Con, taskItemInfo,mySqlUtil):
    remarks = '#'
    taskSeq = taskItemInfo[0]
    uuidTask = taskItemInfo[1]
    taskType = taskItemInfo[2]
    devName = taskItemInfo[6]
    operViewName = taskItemInfo[7]

    filePath = ''#通讯录文件地址
    tooMuckClickFlag = False
    clickLoadFlag = False # 转载通讯录次数超过
    appInstallFlag = False # 通讯录安装
    firstClickLoadFlag = False # 首次执行
    # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
    taskInfoRemarkUpdate(mySqlUtil, taskSeq, 1)

    try:
        taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新

        # 查看通讯录，必须安装正确

        ContactsAppInstallFlag = u2Con.shell("ls /data/app|grep Contacts|wc -l")
        if ContactsAppInstallFlag[1] == 0:
            if '1' in ContactsAppInstallFlag[0]:
                appInstallFlag = True
        if not appInstallFlag:
            logger.info("%s | %s | %s | %s | 未安装通讯录" % (operViewName, taskSeq, devName, taskType))
            # logger.warn("未安装通讯录")
            remarks = '未安装通讯录'
            status = 3
            return (status, remarks)  # 直接返回

        # #获取号码组装通讯录
        addFriendList, addFriendOtherList, sayHi, freindIdListRecover = addFreiendInfoGet(taskSeq, mySqlUtil)
        freindIdListRecoverCopy = freindIdListRecover.copy()
        # 通讯录导入
        if freindIdListRecover:
            filePath = contactsLoad(freindIdListRecover,u2Con)

            taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新

            # 微信加好友
            u2Con.press('home')
            u2Con(text=u"微信").click_exists(timeout=10.0)
            wxUtil.backToHome(u2Con)
            # 主页：点击加好友功能
            wxUtil.clickByClassAndNum(u2Con, WxElementConf.AD_Index_Action, "android.widget.ImageView", 1)  # 点击微信主页+号按钮
            wxUtil.clickByText(u2Con, wxElementConf.AD_Add_Action, "添加朋友")  # 点击添加朋友按钮
            time.sleep(1)
            reload = False #通讯录是否重载成功
            clicks = 1 #点击手机联系人次数
            past_phone = '' #记录上次第一位电话号码
            now_phone= '' #记录这次执行第一位的电话
            wxUtil.clickByText(u2Con, wxElementConf.AD_Mail_List, "手机联系人")  # 点击手机联系人
            time.sleep(2)
            if wxUtil.elementExistByText(u2Con, wxElementConf.AD_Bind_Phone, "绑定手机号"):
                remarks = "请绑定手机号再执行通讯录加好友"
                status = 3
            else:
                if wxUtil.elementExistByText(u2Con, wxElementConf.AD_Upload_Mail_List, "上传通讯录"):
                    wxUtil.clickByText(u2Con, wxElementConf.AD_Upload_Mail_List, "上传通讯录")
                    time.sleep(1)
                    wxUtil.clickByText(u2Con, wxElementConf.AD_Sure_Mail_list, '是')
                    time.sleep(2)
                    wxUtil.clickByText(u2Con, wxElementConf.AD_Upload_Mail_List, '查看手机通讯录')
                    time.sleep(2)
                    wxUtil.clickById(u2Con, wxElementConf.AD_Back)  # 点击返回
                if wxUtil.elementExistById(u2Con, wxElementConf.AD_Exist_Name):
                    past_phone = wxUtil.getTextById(u2Con, wxElementConf.AD_Exist_Name)
                    wxUtil.clickById(u2Con, wxElementConf.AD_Back)  # 点击返回
                if wxUtil.elementExistByText(u2Con, wxElementConf.AD_No_Mail_List, "暂无手机联系人", 2):
                    reload = True
                    wxUtil.clickById(u2Con, wxElementConf.AD_Back)  # 点击返回

                # 确认通讯录被更新
                clicksTimes = loadContractRetry
                findNewContract = False # 是否找到新通讯里
                while True:
                    try:
                        taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新

                        if findNewContract:
                            break

                        wxUtil.clickByText(u2Con, wxElementConf.AD_Mail_List, "手机联系人")  # 点击手机联系人
                        time.sleep(0.5)
                        if u2Con(resourceId="com.tencent.mm:id/xx").exists(timeout=3):
                            # 通讯录加载中
                            loadStartTime = time.time()
                            while True:
                                if not u2Con(resourceId="com.tencent.mm:id/xx").exists(timeout=3):  # "通讯录加载中"
                                    break
                                else:
                                    time.sleep(1)
                                breakFlag = False
                                if time.time() - loadStartTime >= 60:
                                    # 防止加载卡主
                                    logger.info(
                                        "%s | %s | %s | %s | 通讯录加载时间超过60秒，重试" % (operViewName, taskSeq, devName, taskType))
                                    # logger.info("通讯录加载时间超过60秒，重试")
                                    u2Con.press('back')
                                    wxUtil.clickById(u2Con, wxElementConf.AD_Back)  # 点击返回
                                    break
                                # if breakFlag:
                                #     continue

                        if clicks >= clicksTimes:
                            ## 20190321新增逻辑，第一次调度通讯录未加载，直接进行搜索补充
                            firstRunTimeSql = """ SELECT EXEC_TIME from OKAY_TASK_INFO 
                                                where TASK_ID = (SELECT DISTINCT(TASK_ID) 
                                                from OKAY_TASK_LIST where TASK_SEQ="%s") """ %(taskSeq)
                            firstRunTime = mySqlUtil.getData(firstRunTimeSql)
                            if not firstRunTime[0][0]:
                                firstClickLoadFlag = True
                                logger.info(
                                    "%s | %s | %s | %s | 首次执行,无法转载通讯录,调用搜索补充" % (operViewName, taskSeq, devName, taskType))

                                # logger.debug("首次执行,无法转载通讯录,调用搜索补充")
                                # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
                                taskInfoRemarkUpdate(mySqlUtil, taskSeq, 2)
                                status = 4
                                remarks = "首次无法加载通讯里,调用搜索补充"

                                # 启动搜索添加
                                taskStatusRecorder.taskInfoInsert(uuidMachine=uuidTask, actionType='32', priority='9',
                                                                  mysqlUtil=mySqlUtil,cronTime = "now()",
                                                                  taskSeq=taskSeq)
                                # 全部项目延迟5分钟
                                allTaskRefresh(taskSeq, mySqlUtil, 2)
                            else:
                                ##
                                clickLoadFlag = True
                                logger.info(
                                    "%s | %s | %s | %s | 微信未加载通讯录，延迟1小时执行" % (
                                    operViewName, taskSeq, devName, taskType))
                                # logger.info("微信未加载通讯录，延迟1小时执行")
                                status = 3
                                remarks = "#1#微信未加载通讯录，延迟1小时执行"
                                notLoadUpdateSql = """update wx_add_friend
                                                        set notLoadTimes = notLoadTimes + 1
                                                        where taskSeq = \"%s\"""" % (taskSeq)
                                mySqlUtil.excSql(notLoadUpdateSql)
                                notLoadTimesSql = """SELECT notLoadTimes from wx_add_friend
                                                                where taskSeq = \"%s\"""" % (taskSeq)
                                notLoadTimes = mySqlUtil.getData(notLoadTimesSql)
                                if notLoadTimes:
                                    notLoadTimesGet = notLoadTimes[0][0]
                                else:
                                    notLoadTimesGet = 0
                                if notLoadTimesGet >= loopGate:

                                    # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
                                    taskInfoRemarkUpdate(mySqlUtil, taskSeq, 3)

                                    status = 4
                                    remarks = "无法加载通讯录，等待搜索执行"
                                    taskAdditionalDispatch(taskSeq, uuidTask, mySqlUtil, 1)
                                    # N 次加载失败，判定未无法加载通讯录
                                    return (status, remarks)  # 直接退出
                                else:
                                    # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
                                    taskInfoRemarkUpdate(mySqlUtil, taskSeq, 3)

                                    allTaskRefresh(taskSeq, mySqlUtil, 1)  # 全部任务延迟一小时

                            return (status, remarks)  # 直接退出

                        # if reload and wxUtil.elementExistById(u2Con, wxElementConf.AD_Exist_Name):
                        #     break

                        if wxUtil.elementExistById(u2Con, wxElementConf.AD_Exist_Name):
                            curFriendNum = wxUtil.getCountById(u2Con, wxElementConf.AD_Exist_Name)
                            for seqItem in range(0, curFriendNum):
                                friendPhone = wxUtil.getTextByInstance(u2Con, wxElementConf.AD_Exist_Name,
                                                                       seqItem).replace(" ", "")  # 获取好友号码

                                if friendPhone in addFriendList:
                                    findNewContract = True
                                    break

                        # if past_phone != now_phone and now_phone != '':
                        #     break

                        # if clicks == 10 and wxUtil.elementExistById(u2Con, wxElementConf.AD_Exist_Name):
                        #     break
                        # if reload and wxUtil.elementExistByText(u2Con, wxElementConf.AD_No_Mail_List, "暂无手机联系人", 2):
                        #     reload = True
                        if findNewContract:
                            break
                        wxUtil.clickById(u2Con, wxElementConf.AD_Back)  # 点击返回

                        logger.info(
                            "%s | %s | %s | %s | 微信未加载通讯录，进行重加载 %s/%s 次" % (
                                operViewName, taskSeq, devName, taskType,clicks, clicksTimes))
                        # logger.info("微信未加载通讯录，进行重加载 %s/%s 次" % (clicks, clicksTimes))
                        clicks += 1
                        time.sleep(1.5)
                    except Exception:
                        logger.warn(traceback.format_exc())

                ######################################### 开始执行添加好友 #########################################

                TFS = True
                firstTop = False  # 第一次开始滚屏到顶部
                downTextFlag = ""
                clickedList = []
                tooMuchClick = 0

                while True:
                    taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新
                    time.sleep(1)
                    try:
                        if tooMuchClick >= 4:
                            tooMuckClickFlag = True
                            break

                        if firstTop: # 开始进行必须到顶部
                            try:
                                # curFriendNum = u2Con(resourceId="com.tencent.mm:id/bc3").count # 通讯录好友列表,电话号码
                                curFriendNum = wxUtil.getCountById(u2Con , wxElementConf.AD_Exist_Name) # 通讯录好友列表,电话号码
                                # downTextFlagCur = u2Con(resourceId="com.tencent.mm:id/bc3",
                                #                      instance=curFriendNum - 1).get_text() # 通讯录最底好友号码
                                if curFriendNum > 0:
                                    downTextFlagCur = wxUtil.getTextByInstance(u2Con, wxElementConf.AD_Exist_Name, curFriendNum - 1)
                                else:
                                    downTextFlagCur = wxUtil.getTextByInstance(u2Con, wxElementConf.AD_Exist_Name, 0)
                            except Exception:
                                curFriendNum = 0
                                logger.warn(traceback.format_exc())
                                stepToFreindList(u2Con)
                                downTextFlagCur = "error"


                            if downTextFlagCur == downTextFlag: # 如果两次滑动的最底号码一样，证明滑动到底部
                                break

                            for seqItem in range(0,curFriendNum):
                                taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新

                                if tooMuchClick >= 4:
                                    tooMuckClickFlag = True
                                    break
                                addFlag = 0  # 添加好友返回标识 1 成功 2 失败 3 用户不存在 4 已经是好友 5 异常（操作频繁）6 等待执行
                                #friendPhone = u2Con(resourceId="com.tencent.mm:id/bc3",instance=seqItem).get_text().replace(" ","") # 获取好友号码
                                friendPhone = wxUtil.getTextByInstance(u2Con, wxElementConf.AD_Exist_Name, seqItem).replace(" ","") # 获取好友号码

                                if (friendPhone in freindIdListRecover or friendPhone in addFriendOtherList) and friendPhone not in clickedList:
                                    # in freindIdListRecover : 1. freindIdListRecover 为全部号码，即开始运行；2. 频繁或者中断的部分号码
                                    # in addFriendOtherList ： 其他同类加好友任务的列表
                                    # not in clickedList ： 不在已经点击的列表

                                    # 7.0.0 获取昵称方式修正
                                    wxName = ""
                                    if wxUtil.elementExistById(u2Con, wxElementConf.AD_Wx_Name, seqItem):
                                        try:
                                            wxName = wxUtil.getTextByInstanceClass(u2Con, wxElementConf.AD_Wx_Name,
                                                                                   "android.widget.TextView", seqItem)
                                            wxName = emoji.demojize(wxName.split(":")[1])
                                        except:
                                            wxName = ""
                                    if wxName == "":
                                        continue

                                    actNum = 0
                                    while True:
                                        #  单个好友处理
                                        tooFrequently = False
                                        if actNum == 2:
                                            clickedList.append(friendPhone)
                                            # 每个好友尝试2次添加
                                            addFlag = 2
                                            break
                                        try:
                                            # u2Con(resourceId="com.tencent.mm:id/bc3", instance=seqItem).click_exists(timeout=10.0) # 点击进入好友号码，进行添加
                                            wxUtil.clickByIdAndNum(u2Con, wxElementConf.AD_Exist_Name,seqItem) # 点击进入好友号码，进行添加
                                            time.sleep(1)
                                            #if u2Con(resourceId="com.tencent.mm:id/ap0").exists(timeout=3): # 添加到通讯录
                                            if wxUtil.elementExistByText(u2Con, wxElementConf.AD_To_Mail_List,"添加到通讯录"): # 添加到通讯录
                                                # 需进行添加动作，“添加到通讯录”
                                                # u2Con(resourceId="com.tencent.mm:id/ap0").click_exists(timeout=10.0)
                                                wxUtil.clickById(u2Con, wxElementConf.AD_To_Mail_List)
                                                cutTime = time.time()
                                                loadFlag = 0 # 0 - 默认，1 - 需验证， 2 - 无需验证
                                                taskSeqFlag = 0 # 0-未发送;1-已发送;2-已完成;3-失败
                                                addFlag = 0 # 0-未添加，1-已添加, 2-待添加
                                                while True:
                                                    # 防止黑屏报错
                                                    #if u2Con(resourceId="com.tencent.mm:id/hg").exists(timeout=3): # 发送键
                                                    if wxUtil.elementExistById(u2Con, wxElementConf.AD_Hi_Send, 3):
                                                        loadFlag = 1
                                                        break # 好友添加界面
                                                    #if u2Con(resourceId="com.tencent.mm:id/ap1").exists(timeout=3): # 发送信息键
                                                    if wxUtil.elementExistByText(u2Con, wxElementConf.AD_To_Mail_List,"发消息"):# 发送信息键
                                                        loadFlag = 2
                                                        break  # 好友无需验证
                                                    if time.time() - cutTime >= 10: # 10秒内黑屏回退，重试
                                                        # u2Con.press("back")
                                                        stepToFreindList(u2Con)
                                                        break # 黑屏导致好友未刷出

                                                if loadFlag == 1:
                                                    # 需要验证
                                                    #u2Con(resourceId="com.tencent.mm:id/d4h").set_text(sayHi) # 设置招呼语
                                                    wxUtil.setTextById(u2Con, wxElementConf.AD_Say_Hi, sayHi) # 设置招呼语
                                                    # u2Con(resourceId="com.tencent.mm:id/hg").click_exists(
                                                    #     timeout=10.0)  # 发送
                                                    wxUtil.clickById(u2Con, wxElementConf.AD_Hi_Send) # 发送
                                                    sendStatus = toastStatus(u2Con, logger)
                                                    # sendStatus : 0  -> 跳过
                                                    # sendStatus : 1  -> 已发送
                                                    # sendStatus : 2  -> 频繁
                                                    if sendStatus == 2:
                                                        logger.debug("操作频繁 %s/5" % tooMuchClick)
                                                        addFlag = 5
                                                        taskSeqFlag = 3
                                                        tooMuchClick += 1  # 操作太频繁
                                                        tooFrequently = True
                                                    elif sendStatus == 1:
                                                        addFlag = 1
                                                        taskSeqFlag = 2
                                                    else:
                                                        addFlag = 7  # 跳过
                                                        taskSeqFlag = 1  # 等待执行
                                                elif loadFlag == 2:
                                                    # 不需要验证
                                                    addFlag = 1
                                                    taskSeqFlag = 2
                                                    # wxName = emoji.emojize(
                                                    #     u2Con(resourceId="com.tencent.mm:id/qj").get_text()) # 微信昵称
                                                    # wxName = ""
                                                    break  # 发送成功

                                            elif wxUtil.elementExistByText(u2Con, wxElementConf.AD_To_Mail_List,"发消息"): # 发送信息
                                                # 无需验证
                                                # wxName = emoji.emojize(
                                                #     u2Con(resourceId="com.tencent.mm:id/qj").get_text())  # 微信昵称
                                                # wxName = emoji.emojize(
                                                #     wxUtil.getTextById(u2Con, wxElementConf.AD_Wechat_Name))  # 微信昵称
                                                # wxName = ""
                                                addFlag = 4
                                                taskSeqFlag = 2
                                            else:
                                                # 防止页面超长
                                                screenDown(u2Con)
                                        except Exception:
                                            logger.warn(traceback.format_exc())
                                        finally:
                                            actNum += 1
                                            clickedList.append(friendPhone)
                                            try:
                                                if addFlag != 0:
                                                    # 删除已处理号码，其他号码为未添加状态
                                                    if friendPhone.replace(" ","") in freindIdListRecover and not tooFrequently and friendPhone.replace(" ","") in freindIdListRecoverCopy:
                                                        freindIdListRecoverCopy.remove(friendPhone)
                                                    freindIdListRecoverRecord(taskSeq, freindIdListRecoverCopy, mySqlUtil)
                                                    statusRecord(taskSeq,friendPhone, wxName, addFlag, taskSeqFlag, mySqlUtil)
                                            except Exception:
                                                logger.warn(traceback.format_exc())
                                            finally:
                                                break


                                            # stepToFreindList(u2Con)


                                stepToFreindList(u2Con)

                            taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新

                            stepToFreindList(u2Con)
                            # downTextFlag = u2Con(resourceId="com.tencent.mm:id/bc3",
                            #                     instance=curFriendNum - 1).get_text()
                            downTextFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.AD_Exist_Name, curFriendNum - 1)
                            if TFS:
                                screenDown(u2Con)
                            else:
                                screenUP(u2Con)
                        # elif u2Con(resourceId="com.tencent.mm:id/bc1").exists(timeout=3):
                        elif wxUtil.elementExistById(u2Con, wxElementConf.C_LIST_TOP):
                            firstTop = True
                        else:
                            screenUP(u2Con)
                            taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新
                    except Exception:
                        stepToFreindList(u2Con)
                        logger.warn(traceback.format_exc())

                if freindIdListRecoverCopy:
                    statusRecordByBatch(taskSeq,freindIdListRecoverCopy,mySqlUtil)

                status = 4
        else:
            status = 4
    except Exception as e:
        taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新
        remarks = "通讯录加好友任务报错"
        logger.warn(traceback.format_exc())
        status = 3
    finally:

        taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新

        if appInstallFlag:
            taskStatusRecorder.taskHeartBeatRefresh(taskSeq, mySqlUtil)  # 心跳更新
            if tooMuckClickFlag:
                status = 3
                allTaskRefresh(taskSeq, mySqlUtil,1)
                remarks = "#1#操作频繁，延迟1小时执行"
                logger.info(
                    "%s | %s | %s | %s | 操作频繁，延迟1小时执行" % (
                        operViewName, taskSeq, devName, taskType))
                # logger.info("操作频繁，延迟1小时执行")
                # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
                taskInfoRemarkUpdate(mySqlUtil, taskSeq, 3)
            else:
                # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
                taskInfoRemarkUpdate(mySqlUtil, taskSeq, 2)

            if filePath !="" and os.path.exists(filePath):
                os.remove(filePath)

            if not clickLoadFlag and not firstClickLoadFlag:
                taskAdditionalDispatch(taskSeq, uuidTask, mySqlUtil)
        else:
            # 未安装通讯录
            # 任务OKAY_TASK_INFO 标注，1 任务执行中；2 任务等待执行；3 任务排队中；4 任务已完成； 5 任务组件缺失
            taskInfoRemarkUpdate(mySqlUtil, taskSeq, 5)

        # 判断是否被下线
        wxUtil.pwModifySkip(u2Con, logger)
        # 判断微信是否被挤下线
        loginOut = wxUtil.judge_logout(u2Con)
        # 判断微信是否登出
        # loginOut = wxUtil.indexJudege(u2ConStart, logger)
        if loginOut:
            wxOffLineSql = """UPDATE wx_account_info SET if_start = 0  where uuid=%s""" % (
                uuidTask)
            mySqlUtil.excSql(wxOffLineSql)
            taskStatusRecorder.taskReset(mySqlUtil, taskSeq, 1)

    return (status, remarks)

if __name__ == '__main__':
    from tools import machinInfo, MysqlDbPool
    import uiautomator2 as u2
    from lib.ModuleConfig import ConfAnalysis

    BASEDIR = os.getcwd()

    # 初始化logger
    logger = getLogger('./log/addFriend.log')
    # # 初始化config
    # configFile = '%s/conf/moduleConfig.conf' % BASEDIR
    # confAllItems = ConfAnalysis(logger, configFile)

    # u2Con = u2.connect('127.0.0.1:21513')
    mySqlUtil_main = MysqlDbPool.MysqlDbPool(1, 4)
    taskAdditionalDispatch('1546929476723994','1',mySqlUtil_main)
    #taskItemInfo = ('1530523796391', '5b2ee29c-8e4b-11e8-8056-ecf4bbe8d4f3', 22, '127.0.0.1', '21513', '17302')
    #OneKeyAction(logger, u2Con, taskItemInfo)
    # addFriendByContact(logger, u2Con)

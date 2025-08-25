import traceback

import emoji

from actionModule import getWxFriendList
from tools import wxUtil, redisUtil
import time,random
# import uiautomator2 as u2
import os

BASEDIR = os.getcwd()
# 初始化logger
from lib.WxElementConf import WxElementConf
from lib.FinalLogger import *

logger = getLogger('./log/groupAction.log')
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
wxElementConf = WxElementConf(logger)


# 一键拉群
def actionCreate(logger, u2Con, taskItemInfo, mySqlUtil):
    '''
    taskItemInfo : (1529744171645, '4129412c-6df1-11e8-951d-246e9664fac5', 9, '127.0.0.1', '21513')
    :param logger:
    :param u2Con:
    :param taskItemInfo:
    :return:
    '''
    remarks = '#'
    try:
        # 任务信息收集
        taskUuid = taskItemInfo[1]
        actionType = taskItemInfo[2]
        devName = taskItemInfo[6]
        operViewName = taskItemInfo[7]
        taskDetail = getTaskDetail(taskItemInfo, mySqlUtil)[0]
        groupName = taskDetail[0]
        groupMainWxName = taskDetail[1]
        friendList = taskDetail[2].split('#')
        friendNum = len(friendList)
        groupUsage = taskDetail[3]
        groupNotice = taskDetail[4]
        wxMianId = taskDetail[5]
        # 主体运行
        if friendNum >= 2:
            wxUtil.clickByClassAndNum(u2Con, WxElementConf.G_Index_Action, "android.widget.ImageView", 1) # 点击微信主页 + 号
            time.sleep(0.5)
            wxUtil.clickById(u2Con, wxElementConf.G_Group_Action)  # 点击发起群聊
            for friend in friendList:
                wxInfo = friend.split('|')
                wxId = wxInfo[0]
                wxName = wxInfo[1]
                if 'wxid_' not in wxId:
                    time.sleep(0.2)
                    wxUtil.setTextById(u2Con, wxElementConf.G_Friend_Search, wxId)  # 如果微信ID不以wxid开头，在搜索框中输入微信ID
                else:
                    time.sleep(0.2)
                    wxUtil.setTextById(u2Con, wxElementConf.G_Friend_Search, wxName)  # 否则在输入框中输入微信昵称

                if wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Not_Find):  # 搜索微信好友结果，判断是否存在
                    if "没有找到" in wxUtil.getTextById(u2Con, wxElementConf.G_Friend_Not_Find):  # 如果结果中包含没有找到
                        time.sleep(1)
                        wxUtil.clearTextById(u2Con, wxElementConf.G_Friend_Search)  # 清空搜索框内容
                        time.sleep(1)
                        wxUtil.setTextById(u2Con, wxElementConf.G_Friend_Search, wxName)  # 将微信昵称输入
                        if wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Not_Find):  # 如果还是不存在，跳出
                            continue
                        elif wxUtil.getCountById(u2Con, wxElementConf.G_Friend_Item) >= 2:  # 如果搜索好友 最常使用/联系人 框不小于2个元素
                            if wxUtil.elementExistByText(u2Con,  wxElementConf.search_result_with_wxid, "昵称: %s" % wxName):
                                wxUtil.clickByText(u2Con, wxElementConf.search_result_with_wxid, "昵称: %s" % wxName)
                            elif u2Con(resourceId=wxElementConf.G_Friend_First, text=u"%s" % wxName).right(
                                    className="android.widget.CheckBox").info.get('enabled'):
                                wxUtil.clickByText(u2Con, wxElementConf.G_Friend_First, wxName)
                        elif wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Find_Click):
                            if u2Con(resourceId=wxElementConf.G_Friend_Find_Click).info.get(
                                    'enabled') == False:  # G_Friend_Find_Click
                                continue
                            else:
                                wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click)
                        else:
                            wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click)
                elif wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Find_Click):
                    if wxUtil.getCountById(u2Con, wxElementConf.G_Friend_Item) >= 2:
                        if wxUtil.elementExistByText(u2Con, wxElementConf.search_result_with_wxid, "昵称: %s" % wxName):
                            wxUtil.clickByText(u2Con,  wxElementConf.search_result_with_wxid, "昵称: %s" % wxName)
                        elif u2Con(resourceId=wxElementConf.G_Friend_First, text=u"%s" % wxName).right(
                                className="android.widget.CheckBox").info.get('enabled'):
                            wxUtil.clickByText(u2Con, wxElementConf.G_Friend_First, wxName)
                    elif u2Con(resourceId=wxElementConf.G_Friend_Find_Click).info.get('enabled') == False:
                        continue
                    else:
                        wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click)
                else:
                    wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click)

            # 动作设置标志位
            groupNameFlag = 0
            if groupNotice:
                groupNoticeEditFlag = 0
            else:
                groupNoticeEditFlag = 1
            groupPerNameOpenFlag = 0
            saveComFlag = 0
            wxNameFlag = 0
            TFS = 0

            wxUtil.clickById(u2Con, wxElementConf.G_Create_Confirm)

            # 20180831 补充添加结束后由提示框
            time.sleep(1)
            if wxUtil.elementExistById(u2Con, wxElementConf.G_Create_Fail):
                if "需要发送验证申请，等对方通过" in wxUtil.getTextById(u2Con, wxElementConf.G_Create_Fail):
                    timeNow = time.time()
                    while time.time() - timeNow <= 10:
                        if wxUtil.elementExistById(u2Con, wxElementConf.G_Create_Fail_Confirm):
                            wxUtil.clickById(u2Con, wxElementConf.G_Create_Fail_Confirm)
                        elif not wxUtil.elementExistById(u2Con, wxElementConf.G_Create_Fail_Confirm):
                            break

            time.sleep(2)
            groupCreateFailFlag = False
            if wxUtil.elementExistById(u2Con, wxElementConf.G_Create_Fail):
                groupCreateFail = wxUtil.getTextById(u2Con, wxElementConf.G_Create_Fail)
                if groupCreateFail == "创建群聊的频率过快，请明日再试。":
                    groupCreateFailFlag = True
            if groupCreateFailFlag:
                wxUtil.clickById(u2Con, wxElementConf.G_Create_Fail_Confirm)
                remarks = "创建群聊的频率过快，请明日再试"
                status = 3
                statusRecord = -1
            else:
                while True:
                    wxUtil.clickById(u2Con, wxElementConf.G_Info_Edit)
                    if not wxUtil.elementExistById(u2Con, wxElementConf.G_Info_Edit):
                        break
                    time.sleep(1)
                while True:
                    # 进入群设置
                    try:
                        if groupNameFlag == 0:
                            time.sleep(0.5)
                            gNexists = wxUtil.elementExistByText(u2Con, wxElementConf.G_Group_Name, "群聊名称")
                            if gNexists:
                                # 修改群名称
                                wxUtil.clickByText(u2Con, wxElementConf.G_Group_Name, "群聊名称")
                                wxUtil.setTextById(u2Con, wxElementConf.G_Group_Name_Set, groupName)
                                wxUtil.clickById(u2Con, wxElementConf.G_Group_Name_Save)
                                groupNameFlag = 1
                        # 填写群公告
                        if groupNoticeEditFlag == 0:
                            time.sleep(0.5)
                            gNoExists = wxUtil.elementExistById(u2Con, wxElementConf.G_Notice)
                            if gNoExists:
                                wxUtil.longclickById(u2Con, wxElementConf.G_Notice)
                                wxUtil.setTextById(u2Con, wxElementConf.G_Notice_Set, groupNotice)
                                wxUtil.clickById(u2Con, wxElementConf.G_Notice_Save)
                                wxUtil.longclickById(u2Con, wxElementConf.G_Notice_Send)
                                groupNoticeEditFlag = 1
                        # 打开成员昵称
                        if groupPerNameOpenFlag == 0:
                            time.sleep(0.5)
                            gpnExists = wxUtil.elementExistByText(u2Con, wxElementConf.G_Person_Name, "显示群成员昵称")
                            if gpnExists:
                                time.sleep(0.5)
                                wxUtil.clickByDescClassAndNum(u2Con, wxElementConf.G_Person_Name_Open, "已关闭",
                                                              "android.view.View", 3)
                                groupPerNameOpenFlag = 1
                        # 打开保存到通讯录
                        if saveComFlag == 0:
                            time.sleep(0.5)
                            # android:id/title
                            scExists = wxUtil.elementExistByText(u2Con, wxElementConf.G_Cont_List, "保存到通讯录")
                            if scExists:
                                time.sleep(0.2)
                                while True:
                                    wxUtil.clickByDescClassAndNum(u2Con, wxElementConf.G_Cont_List_Open, "已关闭",
                                                                  "android.view.View", 2)
                                    saveComListExist = wxUtil.getCountByDescription(u2Con,
                                                                                    wxElementConf.G_Cont_List_Open,
                                                                                    "已开启")
                                    if saveComListExist == 0:
                                        wxUtil.clickByDescClassAndNum(u2Con, wxElementConf.G_Cont_List_Open, "已关闭",
                                                                      "android.view.View", 2)
                                    else:
                                        saveComFlag = 1
                                        break
                        # 20190327 屏蔽
                        # if wxNameFlag == 0:
                        #     time.sleep(0.5)
                        #     wnExists = wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "我在本群的昵称")
                        #     if wnExists:
                        #         # 修改昵称
                        #         wxUtil.longclickByText(u2Con, wxElementConf.G_Main_Name, "我在本群的昵称")
                        #         time.sleep(1)
                        #         wxUtil.setTextById(u2Con, wxElementConf.G_Main_Set, groupMainWxName)
                        #         wxUtil.clickById(u2Con, wxElementConf.G_Main_Confirm)
                        #         # wxUtil.clickById(u2Con, wxElementConf.G_Main_Confirm)
                        #         wxNameFlag = 1
                        if groupNameFlag == 1 and groupNoticeEditFlag == 1 and groupPerNameOpenFlag == 1 and saveComFlag == 1 :
                        # if groupNameFlag == 1 and groupNoticeEditFlag == 1 and groupPerNameOpenFlag == 1 and saveComFlag == 1 and wxNameFlag == 1:
                            break
                        else:
                            if TFS == 0:
                                fromX = u2Con.window_size()[0] / 2
                                fromY = u2Con.window_size()[1] / 2
                                toX = u2Con.window_size()[0] / 2
                                toY = 0
                                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                                if wxUtil.elementExistByText(u2Con, wxElementConf.G_Del_OUT, "删除并退出"):
                                    TFS = 1
                            else:
                                toX = u2Con.window_size()[0] / 2
                                toY = u2Con.window_size()[1] / 2
                                fromX = u2Con.window_size()[0] / 2
                                fromY = toY / 4
                                while True:
                                    u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                                    time.sleep(0.2)
                                    if wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "群聊名称"):
                                        TFS = 0
                                        break
                    except Exception as e:
                        logger.warn(traceback.format_exc())

                # 刷新微信信息，知道找到对应groupId
                # groupId = ""
                # time.sleep(1)
                # while True:
                #     taskItemTmp = (taskItemInfo[0], taskItemInfo[1], '9', taskItemInfo[3], taskItemInfo[4],taskItemInfo[5],taskItemInfo[6],taskItemInfo[7])
                #     logger.debug("拉群后更新微信信息")
                #     statusFin, remarksFin = updateWxInfo(logger, u2Con, taskItemTmp, mySqlUtil)
                #     groupIdGetSql = """SELECT group_id,group_name FROM `wx_group_info`
                #                                     WHERE group_name = \'%s\'
                #                                     and wx_id = \'%s\'""" % (groupName, wxMianId)
                #     groupIdGet = mySqlUtil.fetchData(groupIdGetSql)
                #     # print(groupIdGet)
                #     if groupIdGet[0] == 1 and groupIdGet[1]:
                #         groupId = groupIdGet[1][0][0]
                #         if groupId:
                #             statusFin = 4
                #             remarksFin = '#'
                #             break
                #     else:
                #         time.sleep(1)

                status = 4
                statusRecord = 1
        else:
            status = 3
            statusRecord = -1
    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())
        status = 3
        statusRecord = -1
        groupId = ""
        statusFin = 3
        remarksFin = e
    finally:
        # 刷新好友
        flushFriendGen(taskUuid, wxMianId, mySqlUtil)
        # 群信息记录，20180706 屏蔽，该任务会由调度先写表，失败再更新
        # if groupId:  # description,notice,group_wx_name
        #     statusRecord = 1
        # else:
        #     statusRecord = -1
        #
        # groupInfoRecord(mySqlUtil, type=actionType, group_id=groupId, description=groupUsage, notice=groupNotice,
        #                 group_wx_name=groupMainWxName, group_name=groupName, wx_id=wxMianId, status=statusRecord)

    return (status, remarks)


# 刷新好友
def flushFriendGen(uuid, wxId, mySqlUtil):
    channel_id = "flush_friend"
    message = "%s:~:0#=#0" % wxId
    redisUtil.publishFlushFriend(channel_id, message)

    taskSeq = round(time.time() * 1000 + random.randint(100, 999))
    sql = "INSERT INTO wx_task_manage(taskSeq,uuid,actionType,createTime,status,priority, startTime)" \
          "VALUES(%d,'%s',9,now(),2,5, now())" % (taskSeq, uuid)
    mySqlUtil.execSql(sql)

# 从任务表中拿到type 拼写sql
def getTaskDetail(taskItemInfo, mySqlUtil):
    taskSeq = taskItemInfo[0]
    type = str(taskItemInfo[2])
    if type == '12':
        taskDetailGetSql = """SELECT groupName, mainWxName, friendList, groupUsage, groupNotice, wxId from wx_group_task
                              where taskSeq = %s""" % taskSeq
    elif type == '13':
        taskDetailGetSql = """SELECT groupName, friendList,wxId from wx_group_task
                              where taskSeq = %s""" % taskSeq
    elif type == '14':
        taskDetailGetSql = """SELECT groupName, friendList,wxId from wx_group_task
                              where taskSeq = %s""" % taskSeq
    elif type == '15':
        taskDetailGetSql = """SELECT groupName,wxId from wx_group_task
                              where taskSeq = %s""" % taskSeq
    elif type == '16':
        taskDetailGetSql = """SELECT groupName, wxId, groupNotice from wx_group_task
                                  where taskSeq = %s""" % taskSeq
    elif type == '17':
        taskDetailGetSql = """SELECT groupName, wxId, friendList from wx_group_task
                                  where taskSeq = %s""" % taskSeq
    elif type == '18':
        taskDetailGetSql = """SELECT groupName, wxId, mainWxName from wx_group_task
                                  where taskSeq = %s""" % taskSeq
    else:
        pass

    taskDetail = mySqlUtil.fetchData(taskDetailGetSql)
    return taskDetail[1]


# 更新群信息表的记录
def groupInfoRecord(mySqlUtil, type='', **dictArg):
    if type == 12:
        status = dictArg['status']
        description = dictArg['description']
        notice = dictArg['notice']
        group_wx_name = dictArg['group_wx_name']
        group_name = dictArg['group_name']
        wx_id = dictArg['wx_id']
        group_id = dictArg['group_id']
        recordSql = """update wx_group_info
                            set `status` = \'%s\',
                            description = \'%s\',
                            notice = \'%s\',
                            group_wx_name = \'%s\'
                            where `group_id` = \'%s\'""" % (status, description, notice, group_wx_name, group_id)
        mySqlUtil.execSql(recordSql)
    elif type == 13:
        group_name = dictArg['group_name']
        wx_id = dictArg['wx_id']
        friendAddList = dictArg['friendAddList']
        getGroupId = """SELECT max(group_id) from wx_group_info
                            where group_name = \'%s\'
                            and wx_id = \'%s\' """ % (group_name, wx_id)
        groupId = mySqlUtil.getData(getGroupId)[0][0]
        updateTaskSql = """update wx_group_info
                            set `status` = 1
                            where `group_id`=\'%s\';""" % (groupId)
        logger.debug(updateTaskSql)
        mySqlUtil.execSql(updateTaskSql)
    elif type == 14:
        group_name = dictArg['group_name']
        wx_id = dictArg['wx_id']
        friendDelList = dictArg['friendDelList']
        getGroupId = """SELECT max(group_id) from wx_group_info
                                    where group_name = \'%s\'
                                    and wx_id = \'%s\' """ % (group_name, wx_id)
        groupId = mySqlUtil.getData(getGroupId)[0][0]
        updateTaskSql = """update wx_group_info
                                    set `status` = 1
                                    where `group_id`=\'%s\';""" % (groupId)
        mySqlUtil.execSql(updateTaskSql)
    elif type == 15:
        group_name = dictArg['group_name']
        wx_id = dictArg['wx_id']
        getGroupId = """SELECT max(group_id) from wx_group_info
                                            where group_name = \'%s\'
                                            and wx_id = \'%s\' """ % (group_name, wx_id)
        groupId = mySqlUtil.getData(getGroupId)[0][0]
        updateTaskSql = """update wx_group_info
                                    set `status` = 1
                                    where `group_id`=\'%s\';""" % (groupId)
        mySqlUtil.execSql(updateTaskSql)
    elif type == 16:
        group_name = dictArg['group_name']
        wx_id = dictArg['wx_id']
        groupNotice = dictArg['groupNotice']
        getGroupId = """SELECT max(group_id) from wx_group_info
                                            where group_name = \'%s\'
                                            and wx_id = \'%s\' """ % (group_name, wx_id)
        groupId = mySqlUtil.getData(getGroupId)[0][0]
        recordSql = """UPDATE `wx_group_info` SET `notice`=\'%s\'
                            WHERE `group_id`=\'%s\';""" % (groupNotice, groupId)
        # print(recordSql)
        mySqlUtil.execSql(recordSql)
        updateTaskSql = """update wx_group_info
                                    set `status` = 1
                                    where `group_id`=\'%s\';""" % (groupId)
        mySqlUtil.execSql(updateTaskSql)
    elif type == 17:
        group_name = dictArg['group_name']
        wx_id = dictArg['wx_id']
        wxIdChange = dictArg['wxIdChange']
        getGroupId = """SELECT max(group_id) from wx_group_info
                                                    where group_name = \'%s\'
                                                    and wx_id = \'%s\' """ % (group_name, wx_id)
        groupId = mySqlUtil.getData(getGroupId)[0][0]
        # recordSql = """UPDATE `wx_group_info` SET `wx_id`=\'%s\'
        #                 WHERE `group_id`= \'%s\';""" %(wxIdChange,groupId)
        # mySqlUtil.execSql(recordSql)
        updateTaskSql = """update wx_group_info
                                    set `status` = 1
                                    where `group_id`=\'%s\';""" % (groupId)
        mySqlUtil.execSql(updateTaskSql)
    elif type == 18:
        # type=actionType, group_name=groupName, wx_id=wxId,wxNameChange=wxNameChange
        group_name = dictArg['group_name']
        wx_id = dictArg['wx_id']
        wxNameChange = dictArg['wxNameChange']
        getGroupId = """SELECT max(group_id) from wx_group_info
                                                    where group_name = \'%s\'
                                                    and wx_id = \'%s\' """ % (group_name, wx_id)
        groupId = mySqlUtil.getData(getGroupId)[0][0]
        # recordSql = """UPDATE `wx_group_info` SET `group_wx_name`=\'%s\'
        #                 WHERE `group_id`= \'%s\';""" %(wxNameChange,groupId)
        # mySqlUtil.execSql(recordSql)
        updateTaskSql = """update wx_group_info
                                    set `status` = 1
                                    where `group_id`=\'%s\';""" % (groupId)
        mySqlUtil.execSql(updateTaskSql)

# 群处理操作后增加刷新好友的任务
def updateWxInfo(logger, u2Con, taskItemTmp, mySqlUtil):
    status, remarks = getWxFriendList.get_wx_friend_info(logger, u2Con, taskItemTmp, mySqlUtil)
    return (status, remarks)

# 群增加好友
def actionAdd(logger, u2Con, taskItemInfo, mySqlUtil):
    remarks = '#'
    try:
        friendAddReal = []
        taskUuid = taskItemInfo[1]
        actionType = taskItemInfo[2]
        taskDetail = getTaskDetail(taskItemInfo, mySqlUtil)[0]
        groupName = taskDetail[0]
        friendList = taskDetail[1].split('#')
        wxMianId = taskDetail[2]
        # 主体运行
        wxUtil.clickByClassAndNum(u2Con, WxElementConf.G_Index_Action, "android.widget.ImageView", 1)  # 点击微信主页 + 号
        time.sleep(0.5)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Action)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Pick)
        time.sleep(0.5)

        # 20180809 增加找群滑动
        loopRun = 0
        GTFS = 0
        topFlag = ""
        downFlag = ""
        groupExit = False
        time.sleep(0.5)
        while True:
            groupExistCount = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
            if groupExistCount == 0:
                break
            if wxUtil.elementExistByText(u2Con, wxElementConf.G_Group_PickName, groupName):
                wxUtil.clickByText(u2Con, wxElementConf.G_Group_PickName, groupName)
                groupExit = True
                break
            if loopRun > 2:
                break
            if GTFS == 0:
                fromX = u2Con.window_size()[0] / 2
                fromY = u2Con.window_size()[1] / 2
                toX = u2Con.window_size()[0] / 2
                toY = 0
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                itemCountDown = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
                instanceCount = itemCountDown - 1
                hereDownFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, instanceCount)
                if hereDownFlag == downFlag:
                    GTFS = 1
                    loopRun += 1
                else:
                    downFlag = hereDownFlag
            else:
                toX = u2Con.window_size()[0] / 2
                toY = u2Con.window_size()[1] / 2
                fromX = u2Con.window_size()[0] / 2
                fromY = toY / 4
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                hereTopFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, 0)
                if hereTopFlag == topFlag:
                    GTFS = 0
                    loopRun += 1
                else:
                    topFlag = hereTopFlag

        if groupExit:
            # 20180809 update
            time.sleep(2)
            while True:
                wxUtil.clickById(u2Con, wxElementConf.G_Info_Edit)
                if not wxUtil.elementExistById(u2Con, wxElementConf.G_Info_Edit):
                    break
                time.sleep(0.5)
            time.sleep(1)

            TFS = 0
            while True:
                if wxUtil.elementExistByResourceIdAndDesc(u2Con, wxElementConf.G_Group_Add, "添加成员"):
                    wxUtil.clickByResouceIdAndDesc(u2Con, wxElementConf.G_Group_Add, "添加成员")
                    break
                if TFS == 0:
                    fromX = u2Con.window_size()[0] / 2
                    fromY = u2Con.window_size()[1] / 2
                    toX = u2Con.window_size()[0] / 2
                    toY = 0
                    u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                    if wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "删除并退出"):
                        TFS = 1
                else:
                    toX = u2Con.window_size()[0] / 2
                    toY = u2Con.window_size()[1] / 2
                    fromX = u2Con.window_size()[0] / 2
                    fromY = toY / 4

                    u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                    if wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "添加成员"):
                        TFS = 0
            for friend in friendList:
                wxInfo = friend.split('|')
                wxId = wxInfo[0]
                wxName = emoji.emojize(wxInfo[1])
                if 'wxid_' not in wxId:
                    time.sleep(0.2)
                    wxUtil.setTextById(u2Con, wxElementConf.G_Group_Add_Search, wxId)
                else:
                    time.sleep(0.2)
                    wxUtil.setTextById(u2Con, wxElementConf.G_Group_Add_Search, wxName)
                if wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Not_Find):
                    if "没有找到" in wxUtil.getTextById(u2Con, wxElementConf.G_Friend_Not_Find):
                        wxUtil.setTextById(u2Con, wxElementConf.G_Friend_Search, wxName)
                        if wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Not_Find):
                            continue
                        elif wxUtil.getCountById(u2Con, wxElementConf.G_Friend_Item) >= 2:
                            if wxUtil.elementExistByText(u2Con,  wxElementConf.search_result_with_wxid, "昵称: %s" % wxName):
                                wxUtil.clickByText(u2Con,  wxElementConf.search_result_with_wxid, "昵称: %s" % wxName)
                            elif u2Con(resourceId=wxElementConf.G_Friend_First, text=u"%s" % wxName).right(
                                    className="android.widget.CheckBox").info.get('enabled'):
                                wxUtil.clickByText(u2Con, wxElementConf.G_Friend_First, wxName)
                        elif wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Find_Click):
                            if u2Con(resourceId=wxElementConf.G_Friend_Find_Click).info.get(
                                    'enabled') == False:  # G_Friend_Find_Click
                                continue
                            else:
                                wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click)
                        elif not wxUtil.elementExistById(u2Con, wxElementConf.G_Group_Friend_Not_Find):
                            continue
                        else:
                            wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click)
                            friendAddReal.append(wxInfo)
                elif wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Find_Click):
                    if wxUtil.getCountById(u2Con, wxElementConf.G_Friend_Item) >= 2:
                        if any(u2Con(resourceId= wxElementConf.search_result_with_wxid, text=u"昵称: %s" % wxName)):
                            u2Con(resourceId= wxElementConf.search_result_with_wxid, text=u"昵称: %s" % wxName).click_exists(timeout=10.0)
                        elif u2Con(resourceId=wxElementConf.G_Friend_First, text=u"%s" % wxName).right(
                                className="android.widget.CheckBox").info.get('enabled'):
                            u2Con(resourceId=wxElementConf.G_Friend_First, text=u"%s" % wxName).click_exists(timeout=10.0)
                    elif u2Con(resourceId=wxElementConf.G_Friend_Find_Click).info.get(
                            'enabled') == False:
                        continue
                    else:
                        wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click)
                elif not wxUtil.elementExistById(u2Con, wxElementConf.G_Group_Friend_Not_Find):
                    continue
                else:
                    wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click)
                    friendAddReal.append(wxInfo)

            time.sleep(0.5)
            wxUtil.clickById(u2Con, wxElementConf.G_Group_Add_Confirm)

            time.sleep(0.2)
            u2Con.press("back")
            time.sleep(1)
            u2Con.press("back")
            time.sleep(0.2)

            # taskItemTmp = (taskItemInfo[0], taskItemInfo[1], '9', taskItemInfo[3], taskItemInfo[4],taskItemInfo[5],taskItemInfo[6],taskItemInfo[7])
            # logger.debug("添加好友后更新微信信息")
            # statusFin, remarksFin = updateWxInfo(logger, u2Con, taskItemTmp, mySqlUtil)
            status = 4
        else:
            status = 3
            remarks = "找不到指定群聊信息"
    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())
        status = 3
    finally:
        # 群信息记录
        # type='',group_name='',description='',notice='',wx_id='',status=''
        groupInfoRecord(mySqlUtil, type=actionType, group_name=groupName, wx_id=wxMianId, friendAddList=friendAddReal)
        # 刷新好友
        flushFriendGen(taskUuid, wxMianId, mySqlUtil)

    return (status, remarks)

# 群聊删除好友
def actionDel(logger, u2Con, taskItemInfo, mySqlUtil):
    remarks = '#'
    try:
        taskUuid = taskItemInfo[1]
        actionType = taskItemInfo[2]
        taskDetail = getTaskDetail(taskItemInfo, mySqlUtil)[0]
        groupName = taskDetail[0]
        friendList = taskDetail[1].split('#')
        wxMianId = taskDetail[2]
        # 主体运行
        wxUtil.clickByClassAndNum(u2Con, WxElementConf.G_Index_Action, "android.widget.ImageView", 1)  # 点击微信主页 + 号
        time.sleep(0.5)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Action)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Pick)
        time.sleep(0.5)

        # 20180809 增加找群滑动
        loopRun = 0
        GTFS = 0
        topFlag = ""
        downFlag = ""
        groupExit = False
        time.sleep(0.5)
        while True:
            groupExistCount = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
            if groupExistCount == 0:
                break
            if wxUtil.elementExistByText(u2Con, wxElementConf.G_Group_PickName, groupName):
                wxUtil.clickByText(u2Con, wxElementConf.G_Group_PickName, groupName)
                groupExit = True
                break
            if loopRun > 2:
                break
            if GTFS == 0:
                fromX = u2Con.window_size()[0] / 2
                fromY = u2Con.window_size()[1] / 2
                toX = u2Con.window_size()[0] / 2
                toY = 0
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                itemCountDown = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
                instanceCount = itemCountDown - 1
                hereDownFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, instanceCount)
                if hereDownFlag == downFlag:
                    GTFS = 1
                    loopRun += 1
                else:
                    downFlag = hereDownFlag
            else:
                toX = u2Con.window_size()[0] / 2
                toY = u2Con.window_size()[1] / 2
                fromX = u2Con.window_size()[0] / 2
                fromY = toY / 4
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                hereTopFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, 0)
                if hereTopFlag == topFlag:
                    GTFS = 0
                    loopRun += 1
                else:
                    topFlag = hereTopFlag

        if groupExit:
            # 20180809 update
            time.sleep(2)
            while True:
                wxUtil.clickById(u2Con, wxElementConf.G_Info_Edit)
                if not wxUtil.elementExistById(u2Con, wxElementConf.G_Info_Edit):
                    break
                time.sleep(0.5)
            time.sleep(1)

            TFS = 0
            while True:
                if wxUtil.elementExistByResourceIdAndDesc(u2Con, wxElementConf.G_Grouo_Del, "删除成员"):
                    wxUtil.clickByResouceIdAndDesc(u2Con, wxElementConf.G_Grouo_Del, "删除成员")
                    break
                if TFS == 0:
                    fromX = u2Con.window_size()[0] / 2
                    fromY = u2Con.window_size()[1] / 2
                    toX = u2Con.window_size()[0] / 2
                    toY = 0
                    u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                    if wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "删除并退出"):
                        TFS = 1
                else:
                    toX = u2Con.window_size()[0] / 2
                    toY = u2Con.window_size()[1] / 2
                    fromX = u2Con.window_size()[0] / 2
                    fromY = toY / 4

                    u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                    if wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "删除成员"):
                        TFS = 0

            delExistNum = 0
            friendDelReal = []
            for friend in friendList:
                wxInfo = friend.split('|')
                wxId = wxInfo[0]
                wxName = wxInfo[1]
                if 'wxid_' not in wxId:
                    time.sleep(0.2)
                    wxUtil.setTextById(u2Con, wxElementConf.G_Group_Del_Search, wxId)
                else:
                    time.sleep(0.2)
                    wxUtil.setTextById(u2Con, wxElementConf.G_Group_Del_Search, wxName)
                time.sleep(1)
                if wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Not_Find):
                    if "没有找到" in wxUtil.getTextById(u2Con, wxElementConf.G_Friend_Not_Find):
                        wxUtil.setTextById(u2Con, wxElementConf.G_Friend_Search, wxName)
                        if wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Not_Find):
                            continue
                        elif u2Con(resourceId=wxElementConf.G_Friend_Item).count >= 2:
                            if any(u2Con(resourceId= wxElementConf.search_result_with_wxid, text=u"昵称: %s" % wxName)):
                                u2Con(resourceId= wxElementConf.search_result_with_wxid, text=u"昵称: %s" % wxName).click_exists(
                                    timeout=10.0)
                            elif u2Con(resourceId=wxElementConf.G_Friend_First, text=u"%s" % wxName).right(
                                    className="android.widget.CheckBox").info.get('enabled'):
                                u2Con(resourceId=wxElementConf.G_Friend_First, text=u"%s" % wxName).click_exists(timeout=10.0)
                        elif any(u2Con(resourceId=wxElementConf.G_Friend_Find_Click_D)):  # G_Friend_Find_Click_D
                            if u2Con(resourceId=wxElementConf.G_Friend_Find_Click_D).info.get(
                                    'enabled') == False:  # G_Friend_Find_Click_D
                                continue
                            else:
                                delExistNum += 1

                                time.sleep(0.8)
                                wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click_D)

                                friendDelReal.append(wxName)
                        elif not wxUtil.elementExistById(u2Con, wxElementConf.G_Group_Friend_Not_Find):
                            continue
                        else:
                            delExistNum += 1
                            wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click_D)
                            friendDelReal.append(wxName)
                elif wxUtil.elementExistById(u2Con, wxElementConf.G_Friend_Find_Click_D):
                    if u2Con(resourceId=wxElementConf.G_Friend_Item).count >= 2:
                        if any(u2Con(resourceId= wxElementConf.search_result_with_wxid, text=u"昵称: %s" % wxName)):
                            u2Con(resourceId= wxElementConf.search_result_with_wxid, text=u"昵称: %s" % wxName).click_exists(timeout=10.0)
                        elif u2Con(resourceId=wxElementConf.G_Friend_First, text=u"%s" % wxName).right(
                                className="android.widget.CheckBox").info.get('enabled'):
                            u2Con(resourceId=wxElementConf.G_Friend_First, text=u"%s" % wxName).click_exists(timeout=10.0)
                    elif u2Con(resourceId=wxElementConf.G_Friend_Find_Click_D).info.get(
                            'enabled') == False:  # G_Friend_Find_Click
                        continue
                    else:
                        delExistNum += 1
                        time.sleep(0.8)
                        wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click_D)

                        friendDelReal.append(wxName)
                elif not wxUtil.elementExistById(u2Con, wxElementConf.G_Group_Friend_Not_Find):
                    continue
                else:
                    delExistNum += 1
                    time.sleep(0.5)
                    wxUtil.clickById(u2Con, wxElementConf.G_Friend_Find_Click_D)
                    friendDelReal.append(wxName)

            if delExistNum > 0:
                time.sleep(0.5)
                wxUtil.clickById(u2Con, wxElementConf.G_Group_Del_Confirm)
                wxUtil.longclickById(u2Con, wxElementConf.G_Group_Del_Fin)

            # taskItemTmp = (taskItemInfo[0], taskItemInfo[1], '9', taskItemInfo[3], taskItemInfo[4],taskItemInfo[5],taskItemInfo[6],taskItemInfo[7])
            # logger.debug("群删好友后更新微信信息")
            # statusFin, remarksFin = updateWxInfo(logger, u2Con, taskItemTmp, mySqlUtil)
            statusRecord = 1
            status = 4
        else:
            statusRecord = 0
            status = 3
            remarks = "找不到指定群聊信息"
    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())
        statusRecord = 0
        status = 3
    finally:
        # 群信息记录
        if statusRecord == 1:
            groupInfoRecord(mySqlUtil, type=actionType, group_name=groupName, wx_id=wxMianId,
                            friendDelList=friendDelReal)
        # 刷新好友
        flushFriendGen(taskUuid, wxMianId, mySqlUtil)

    return (status, remarks)

# 群解散
def groupDel(logger, u2Con, taskItemInfo, mySqlUtil):
    remarks = '#'
    # 滑动屏幕的时候的坐标
    fromX = u2Con.window_size()[0] / 2
    fromY = u2Con.window_size()[1] / 2
    toX = u2Con.window_size()[0] / 2
    toY = 0
    try:
        # 任务信息收集
        taskUuid = taskItemInfo[1]
        actionType = taskItemInfo[2]
        taskDetail = getTaskDetail(taskItemInfo, mySqlUtil)[0]
        groupName = taskDetail[0]
        wx_id = taskDetail[1]
        # 主体运行
        wxUtil.backToHome(u2Con)
        # 发起群聊
        wxUtil.clickByClassAndNum(u2Con, WxElementConf.G_Index_Action, "android.widget.ImageView", 1)  # 点击微信主页 + 号
        time.sleep(0.5)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Action)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Pick)
        time.sleep(1)

        # 20180809 增加找群滑动
        loopRun = 0
        GTFS = 0
        topFlag = ""
        downFlag = ""
        groupExit = False
        time.sleep(0.5)
        while True:
            groupExistCount = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
            if groupExistCount == 0:
                break
            if wxUtil.elementExistByText(u2Con, wxElementConf.G_Group_PickName, groupName):
                wxUtil.clickByText(u2Con, wxElementConf.G_Group_PickName, groupName)
                groupExit = True
                break
            if loopRun > 2:
                break
            if GTFS == 0:
                fromX = u2Con.window_size()[0] / 2
                fromY = u2Con.window_size()[1] / 2
                toX = u2Con.window_size()[0] / 2
                toY = 0
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                itemCountDown = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
                instanceCount = itemCountDown - 1
                hereDownFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, instanceCount)
                if hereDownFlag == downFlag:
                    GTFS = 1
                    loopRun += 1
                else:
                    downFlag = hereDownFlag
            else:
                toX = u2Con.window_size()[0] / 2
                toY = u2Con.window_size()[1] / 2
                fromX = u2Con.window_size()[0] / 2
                fromY = toY / 4
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                hereTopFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, 0)
                if hereTopFlag == topFlag:
                    GTFS = 0
                    loopRun += 1
                else:
                    topFlag = hereTopFlag

        if groupExit:
            time.sleep(2)
            # 20180809 update
            while True:
                wxUtil.clickById(u2Con, wxElementConf.G_Info_Edit)
                if not wxUtil.elementExistById(u2Con, wxElementConf.G_Info_Edit):
                    break
                time.sleep(0.5)
            time.sleep(1)

            finFlag = True
            breakCount = 0
            while True:
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                deleteButtonExist = wxUtil.getCountByText(u2Con, wxElementConf.G_Del_OUT, "删除并退出")

                if deleteButtonExist > 0:
                    wxUtil.clickByText(u2Con, wxElementConf.G_Del_OUT, "删除并退出")
                    time.sleep(1)
                    quitGroupExist = wxUtil.getCountById(u2Con, wxElementConf.G_Group_Del)
                    quitDelGroupExist = wxUtil.getCountById(u2Con, wxElementConf.G_Group_Delete_An)
                    if quitGroupExist > 0:
                        time.sleep(0.5)
                        wxUtil.clickById(u2Con, wxElementConf.G_Group_Del)
                        break
                    elif quitDelGroupExist > 0:
                        time.sleep(0.5)
                        wxUtil.longclickById(u2Con, wxElementConf.G_Group_Delete_An)
                        break
                if breakCount >= 10:
                    remarks = "删除群失败，无法定位删除控件ID"
                    finFlag = False
                    break
                breakCount += 1

            if not finFlag:
                status = 3
            else:
                status = 4
            statusRecord = 1
        else:
            statusRecord = 0
            status = 3
            remarks = "找不到指定群聊信息"
        # wxUtil.backToHome(u2Con)

        # 群信息记录
        # groupInfoRecord(actionType,groupName,groupUsage,groupNotice,wxMianId,groupExitsPersionNum)

    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())
        statusRecord = 0
        status = 3
    finally:
        if status == 3:
            logger.debug("群解散任务失败")
            # taskItemTmp = (taskItemInfo[0], taskItemInfo[1], '9', taskItemInfo[3], taskItemInfo[4],taskItemInfo[5],taskItemInfo[6],taskItemInfo[7])
            # updateWxInfo(logger, u2Con, taskItemTmp, mySqlUtil)
        groupInfoRecord(mySqlUtil, type=actionType, group_name=groupName, wx_id=wx_id)
        # 刷新好友
        flushFriendGen(taskUuid, wx_id, mySqlUtil)


    return (status, remarks)

# 修改公告
def noticeModify(logger, u2Con, taskItemInfo, mySqlUtil):
    remarks = '#'
    try:
        # 任务信息收集
        taskUuid = taskItemInfo[1]
        actionType = taskItemInfo[2]
        taskDetail = getTaskDetail(taskItemInfo, mySqlUtil)[0]
        groupName = taskDetail[0]
        wxId = taskDetail[1]
        groupNotice = taskDetail[2]
        # 主体运行
        wxUtil.backToHome(u2Con)
        # 发起群聊
        wxUtil.clickByClassAndNum(u2Con, WxElementConf.G_Index_Action, "android.widget.ImageView", 1)  # 点击微信主页 + 号
        time.sleep(0.5)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Action)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Pick)
        time.sleep(1)

        # 20180809 增加找群滑动
        loopRun = 0
        GTFS = 0
        topFlag = ""
        downFlag = ""
        groupExit = False
        time.sleep(0.5)
        while True:
            groupExistCount = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
            if groupExistCount == 0:
                break
            if wxUtil.elementExistByText(u2Con, wxElementConf.G_Group_PickName, groupName):
                wxUtil.clickByText(u2Con, wxElementConf.G_Group_PickName, groupName)
                groupExit = True
                break
            if loopRun > 2:
                break
            if GTFS == 0:
                fromX = u2Con.window_size()[0] / 2
                fromY = u2Con.window_size()[1] / 2
                toX = u2Con.window_size()[0] / 2
                toY = 0
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                itemCountDown = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
                instanceCount = itemCountDown - 1
                hereDownFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, instanceCount)
                if hereDownFlag == downFlag:
                    GTFS = 1
                    loopRun += 1
                else:
                    downFlag = hereDownFlag
            else:
                toX = u2Con.window_size()[0] / 2
                toY = u2Con.window_size()[1] / 2
                fromX = u2Con.window_size()[0] / 2
                fromY = toY / 4
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                hereTopFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, 0)
                if hereTopFlag == topFlag:
                    GTFS = 0
                    loopRun += 1
                else:
                    topFlag = hereTopFlag

        TFS = 0
        actionComp = 0
        if groupExit:
            time.sleep(2)
            # 20180809 update
            while True:
                wxUtil.clickById(u2Con, wxElementConf.G_Info_Edit)
                if not wxUtil.elementExistById(u2Con, wxElementConf.G_Info_Edit):
                    break
                time.sleep(0.5)
            time.sleep(1)
            # 群公告
            while True:
                if actionComp == 0:
                    if wxUtil.elementExistById(u2Con, wxElementConf.G_Group_Notice):
                        wxUtil.longclickById(u2Con, wxElementConf.G_Group_Notice)
                        wxUtil.clickById(u2Con, wxElementConf.G_Group_NoticeEdit)
                        wxUtil.clearTextById(u2Con, wxElementConf.G_Grpup_Notice_Set)
                        wxUtil.setTextById(u2Con, wxElementConf.G_Grpup_Notice_Set, groupNotice)
                        wxUtil.clickById(u2Con, wxElementConf.G_Group_NoticeEdit)
                        wxUtil.longclickById(u2Con, wxElementConf.G_Group_Notice_Fin)
                        status = 4
                        statusRecord = 0
                        actionComp = 1
                    else:
                        if TFS == 0:
                            fromX = u2Con.window_size()[0] / 2
                            fromY = u2Con.window_size()[1] / 2
                            toX = u2Con.window_size()[0] / 2
                            toY = 0
                            u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                            if wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "删除并退出"):
                                TFS = 1
                        else:
                            toX = u2Con.window_size()[0] / 2
                            toY = u2Con.window_size()[1] / 2
                            fromX = u2Con.window_size()[0] / 2
                            fromY = toY / 4
                            while True:
                                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                                time.sleep(0.2)
                                if wxUtil.elementExistByText(u2Con, wxElementConf.wo_shezhi, "群聊名称"):
                                    TFS = 0
                                    break
                else:
                    break

            # taskItemTmp = (taskItemInfo[0], taskItemInfo[1], '9', taskItemInfo[3], taskItemInfo[4],taskItemInfo[5],taskItemInfo[6],taskItemInfo[7])
            # logger.debug("修改公告后更新微信信息")
            # statusFin, remarksFin = updateWxInfo(logger, u2Con, taskItemTmp, mySqlUtil)

            statusRecord = 1
            status = 4
        else:
            statusRecord = 0
            status = 3
            remarks = "找不到指定群聊信息"
        wxUtil.backToHome(u2Con)
    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())
        statusRecord = 0
        status = 3
    finally:
        # 群信息记录
        if statusRecord == 0:
            groupInfoRecord(mySqlUtil, type=actionType, group_name=groupName, groupNotice=groupNotice, wx_id=wxId)

        flushFriendGen(taskUuid, wxId, mySqlUtil)

    return (status, remarks)

# 修改群主昵称
def wxNameModify(logger, u2Con, taskItemInfo, mySqlUtil):
    remarks = '#'
    try:
        # 任务信息收集
        taskUuid = taskItemInfo[1]
        actionType = taskItemInfo[2]
        taskDetail = getTaskDetail(taskItemInfo, mySqlUtil)[0]
        groupName = taskDetail[0]
        wxId = taskDetail[1]
        wxNameChange = taskDetail[2]
        # 主体运行
        wxUtil.backToHome(u2Con)
        # 发起群聊
        wxUtil.clickByClassAndNum(u2Con, WxElementConf.G_Index_Action, "android.widget.ImageView", 1)  # 点击微信主页 + 号
        time.sleep(0.5)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Action)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Pick)
        time.sleep(1)

        # 20180809 增加找群滑动
        loopRun = 0
        GTFS = 0
        topFlag = ""
        downFlag = ""
        groupExit = False
        time.sleep(0.5)
        while True:
            groupExistCount = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
            if groupExistCount == 0:
                break
            if wxUtil.elementExistByText(u2Con, wxElementConf.G_Group_PickName,groupName):
                wxUtil.clickByText(u2Con, wxElementConf.G_Group_PickName, groupName)
                groupExit = True
                break
            if loopRun > 2:
                break
            if GTFS == 0:
                fromX = u2Con.window_size()[0] / 2
                fromY = u2Con.window_size()[1] / 2
                toX = u2Con.window_size()[0] / 2
                toY = 0
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                itemCountDown = wxUtil.getCountById(wxElementConf.G_Group_PickName)
                instanceCount = itemCountDown - 1
                hereDownFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, instanceCount)
                if hereDownFlag == downFlag:
                    GTFS = 1
                    loopRun += 1
                else:
                    downFlag = hereDownFlag
            else:
                toX = u2Con.window_size()[0] / 2
                toY = u2Con.window_size()[1] / 2
                fromX = u2Con.window_size()[0] / 2
                fromY = toY / 4
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                hereTopFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, 0)
                if hereTopFlag == topFlag:
                    GTFS = 0
                    loopRun += 1
                else:
                    topFlag = hereTopFlag

        TFS = 0
        actionComp = 0
        if groupExit:
            time.sleep(2)
            # 20180809 update
            while True:
                wxUtil.clickById(u2Con, wxElementConf.G_Info_Edit)
                if not wxUtil.elementExistById(u2Con, wxElementConf.G_Info_Edit):
                    break
                time.sleep(0.5)
            time.sleep(1)

            while True:
                if actionComp == 0:
                    # 修改昵称
                    if wxUtil.elementExistByText(u2Con, wxElementConf.wo_shezhi, "我在本群的昵称"):
                        loopBreakNum = 0
                        while True:
                            loopBreakNum += 1
                            if not wxUtil.elementExistByText(u2Con, wxElementConf.wo_shezhi, "我在本群的昵称"):
                                break
                            elif wxUtil.elementExistByText(u2Con, wxElementConf.wo_shezhi, "我在本群的昵称"):
                                wxUtil.clickByText(u2Con, wxElementConf.wo_shezhi, "我在本群的昵称")
                            elif loopBreakNum >= 10:
                                break
                        time.sleep(1)
                        wxUtil.clearTextById(u2Con, wxElementConf.G_Group_WxName_Set)
                        wxUtil.setTextById(u2Con, wxElementConf.G_Group_WxName_Set, wxNameChange)
                        wxUtil.clickById(u2Con, wxElementConf.G_Group_WxName_Confirm)

                        status = 4
                        statusRecord = 1
                        actionComp = 1
                    else:
                        if TFS == 0:
                            fromX = u2Con.window_size()[0] / 2
                            fromY = u2Con.window_size()[1] / 2
                            toX = u2Con.window_size()[0] / 2
                            toY = 0
                            u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                            if wxUtil.elementExistByText(u2Con, wxElementConf.wo_shezhi, "删除并退出"):
                                TFS = 1
                        else:
                            toX = u2Con.window_size()[0] / 2
                            toY = u2Con.window_size()[1] / 2
                            fromX = u2Con.window_size()[0] / 2
                            fromY = toY / 4
                            while True:
                                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                                time.sleep(0.2)
                                if wxUtil.elementExistByText(u2Con, wxElementConf.wo_shezhi, "群聊名称"):
                                    TFS = 0
                                    break
                else:
                    break
            # taskItemTmp = (taskItemInfo[0], taskItemInfo[1], '9', taskItemInfo[3], taskItemInfo[4],taskItemInfo[5],taskItemInfo[6],taskItemInfo[7])
            # logger.debug("修改公告后更新微信信息")
            # statusFin, remarksFin = updateWxInfo(logger, u2Con, taskItemTmp, mySqlUtil)

            statusRecord = 1
            status = 4
        else:
            statusRecord = 0
            status = 3
            remarks = "找不到指定群聊信息"
    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())
        # logger.warn(e)
        status = 3
        statusRecord = 0
    finally:
        if statusRecord == 1:
            groupInfoRecord(mySqlUtil, type=actionType, group_name=groupName, wx_id=wxId, wxNameChange=wxNameChange)
        flushFriendGen(taskUuid, wxId, mySqlUtil)
    return (status, remarks)

# 更换群主
def mainWxChange(logger, u2Con, taskItemInfo, mySqlUtil):
    remarks = '#'
    try:
        # 任务信息收集
        taskUuid = taskItemInfo[1]
        actionType = taskItemInfo[2]
        taskDetail = getTaskDetail(taskItemInfo, mySqlUtil)[0]
        groupName = taskDetail[0]
        wxId = taskDetail[1]
        wxIdChange = taskDetail[2]
        # 发起群聊
        wxUtil.clickByClassAndNum(u2Con, WxElementConf.G_Index_Action, "android.widget.ImageView", 1)  # 点击微信主页 + 号
        time.sleep(0.5)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Action)
        wxUtil.clickById(u2Con, wxElementConf.G_Group_Pick)
        time.sleep(1)

        # 20180809 增加找群滑动
        loopRun = 0
        GTFS = 0
        topFlag = ""
        downFlag = ""
        groupExit = False
        time.sleep(0.5)
        while True:
            groupExistCount = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
            if groupExistCount == 0:
                break
            if wxUtil.elementExistByText(u2Con, wxElementConf.G_Group_PickName, groupName):
                wxUtil.clickByText(u2Con, wxElementConf.G_Group_PickName, groupName)
                groupExit = True
                break
            if loopRun > 2:
                break
            if GTFS == 0:
                fromX = u2Con.window_size()[0] / 2
                fromY = u2Con.window_size()[1] / 2
                toX = u2Con.window_size()[0] / 2
                toY = 0
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                itemCountDown = wxUtil.getCountById(u2Con, wxElementConf.G_Group_PickName)
                instanceCount = itemCountDown - 1
                hereDownFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, instanceCount)
                if hereDownFlag == downFlag:
                    GTFS = 1
                    loopRun += 1
                else:
                    downFlag = hereDownFlag
            else:
                toX = u2Con.window_size()[0] / 2
                toY = u2Con.window_size()[1] / 2
                fromX = u2Con.window_size()[0] / 2
                fromY = toY / 4
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                hereTopFlag = wxUtil.getTextByInstance(u2Con, wxElementConf.G_Group_PickName, 0)

                if hereTopFlag == topFlag:
                    GTFS = 0
                    loopRun += 1
                else:
                    topFlag = hereTopFlag
        TFS = 0
        actionComp = 0
        if groupExit:
            time.sleep(2)
            # 20180809 update
            while True:
                wxUtil.clickById(u2Con, wxElementConf.G_Info_Edit)
                if not wxUtil.elementExistById(u2Con, wxElementConf.G_Info_Edit):
                    break
                time.sleep(0.5)
            time.sleep(1)
            while True:
                if actionComp == 0:
                    if wxUtil.elementExistByText(u2Con, wxElementConf.wo_shezhi, "群管理"):
                        wxUtil.clickByText(u2Con, wxElementConf.wo_shezhi, "群管理")
                        wxUtil.clickByText(u2Con, wxElementConf.wo_shezhi, "群主管理权转让")
                        wxUtil.setTextById(u2Con, wxElementConf.G_Group_MainCh_Search,wxIdChange)
                        time.sleep(1)
                        notFind_byId = wxUtil.getCountById(u2Con, wxElementConf.G_Group_MainCh_Find)
                        if notFind_byId != 0:
                            wxUtil.clickById(u2Con, wxElementConf.G_Group_MainCh_Find)
                            time.sleep(0.5)
                            wxUtil.clickById(u2Con, wxElementConf.G_Group_MainCh_Fin)
                            statusRecord = 1
                        else:
                            statusRecord = 0
                        status = 4
                        actionComp = 1
                    else:
                        if TFS == 0:
                            fromX = u2Con.window_size()[0] / 2
                            fromY = u2Con.window_size()[1] / 2
                            toX = u2Con.window_size()[0] / 2
                            toY = 0
                            u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                            if wxUtil.elementExistByText(u2Con, wxElementConf.wo_shezhi, "删除并退出"):
                                TFS = 1
                        else:
                            toX = u2Con.window_size()[0] / 2
                            toY = u2Con.window_size()[1] / 2
                            fromX = u2Con.window_size()[0] / 2
                            fromY = toY / 4
                            while True:
                                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                                time.sleep(0.2)
                                if wxUtil.elementExistByText(u2Con, wxElementConf.wo_shezhi, "群聊名称"):
                                    TFS = 0
                                    break
                else:
                    break

            # taskItemTmp = (taskItemInfo[0], taskItemInfo[1], '9', taskItemInfo[3], taskItemInfo[4],taskItemInfo[5],taskItemInfo[6],taskItemInfo[7])
            # logger.debug("修改公告后更新微信信息")
            # statusFin, remarksFin = updateWxInfo(logger, u2Con, taskItemTmp, mySqlUtil)

            statusRecord = 1
            status = 4
        else:
            statusRecord = 0
            status = 3
            remarks = "找不到指定群聊信息"
        # wxUtil.backToHome(u2Con)
        # 群信息记录
        # groupInfoRecord(actionType,groupName,groupUsage,groupNotice,wxMianId,groupExitsPersionNum)
    except Exception as e:
        remarks = e
        statusRecord = 0
        logger.warn(traceback.format_exc())
        status = 3
    finally:
        if statusRecord == 1:
            groupInfoRecord(mySqlUtil, type=actionType, group_name=groupName, wx_id=wxId, wxIdChange=wxIdChange)
        flushFriendGen(taskUuid, wxId, mySqlUtil)

    return (status, remarks)


def check(u2Con, taskItemInfo, mySqlUtil):
    actionType = taskItemInfo[2]
    taskDetail = getTaskDetail(taskItemInfo, mySqlUtil)[0]
    groupName = taskDetail[0]
    groupMainWxName = taskDetail[1]
    friendList = taskDetail[2].split('#')
    friendNum = len(friendList)
    groupUsage = taskDetail[3]
    groupNotice = taskDetail[4]
    wxMianId = taskDetail[5]
    wxUtil.clickById(u2Con, wxElementConf.G_Info_Edit)
    groupNameFlag = 0
    if groupNotice:
        groupNoticeFlag = 0
    else:
        groupNoticeFlag = 1
    groupPerNameOpenFlag = 0
    saveComFlag = 0
    wxNameFlag = 0
    TFS = 0
    while True:
        # 进入群设置
        groupNameFlag = 0
        if groupNameFlag == 0:
            time.sleep(0.5)
            gNexists = wxUtil.elementExistByText(u2Con, wxElementConf.G_Group_Name, "群聊名称")
            if gNexists:
                # 修改群名称
                wxUtil.elementExistByText(u2Con, wxElementConf.G_Group_Name, "群聊名称")
                wxUtil.setTextById(u2Con, wxElementConf.G_Group_Name_Set, groupName)
                wxUtil.clickById(u2Con, wxElementConf.G_Group_Name_Save)
                groupNameFlag = 1
        # 填写群公告
        if groupNoticeFlag == 0:
            time.sleep(0.5)
            gNoExists = wxUtil.elementExistById(u2Con, wxElementConf.G_Notice)
            if gNoExists:
                wxUtil.longclickById(u2Con, wxElementConf.G_Notice)
                wxUtil.setTextById(u2Con, wxElementConf.G_Notice_Set, groupNotice)
                wxUtil.clickById(u2Con, wxElementConf.G_Notice_Save)
                wxUtil.longclickById(u2Con, wxElementConf.G_Notice_Send)
                groupNoticeFlag = 1
        # 打开成员昵称
        if groupPerNameOpenFlag == 0:
            time.sleep(0.5)
            gpnExists = wxUtil.elementExistByText(u2Con, wxElementConf.G_Person_Name, "显示群成员昵称")
            if gpnExists:
                time.sleep(0.5)
                wxUtil.clickByDescClassAndNum(u2Con, wxElementConf.G_Person_Name_Open, "已关闭", "android.view.View", 3)
                groupPerNameOpenFlag = 1
        # 打开保存到通讯录
        if saveComFlag == 0:
            time.sleep(0.5)
            scExists = wxUtil.elementExistByText(u2Con, wxElementConf.G_Cont_List, "保存到通讯录")
            if scExists:
                time.sleep(0.2)
                while True:
                    wxUtil.clickByDescClassAndNum(u2Con, wxElementConf.G_Cont_List_Open, "已关闭", "android.view.View", 2)
                    saveComListExist = wxUtil.getCountByDescription(u2Con, wxElementConf.G_Cont_List_Open, "已开启")
                    if saveComListExist == 0:
                        wxUtil.clickByDescClassAndNum(u2Con, wxElementConf.G_Cont_List_Open, "已关闭", "android.view.View",
                                                      2)
                    else:
                        saveComFlag = 1
                        break
        if wxNameFlag == 0:
            time.sleep(0.5)
            wnExists = wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "我在本群的昵称")
            if wnExists:
                # 修改昵称
                wxUtil.longclickByText(u2Con, wxElementConf.G_Main_Name, "我在本群的昵称")
                time.sleep(1)
                wxUtil.setTextById(u2Con, wxElementConf.G_Main_Set, groupMainWxName)
                wxUtil.clickById(u2Con, wxElementConf.G_Main_Confirm)
                wxNameFlag = 1
        if groupNameFlag == 1 and groupNoticeFlag == 1 and groupPerNameOpenFlag == 1 and saveComFlag == 1 and wxNameFlag == 1:
            break
        else:
            if TFS == 0:
                fromX = u2Con.window_size()[0] / 2
                fromY = u2Con.window_size()[1] / 2
                toX = u2Con.window_size()[0] / 2
                toY = 0
                u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                if wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "删除并退出"):
                    TFS = 1
            else:
                toX = u2Con.window_size()[0] / 2
                toY = u2Con.window_size()[1] / 2
                fromX = u2Con.window_size()[0] / 2
                fromY = toY / 4
                while True:
                    u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                    time.sleep(0.2)
                    if wxUtil.elementExistByText(u2Con, wxElementConf.G_Main_Name, "群聊名称"):
                        TFS = 0
                        break

    # if __name__ == '__main__':
    import uiautomator2 as u2
    u2Con = u2.connect('127.0.0.1:21533')
    logger = ""
    taskItemInfo = (1530183800667, '417b5701-5cd2-11e8-83ff-000e1e4932e0', 18, '127.0.0.1', '21533', '13112926341')
    check(u2Con, taskItemInfo, mySqlUtil)
    if taskItemInfo[2] == 12:
        actionCreate(logger, u2Con, taskItemInfo)
    elif taskItemInfo[2] == 13:
        actionAdd(logger, u2Con, taskItemInfo)
    elif taskItemInfo[2] == 14:
        actionDel(logger, u2Con, taskItemInfo)
    elif taskItemInfo[2] == 15:
        groupDel(logger, u2Con, taskItemInfo)
    elif taskItemInfo[2] == 16:
        noticeModify(logger, u2Con, taskItemInfo)
    elif taskItemInfo[2] == 17:
        mainWxChange(logger, u2Con, taskItemInfo, mySqlUtil)
    elif taskItemInfo[2] == 18:
        wxNameModify(logger, u2Con, taskItemInfo, mySqlUtil)

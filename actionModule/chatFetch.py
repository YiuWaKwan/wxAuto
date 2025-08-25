# import uiautomator2 as u2
import time
from tools import wxUtil
import win32clipboard as w
import win32con
import copy
from lib.ModuleConfig import ConfAnalysis
import os
import random

BASEDIR = os.getcwd()

def copyChannalClean():
    w.OpenClipboard()
    w.EmptyClipboard()
    w.CloseClipboard()
    time.sleep(0.5)

def getCopyText(u2Con,num):
    loopStop = 1
    loopNum = 1
    while loopStop:
        try:
            copyChannalClean()
            time.sleep(0.5)
            u2Con(resourceId="com.tencent.mm:id/jz", instance=num).long_click(1.5)
            time.sleep(0.2)
            u2Con(text=u"复制").click_exists(timeout=10.0)
            time.sleep(1)
            w.OpenClipboard()
            textRet = w.GetClipboardData(win32con.CF_TEXT)
            w.EmptyClipboard()
            w.CloseClipboard()
            retText = textRet.decode('gbk',errors='ignore')
            loopStop = None
        except Exception:
            retText = ""
            if loopNum == 10:
                break
            loopNum +=1
            pass
    # spaceLen = len(retText) - len(retText.replace(" ",""))
    # print(spaceLen)
    # retText = retText[:retText.rfind(" ")]
    return retText

def friendRel(wxId,wxFriendId,chatContent,mySqlUtil):
    # 好友列表
    friendExitSql = """SELECT count(1) from wx_friend_list
                        where wx_id = \'%s\'""" %wxFriendId
    friendExist = mySqlUtil.getData(friendExitSql)
    # 好友关系表
    friendRelaSql = """SELECT count(1) from wx_friend_rela
                        where wx_main_id = \'%s\'  
                        and wx_id = \'%s\'""" %(wxId,wxFriendId)
    friendRelaExist = mySqlUtil.getData(friendRelaSql)
    # print(friendExist,friendRelaExist) # ((1,),) ((0,),)
    # print(friendExist[0][0],friendRelaExist[0][0])
    # 查看好友是否已存在wx_friend_list ， 未存在，下发 任务9 ，以及下发wx_friend_refresh 子任务表
    if friendExist[0][0] == 0:
        wxMainIdUuidSql = """SELECT uuid from wx_account_info
                                where wx_id = \'%s\'""" %wxId
        wxMainIdUuid = mySqlUtil.getData(wxMainIdUuidSql)
        taskSeq = round(time.time() * 1000 + random.randint(100, 999))
        insertTaskSql = """INSERT INTO `wx_task_manage` (`taskSeq`, `uuid`, `actionType`, `createTime`,  `priority`, `status`) 
                        VALUES (\'%s\', \'%s\', '9', now(), '5', '1')""" %(taskSeq,wxMainIdUuid[0][0])

        mySqlUtil.execSql(insertTaskSql)
        insertSubTaskSql = """INSERT INTO `wx_friend_refresh` (`taskSeq`, `wx_main_id`, `wx_friend_id`) 
                        VALUES (\'%s\', \'%s\', \'%s\');""" %(taskSeq,wxId,wxFriendId)

        mySqlUtil.execSql(insertSubTaskSql)

    # 好友列表存在，但好友关系表未存在，插入好友关系表wx_friend_rela
    elif friendExist[0][0] > 0 and friendRelaExist[0][0] == 0:
        insertSql = """INSERT INTO `wx_friend_rela` (`wx_main_id`, `wx_id`, `add_time`, `add_type`, `state`, `source`, `last_chart_time`, `last_chart_content`, `isTop`, `send_type`) 
              VALUES (\'%s\', \'%s\', now(), 1, 1, '主动添加', now(), \'%s\', '0', '2');"""%(wxId,wxFriendId,chatContent)

        mySqlUtil.execSql(insertSql)


def action(logger, u2Con,taskItemInfo,mySqlUtil):
    '''
        聊天内容获取
        :param u2Con:
        :param taskItemInfo: (1529744171645, '4129412c-6df1-11e8-951d-246e9664fac5', 7, '127.0.0.1', '21513')
        :return:
        '''
    # print(taskItemInfo)
    # 初始化config
    remarks = '#'
    try:
        devName = taskItemInfo[6]
        configFile = '%s/conf/moduleConfig.conf' % BASEDIR
        confAllItemsHere = ConfAnalysis(logger, configFile, '')

        currentWxIdSql = """SELECT A.wx_id from wx_account_info A
                            where A.uuid = \'%s\'""" %taskItemInfo[1]
        currentWxIdRet = mySqlUtil.fetchData(currentWxIdSql)
        if currentWxIdRet[0] == 1:
            currentWxId = currentWxIdRet[1][0][0]
        else:
            currentWxId = ""
        # u2Con(text=u"微信").click()

        wxUtil.backToHome(u2Con)

        # 屏幕尺寸
        time.sleep(0.5)
        screenSizeCenter = u2Con(resourceId="com.tencent.mm:id/c4i").center()

        messageList = []
        while True:
            try:
                # 红点个数
                redPointCount = u2Con(resourceId="com.tencent.mm:id/jj").count
                if redPointCount > 0:
                    # 红点数字，即未读信息数目
                    # print(time.time())
                    # a = u2Con(resourceId="com.tencent.mm:id/jj").right(className="android.view.View").down(className="android.view.View").get_text()
                    # print(a)
                    # print(time.time())
                    redPointText = u2Con(resourceId="com.tencent.mm:id/jj").get_text()
                    u2Con(resourceId="com.tencent.mm:id/jj").click()
                    time.sleep(0.5)
                    # 判断公众号
                    wxMsgPanCount = u2Con(resourceId="com.tencent.mm:id/abh").count

                    if  wxMsgPanCount == 0:
                        # 微信昵称获取
                        time.sleep(0.2)
                        wxFriendNameReal = u2Con(resourceId="com.tencent.mm:id/hn").get_text()
                        wxNameFilter = confAllItemsHere.getOneOptions('filterWxName', 'filterList')
                        wxNameFilterList = wxNameFilter.split(',')

                        if wxFriendNameReal not in wxNameFilterList:
                            messageNumJZ = u2Con(resourceId="com.tencent.mm:id/jz").count
                            # messageNumJX = u2Con(resourceId="com.tencent.mm:id/jz").count
                            # instanceIndexJX = 1
                            instanceIndex = 1
                            # 好友微信号获取开始
                            u2Con(resourceId="com.tencent.mm:id/gd").click_exists(timeout=10.0)

                            # 判断是否为群聊，依据能否删除好友
                            time.sleep(1)
                            if not u2Con(resourceId="com.tencent.mm:id/cz1").exists:
                                toX = u2Con.window_size()[0] / 2
                                toY = u2Con.window_size()[1] / 2
                                fromX = u2Con.window_size()[0] / 2
                                fromY = toY / 4
                                while True:
                                    u2Con.swipe(fromX, fromY, toX, toY, 0.1)
                                    time.sleep(0.2)
                                    if  u2Con(resourceId="com.tencent.mm:id/cz1").exists:
                                        break
                            # 个人号id/cz1.count 等于2
                            picNum = u2Con(resourceId="com.tencent.mm:id/cz1").count
                            # 个人号groupNmae 等于0
                            groupNmae = u2Con(resourceId="android:id/title", text=u"群聊名称").count
                            if picNum == 2 and groupNmae == 0:
                                ifGroup = False
                            else:
                                ifGroup =True

                            if not ifGroup:
                                # ifGroup == 0 即为个人号
                                u2Con(resourceId="com.tencent.mm:id/cz1").click_exists(timeout=10.0)
                                time.sleep(0.8)
                                wxFriendIdStr  = u2Con(resourceId="com.tencent.mm:id/ang").get_text()
                                wxFriendId = wxFriendIdStr.split(":")[1].replace(" ","")

                                time.sleep(0.2)
                                u2Con.press("back")
                                time.sleep(0.2)
                                u2Con.press("back")
                                # 微信号获取结束

                                while True:
                                    messageListTmp = []
                                    messageSizeCenter = u2Con(resourceId="com.tencent.mm:id/jz", instance=(messageNumJZ - instanceIndex)).center()
                                    if messageSizeCenter[0] < screenSizeCenter[0]:
                                        messageListTmp.append(currentWxId)
                                        messageListTmp.append(wxFriendId)
                                        # copyChannalClean()
                                        # u2Con(resourceId="com.tencent.mm:id/jz", instance=(messageNumJZ - instanceIndex)).long_click()
                                        # time.sleep(0.1)
                                        # u2Con(text=u"复制").click_exists(timeout=10.0)
                                        chatText = getCopyText(u2Con,(messageNumJZ - instanceIndex))
                                        messageListTmp.append(chatText.replace('\x00',''))
                                        messageList.append(copy.deepcopy(messageListTmp))

                                        # 判断好友关系
                                        friendRel(currentWxId, wxFriendId,chatText.replace('\x00',''),mySqlUtil)
                                    if len(messageList) >= int(redPointText):
                                        break
                                    instanceIndex += 1

                                time.sleep(0.2)
                                u2Con.press("back")
                                # else:
                                #     u2Con.press("back")
                            else:
                                # ifGroup == 0 即为群聊
                                wxUtil.backToHome(u2Con)
                        else:
                            # 过滤列表
                            u2Con.press("back")
                            time.sleep(1)
                        # 如果是公众号，返回
                    else:
                        u2Con.press("back")
                        time.sleep(2)
                else:
                    break
                time.sleep(1)
            except Exception as e:
                logger.warn(e)
                pass

        if messageList:
            dataSaver(messageList,mySqlUtil)
        wxUtil.backToHome(u2Con)

        # 删除 任务 5的前期任务
        clearBeforeTask(taskItemInfo,mySqlUtil)
        status = 4
    except Exception as e:
        logger.warn(e)
        remarks = e
        status = 3

    return (status,remarks)

def dataSaver(value,mySqlUtil):
    sqlTmp = ""
    for valueItem in value:
        sqlTmp += "(\'%s\', \'%s\', now(), \'%s\')," %(valueItem[0],valueItem[1],valueItem[2])
    exeSql = "INSERT INTO `wx_chat_info` (`wx_main_id`, `wx_id`, `send_time`, `content`)  VALUES %s" %(sqlTmp[:-1])
    mySqlUtil.excSql(exeSql)

def clearBeforeTask(taskItemInfo,mySqlUtil):
    taskSeq = taskItemInfo[0]
    uuid = taskItemInfo[1]
    clearTaskSql = """DELETE from `wx_task_manage`
                        where taskSeq < %s
                        and actionType = 5
                        and `status` = 1
                        and uuid = \'%s\'""" %(taskSeq,uuid)
    mySqlUtil.execSql(clearTaskSql)

# if __name__ == '__main__':
#     import uiautomator2 as u2
#     u2Con = u2.connect('127.0.0.1:21533')
#     while True:
#         print('sss')
#         logger = ''
#         taskItemInfo = (1530527705928, '417b5701-5cd2-11e8-83ff-000e1e4932e0', 5, '127.0.0.1', '21533', '13112926341')
#         action(logger, u2Con, taskItemInfo)
#         time.sleep(0.5)
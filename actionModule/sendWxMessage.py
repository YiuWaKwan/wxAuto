import base64
import traceback
from tools import wxUtil, common, redisUtil
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
from lib.WxElementConf import WxElementConf
import emoji
import datetime, random
from urllib import request

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/sendWxMessage.log')
# 初始化config
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)
WxElementConf = WxElementConf(logger)

devId = confAllItems.getOneOptions('devInfo', 'dev')


def send_text(u2conn, wx_message):
    # d(resourceId="com.tencent.mm:id/ac8").set_text("hahah ")
    u2conn(resourceId="" + WxElementConf.set_message_content + "").set_text("" + wx_message + "")
    time.sleep(0.5)
    # d(resourceId="com.tencent.mm:id/acd").click()
    u2conn(resourceId="" + WxElementConf.send_message + "").click_exists(timeout=10.0)

def statusRecordAction(taskSeq, status, mySqlUtil, remarks=""):
    '''
    进行状态记录
    :param taskSeq:
    :param status:
    :return:
    '''
    if remarks == "#":
        remarks = "执行成功"
    else:
        str(remarks).replace("'", "")

    #logger.info("状态记录 by taskSeq: %s, status: %s, remark: %s" % (taskSeq, status, remarks))
    startTimeCheckSql = """SELECT startTime from wx_task_manage
        where taskSeq = \'%s\'""" % (taskSeq)
    # print(startTimeCheckSql)

    try:
        startTimeCheckRet = mySqlUtil.getData(startTimeCheckSql)
        if startTimeCheckRet[0][0] is None:
            sql = """UPDATE wx_task_manage
                set status = %s,startTime = now(),remarks = \"%s\" 
                where taskSeq = %s""" % (status, remarks, taskSeq)
        else:
            sql = """UPDATE wx_task_manage
                set status = %s,endTime = now(),remarks = \"%s\"
                where taskSeq = %s""" % (status, remarks, taskSeq)
        mySqlUtil.execSql(sql)
    except (Exception) as e:
        logger.warn(traceback.format_exc())

def fastInputConfirm(u2ConStart):
    '''
    切换界面已激活快速输入
    :param u2ConStart:
    :return:
    '''
    dealtime = time.time()
    while time.time() - dealtime <= 10:
        time.sleep(0.8)
        if u2ConStart(resourceId="com.github.uiautomator:id/keyboard").exists or any(
                u2ConStart(resourceId="com.github.uiautomator:id/keyboard")):
            break
        else:
            wxUtil.clickById(u2ConStart, WxElementConf.biaoqing)
            # u2ConStart.set_fastinput_ime(True)  # 切换成FastInputIME输入法

def textAction(u2ConStart,wxNameReal, taskItemList,mySqlUtil, wx_main_id, wx_id,devName,operViewName,actType):
    textTaskSeqByXposedList = {}
    textTaskList = []
    remarks = '#'
    for taskItem in sorted(taskItemList):
        taskSeq = taskItem[0]
        content = taskItem[1]
        noticeName = taskItem[2]
        msgId = taskItem[4]
        getResult = redisUtil.publishMessage(u2ConStart, wx_main_id, "send_message", "%s:~:%d#^#%s#^#%s#^#%s#^#%s#^#%s"
                          % (wx_main_id, taskSeq, wx_id, base64.b64encode(content.encode('utf-8')),
                             noticeName, msgId, actType),  20, '')
        if "ok" != getResult:
            common.messageNotice(wx_main_id, wx_id, getResult, taskSeq, mySqlUtil)
            logger.error("%s|%s|%s|发送消息|%s|信息发送失败" % (operViewName,taskSeq, devName, taskItem[1]))
            return (2, getResult)
        else:
            logger.info("%s|%s|%s|发送消息|%s" % (operViewName,taskSeq, devName, taskItem[1]))
            return (2, "定时消息广播成功")
        # try:
        #     if noticeName == '#NOTICENAMEPASS':
        #         textTaskSeqByXposedList[taskSeq] = [3, '#', msgId]
        #         textTaskList.append(str(taskSeq))
        #     else:  # 有@
        #         msg = wxUtil.jumpToCurrentWx(u2ConStart, wxNameReal)
        #         # 反馈到前台
        #         if msg != "":
        #             msgId = round(time.time() * 1000 + random.randint(100, 999))
        #             common.messageNotice(wx_main_id, wx_id, "消息发送失败：" + msg, msgId, mySqlUtil)
        #         if wxUtil.elementExistById(u2ConStart, WxElementConf.RC_Voice_Say):
        #             if wxUtil.getTextById(u2ConStart, WxElementConf.RC_Voice_Say) == "按住 说话":
        #                 wxUtil.clickById(u2ConStart, WxElementConf.RC_Change_Voice)
        #         time.sleep(0.3)
        #         wxUtil.clickById(u2ConStart, WxElementConf.set_message_content)  # 点击输入框
        #
        #         u2ConStart.set_fastinput_ime(False)  # 切换成正常的输入法
        #         time.sleep(0.1)
        #         u2ConStart.set_fastinput_ime(True)  # 切换成FastInputIME输入法
        #
        #         breakNum = 3
        #         atNum = 0
        #         while True:
        #             wxUtil.clearTextById(u2ConStart, WxElementConf.set_message_content)  # 清理输入框
        #             if breakNum == 0:
        #                 status = 3
        #                 remarks = "@操作无法正确完成"
        #                 break
        #             for noticeNameItem in noticeName.split('|'):
        #                 u2ConStart.send_keys("@")  # adb广播输入
        #                 time.sleep(0.5)
        #                 # 查找用户
        #                 if wxUtil.elementExistByText(u2ConStart, WxElementConf.at_nickname, u"%s" % (noticeNameItem)):
        #                     wxUtil.clickByText(u2ConStart, WxElementConf.at_nickname, u"%s" % (noticeNameItem))
        #                     atNum += 1
        #                 else:
        #                     wxUtil.clickById(u2ConStart, WxElementConf.at_search)
        #                     u2ConStart.send_keys(noticeNameItem)
        #                     # wxUtil.setTextById(u2ConStart, WxElementConf.searchText, u"%s" % (noticeNameItem))
        #                     if wxUtil.elementExistByText(u2ConStart, WxElementConf.at_nickname,
        #                                                  u"%s" % (noticeNameItem)):
        #                         wxUtil.clickByText(u2ConStart, WxElementConf.at_nickname, u"%s" % (noticeNameItem))
        #                         atNum += 1
        #                     elif wxUtil.elementExistById(u2ConStart, WxElementConf.at_nickname):
        #                         count = wxUtil.getCountById(u2ConStart, WxElementConf.at_nickname)
        #                         if count == 1:
        #                             wxUtil.clickById(u2ConStart, WxElementConf.at_nickname)
        #                         elif count > 1:
        #                             wxUtil.clickByIdAndNum(u2ConStart, WxElementConf.at_nickname, 0)
        #                     else:  # @找不到正确的成员
        #                         common.messageNotice(wx_main_id, wx_id,
        #                                              "@%s 在群里找不到该名字，或者该群友已改昵称，请刷新好友后再重试" % noticeNameItem, msgId,
        #                                              mySqlUtil)
        #                         wxUtil.clickById(u2ConStart, WxElementConf.back_to_at_button)  # 查询结果界面返回
        #                         wxUtil.clickById(u2ConStart, WxElementConf.back_to_chat_button)  # 返回到聊天界面
        #                 fastInputConfirm(u2ConStart)
        #                 time.sleep(0.5)
        #             fastInputConfirm(u2ConStart)
        #             u2ConStart.send_keys(content)
        #             time.sleep(0.2)
        #             insertMsg = wxUtil.getTextById(u2ConStart, WxElementConf.set_message_content)
        #             if insertMsg.count('@') >= atNum and content in insertMsg:
        #                 wxUtil.clickById(u2ConStart, WxElementConf.send_message)
        #                 status = 4
        #                 break
        #             else:
        #                 breakNum -= 1
        #         u2ConStart.set_fastinput_ime(False)  # 切换成正常的输入法
        #     # 任务状态回收
        # except Exception as e:
        #     remarks = e
        #     status = 3
        #     noticeContent = ""
        #     if noticeName != '#NOTICENAMEPASS':
        #         for noticeNameItem in noticeName.split('|'):
        #             noticeContent = "%s@%s " % (noticeContent, noticeNameItem)
        #     common.messageNotice(wx_main_id, wx_id, "消息（%s%s）发送失败" % (noticeContent, content), msgId, mySqlUtil)
        #     u2ConStart.set_fastinput_ime(False)  # 切换成正常的输入法
        # finally:
        #     if taskSeq not in textTaskSeqByXposedList.keys():
        #         statusRecordAction(taskSeq, status, mySqlUtil, remarks)
        # statusRecordAction(taskSeq, 2, mySqlUtil, "#")
        #

    #发送到app处理
    # textTaskCount = len(textTaskList)
    # logger.info("发送%d条消息"%textTaskCount)
    # if textTaskCount > 0:
    #     getResult = common.publishMessage(u2ConStart, wx_main_id, 'send_message', "%s:~:'%s'" % (wx_main_id,"','".join(textTaskList)), textTaskCount * 10, '')
    #     if "失败" == getResult or "超时" == getResult:
    #         for taskSeqHere in textTaskSeqByXposedList:
    #             msgIdHere = textTaskSeqByXposedList[taskSeqHere][2]
    #             statusRecordAction(taskSeqHere, 3, mySqlUtil, "网络异常")
    #             common.messageNotice(wx_main_id, wx_id, "信息发送失败", msgIdHere, mySqlUtil)
    # logger.info("发送成功")


def fileDownload(taskItemList, u2ConStart, mySqlUtil):
    resultRemarks = []
    #清理模拟器文件
    u2ConStart.adb_shell("rm -rf  /storage/sdcard0/tencent/MicroMsg/Download/*")
    for taskItem in taskItemList:
        taskSeq = taskItem[0]
        fileName = taskItem[1].split('|')
        msgId = taskItem[4]
        if len(fileName) == 2:
            targetFileName = 'data/%s' % fileName[0]
            statusRecordAction(taskSeq, 2, mySqlUtil, "#")
            try:
                #下载文件
                fileObj = request.urlopen(fileName[1])
                fileContent = fileObj.read()
                with open(targetFileName, 'ab+') as f:#生成本地文件
                    f.write(fileContent)
                #推送到模拟器
                u2ConStart.push(targetFileName, '/storage/sdcard0/tencent/MicroMsg/Download/')
                #刷新文件时间
                u2ConStart.adb_shell('touch /storage/sdcard0/tencent/MicroMsg/Download/%s' % fileName[0])
                #删除本地文件
                os.remove(targetFileName)
                resultRemarks.append((taskSeq, 4, "#", msgId))
            except Exception as e:
                logger.warn(traceback.format_exc())
                resultRemarks.append((taskSeq, 3, "网络异常，文件从文件服务器下载失败：%s" % fileName[1], msgId))
        else:
            resultRemarks.append((taskSeq, 3, "聊天内容格式不正确", msgId))
    return resultRemarks

#把下载文件目录中的文件都发出去
def sendAllFileInDownLoad(u2ConStart):
    deadTime = time.time() + 60
    while deadTime - time.time() > 0:
        if wxUtil.elementExistByText(u2ConStart,WxElementConf.chat_objectsend, u"文件"):  #点击文件菜单
            wxUtil.clickByText(u2ConStart, WxElementConf.chat_objectsend, u"文件")
            break
        elif wxUtil.elementExistByText(u2ConStart,WxElementConf.chat_objectsend, u"相册"):
            u2ConStart(resourceId=WxElementConf.chat_objectsend, text=u"位置").drag_to(
                resourceId=WxElementConf.chat_objectsend, text=u"相册", duration=0.25)  # 往左拖动，找到文件按钮
        elif wxUtil.elementExistById(u2ConStart, WxElementConf.chat_addbutton):
            wxUtil.clickById(u2ConStart, WxElementConf.chat_addbutton)    #点击加号打开功能菜单
        else:
            wxUtil.clickById(u2ConStart, WxElementConf.change_to_keyboard) #切换输入

    deadTime1 = time.time() + 60
    while deadTime1 - time.time() > 0:
        if wxUtil.getTextById(u2ConStart, WxElementConf.windowname) == "	手机存储":
            wxUtil.clickById(u2ConStart, WxElementConf.file_button) #点击左下角按钮
            wxUtil.clickByText(u2ConStart, WxElementConf.file_button_item, u"微信文件") #切换为微信文件
        elif wxUtil.getTextById(u2ConStart, WxElementConf.windowname) == "微信文件":
            fileCount = wxUtil.getCountById(u2ConStart, WxElementConf.checkbox) #获取可选文件数
            for fileNum in range(0, fileCount): #按顺序选择文件
                wxUtil.clickByClassAndNum(u2ConStart, WxElementConf.checkbox, "android.widget.CheckBox", fileNum)
            wxUtil.clickById(u2ConStart, WxElementConf.send_file)         #发送按钮
            wxUtil.clickById(u2ConStart, WxElementConf.oper_confirm)      #确认按钮
            break

#发送文件
def fileAction(u2ConStart, msg, taskItemList, mySqlUtil, wx_main_id, wx_id):
    if msg == "":
        # 下载文件并推送到模拟器
        resultRemarks = fileDownload(taskItemList, u2ConStart, mySqlUtil)

        isSend = False
        for taskInfo in resultRemarks:
            if taskInfo[1] == 4:
                isSend = True
            else:
                common.messageNotice(wx_main_id, wx_id, "消息发送失败："+taskInfo[2], taskInfo[3], mySqlUtil)
        if isSend:
            # 把下载文件目录种的文件都发出去
            sendAllFileInDownLoad(u2ConStart)

        for taskInfo in resultRemarks:
            #taskSeq = taskInfo[0]
            status = taskInfo[1]
            remarks = taskInfo[2]
            #statusRecordAction(taskSeq, status, mySqlUtil, remarks)
            return (status, remarks)
    else:
        # for taskItem in sorted(taskItemList):
        #     taskSeq = taskItem[0]
        #     statusRecordAction(taskSeq, 3, mySqlUtil, msg)
        return (3, msg)

# def picAction(u2ConStart, taskItemList, mySqlUtil, wx_main_id, wx_id):
#     textTaskSeqByXposedList = {}
#     textTaskList = []
#     for taskItem in sorted(taskItemList):
#         taskSeq = taskItem[0]
#         msgId = taskItem[4]
#         statusRecordAction(taskSeq, 2, mySqlUtil, "#")
#         textTaskSeqByXposedList[taskSeq] = [3,'#',msgId]
#         textTaskList.append(str(taskSeq))
#
#     textTaskCount = len(textTaskList)
#     logger.info("发送%d条消息" % textTaskCount)
#
#     if textTaskCount > 0:
#         getResult = common.publishMessage(u2ConStart, wx_main_id, 'send_message',
#                                           "%s:~:'%s'" % (wx_main_id, "','".join(textTaskList)), textTaskCount * 10, '')
#         if "失败" == getResult:
#             for taskSeqHere in textTaskSeqByXposedList:
#                 msgIdHere = textTaskSeqByXposedList[taskSeqHere][2]
#                 statusRecordAction(taskSeqHere, 3, mySqlUtil, "网络异常")
#                 common.messageNotice(wx_main_id, wx_id, "信息发送失败", msgIdHere, mySqlUtil)
#     logger.info("发送成功")

def taskDispatch(taskSeq, u2ConStart, wx_main_id, wx_id, taskInfo, mySqlUtil, type, msgId,devName,operViewName,taskType):

    sql = """select trim(remark) from wx_friend_rela where wx_main_id = '%s' and wx_id = '%s' 
                """ % (wx_main_id, wx_id)
    wx_name = mySqlUtil.getData(sql)
    if wx_name:
        wx_name_real = emoji.emojize(wx_name[0][0])

        if '1' == type :
            if taskType in [23,24]:
                return textAction(u2ConStart, wx_name_real, taskInfo, mySqlUtil, wx_main_id, wx_id,devName,operViewName,type)
            else:
                return (3, "不再通过这种方式发送文本消息")  # 暂时屏蔽

        if '2' == type or '7' == type:
            if taskType in [23,24]:
                return textAction(u2ConStart, wx_name_real, taskInfo, mySqlUtil, wx_main_id, wx_id,devName,operViewName,type)
            else:
                return (3, "不再通过这种方式发送文本消息")  # 暂时屏蔽
        if '3' == type:
            # 跳转到当前聊天页面
            msg = wxUtil.jumpToCurrentWx(u2ConStart, wx_name_real)
            # 反馈到前台
            if msg != "":
                common.messageNotice(wx_main_id, wx_id, "消息发送失败：" + msg, msgId, mySqlUtil)
            return fileAction(u2ConStart, msg, taskInfo, mySqlUtil, wx_main_id, wx_id)
    else:
        status = 3
        remarks = "未找到 %s（MAIN），%s 对应关系" %(wx_main_id,wx_id)
        statusRecordAction(taskSeq, status, mySqlUtil, remarks)
        common.messageNotice(wx_main_id, wx_id, "消息发送失败：找不到好友关系", msgId, mySqlUtil)
        return (status, remarks)

def action(logger, u2ConStart, taskItemInfo, mySqlUtil,taskType):
    remarks = '#'
    try:
        # 获取基本信息
        # sql = """SELECT wx_main_id,wx_id,msgId  from wx_chat_task where taskSeq = \'%s\'""" %(taskItemInfo[0])
        # chatInfo = mySqlUtil.excSql(sql)
        # if chatInfo:
        #     wx_main_id = chatInfo[0][0]
        #     wx_id = chatInfo[0][1]
        #     msgId = chatInfo[0][2]
        # else:
        #     return (3, "微信聊天信息找不到")

        #把任务状态修正为1
        #sql = """update wx_task_manage set status = 1 where taskSeq = %s""" % taskItemInfo[0]
        #mySqlUtil.excSql(sql)

        # 获取一个类型
        # sql = """SELECT distinct type from wx_task_manage A, wx_chat_task B
        #           where A.taskSeq = B.taskSeq and actionType in (6,23,24)
        #                and A.status = 1 and unix_timestamp(now()) >= unix_timestamp(A.cronTime)
        #                and A.uuid = '%s' and B.wx_main_id = '%s' and B.wx_id = '%s'
        #        """ %(taskItemInfo[1], wx_main_id, wx_id)
        #
        # taskInfoList = mySqlUtil.excSql(sql)
        # if taskInfoList:
        #     type = taskInfoList[0][0];
        # else:
        #     common.messageNotice(wx_main_id, wx_id, "消息发送失败：微信聊天信息类型有误", msgId, mySqlUtil)
        #     return (3, "微信聊天信息类型有误")
        # 获取此类型的聊天记录 最多9条
        # sql = """SELECT B.taskSeq,B.content,B.noticeName,A.actionType, B.msgId from wx_task_manage A, wx_chat_task B
        #                   where A.taskSeq = B.taskSeq and actionType in (6,23,24)
        #                        and A.status = 1 and unix_timestamp(now()) >= unix_timestamp(A.cronTime)
        #                        and A.uuid = '%s' and B.wx_main_id = '%s' and B.wx_id = '%s' and B.type='%s'
        #       ORDER BY B.createTime limit 9""" % (taskItemInfo[1], wx_main_id, wx_id, type)
        sql="""SELECT B.taskSeq,B.content,B.noticeName,A.actionType, B.msgId, B.wx_main_id, B.wx_id , B.type 
                          from wx_task_manage A, wx_chat_task B
                           where A.taskSeq = B.taskSeq and A.taskSeq = '%s' """ % (taskItemInfo[0])
        taskInfoList = mySqlUtil.excSql(sql)
        infoDict = []
        for infoItem in taskInfoList:
            taskSeq = infoItem[0]
            content = infoItem[1]
            actionType = infoItem[3]
            msgId = infoItem[4]
            wx_main_id = infoItem[5]
            wx_id = infoItem[6]
            type = infoItem[7]
            if infoItem[2]:
                noticeName = infoItem[2]
            else:
                noticeName = "#NOTICENAMEPASS"

            infoDict.append((taskSeq, content, noticeName, actionType, msgId))

        (status, remarks) = taskDispatch(taskItemInfo[0], u2ConStart, wx_main_id, wx_id, infoDict, mySqlUtil, type, msgId, taskItemInfo[6],taskItemInfo[7],taskType)
    except Exception as e:
        remarks = e
        status = 3
        logger.warn(traceback.format_exc())

    return (status, remarks)

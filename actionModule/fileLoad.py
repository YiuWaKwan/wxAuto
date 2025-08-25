import re
import traceback

from tools import wxUtil, common, redisUtil
import random
import linecache
import time
import os, uuid, redis
import subprocess
import hashlib
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
from lib.WxElementConf import WxElementConf
import os
BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('randomChat.log')
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)
WxElementConf = WxElementConf(logger)

# 目录root
BASEDIR = os.getcwd()
ADBDIR = "/data/data/com.gz.pbs.copyfile/files/"

def md5File(devUin):
    hl = hashlib.md5()
    mm_uin = "mm" + devUin
    hl.update(mm_uin.encode(encoding='utf-8'))
    filePath = hl.hexdigest()
    return filePath

def videoAction(u2Con,fileName, timeLen, volumeBytesStr, filepath):
    actionStatus = -1
    timeLenStr = "0:00"
    min = int(int(timeLen) / 60)
    second = int(int(timeLen) % 60)
    if second < 10:
        timeLenStr = "%d:0%d" % (min, second)
    else:
        timeLenStr = "%d:%d" % (min, second)
    wxUtil.clickByText(u2Con, WxElementConf.chat_record_item, u"图片及视频")
    time.sleep(1)

    if wxUtil.elementExistById(u2Con, WxElementConf.chat_record_video_item):
        count = wxUtil.getCountByText(u2Con, WxElementConf.chat_record_video_item, timeLenStr)
        tryCount = 3
        while count == 0 and tryCount > 0:
            wxUtil.scrollUp(u2Con)
            count = wxUtil.getCountByText(u2Con, WxElementConf.chat_record_video_item, timeLenStr)
            tryCount = tryCount - 1

        for i in range(0, count):
            wxUtil.clickByTextClassAndNum(u2Con, WxElementConf.chat_record_video_item, timeLenStr, "android.widget.TextView", i)
            time.sleep(1)
            u2Con.press("back")#退出视频播放
            fileLoadFlag = checkDownLoadUtilTure(u2Con, filepath, fileName, volumeBytesStr)
            if fileLoadFlag == 1:
                return fileLoadFlag
    return 0

def pictureAction(u2Con,  filepath,filepath_new,filepath_third, fileName):
    wxUtil.clickByText(u2Con, WxElementConf.chat_record_item, u"图片及视频")

    if wxUtil.elementExistById(u2Con, WxElementConf.chat_record_video_pic_item, 1):#图片和视频选项
        time.sleep(0.5)
        count = wxUtil.getCountById(u2Con, WxElementConf.chat_record_video_pic_item) # 获取总数

        while count > 0: #从后往前检索，因为越后面的越新
            wxUtil.clickByIdAndNum(u2Con, WxElementConf.chat_record_video_pic_item, count - 1)
            if wxUtil.elementExistById(u2Con, WxElementConf.download_picture, 0.1):
                wxUtil.clickById(u2Con, WxElementConf.download_picture)
                time.sleep(0.1)
            u2Con.press("back") #退出视频播放
            count = count - 1
            check_result,fileName=checkFileExists(u2Con,  filepath, fileName)
            if not check_result:
                check_result, fileName_real = checkFileExists(u2Con, filepath_new, fileName)
                if check_result:
                    fileName=fileName_real
                    if check_result:
                        cmd1 = """mkdir /sdcard/copyfile/image2"""
                        u2Con.shell(cmd1)
                        cmd2 = "cp %s /sdcard/copyfile/image2/%s" % (filepath_new + fileName_real, fileName_real)
                        u2Con.shell(cmd2)
                    filepath = "/sdcard/copyfile/image2/"
                else:
                    check_result, fileName_real = checkFileExists(u2Con, filepath_third, fileName)
                    if check_result:
                        fileName = fileName_real
                        if check_result:
                            cmd1 = """mkdir /sdcard/copyfile/image2"""
                            u2Con.shell(cmd1)
                            cmd2 = "cp %s /sdcard/copyfile/image2/%s" % (filepath_third + fileName_real, fileName_real)
                            u2Con.shell(cmd2)
                        filepath = "/sdcard/copyfile/image2/"
            if check_result:
                time.sleep(2)#等待图片下载完成
                return fileName,filepath
    return -3,filepath

def fileAction(u2Con, fileName, viewName, volumeBytesStr):
    actionStatus = -1
    wxUtil.clickByText(u2Con, WxElementConf.chat_record_item, u"文件")
    wxUtil.setTextById(u2Con, WxElementConf.searchText, viewName)
    time.sleep(1)

    fileFindFlag = False
    viewName = str(viewName)
    if wxUtil.elementExistByText(u2Con, WxElementConf.chat_record_file_item, u"%s" % (viewName)):#根据id和名称检索文件存在
        wxUtil.clickByText(u2Con, WxElementConf.chat_record_file_item, u"%s" % (viewName))
        fileFindFlag = True
    elif '没有找到' in wxUtil.getTextById(u2Con, WxElementConf.searchErrorResult):
        if ' ' in viewName:
            wxUtil.setTextById(u2Con, WxElementConf.searchText, viewName.split(' ')[0])
        elif '\xa0'in viewName:
            wxUtil.setTextById(u2Con, WxElementConf.searchText, viewName.split('\xa0')[0])
        else:
            wxUtil.setTextById(u2Con, WxElementConf.searchText, viewName[:int(len(viewName)/2)])
        time.sleep(1)
        if wxUtil.elementExistByText(u2Con, WxElementConf.chat_record_file_item, u"%s" % (viewName)):
            wxUtil.clickByText(u2Con, WxElementConf.chat_record_file_item, u"%s" % (viewName))
            fileFindFlag = True

    # 截图
    # screenshotCommand = """python -m uiautomator2 screenshot 127.0.0.1:%s  data\screenshot\%s_27.jpg"""%(taskPort,taskSeq)
    # subprocess.check_output(screenshotCommand)
    if fileFindFlag:
        while True:
            time.sleep(1)
            if wxUtil.elementExistByText(u2Con, WxElementConf.oper_tips, u"文件已过期或已被清理"):
                # 文件已过期或已被清理
                actionStatus = -3
                break
            if wxUtil.elementExistByText(u2Con, WxElementConf.download_tips, u"继续下载"):
                wxUtil.clickByText(u2Con, WxElementConf.download_tips, u"继续下载")
            # 弹出框选择文件打开软件
            if wxUtil.elementExistById(u2Con, WxElementConf.open_file_choose):
                if wxUtil.elementExistById(u2Con, WxElementConf.oper_once):
                    wxUtil.clickById(u2Con, WxElementConf.oper_once)
            if wxUtil.elementExistById(u2Con, WxElementConf.open_file_button):#用其他应用打开文件按钮
                actionStatus = 1
                break
            # 跳转到文本打印界面， txt文件会出现这种情况
            if wxUtil.elementExistById(u2Con, WxElementConf.file_print):
                wxUtil.clickById(u2Con, WxElementConf.return_to_wx)

        # 获取后台数据容量
        if actionStatus == 1:
            timeGate = time.time()
            while True:
                try:
                    if time.time() - timeGate >= 30:
                        # 文件容量小于指定，下载错误
                        actionStatus = -2
                        break
                    findAdbCommand = """ls -l /sdcard/tencent/MicroMsg/Download|grep \'%s\'|awk \'{print $4}\'"""%(fileName)
                    output, exit_code = u2Con.shell(findAdbCommand)
                    if exit_code == 0:
                        if output.replace('\n',''):
                            fileVol = int(output.replace('\n',''))
                            if fileVol >= int(volumeBytesStr):
                                # mvCommand = "mv /sdcard/tencent/MicroMsg/Download/\'%s\' %s/%s"%(fileName, ADBDIR, newFileName)
                                # u2Con.shell(mvCommand)
                                actionStatus = 1
                                break
                    time.sleep(1)
                except Exception as e:
                    logger.error(traceback.format_exc())
    else:
        actionStatus = -4

    return actionStatus

def finish_download(mySqlUtil,msgId, wx_id, retUrl, state, wx_main_id):
    sql = """select content from wx_chat_info_his WHERE msgId='%s'  and wx_id='%s' and type in ('2','3','7') """ \
          % (msgId, wx_id)
    getRet = mySqlUtil.getData(sql)
    if getRet and len(getRet) > 0:
        contentList = getRet[0][0].split('|')
        if len(contentList) >= 6:#文件/视频
            contentList[4] = state
            if retUrl:
                contentList[5] = retUrl
            contentJoinStr = '|'.join(contentList)
            update_chat_his(mySqlUtil, msgId, wx_main_id, wx_id, contentJoinStr)
        elif len(contentList) >= 2:#图片
            contentList[1] = state
            if retUrl:
                contentList[0] = retUrl
            contentJoinStr = '|'.join(contentList)
            update_chat_his(mySqlUtil, msgId, wx_main_id, wx_id, contentJoinStr)

def update_chat_his(mySqlUtil,msgId, wx_main_id, wx_id, content):
    sql = """UPDATE wx_chat_info_his SET content='%s' WHERE msgId='%s' 
            and wx_main_id='%s' and wx_id='%s' and type in ('2', '3', '7') """ % (content, msgId, wx_main_id, wx_id)
    mySqlUtil.excSql(sql)

def compAction(mySqlUtil,msgId,actType,fileName,taskSeq,u2Con, wx_id, wx_main_id, file_path):
    remarks = "#"
    status = 3
    if actType == 1:
        message = "%s:~:%s%s#=#%s" % (wx_main_id, file_path, fileName, taskSeq)
        logger.info(message)
        getResult = redisUtil.publishMessageNew(u2Con, wx_main_id, "file_upload", message, 20, taskSeq)
        if "超时" == getResult:
            remarks=getResult
            common.messageNotice(wx_main_id, wx_id, "文件上传文件服务器超时", msgId, mySqlUtil)
            finish_download(mySqlUtil, msgId, wx_id, None, "3", wx_main_id)
        elif "失败" == getResult:
            remarks = getResult
            common.messageNotice(wx_main_id, wx_id, "网络异常文件处理失败", msgId, mySqlUtil)
            finish_download(mySqlUtil, msgId, wx_id, None, "3", wx_main_id)
        if '#=#' in getResult:
            getResult = getResult.split('#=#')
            retStatus = getResult[0]
            retSeq = getResult[1]
            retUrl = getResult[2]
            if str(taskSeq) == str(retSeq):
                if retStatus == 'ok':
                    finish_download(mySqlUtil, msgId, wx_id, retUrl, "1", wx_main_id)
                    status = 4
                else:
                    remarks = retUrl
                    finish_download(mySqlUtil, msgId, wx_id, None, "3", wx_main_id)
    else:
        remarks = "文件下载失败"
        finish_download(mySqlUtil, msgId, wx_id, None, "3", wx_main_id)

    return (status,remarks)

def openWxChatWindow(u2Con, wxName):
    wxNameFindFlag = False
    msg = wxUtil.jumpToCurrentWx(u2Con, wxName)
    # 反馈到前台
    if msg != "":
        return False

    # 三秒内找对端微信
    timeGate = time.time()
    while time.time() - timeGate <= 3:
        time.sleep(0 / 5)
        #打开聊天记录界面
        wxUtil.clickById(u2Con, WxElementConf.friend_more)
        while True:
            if wxUtil.elementExistByText(u2Con, WxElementConf.detail_title, u"查找聊天记录"):
                wxUtil.clickByText(u2Con, WxElementConf.detail_title, u"查找聊天记录")
                break
            else:
                wxUtil.scrollDown(u2Con)

        wxNameFindFlag = True
        break
    return wxNameFindFlag

def checkDownLoadUtilTure(u2Con, filepath, fileName, volumeBytes):
    timeGate = time.time()
    while True:
        if time.time() - timeGate >= 30:
            return -2
        # 查找文件是否已经下载下来
        findAdbCommand = """ls -l %s |grep \'%s\'|awk \'{print $4}\'""" % (filepath, fileName)
        output, exit_code = u2Con.shell(findAdbCommand)
        if exit_code == 0:
            if output is None or output == '':
                return 0
            if output.replace('\n', ''):
                fileVol = int(output.replace('\n', ''))
                if fileVol < int(volumeBytes):
                    None
                else:
                    # mvCommand = "cp %s%s %s" % (filepath, fileName, ADBDIR)
                    # u2Con.shell(mvCommand)
                    return 1
        else:
            return 0

def checkDownLoad(u2Con, filepath, fileName, volumeBytes):
    # 查找文件是否已经下载下来
    findAdbCommand = """ls -l %s |grep \'%s\'|awk \'{print $4}\'""" % (filepath, fileName)
    output, exit_code = u2Con.shell(findAdbCommand)
    if exit_code == 0:
        if output is None or output == '':
            return 0
        if output.replace('\n', ''):
            fileVol = int(output.replace('\n', ''))
            if fileVol < int(volumeBytes):
                return 0
            else:
                # mvCommand = "cp %s%s %s" % (filepath, fileName, ADBDIR)
                # u2Con.shell(mvCommand)
                return 1
    return 0

def checkFileExists(u2Con,  filepath, fileName):
    rr=re.compile(r'\S+\.')
    if '.' in fileName:
        fileName=str(rr.findall(fileName)[0]).replace(".","")
    # 查找文件是否已经下载下来
    findAdbCommand = """ls -l %s""" % filepath+fileName+".*"
    output, exit_code = u2Con.shell(findAdbCommand)
    if exit_code == 0:
        if "No such file or directory" in output or '.temp' == output[-5:]:
            return (0,fileName)
        else:
            rr_new = re.compile(fileName+r'\.\S+')
            fileName=str(rr_new.findall(output)[0])
        # mvCommand = "cp %s %s" % (filepath, ADBDIR)
        # u2Con.shell(mvCommand)
        return (1,fileName)
    return (0,fileName)

# 文件、视频
def fileLoadAction(logger, u2Con, taskItemInfo, mySqlUtil, fileLoadRet):
    '''
        文件下载点击
        :param u2Con:
        :param taskItemInfo:
        :return:
        '''
    remarks = '#'
    try:
        taskSeq = taskItemInfo[0]
        taskPort = taskItemInfo[4]

        wx_id = fileLoadRet[1]
        wxName = fileLoadRet[2]
        wxMd5Path = md5File(fileLoadRet[6])
        fileName = fileLoadRet[3]
        viewName = fileLoadRet[4]
        actType = fileLoadRet[5]
        volumeKbytes = fileLoadRet[7]
        volumeBytes = fileLoadRet[8]
        timeLen = fileLoadRet[9]
        devDir = fileLoadRet[10]
        msgId = fileLoadRet[11]
        wx_main_id = fileLoadRet[12]

        # 执行具体文件点击
        file_load_flag = 0
        new_file_name = fileName
        notice_head = ""
        filepath = "/sdcard/tencent/MicroMsg/Download/"
        if actType == 1:
            notice_head = "文件下载失败"
            if openWxChatWindow(u2Con, wxName):
                new_file_name = viewName
                # fileInfo = fileName.split(r".")
                # if len(fileInfo) >= 1:
                #     new_file_name = "%s.%s"% (uuid.uuid1(), fileInfo[-1])
                file_load_flag = fileAction(u2Con, fileName, viewName, volumeBytes)

            else:
                file_load_flag = -5
        elif actType == 2:
            notice_head = "视频下载失败"
            filepath = "/sdcard/tencent/MicroMsg/%s/video/"%wxMd5Path
            #查找文件是否已经下载下来
            file_load_flag = checkDownLoad(u2Con, filepath, fileName, volumeBytes)
            # if file_load_flag == 0:#app根目录
            #     file_load_flag = checkDownLoad(u2Con, ADBDIR, fileName, volumeBytes)
            if file_load_flag == 0:#重新点击下载
                if openWxChatWindow(u2Con, wxName):
                    file_load_flag = videoAction(u2Con, fileName, timeLen, volumeBytes, filepath)
                else:
                    file_load_flag = -5
        elif actType == 5:
            notice_head = "原图下载失败"
            logger.debug("开始查找文件")
            if len(fileName) <= 4:
                common.messageNotice(wx_main_id, wx_id, "%s图片名称不合法" % notice_head, msgId, mySqlUtil)
                return (3, "文件名不合法")
            filepath = "/sdcard/tencent/MicroMsg/%s/image2/%s/%s/" % (wxMd5Path, fileName[0:2], fileName[2:4])
            filepath_new = "/data/media/0/tencent/MicroMsg/%s/image2/%s/%s/" % (wxMd5Path, fileName[0:2], fileName[2:4])
            filepath_third = "/mnt/shell/emulated/0/tencent/MicroMsg/%s/image2/%s/%s/" % (wxMd5Path, fileName[0:2], fileName[2:4])
            #查找文件是否已经下载下来
            check_result,fileName_real=checkFileExists(u2Con, filepath, fileName)
            if not check_result:
                logger.debug("开始第二次查找文件")
                check_result, fileName_real = checkFileExists(u2Con, filepath_new, fileName)
                if check_result:
                    cmd1 = """mkdir /sdcard/copyfile/image2"""
                    u2Con.shell(cmd1)
                    cmd2="cp %s /sdcard/copyfile/image2/%s" %(filepath_new+fileName_real,fileName_real)
                    u2Con.shell(cmd2)
                    filepath="/sdcard/copyfile/image2/"
                else:
                    logger.debug("开始第三次查找文件")
                    check_result, fileName_real = checkFileExists(u2Con, filepath_third, fileName)
                    if check_result:
                        cmd1 = """mkdir /sdcard/copyfile/image2"""
                        u2Con.shell(cmd1)
                        cmd2 = "cp %s /sdcard/copyfile/image2/%s" % (filepath_third + fileName_real, fileName_real)
                        u2Con.shell(cmd2)
                        filepath = "/sdcard/copyfile/image2/"
            if fileName_real!=fileName:
                new_file_name=fileName_real
                fileName=fileName_real
            if check_result== True:
                file_load_flag = 1
            if file_load_flag == 0:
                if openWxChatWindow(u2Con, wxName):
                    file_load_flag,filepath = pictureAction(u2Con, filepath,filepath_new,filepath_third,fileName)
                    if file_load_flag != -3:
                        new_file_name = file_load_flag
                        file_load_flag = 1
                else:
                    file_load_flag = -5
        if file_load_flag == 1:
            logger.debug('下载文件')
            status, remarks = compAction(mySqlUtil, msgId, 1, new_file_name, taskSeq, u2Con, wx_id, wx_main_id, filepath)
        else:
            if file_load_flag == -1:
                remarks = notice_head
            elif file_load_flag == -2:
                remarks = '%s:因网络原因文件下载不了，请再试' % notice_head
            elif file_load_flag == -3:
                remarks = '%s:文件已过期或已被清理' % notice_head
            elif file_load_flag == -4:
                remarks = '%s:未找到指定文件或视频(%s)' % (notice_head, fileName)
            elif file_load_flag == -5:
                remarks = '群/好友(%s)不存在, 请刷新好友重试' % wxName
            else:
                remarks = notice_head
            logger.error(remarks)
            common.messageNotice(wx_main_id, wx_id, remarks, msgId, mySqlUtil)
            logger.debug('下载文件')
            compAction(mySqlUtil, msgId, 2, new_file_name, taskSeq, u2Con, wx_id, wx_main_id, filepath)
            status = 3
    except Exception as e:
        remarks = "文件下载出错：%s"%e
        logger.error(traceback.format_exc())
        status = 3
    return (status, remarks)

#链接
def linkAction(logger, u2Con, fileLoadRet, mySqlUtil):
    remarks = '#'
    status = 3
    try:
        wxName = fileLoadRet[2]
        targetName = fileLoadRet[3]
        content = fileLoadRet[4]
        msgId = fileLoadRet[11]
        if openWxChatWindow(u2Con, wxName):
            wxUtil.clickByText(u2Con, WxElementConf.chat_record_item, u"链接")
            wxUtil.setTextById(u2Con, WxElementConf.searchText, content)
            time.sleep(1)
            if wxUtil.elementExistByText(u2Con, WxElementConf.chat_record_file_item, u"%s" % (targetName)):
                wxUtil.clickByText(u2Con, WxElementConf.chat_record_file_item, u"%s" % (targetName))
                wxUtil.clickByDesc(u2Con, u"加入群聊")

                if wxUtil.elementExistById(u2Con, WxElementConf.remark_save_tips) and \
                        wxUtil.getTextById(u2Con, WxElementConf.remark_save_tips) == \
                        "你需要实名验证后才能接受邀请，可在“我”->“钱包”中绑定银行卡进行验证。":
                    wxUtil.clickById(u2Con, WxElementConf.oper_confirm)
                    common.messageNotice(fileLoadRet[12], fileLoadRet[1], '加入失败：需要实名验证后才能加入群', msgId, mySqlUtil)
                    return (3, '未实名验证')
                else:
                    return (4, '加入成功')
        else:
            common.messageNotice(fileLoadRet[12], fileLoadRet[1], '群/好友(%s)不存在' % wxName, msgId, mySqlUtil)
            return (3, '未能找到对应微信号')
    except Exception as e:
        remarks = "邀请加入群出错：%s"%e
        logger.error(traceback.format_exc())
        common.messageNotice(fileLoadRet[12], fileLoadRet[1], '加入失败：需要实名验证后才能加入群', msgId, mySqlUtil)
        status = 3
    return (status, remarks)


# 聊天记录入库
def chatRecordAction(logger, u2Con, taskItemInfo, mySqlUtil):
    remarks = '#'
    status = 4
    try:
        taskSeq = taskItemInfo[0]
        taskUuid = taskItemInfo[1]
        fileLoadInfoSql = """SELECT taskSeq,objectId,objectName,fileName,viewName,type,
                                (SELECT uin from wx_account_info where uuid='%s') as uin,
                                volumeKbytes,volumeBytes,timeLen,
                                (select devDir from wx_machine_info where uuid ='%s' limit 1) as devDir,
                                msgId, 
                                (select wx_id from wx_account_info where uuid ='%s') as wx_main_id
                                from wx_fileLoad_task
                                where taskSeq = '%s'""" %(taskUuid, taskUuid, taskUuid, taskSeq)

        rs = mySqlUtil.getData(fileLoadInfoSql)
        if rs and len(rs) > 0:
            fileLoadRet = rs[0]
        else:
            fileLoadRet = []

        if fileLoadRet is None or len(fileLoadRet) == 0:
            return (3, "字表记录为空，taskSeq:%s" % taskSeq)
        actType = fileLoadRet[5]
        #if actType == 1 or actType == 2 or actType == 5:#文件和图片、视频下载
        if actType == 1 or actType == 2 :  # 文件和视频下载
            status, remarks = fileLoadAction(logger, u2Con, taskItemInfo, mySqlUtil, fileLoadRet)
        elif actType == 3: #加入群聊
            status, remarks = linkAction(logger, u2Con, fileLoadRet, mySqlUtil)
        elif actType == 4: #交易操作
            None
        else:
            status = 3
            remarks = "无效类型"
    except Exception as e:
        remarks = "操作失败：%s"%e
        logger.error(traceback.format_exc())
        status = 3
    return (status, remarks)
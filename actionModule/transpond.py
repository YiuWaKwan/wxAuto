import traceback

from tools import wxUtil, common
import random
import linecache
import time
import os, uuid
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
wxElementConf = WxElementConf(logger)

# 目录root
BASEDIR = os.getcwd()
ADBDIR = "/data/data/com.gz.pbs.copyfile/files/"

def md5File(devUin):
    hl = hashlib.md5()
    mm_uin = "mm" + devUin
    hl.update(mm_uin.encode(encoding='utf-8'))
    filePath = hl.hexdigest()
    return filePath

def send(u2Con, namelist, link_title):
    remarks = ""
    error_name_list = []
    wxUtil.clearTextById(u2Con, WxElementConf.searchText)
    wxUtil.setTextById(u2Con, WxElementConf.searchText, link_title)  # 查找音乐或链接
    if wxUtil.elementExistByText(u2Con, WxElementConf.chat_record_file_item, u"%s" % link_title, 1):
        time.sleep(0.5)
        wxUtil.longclickByText(u2Con, WxElementConf.chat_record_file_item, u"%s" % link_title)  # 长按记录
        if wxUtil.elementExistByText(u2Con, WxElementConf.transpond_to_friend, u"发送给朋友", 0.5):
            wxUtil.clickByText(u2Con, WxElementConf.transpond_to_friend, u"发送给朋友")  # 点击发送给朋友选项
            time.sleep(0.5)
            wxUtil.clickById(u2Con, WxElementConf.multi_select)  # 点击多选按钮
            for name in namelist:
                wxUtil.setTextById(u2Con, wxElementConf.G_Friend_Search, name)  # 设置搜索框的文本
                if wxUtil.elementExistByText(u2Con, wxElementConf.fileHelper, u"%s" % name, 0.5):
                    wxUtil.clickByText(u2Con, wxElementConf.fileHelper, u"%s" % name)
                else:
                    wxUtil.clearTextById(u2Con, wxElementConf.G_Friend_Search)  # 清理搜索框的文本
                    error_name_list.append(name)
            if len(error_name_list) < len(namelist):
                wxUtil.clickById(u2Con, WxElementConf.fabiao)  # 点击提交按钮
                if wxUtil.elementExistById(u2Con, wxElementConf.oper_confirm, 0.5):
                    wxUtil.clickById(u2Con, wxElementConf.oper_confirm)
                else:
                    remarks = '转发(%s)失败：流程不正确' % link_title
            else:
                u2Con.press("back")  # 点击返回按钮
        else:
            remarks = '转发(%s)失败：找不到发送给朋友的按钮' % link_title
    else:
        remarks = '转发(%s)失败：聊天记录找不到' % link_title
    return (remarks, error_name_list)

#转发链接
def linkAction(logger, u2Con, transpondRet, mySqlUtil, menu_name):
    remarks = '#'
    status = 3
    error_list = []
    success_num = 0
    try:
        wxName = transpondRet[7]
        link_title = transpondRet[4]
        msgId = transpondRet[6]
        transpond_name = transpondRet[5]
        transpondlist = transpond_name.split(",")
        if wxUtil.openWxChatWindow(u2Con, wxName):
            wxUtil.clickByText(u2Con, WxElementConf.chat_record_item, menu_name) # 打开音乐或链接界面
            #循环发送从这里开始
            namelist = []
            for name in transpondlist:
                namelist.append(name)
                if len(namelist) == 9:
                    (temp_remark, error_name_list) = send(u2Con, namelist, link_title)
                    if len(error_name_list) > 0:
                        for errorname in error_name_list:
                            error_list.append(errorname)
                    if len(temp_remark) > 0:
                        remarks = temp_remark
                        break
                    else:
                        success_num += len(namelist) - len(error_name_list)
                    namelist = []

            if len(namelist) > 0:
                (temp_remark, error_name_list) = send(u2Con, namelist, link_title)
                if len(error_name_list) > 0:
                    for errorname in error_name_list:
                        error_list.append(errorname)
                if len(temp_remark) > 0:
                    remarks = temp_remark
                else:
                    success_num += len(namelist) - len(error_name_list)
        else:
            remarks = '转发(%s)失败：发送人(%s)不存在，请刷新好友' % (link_title, wxName)

        if remarks != '#':
            if success_num > 0:
                remarks = "%s, 共需转发%d个好友，已成功转发%d个好友" % (remarks, len(transpondlist), success_num)
            common.messageNotice(transpondRet[1], transpondRet[2], remarks, msgId, mySqlUtil)
        else:
            status = 4
        if len(error_list) > 0:
            common.messageNotice(transpondRet[1], transpondRet[2],
                                 "转发信息(%s):成功发送%d个好友, 以下好友检索不到：%s,请刷新好友重试!" %
                                 (link_title, success_num, ','.join(error_list)),  msgId, mySqlUtil)
    except Exception as e:
        logger.error(traceback.format_exc())
        common.messageNotice(transpondRet[1], transpondRet[2], '转发(%s)失败：未知错误' % link_title, msgId, mySqlUtil)
        status = 3
    return (status, remarks)


# 聊天记录入库
def transpondAction(logger, u2Con, taskItemInfo, mySqlUtil):
    remarks = '#'
    status = 4
    try:
        taskSeq = taskItemInfo[0]
        sql = """SELECT taskSeq, wx_main_id , wx_id, type, content link_title, transpondName, msgId, 
                (select remark from wx_friend_rela where wx_main_id = t.wx_main_id and wx_id = t.wx_id) wxName
                from wx_transpond_task t where taskSeq = '%s'""" % taskSeq

        rs=mySqlUtil.getData(sql)
        if len(rs)>0:
            transpondRet = rs[0]
        else:
            transpondRet=[]

        if transpondRet is None or len(transpondRet) == 0:
            return (3, "字表记录为空，taskSeq:%s" % taskSeq)

        type = transpondRet[3]
        if type == '9' :#链接转发
            status, remarks = linkAction(logger, u2Con, transpondRet, mySqlUtil, "链接")
        elif type == '12' :#链接转发
            status, remarks = linkAction(logger, u2Con, transpondRet, mySqlUtil, "音乐")
        else:
            common.messageNotice(transpondRet[1], transpondRet[2], '转发(%s)失败：消息类型有误' % transpondRet[4], transpondRet[6], mySqlUtil)
    except Exception as e:
        remarks = "转发失败：%s"%e
        logger.error(traceback.format_exc())
        status = 3
    return (status, remarks)
# -*- coding: utf-8 -*-

# @Time    : 2018/6/26 10:54
# @Author  : xiaoguobiao
# @File    : getWxFriendList.py
import hashlib
import os, urllib
import time, random
import subprocess
import traceback

#from actionModule.login import push_conf_file, update_wx_oper_wx
from lib.WxElementConf import WxElementConf
from tools import common,wxUtil
from lib.ModuleConfig import ConfAnalysis
from lib.FinalLogger import getLogger
BASEDIR = os.getcwd()
# 初始化logger
loggerFIle = './log/multiTask.log'
logger = getLogger(loggerFIle)
loggerFIle_err = './log/multiTask_err.log'
errlogger = getLogger(loggerFIle_err)
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)
user_list = confAllItems.getOneOptions("alarm", "user_list")
alarm_server = confAllItems.getOneOptions("alarm", "alarm_server")
dev_id = confAllItems.getOneOptions("devInfo", "dev")
#向模拟器下发刷新好友任务的文件
from tools.wxUtil import clickByDesc, setTextById, clickById, elementExistByText, clickByText, \
     getCountByText


# def get_wx_friend_info(logger, u2conn, taskItemInfo, mySqlUtil):
#     status = 4
#     remark = '#'
#     try:
#         port = taskItemInfo[4]
#         uuid = taskItemInfo[1]
#         sql = "select uin, db_passwd, wx_id, wx_login_id, is_first_time, wx_name from wx_account_info where uuid='" + str(
#             uuid) + "' and uin !='' and db_passwd !=''"
#         wx_info = mySqlUtil.getData(sql)
#         if wx_info and len(wx_info) > 0:
#             uin = wx_info[0][0]
#             db_passwd = wx_info[0][1]
#             wx_id = wx_info[0][2]
#             wx_login_id = wx_info[0][3]
#             is_first_time = wx_info[0][4]
#             wx_name = wx_info[0][5]
#             taskSeq = taskItemInfo[0]
#             #uuidTask = taskItemInfo[1]
#             #taskType = taskItemInfo[2]
#             devName = taskItemInfo[6]
#             operViewName = taskItemInfo[7]
#             #logger.info("%s|%s|%s|刷新好友信息开始" % (operViewName,taskSeq, devName))
#
#             if is_first_time == '1':
#                 push_conf_file('0', port, db_passwd, uin, uuid, mySqlUtil, 0)
#                 wxUtil.appStart(u2conn, logger)
#                 time.sleep(3)
#                 sql = "select wx_id, is_first_time from wx_account_info where uuid='" + str(uuid) + "'"
#                 tmp_info = mySqlUtil.getData(sql)
#                 if tmp_info[0][1] == '0':#更新微信id
#                     wx_id = tmp_info[0][0]
#                 else:
#                     # 生成重刷好友任务
#                     remark = "%s|%s|%s|刷新好友信息|微信微信登陆账号%s首次登陆微信id获取失败，正在重试" % (
#                     operViewName, taskSeq, devName,wx_login_id)
#                     logger.info(remark)
#                     alarm(remark)
#                     reFlushFriend(mySqlUtil, uuid)
#                     return (3, "微信id获取失败")
#             else:
#                 push_conf_file(wx_id, port, db_passwd, uin, uuid, mySqlUtil, 0)
#
#             getResult = common.publishFlushFriend(u2conn, wx_id, "flush_friend", "%s:~:0#=#0" % wx_id, 60, '')
#             if "超时" == getResult:
#                 status = 3
#                 remark="%s|%s|%s|刷新好友信息|微信[%s-%s]刷新好友超时，正在重试" % (operViewName,taskSeq, devName, wx_id, wx_name)
#                 # 生成重刷好友任务
#                 alarm(remark)
#                 reFlushFriend(mySqlUtil, uuid)
#             elif "失败" == getResult:
#                 status = 3
#                 #remark = "网络异常"
#                 # 生成重刷好友任务
#                 remark="%s|%s|%s|刷新好友信息|微信[%s-%s]刷新好友网络异常，正在重试" % (operViewName,taskSeq, devName, wx_id, wx_name)
#                 alarm(remark)
#                 reFlushFriend(mySqlUtil, uuid)
#             elif getResult == 'ok':
#                 status = 4
#                 remark = "刷新好友成功"
#                 update_wx_oper_wx(mySqlUtil, wx_login_id, logger)
#             else:
#                 status = 3
#                 remark = str(getResult)
#                 logger.info(getResult)
#         else:
#             remark = "微信状态不正常"
#             status = 3
#         logger.info("%s|%s|%s|刷新好友信息结束|%s" % (operViewName, taskSeq, devName,remark))
#
#     except(Exception) as e:
#         logger.warn(traceback.format_exc())
#         status = 3
#         remark = e
#     return (status, remark)

def reFlushFriend(mySqlUtil, uuid):
    sql = "insert into wx_task_manage(taskSeq,uuid,actionType,createTime,priority,status)value (%d,'%s','9',now(),'5','1')" \
          % (round(time.time() * 1000 + random.randint(100, 999)), uuid)
    mySqlUtil.excSql(sql)

def alarm(msg):
    msg = urllib.parse.quote(msg)
    warn_msg = "%s?msg=%s&type=2&user=%s&creator=maizq" % (alarm_server, msg, user_list)
    warning(warn_msg)

def warning(url):
    http_client=urllib.request.urlopen(url, timeout = 5)
    print(http_client.read())
    return http_client.read()

# 修改微信好友备注
#如果通过微信ID能找到，就直接根据微信ID来修改
#如果微信ID还没修改过，则根据微信备注查找，如果找到的结果唯一，则修改备注
#如果微信备注找到不是唯一的，则放弃修改
def change_friend_remark(logger, u2conn, taskItemInfo, mySqlUtil):
    wxElementConf = WxElementConf(logger)
    remark = "#"
    status=3
    try:
        logger.info("开始修改好友备注："+str(taskItemInfo[6]))
        taskSeq = taskItemInfo[0]
        query_friend_sql = "select wx_main_id,wx_friend_id,wx_name from wx_friend_refresh where taskSeq = '%s'" % taskSeq
        result = mySqlUtil.getData(query_friend_sql)
        if len(result) > 0:
            wx_main_id = result[0][0]
            wx_friend_id = result[0][1]
            wx_friend_nickname = result[0][2]
            if "'" in wx_friend_nickname:
                wx_friend_nickname = wx_friend_nickname.replace("'", "*")
            get_friend_remark = "select remark from wx_friend_rela where wx_main_id = '%s' and wx_id = '%s'" % (wx_main_id, wx_friend_id)
            rs=mySqlUtil.getData(get_friend_remark)
            friend_remark=""
            if len(rs)>0:
                friend_remark=rs[0][0]
            else:
                remark="没找到好友关系，请刷新好友后重试"
            clickByDesc(u2conn,u"搜索")
            readyFlag=False
            if wx_friend_id:
                setTextById(u2conn,wxElementConf.search_content_box,wx_friend_id)#输入wxid来搜索好友
                time.sleep(1)
                wxidStr="微信号: "+str(wx_friend_id)
                if elementExistByText(u2conn,wxElementConf.search_result_with_wxid,wxidStr):#存在这个微信好友
                    clickByText(u2conn,wxElementConf.search_result_with_wxid,wxidStr) #点开这个微信号
                    logger.info("通过微信ID找到此好友")
                    readyFlag=True
                else:
                    logger.info("通过微信号找不到好友，将通过微信备注来查找")
                if (not readyFlag) and friend_remark:
                    setTextById(u2conn, wxElementConf.search_content_box, friend_remark)  # 输入备注来搜索好友
                    time.sleep(1)
                    if elementExistByText(u2conn,wxElementConf.fileHelper,friend_remark):
                        if getCountByText(u2conn,wxElementConf.fileHelper,friend_remark)>1:
                            remark="存在多个备注相同的好友，无法准确修改该好友的备注"
                            readyFlag=False
                        else:
                            clickByText(u2conn,wxElementConf.fileHelper,friend_remark)
                            logger.info("通过备注找到唯一的好友")
                            readyFlag = True
                    else:
                        remark="没找到好友，请刷新好友后重试"
                        readyFlag = False
                if readyFlag:
                    clickById(u2conn, wxElementConf.user_more_button)
                    clickById(u2conn, wxElementConf.friend_page)
                    clickById(u2conn, wxElementConf.friend_more)
                    clickById(u2conn, wxElementConf.select_set_friend_remark)
                    time.sleep(0.5)
                    setTextById(u2conn, wxElementConf.set_friend_remark, wx_friend_nickname)
                    clickById(u2conn, wxElementConf.finish_update_remark)
                    update_remark_sql = "update wx_friend_rela set remark = '%s' where wx_main_id = '%s' and wx_id = '%s' " % (
                        wx_friend_nickname, wx_main_id, wx_friend_id)
                    logger.info(update_remark_sql)
                    mySqlUtil.excSql(update_remark_sql)
                    logger.info("修改好友备注成功！")
                    status = 4
            else:
                remark="此任务的好友微信号为空，无法继续运行"

        else:
            status = 3
            logger.info("没有好友备注信息，请核查！")
    except(Exception) as error:
        logger.exception(error)
        remark = error
    return (status, remark)
def push_task_file(port,type,obj_id,wx_id,uin,logger):  #type 0-4
    dm5_path = md5_file(uin)
    local_path="data/"+str(wx_id)+"/"
    file_name = local_path+"refresh_wx_info.task"
    if not os.path.exists(local_path):
        os.makedirs(local_path)
    file_obj = open(file_name, 'w')  # 若是'wb'就表示写二进制文件
    input_str=str(type)+';'+str(obj_id)
    file_obj.write(input_str)
    file_obj.close()
    judge_exists_cmd = "adb -s 127.0.0.1:%s shell ls -d /data/data/com.gz.pbs.copyfile/files/" % port
    judge_exists_ret = subprocess.Popen(judge_exists_cmd, shell=False, stdout=subprocess.PIPE).stdout.read()
    if "No such file or directory" in str(judge_exists_ret):
        logger.info("没有找到app路径，请安装app")
        return False
    else:
        push_command = "adb -s 127.0.0.1:%s push %s /data/data/com.gz.pbs.copyfile/files/" % (port, file_name)
        p = subprocess.Popen(push_command)
        p.wait()
        exc_cmd = "adb -s 127.0.0.1:%s shell chmod 777 /data/data/com.tencent.mm|" \
                  "chmod 777 /data/data/com.tencent.mm/MicroMsg|" \
                  "chmod 777 /data/data/com.tencent.mm/MicroMsg/%s|" \
                  "chmod 666 /data/data/com.tencent.mm/MicroMsg/%s/EnMicroMsg.db*|" \
                  "chmod 777 /data/data/com.tencent.mm/shared_prefs |" \
                  "chmod 777 /data/data/com.gz.pbs.copyfile/files |" \
                  "chmod 666 /data/data/com.tencent.mm/shared_prefs/system_config_prefs_showdown.xml " % (port, dm5_path, dm5_path)
        p = subprocess.Popen(exc_cmd)
        p.wait()
        return True
# md5加密生成微信加密路径
def md5_file(devUin):
    hl = hashlib.md5()
    mm_uin = "mm" + devUin
    hl.update(mm_uin.encode(encoding='utf-8'))
    sqlite_path = hl.hexdigest()
    return sqlite_path

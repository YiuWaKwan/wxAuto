# -*- coding: utf-8 -*-

# @Time    : 2018/9/7 16:50
# @Author  : xiaoguobiao
# @File    : wechat.py

import multiprocessing
import random
import signal
import hashlib
import datetime
import subprocess
import threading
import time

import taskMonitor
from lib.ModuleConfig import ConfAnalysis
from lib.FinalLogger import *
from tools import MysqlDbPool
from xml.etree.ElementTree import fromstring, ElementTree
import requests
from multiprocessing import Pool
from pysqlcipher3 import dbapi2 as sqlite

errorFile = "./log/wechat-error.log"
loggerFile = "./log/wechat.log"
logger = getLogger(loggerFile)
configFile = './conf/moduleConfig.conf'
confAllItems = ConfAnalysis(logger, configFile)
pool_size = confAllItems.getOneOptions("taskPool", "maxTask")
devId = confAllItems.getOneOptions('devInfo', 'dev')
imgSendUrl = confAllItems.getOneOptions('img', 'chatImageURL')
mysqlPool = MysqlDbPool.MysqlDbPool(1, 10) # modify by edent 20180926
RunFlag = 1
project_path = os.getcwd()
file_split = os.sep
type_fileds = [1, 3, 43, 47, 49, 10000, 570425393]


def weixin_message(deviceInfo, devUin, dbPassword, wx_id, process_seq, uuid):
    try:
        uin_encrypted_path = md5_file(devUin)
        local_wechat_db_path = project_path + file_split + "wechatdb" + file_split + wx_id
        if not os.path.exists(local_wechat_db_path):
            os.makedirs(local_wechat_db_path)
        pull_result = weixin_files_pull(local_wechat_db_path, deviceInfo, wx_id, process_seq, uin_encrypted_path)
        if pull_result == 1:
            write_message_into_mysql(local_wechat_db_path, dbPassword, uuid, deviceInfo, uin_encrypted_path,
                                     process_seq, wx_id)
            write_process_log(wx_id, process_seq, "program_endtime", 1)
    except (Exception) as error:
        logger.exception(error)
        logger.error(error)
        with open(errorFile, 'a+') as f:
            error_message = "%s 获取微信消息异常 %s %s \n" % (datetime.datetime.now(), wx_id, error)
            f.write(error_message)
        raise Exception("%s 获取微信消息异常" % wx_id)
    finally:
        pass


# 将微信本地数据库的消息内容写入到mysql中
def write_message_into_mysql(local_wechat_db_path, dbPassword, uuid, deviceInfo, uin_encrypted_path, process_seq,
                             wx_id):
    group_member_name = ""
    group_member_id = ""
    group_member_img = ""
    message = ""
    weixin_encypt_db_path = local_wechat_db_path + os.sep + "EnMicroMsg.db"
    conn = sqlite.connect(weixin_encypt_db_path)
    weixin = conn.cursor()
    weixin.execute("PRAGMA key = '" + dbPassword + "';")
    weixin.execute("PRAGMA cipher_use_hmac = OFF;")
    weixin.execute("PRAGMA kdf_iter = 4000;")

    try:
        userinfo = dict(weixin.execute(""" SELECT id, value FROM userinfo """).fetchall())
        wx_main_id = userinfo[2]
    except(Exception) as error:
        logger.exception(error)
        logger.error(error)
        with open(errorFile, 'a+') as f:
            error_message = "%s 解析userinfo表异常 %s %s \n" % (datetime.datetime.now(), wx_id, error)
            f.write(error_message)
        raise Exception("%s 解析userinfo表异常" % wx_id)

    try:
        # 获取weixinDB中的最近聊天时间
        latest_time_result = weixin.execute("""select max(createTime) from message""").fetchone()
        if latest_time_result:
            max_time = latest_time_result[0]
        else:
            max_time = 0
        # 获取本地数据库中记录的最近聊天时间
        get_lastest_message_sql = "select min(createTime) from wx_message_timestamp where wx_main_id = '%s' " \
                                  "GROUP BY createTime " % wx_main_id
        query_result = mysqlPool.getData(get_lastest_message_sql)
        if len(query_result) > 0 and max_time > 0:
            query_message_time = query_result[0][0] - 1000
            updte_max_time_sql = "update wx_message_timestamp set createTime = %s where wx_main_id='%s'" % (
                max_time, wx_main_id)
            query_message_sql = "SELECT msgSvrId,type,isSend,createTime,talker,content,imgPath FROM message " \
                                "where createTime > %s  and isSend != 1 order by createTime asc" % query_message_time
        else:
            updte_max_time_sql = "insert into wx_message_timestamp(createTime,wx_main_id) values (%s,'%s')" % (
                max_time, wx_main_id)
            query_message_sql = "SELECT msgSvrId,type,isSend,createTime,talker,content,imgPath FROM message " \
                                "where isSend != 1 order by createTime asc"

        # 获取聊天消息内容
        db_msgs = weixin.execute(query_message_sql).fetchall()
        db_msgs_list = []
        db_content_list = []
        start_time = datetime.datetime.now()
        for row in db_msgs:
            msgSvrId, type, isSend, createTime, talker, content, imgPath = row
            judeg_message_sql = "select count(*) from wx_chat_info where msgId = %s and wx_main_id = '%s' " \
                                "union all select count(*) from wx_chat_info_his where msgId = %s and wx_main_id = '%s' " % (
                                    msgSvrId, wx_main_id, msgSvrId, wx_main_id)
            result = mysqlPool.getData(judeg_message_sql)
            judge_result = result[0][0]
            judge_history_result = result[1][0]
            if judge_result == 0 and judge_history_result == 0:
                send_time = datetime.datetime.fromtimestamp(createTime / 1000)
                if type == 1:  # 文本消息
                    converse_type = 1
                    group_member_id, message, group_member_name, group_member_img = \
                        parse_content(content, type, imgPath, uin_encrypted_path, deviceInfo, wx_main_id, weixin,
                                      process_seq)
                elif type == 3:  # 图片信息
                    converse_type = 2
                    group_member_id, message, group_member_name, group_member_img = \
                        parse_content(content, type, imgPath, uin_encrypted_path, deviceInfo, wx_main_id, weixin,
                                      process_seq)
                elif type == 47:  # 自定义表情内容,保存图片链接
                    converse_type = 2
                    group_member_id, message, group_member_name, group_member_img = \
                        parse_content(content, type, imgPath, uin_encrypted_path, deviceInfo, wx_main_id, weixin,
                                      process_seq, talker)
                elif type == 10000:  # 系统消息
                    converse_type = 5
                    group_member_id = ""
                    if "你已添加了" in content:
                        taskSeq = round(time.time() * 1000 + random.randint(100, 999))
                        insert_task_sql = "insert into wx_task_manage(taskSeq,uuid,actionType,createTime,priority,status) " \
                                          "value ('%s','%s','%s',now(),'%s','1')" % (taskSeq, uuid, 9, 5)
                        print("2: %s" % insert_task_sql)
                        mysqlPool.excSql(insert_task_sql)
                    if "移出群聊" in content:
                        judege_rela_exist_sql = "select count(*) from wx_friend_rela where wx_main_id= '%s' " \
                                                "and wx_id = '%s'" % (wx_main_id, talker)
                        exist_result = mysqlPool.getData(judege_rela_exist_sql)[0][0]
                        if exist_result == 1:
                            update_rela_sql = "update wx_friend_rela set state = '3' where wx_main_id= '%s' and wx_id = '%s'" \
                                              % (wx_main_id, talker)
                            mysqlPool.excSql(update_rela_sql)
                    message = content
                elif type == 570425393:  # XX通过XX分享的二维码扫描入群信息
                    converse_type = 4
                    group_member_id, message, group_member_name, group_member_img = \
                        parse_content(content, type, imgPath, uin_encrypted_path, deviceInfo, wx_main_id, weixin,
                                      process_seq, talker)
                    taskSeq = round(time.time() * 1000 + random.randint(100, 999))
                    insert_task_sql = "insert into wx_task_manage(taskSeq,uuid,actionType,createTime,priority,status) " \
                                      "value ('%s','%s','%s',now(),'%s','1')" % (taskSeq, uuid, 9, 5)
                    print("3: %s" % insert_task_sql)
                    mysqlPool.excSql(insert_task_sql)
                if message:
                    if msgSvrId == None:
                        msgSvrId = ""
                    group_member_name = mysqlPool.transfer_string(group_member_name)
                    db_msg_tuple = (wx_main_id, talker, send_time, converse_type, message, msgSvrId, createTime,
                                    group_member_name, group_member_id, group_member_img)
                    db_msgs_list.append(db_msg_tuple)
                    db_content_list.append(message)
                    # 消息内容单条循环写入mysql表
                    start_time = datetime.datetime.now()
                    write_process_log(wx_id, process_seq, "write_mysql_starttime", 1)
                    record_message_sql = "insert into wx_chat_info(wx_main_id,wx_id,send_time,type,content," \
                                         "msgId,createTime,group_member_name,group_member_id,head_picture) values " \
                                         "('%s','%s','%s',%s,'%s',%s,%s,'%s','%s','%s')" \
                                         % (wx_main_id, talker, send_time, converse_type, message, msgSvrId, createTime,
                                            group_member_name, group_member_id, group_member_img)
                    mysqlPool.excSql(record_message_sql)
                else:
                    continue
                # 更新最近联系时间和内容
                updateLastChatSql = "update wx_friend_rela set last_chart_time='%s',last_chart_content='%s' where " \
                                    "wx_main_id='%s' and wx_id='%s'" % (send_time, message, wx_main_id, talker)
                mysqlPool.excSql(updateLastChatSql)
                # 判断是否含@
                try:
                    if '@' in message and '@chatroom' in talker:
                        at_message_sql = "insert into wx_group_at_info(wx_main_id,wx_id,group_id,send_time,status,msgId,content)" \
                                         " values ('%s','%s','%s',now(),0,'%s','%s')" % (
                                             wx_main_id, group_member_id, talker, msgSvrId, message)
                        # logger.info("at_message_sql sqlbeiginTime:%s" % datetime.datetime.now())
                        mysqlPool.excSql(at_message_sql)
                        # logger.info("at_message_sql sqlendTime:%s" % datetime.datetime.now())
                except (Exception) as e:
                    print("群@消息已入库,主键冲突：" + str(msgSvrId))
        # 消息批量写入mysql数据库
        # start_time = datetime.datetime.now()
        # write_process_log(wx_id, process_seq, "write_mysql_starttime", 1)
        # record_message_sql = "insert into wx_chat_info(wx_main_id,wx_id,send_time,type,content,msgId,createTime," \
        #                      "group_member_name,group_member_id,head_picture) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        # mysqlPool.executeMany(record_message_sql, db_msgs_list)
        end_time = datetime.datetime.now()
        seconds = (end_time - start_time).seconds
        # print("%s 本次记录消息内容为：%s,耗时%s秒" % (wx_main_id, db_msgs_list, seconds))
        mysqlPool.excSql(updte_max_time_sql)
        this_time = datetime.datetime.now()
        db_content = ','.join(str(s) for s in db_content_list if s not in [None])
        update_log_sql = "update wx_decypt_log set write_mysql_endtime = '%s',content = '%s' where wx_main_id = '%s' " \
                         "and taskseq = '%s'" % (this_time, db_content, wx_id, process_seq)
        mysqlPool.excSql(update_log_sql)
        conn.close()
    except(Exception) as error:
        logger.exception(error)
        with open(errorFile, 'a+') as f:
            error_message = "%s 解析%s message表异常 %s %s \n" % (datetime.datetime.now(), wx_id, error)
            f.write(error_message)
        raise Exception("解析%s message表异常" % wx_main_id)
    finally:
        pass


# 处理微信消息内容
def parse_content(content, type, imgPath, uin_encrypted_path, deviceInfo, wx_main_id, weixin, process_seq, talker=""):
    try:
        group_member_id = ""
        group_member_img = ""
        group_member_name = ""
        message = ""
        if type == 1:
            if ':\n' in content:
                group_member_id = content.split(':\n')[0]
                group_member_name, group_member_img = group_member_info(weixin, group_member_id)
                message = content.split(':\n')[1]
            else:
                message = content
        if type == 3 and 'th_' in imgPath:
            if ':\n' in content:
                group_member_id = content.split(':\n')[0]
                group_member_name, group_member_img = group_member_info(weixin, group_member_id)
            chatImagePath = project_path + file_split + "wechatdb" + file_split + wx_main_id + file_split + "chatImage"
            if not os.path.exists(chatImagePath):
                os.makedirs(chatImagePath)
            pic_path = imgPath.split('th_')[1]
            pic_name = pic_path + ".jpg"
            # /data/data/com.tencent.mm/MicroMsg/ adb本地图片存放路径
            pic_path_dir = pic_path[0:2] + "/" + pic_path[2:4] + "/" + pic_name
            judgePicExistCommand = "adb -s %s shell ls /sdcard/tencent/MicroMsg/%s/image2/%s | wc -l" % (
                deviceInfo, uin_encrypted_path, pic_path_dir)
            judge = subprocess.Popen(judgePicExistCommand, shell=False, stdout=subprocess.PIPE).stdout.readlines()
            if len(judge) == 1:
                dragPicCommand = "adb -s %s pull /sdcard/tencent/MicroMsg/%s/image2/%s %s" % (
                    deviceInfo, uin_encrypted_path, pic_path_dir, chatImagePath)
                drag = subprocess.Popen(dragPicCommand)
                drag.wait()
                file = chatImagePath + "\\" + pic_name
                files = {"file": (pic_name, open(file, "rb"), "image/jpg")}
                req = requests.post(imgSendUrl, files=files, data={"file_path": "chatImage"})
                if req.status_code == 200:
                    logger.info("upload chat picture success")
                message = "\\\\static\\\\img\\\\chatImage\\\\" + pic_name
            else:
                thumb_pic_name = imgPath.split('//')[1]
                thumb_pic_path_dir = pic_path[0:2] + "/" + pic_path[2:4] + "/" + thumb_pic_name
                dragPicCommand = "adb -s %s pull /sdcard/tencent/MicroMsg/%s/image2/%s %s" % (
                    deviceInfo, uin_encrypted_path, thumb_pic_path_dir, chatImagePath)
                drag = subprocess.Popen(dragPicCommand)
                drag.wait()
                oldfile = chatImagePath + "\\" + thumb_pic_name
                file = chatImagePath + "\\" + thumb_pic_name + ".jpg"
                pic_name = thumb_pic_name + ".jpg"
                os.rename(oldfile, file)
                files = {"file": (pic_name, open(file, "rb"), "image/jpg")}
                req = requests.post(imgSendUrl, files=files, data={"file_path": "chatImage"})
                if req.status_code == 200:
                    logger.info("upload chat picture success")
                message = "\\\\static\\\\img\\\\chatImage\\\\" + pic_name
        if type == 47:
            if talker.endswith("@chatroom"):
                group_member_id = content.split(":")[0]
                group_member_name, group_member_img = group_member_info(weixin, group_member_id)
            try:
                if "cdnurl=\"" in content:
                    message = content.split("cdnurl=\"")[1].split("\"")[0].replace("*#*", "s:")
                elif "cdnurl = \"" in content:
                    message = content.split("cdnurl = \"")[1].split("\"")[0].replace("*#*", "s:")
                else:
                    message = ""
            except(Exception) as error:
                logger.exception(error)
                logger.info(message)
                message = ""
                raise Exception("获取cdn地址异常")
            finally:
                pass
        if type == 570425393:
            if ':\n' in content:
                group_member_id = content.split(':\n')[0]
                xmlData = content.split(':\n')[1]
                tree = ElementTree(fromstring(xmlData))
                xml_content = {}
                for elem in tree.iter():
                    if elem.tag == "template":
                        xml_content["template"] = elem.text
                if "\"$username$\"邀请\"$names$\"加入了群聊" in xml_content["template"]:
                    first_param = tree.findall(".//link[@name='username']/memberlist/member/nickname")[0].text
                    second_param = tree.findall(".//link[@name='names']/memberlist/member/nickname")[0].text
                    message = xml_content["template"].replace("$username$", first_param). \
                        replace("$names$", second_param)
                if "\"$username$\"邀请你加入了群聊，群聊参与人还有：$others$" in xml_content["template"]:
                    first_param = tree.findall(".//link[@name='username']/memberlist/member/nickname")[0].text
                    second_param = tree.findall(".//link[@name='others']/plain")
                    second_param_list = ""
                    for name in second_param:
                        second_param_list += name.text + ","
                    second_param_list = second_param_list[:-1]
                    message = xml_content["template"].replace("$username$", first_param). \
                        replace("$others$", second_param_list)
                if "\"$username$\"修改群名为“$remark$”" in xml_content["template"]:
                    first_param = tree.findall(".//link[@name='username']/memberlist/member/nickname")[0].text
                    second_param = tree.findall(".//link[@name='remark']/plain")[0].text
                    message = xml_content["template"].replace("$username$", first_param). \
                        replace("$remark$", second_param)
                if "\"$username$\"邀请你和\"$names$\"加入了群聊" in xml_content["template"]:
                    first_param = tree.findall(".//link[@name='username']/memberlist/member/nickname")[0].text
                    second_param = tree.findall(".//link[@name='names']/memberlist/member/nickname")
                    second_param_list = ""
                    for name in second_param:
                        second_param_list += name.text + ","
                    second_param_list = second_param_list[:-1]
                    message = xml_content["template"].replace("$username$", first_param). \
                        replace("$names$", second_param_list)
                if "你邀请\"$names$\"加入了群聊  $revoke$" in xml_content["template"]:
                    first_param = tree.findall(".//link[@name='names']/memberlist/member/nickname")[0].text
                    message = xml_content["template"].replace("$names$", first_param). \
                        replace("$revoke$", "").strip()
                if "\" $adder$\"通过扫描\"$from$\"分享的二维码加入群聊" in xml_content["template"]:
                    first_param = tree.findall(".//link[@name='adder']/memberlist/member/nickname")[0].text
                    second_param = tree.findall(".//link[@name='from']/memberlist/member/nickname")[0].text
                    message = xml_content["template"].replace("$adder$", first_param). \
                        replace("$from$", second_param)
                if "你将\"$kickoutname$\"移出了群聊" in xml_content["template"]:
                    first_param = tree.findall(".//link[@name='kickoutname']/memberlist/member/nickname")[0].text
                    message = xml_content["template"].replace("$kickoutname$", first_param)
                if "通过扫描你分享的二维码加入群聊" in xml_content["template"]:
                    first_param = tree.findall(".//link[@name='adder']/memberlist/member/nickname")[0].text
                    message = xml_content["template"].replace("\"$adder$\"", first_param).\
                        replace("$revoke$","").strip()
    except(Exception) as e:
        logger.exception(e)
        with open(errorFile, 'a+') as f:
            error_message = "%s 解析消息内容parse_content异常 %s %s \n" % (datetime.datetime.now(), wx_id, error)
            f.write(error_message)
        raise Exception("%s 解析消息内容异常" % wx_main_id)
    return (group_member_id, message, group_member_name, group_member_img)


# 获取群聊成员信息
def group_member_info(weixin, group_member_id):
    try:
        group_member_name = ""
        group_member_img = ""
        get_groupmember_nickname_and_img_sql = "select a.nickname,b.reserved1 from rcontact a, img_flag b where " \
                                               "a.username = b.username and a.username = '%s'" % group_member_id
        group_member_info = weixin.execute(get_groupmember_nickname_and_img_sql).fetchone()
        if group_member_info:
            group_member_name = group_member_info[0]
            group_member_img = group_member_info[1]
    except(Exception) as error:
        logger.exception(error)
        with open(errorFile, 'a+') as f:
            error_message = "%s 获取群成员信息异常 %s %s \n" % (datetime.datetime.now(), wx_id, error)
            f.write(error_message)
        raise Exception("获取群成员信息异常！")
    return (group_member_name, group_member_img)


# 获取微信文件方法
def weixin_files_pull(local_wechat_db_path, deviceInfo, wx_id, process_seq, uin_encrypted_path):
    try:
        wechat_db_file_list = ["EnMicroMsg.db", "EnMicroMsg.db-shm", "EnMicroMsg.db-wal", "EnMicroMsg.db.ini",
                               "EnMicroMsg.db.sm", "EnMicroMsg.db-journal"]
        localdb = wechat_db_file_list[0]
        localdb_path = local_wechat_db_path + file_split + localdb
        shmfile = wechat_db_file_list[1]
        shmfile_path = local_wechat_db_path + file_split + shmfile
        walfile = wechat_db_file_list[2]
        walfile_path = local_wechat_db_path + file_split + walfile
        inifile = wechat_db_file_list[3]
        inifile_path = local_wechat_db_path + file_split + inifile
        smfile = wechat_db_file_list[4]
        smfile_path = local_wechat_db_path + file_split + smfile
        journalfile = wechat_db_file_list[5]
        journalfile_path = local_wechat_db_path + file_split + journalfile
        if os.path.exists(localdb_path):
            os.remove(localdb_path)
        if os.path.exists(shmfile_path):
            os.remove(shmfile_path)
        if os.path.exists(walfile_path):
            os.remove(walfile_path)
        if os.path.exists(inifile_path):
            os.remove(inifile_path)
        if os.path.exists(smfile_path):
            os.remove(smfile_path)
        if os.path.exists(journalfile_path):
            os.remove(journalfile_path)
        # query_time_sql = "select localdbtime,shmfileTime from wx_message_timestamp where wx_main_id = '%s'" % wx_id
        # weixin_time = mysqlPool.getData(query_time_sql)
        # weixin_db_time_adb = check_wechat_db_time(deviceInfo, uin_encrypted_path, localdb)
        # weixin_shm_time_adb = check_wechat_db_time(deviceInfo, uin_encrypted_path, shmfile)

        # ========  拉取文件开始 记录日志 ==========
        write_process_log(wx_id, process_seq, "get_localdb_starttime", 1)
        # ======== 记录结束 ==========
        # if len(query_time_sql) > 0 and weixin_db_time_adb is not None and weixin_shm_time_adb is not None:
        #     weixin_db_time_mysql = weixin_time[0][0]
        #     weixin_shm_time_mysql = weixin_time[0][1]
        #     if weixin_shm_time_adb > weixin_shm_time_mysql and weixin_db_time_mysql == weixin_db_time_adb:
        #         # adb_pull_file(deviceInfo, uin_encrypted_path, localdb, local_wechat_db_path)
        #         adb_pull_file(deviceInfo, uin_encrypted_path, shmfile, local_wechat_db_path)
        #         adb_pull_file(deviceInfo, uin_encrypted_path, walfile, local_wechat_db_path)
        #         update_time_sql = "update wx_message_timestamp set shmfileTime='%s' where wx_main_id='%s'" \
        #                           % (weixin_shm_time_adb, wx_id)
        #         mysqlPool.excSql(update_time_sql)
        #     elif weixin_shm_time_adb > weixin_shm_time_mysql and weixin_db_time_adb > weixin_db_time_mysql:
        #         adb_pull_file(deviceInfo, uin_encrypted_path, localdb, local_wechat_db_path)
        #         adb_pull_file(deviceInfo, uin_encrypted_path, shmfile, local_wechat_db_path)
        #         adb_pull_file(deviceInfo, uin_encrypted_path, walfile, local_wechat_db_path)
        #         if not os.path.exists(inifile_path):
        #             adb_pull_file(deviceInfo, uin_encrypted_path, inifile, local_wechat_db_path)
        #         if not os.path.exists(smfile_path):
        #             adb_pull_file(deviceInfo, uin_encrypted_path, smfile, local_wechat_db_path)
        #         update_time_sql = "update wx_message_timestamp set localdbtime = '%s',shmfileTime='%s' where wx_main_id='%s'" \
        #                           % (weixin_db_time_adb, weixin_shm_time_adb, wx_id)
        #         mysqlPool.excSql(update_time_sql)
        #     else:
        #         update_time_sql = "update wx_message_timestamp set localdbtime = '%s',shmfileTime='%s' where wx_main_id='%s'" \
        #                           % (weixin_db_time_adb, weixin_shm_time_adb, wx_id)
        #         mysqlPool.excSql(update_time_sql)
        # elif len(query_time_sql) == 0 and weixin_db_time_adb is not None and weixin_shm_time_adb is not None:
        #     adb_pull_file(deviceInfo, uin_encrypted_path, localdb, local_wechat_db_path)
        #     adb_pull_file(deviceInfo, uin_encrypted_path, shmfile, local_wechat_db_path)
        #     adb_pull_file(deviceInfo, uin_encrypted_path, walfile, local_wechat_db_path)
        #     adb_pull_file(deviceInfo, uin_encrypted_path, inifile, local_wechat_db_path)
        #     adb_pull_file(deviceInfo, uin_encrypted_path, smfile, local_wechat_db_path)
        #     query_record_sql = "select count(1) from wx_message_timestamp where wx_main_id = '%s'" % wx_id
        #     record = mysqlPool.getData(query_record_sql)[0][0]
        #     if record == 1:
        #         update_time_sql = "update wx_message_timestamp set localdbtime = '%s',shmfileTime='%s' where wx_main_id='%s'" \
        #                           % (weixin_db_time_adb, weixin_shm_time_adb, wx_id)
        #     else:
        #         update_time_sql = "insert into wx_message_timestamp(localdbtime,shmfileTime,wx_main_id) values" \
        #                           "('%s','%s','%s')" % (weixin_db_time_adb, weixin_shm_time_adb, wx_id)
        #     mysqlPool.excSql(update_time_sql)
        adb_pull_file(deviceInfo, uin_encrypted_path, localdb, local_wechat_db_path)
        adb_pull_file(deviceInfo, uin_encrypted_path, shmfile, local_wechat_db_path)
        adb_pull_file(deviceInfo, uin_encrypted_path, walfile, local_wechat_db_path)
        adb_pull_file(deviceInfo, uin_encrypted_path, inifile, local_wechat_db_path)
        adb_pull_file(deviceInfo, uin_encrypted_path, smfile, local_wechat_db_path)
        adb_pull_file(deviceInfo, uin_encrypted_path, journalfile, local_wechat_db_path)

        # ========  拉取文件结束 记录日志 ==========
        write_process_log(wx_id, process_seq, "get_localdb_endtime", 1)
        # ======== 记录结束 ==========
        status = 1
    except(Exception) as error:
        logger.exception(error)
        logger.error(error)
        with open(errorFile, 'a+') as f:
            error_message = "%s weixin_files拉取异常 %s %s \n" % (datetime.datetime.now(), wx_id, error)
            f.write(error_message)
        raise Exception("weixin_files拉取异常")
        status = 0
    return status


# 写进程日志，记录过程中的日志
def write_process_log(wx_id, process_seq, update_column, flag):
    try:
        now_time = datetime.datetime.now()
        if flag == 0:
            update_log_sql = "insert into wx_decypt_log(wx_main_id,%s,taskseq) values ('%s','%s','%s')" % \
                             (update_column, wx_id, now_time, process_seq)
        else:
            update_log_sql = "update wx_decypt_log set %s = '%s'where wx_main_id = '%s' and taskseq = '%s'" % \
                             (update_column, now_time, wx_id, process_seq)
        mysqlPool.excSql(update_log_sql)
    except(Exception) as error:
        logger.exception(error)
        raise Exception("流程耗时写日志记录异常！")


# check微信DB和缓存文件的时间方法
def check_wechat_db_time(deviceInfo, sqlite_path, filename):
    try:
        judgeFileExistCommand = "adb -s %s shell ls /data/data/com.tencent.mm/MicroMsg/%s/%s | wc -l" % (
            deviceInfo, sqlite_path, filename)
        judge = subprocess.Popen(judgeFileExistCommand, shell=False, stdout=subprocess.PIPE).stdout.readlines()
        if len(judge) == 1:
            command = "adb -s %s shell stat /data/data/com.tencent.mm/MicroMsg/%s/%s | " \
                      "grep \"Modify:\"" % (deviceInfo, sqlite_path, filename)
            result = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE).stdout.readlines()
            modify_time = string_to_datetime(str(result[0]).split(": ")[1].split(".")[0])
            return modify_time
        else:
            return None
    except(Exception) as error:
        logger.exception(error)
        raise Exception("获取模拟器微信DB时间异常！")


# 通过adb 拉取文件方法
def adb_pull_file(deviceInfo, sqlite_path, file_name, local_wechat_db_path):
    try:
        judgeFileExistCommand = "adb -s %s shell ls /data/data/com.tencent.mm/MicroMsg/%s/%s | wc -l" % (
            deviceInfo, sqlite_path, file_name)
        judge = subprocess.Popen(judgeFileExistCommand, shell=False, stdout=subprocess.PIPE).stdout.readlines()
        if len(judge) == 1:
            desfile = local_wechat_db_path + file_split + file_name
            if os.path.exists(desfile):
                os.remove(desfile)
            pull_command = "adb -s %s pull /data/data/com.tencent.mm/MicroMsg/%s/%s %s" % (
                deviceInfo, sqlite_path, file_name, local_wechat_db_path)
            p = subprocess.Popen(pull_command)
            p.wait()
    except (Exception) as error:
        logger.exception(error)
        with open(errorFile, 'a+') as f:
            error_message = "%s 拉取文件%s异常 %s \n" % (datetime.datetime.now(), file_name, error)
            f.write(error_message)
        raise Exception("拉取文件%s异常" % file_name)
    finally:
        pass


# md5加密结果
def md5_file(devUin):
    hl = hashlib.md5()
    mm_uin = "mm" + devUin
    hl.update(mm_uin.encode(encoding='utf-8'))
    sqlite_path = hl.hexdigest()
    return sqlite_path


# 将字符串格式的时间转为datetime类型
def string_to_datetime(string):
    format_datetime = datetime.datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
    return format_datetime


if __name__ == '__main__':
    # pool = Pool(int(pool_size))
    # pool_dict = {}
    while RunFlag:
        try:
            threads = []
            process_seq = int(round(time.time() * 1000))
            multiprocessing.freeze_support()
            # 判断当前模拟器微信在线
            current_online_weixin_sql = "select tb.devIp,tb.devport,ta.uin,ta.db_passwd,ta.wx_id,ta.uuid from " \
                                        "wx_account_info ta ,wx_machine_info tb where ta.uuid = tb.uuid and " \
                                        "tb.clientId = '%s' and ta.uin is not null and ta.if_start=1" % devId
            print(current_online_weixin_sql)
            current_online_weixin = mysqlPool.getData(current_online_weixin_sql)
            # 当前在线微信列表 online_devices_list ：IP + port
            online_devices_list = []
            for item in current_online_weixin:
                itemInfo = item[0] + ":" + item[1]
                online_devices_list.append(itemInfo)
            current_online_adb = []
            result = subprocess.check_output("adb devices").decode(encoding="utf-8").split('\r\n')
            for i in result:
                if ":" in i and i.split('\t')[1] != "offline":
                    current_online_adb.append(i.split('\t')[0])
            print(current_online_adb)
            if len(current_online_adb) > 0:
                need_alarm_list = list(set(online_devices_list).difference(set(current_online_adb)))
                if len(need_alarm_list) > 0:
                    for item in need_alarm_list:
                        try:
                            adb_connect_cmd = "adb connect %s" % item
                            p = subprocess.Popen(adb_connect_cmd, shell=True, stdout=subprocess.PIPE)
                        except(Exception) as error:
                            logger.exception(error)
                            raise Exception("1- adb重连异常！")
                for weixin_info in current_online_weixin:
                    dev_info = weixin_info[0] + ":" + weixin_info[1]
                    devUin = weixin_info[2]
                    dbPassword = weixin_info[3]
                    wx_id = weixin_info[4]
                    uuid = weixin_info[5]
                    for adb_info in current_online_adb:
                        # if adb_info == dev_info and (pool_dict.get(wx_id) and pool_dict.get(wx_id).ready()
                        #                              and pool_dict.get(wx_id).successful() or not pool_dict.get(wx_id)):
                        #     # 进程开始 记录日志
                        #     write_process_log(wx_id, process_seq, "program_begintime", 0)
                        #     # ======== 记录结束 ==========
                        #     res = pool.apply_async(weixin_message,
                        #                            args=(dev_info, devUin, dbPassword, wx_id, process_seq, uuid,))
                        #     pool_dict[wx_id] = res
                        if adb_info == dev_info:
                            print(adb_info)
                            # 进程开始 记录日志
                            write_process_log(wx_id, process_seq, "program_begintime", 0)
                            # ======== 记录结束 ==========
                            thread = threading.Thread(target=weixin_message,
                                                      args=(dev_info, devUin, dbPassword, wx_id, process_seq, uuid,))
                            threads.append(thread)
            else:
                # 判断微信状态表微信是否在线，若在线，adb connect 否则pass
                if len(online_devices_list) > 0:
                    for item in online_devices_list:
                        try:
                            adb_connect_cmd = "adb connect %s" % item
                            p = subprocess.Popen(adb_connect_cmd, shell=True, stdout=subprocess.PIPE)
                        except(Exception) as error:
                            logger.exception(error)
                            raise Exception("2- adb重连异常！")
            # print(threads)
            for t in threads:
                t.setDaemon(False)
                t.start()
            for t in threads:
                t.join()
            time.sleep(1)
        except(Exception) as error:
            logger.exception(error)
    # pool.close()
    # pool.join()

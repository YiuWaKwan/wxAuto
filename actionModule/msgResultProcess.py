import base64
import datetime
import json
import random
import time
import traceback
import urllib
import pymysql

from tools import MysqlDbPool, common, redisUtil

def update_wx_oper_wx(mysqlUtils,wxId):
    sqlUpdate = """UPDATE wx_oper_wx
                    SET object_id = "%s"
                    WHERE
                        object_id = (
                            SELECT
                                wx_login_id
                            FROM
                                wx_account_info
                            WHERE
                                wx_id = "%s"
                        )""" %(wxId, wxId)
    mysqlUtils.execSql(sqlUpdate)


def msgSendaction(logger, msgInfo, mySql):
    '''
    消息发送结果处理
    :param logger:
    :param msgInfo:   taskSeq:~:结果
    :param mySql:
    :return:
    '''
    mySqlUtil = None
    try:
        if mySql:
            mySqlUtil = mySql
        else:
            mySqlUtil = MysqlDbPool.MysqlConn()

        if ":~:" in msgInfo:
            spiltFlag = ":~:"
            msgInfoList = msgInfo.split(spiltFlag)
            taskSeq = msgInfoList[0]
            resutlStatus = msgInfoList[1]   # 返回结果，正常-ok

            if resutlStatus == "ok":
                task_manage_status = 4
            else:
                task_manage_status = 3
                # 获取发送消息信息
                sql = """SELECT type, wx_main_id, wx_id, content FROM wx_chat_task WHERE taskSeq = %s """ % (taskSeq)
                taskSeqInfo = mySqlUtil.getData(sql)

                if taskSeqInfo:
                    actType = taskSeqInfo[0][0]
                    actWxMainId = taskSeqInfo[0][1]
                    actWxId = taskSeqInfo[0][2]
                    content = taskSeqInfo[0][3]
                    resutlMsg = chartTypeTranslate(content, actType)
                    resultErrorMsg = "%s 错误信息: %s" % (resutlMsg, resutlStatus)
                    common.messageNotice(actWxMainId, actWxId, resultErrorMsg, taskSeq, mySqlUtil)
                else:
                    logger.warn("can't find info by taskSeq(%s)(%s)" % (taskSeq, str(taskSeqInfo)))
            remarks = resutlStatus

            sql = """ UPDATE wx_task_manage SET remarks = '%s', status = '%s', endTime = now()
                                        WHERE taskSeq = %s """ % (remarks, task_manage_status, taskSeq)
            # 更新wx_task_manage表状态
            mySqlUtil.execSql(sql)
        else:
            logger.warn("msgResultProcess accept msgInfo is error -- %s" % (msgInfo))

    except Exception as e:
        logger.info(traceback.format_exc())
    finally:
        if not mySql:
            mySqlUtil.conn.close()

def chartTypeTranslate(content, type):
    type = str(type)
    if type == "1":
        return content
    elif type == "6":
        return "[语音]"
    elif type == "2":
        return "[图片]"
    elif type == "7":
        return "[视频]"
    elif type == "3":
        return "[附件]"
    elif type == "8":
        return "[名片]"
    elif type == "9":
        return "[链接]"
    elif type == "10":
        return "[位置]"
    elif type == "11":
        return "[红包]"
    return content

def wxIdUpateProcess(logger, msgInfo, mySql):
    '''
    微信ID更新处理
    :param logger:
    :param msgInfo:  UUID:~:wx_main_id
    :param mySql:
    :return:
    '''
    mySqlUtil = None
    try:
        if mySql:
            mySqlUtil = mySql
        else:
            mySqlUtil = MysqlDbPool.MysqlConn()

        if ":~:" in msgInfo:
            spiltFlag = ":~:"
            msgInfoList = msgInfo.split(spiltFlag)
            actUuid = msgInfoList[0]
            actWxId = msgInfoList[1]

            wxInfoUpdateSql = """update wx_account_info
                                    set wx_id = "%s",
                                    is_first_time = "0"
                                    where uuid="%s" """ %(actWxId, actUuid)
            mySqlUtil.execSql(wxInfoUpdateSql)

            update_wx_oper_wx(mySqlUtil, actWxId)
            logger.info("%s wxId 更新成功 ：%s" %(actUuid, actWxId))

        else:
            logger.warn("wxIdUpateProcess accept msgInfo is empty -- %s" %(msgInfo) )

    except Exception as e:
        logger.info(traceback.format_exc())
    finally:
        if not mySql:
            mySqlUtil.conn.close()

def hdPicUploadProcess(logger, msgInfo, mySql):
    '''
    更新查看原图的任务结果
    :param logger:
    :param msgInfo:  wxid_nssbfgrn801622:~:8322955476944693347#^#url
    :param mySql:
    :return:
    '''
    #wxid_nssbfgrn801622:~:8322955476944693347
    # #^#http://124.172.189.98:8001/static/wxmsg/20190610/wxid_nssbfgrn801622/pic/c43c05a80c61b9e60bbdac8d9327ded2.jpg
    mySqlUtil = None
    try:
        if mySql:
            mySqlUtil = mySql
        else:
            mySqlUtil = MysqlDbPool.MysqlConn()

        if ":~:" in msgInfo:
            spiltFlag = ":~:"
            msgInfoList = msgInfo.split(spiltFlag)
            wx_main_id = msgInfoList[0]
            msg_content= msgInfoList[1]
            if "#^#" in msg_content:
                msgId=msg_content.split("#^#")[0]
                resultState=msg_content.split("#^#")[1]
                hdPicUrl=msg_content.split("#^#")[2]#失败时为失败原因
                check_seq_sql = "select content from wx_chat_info_his where wx_main_id='%s' and msgid='%s'" % (
                wx_main_id, msgId)
                rs = mySqlUtil.getData(check_seq_sql)
                taskSeq = str(rs[0][0]).split("|")[2]
                old_pic_url = str(rs[0][0]).split("|")[0]
                if str(resultState)=='3':
                    update_sql = "update wx_chat_info_his set content='%s|3|%s' where wx_main_id='%s' and msgid='%s'" % (
                        old_pic_url, taskSeq, wx_main_id, msgId)
                    mySqlUtil.execSql(update_sql)

                    sql = """UPDATE wx_task_manage
                            set status =3,endTime = now(),remarks ='%s'
                            where taskSeq = %s""" % (hdPicUrl,taskSeq)
                    mySqlUtil.execSql(sql)
                elif str(resultState)=='4':
                    update_sql = "update wx_chat_info_his set content='%s|1|%s' where wx_main_id='%s' and msgid='%s'" % (
                        hdPicUrl,taskSeq, wx_main_id, msgId)
                    mySqlUtil.execSql(update_sql)

                    sql = """UPDATE wx_task_manage
                            set status =4,endTime = now(),remarks ='%s'
                            where taskSeq = %s""" %  (hdPicUrl,taskSeq)
                    mySqlUtil.execSql(sql)
        else:
            logger.warn("下载高清图广播返回信息异常")

    except Exception as e:
        logger.info(traceback.format_exc())
    finally:
        if not mySql:
            mySqlUtil.conn.close()

def msgFetchProcess(logger, msgInfo, mySql):
    '''
    消息获取处理
    :param logger:
    :param msgInfo:  "见文档"
    :param mySql:
    :return:
    '''
    mySqlUtil = None
    try:
        if mySql:
            mySqlUtil = mySql
        else:
            mySqlUtil = MysqlDbPool.MysqlConn()
        # print(msgInfo)
        if msgInfo and msgInfo != "null":

            resultMap = {}
            spiltFlag = ":~:"
            msgInfoList = msgInfo.split(spiltFlag)
            if msgInfoList[1] != "null":
                msgList = [ i for i in msgInfoList[1].split('&')]

                for item in msgList:
                    aplitFlag = "='"
                    aplitFlagLen = len(aplitFlag)
                    flagIndex = item.find("='")
                    key = item[:flagIndex]
                    value = item[ flagIndex+aplitFlagLen : -1]
                    resultMap[key] = value

                # print(resultMap,'******')
                # 初始化
                mps = MessageParseSubService(resultMap,logger,mySqlUtil)
                # 执行处理
                mps.messageSqlCreate()
            elif  msgInfoList[1] == "null":
                logger.warn("msgFetchProcess accept msgInfo is null")
        elif msgInfo == "null":
            logger.warn("msgFetchProcess accept msgInfo is null")
        else:
            logger.warn("msgFetchProcess accept msgInfo is empty")

    except Exception as e:
        logger.info(traceback.format_exc())
    finally:
        if not mySql:
            mySqlUtil.conn.close()

class MessageParseSubService(object):

    def __init__(self,resultMap,logger,mysqlUtil):
        self.resultMap = resultMap
        self.logger = logger
        self.mysqlUtil = mysqlUtil

    def messageSqlCreate(self):
        # 获取信息
        messageMap = self.resultMap
        message = messageMap.get("message","")
        message = base64.b64decode(message).decode('utf-8')
        wx_main_id = messageMap.get("wx_main_id","")
        sendtime = messageMap.get("sendtime","")
        talker = messageMap.get("talker","")
        group_member_id = messageMap.get("group_member_id","")
        group_member_name = messageMap.get("group_member_name","")
        # print(group_member_name)
        group_member_name = base64.b64decode(group_member_name).decode('utf-8')
        group_member_img = messageMap.get("group_member_img","")
        msg_type = messageMap.get("msg_type","")
        msgSvrId = messageMap.get("msgSvrId","")
        uuid = messageMap.get("uuid","")
        deleteMember = messageMap.get("deleteMember","")
        deleteRelation = messageMap.get("deleteRelation","")
        updateGroup = messageMap.get("updateGroup","")

        # 消息内容
        last_chart_content = message
        msg_type = str(msg_type)
        if msg_type == "2":
            last_chart_content = group_member_name+"[图片]"
        elif msg_type == "6":
            last_chart_content = group_member_name + "[语音]"
        elif msg_type == "7":
            last_chart_content = group_member_name + "[视频]"
        elif msg_type == "8":
            last_chart_content = group_member_name + "[名片]"
        elif msg_type == "9":
            last_chart_content = group_member_name + "[链接]"
        elif msg_type == "10":
            last_chart_content = group_member_name + "[位置]"
        elif msg_type == "11":
            last_chart_content = group_member_name + "[红包]"

        if talker == "8999240664@chatroom": # 监控群ID
            insert_wx_chat_info = """insert into wx_chat_info_his(`wx_main_id`,`wx_id`,`send_time`,`type`,`content`,`send_type`,`status`,`group_member_name`,`msgId`,`createTime`,`group_member_id`,`head_picture`,`oper_id`,`seqId`) 
                                        values ("%s","%s","%s","1","%s","2","1","%s","%s",now(),"%s","%s","0","0") """ % (
                                        wx_main_id, talker, sendtime, pymysql.escape_string(message), group_member_name, msgSvrId, group_member_id,
                                        group_member_img)
        else:
            insert_wx_chat_info = """insert into wx_chat_info(wx_main_id,wx_id,send_time,type,content,msgId,createTime,group_member_name,group_member_id,head_picture,send_type)
                                          values ("%s","%s","%s","%s","%s","%s",now(),"%s","%s","%s","2")""" %(wx_main_id, talker, sendtime, msg_type, pymysql.escape_string(message), msgSvrId, group_member_name, group_member_id, group_member_img)
        self.mysqlUtil.execSql(insert_wx_chat_info)
        self.logger.debug(insert_wx_chat_info)
        if talker != "8999240664@chatroom":
            update_wx_friend_rela = """update wx_friend_rela
                                        set last_chart_time="%s",last_chart_content="%s"
                                        where wx_main_id="%s" and wx_id="%s" """ %(sendtime, pymysql.escape_string(last_chart_content), wx_main_id,talker)
        # print(update_wx_friend_rela)
            self.mysqlUtil.execSql(update_wx_friend_rela)
            self.logger.debug(update_wx_friend_rela)


        if talker.endswith("@chatroom") and message.find("@") != -1:
            sqlcontent = """ insert into wx_group_at_info(wx_main_id,wx_id,group_id,send_time,status,msgId,content) 
                                 values ("%s","%s","%s",now(),'0',"%s","%s") 
                          """ %(wx_main_id, group_member_id, talker, msgSvrId, pymysql.escape_string(message) )
            self.mysqlUtil.execSql(sqlcontent)

        update_flag=True
        if deleteRelation and deleteRelation != 'false':
            update_flag=False
            sqlcontent = """ update wx_friend_rela set state = '3' 
                              where wx_main_id = "%s"
                              and   wx_id = "%s" """%(wx_main_id, talker)
            self.mysqlUtil.execSql(sqlcontent)

        if deleteMember and deleteMember != 'false':
            update_flag = False
            sqlcontent = """ delete from  wx_group_member
                              where wx_id= "%s"
                              and group_id = "%s"
                              """ %(wx_main_id, talker)
            self.mysqlUtil.execSql(sqlcontent)
            sql_insert = "insert into wx_group_member_del select  *,now() from wx_group_member " \
                         " where group_id='%s' and wx_id='%s' " %(talker,wx_main_id)
            self.mysqlUtil.execSql(sql_insert)
        if msg_type == "4":
            if update_flag:
                self.flush_friend(wx_main_id, talker)
        else:
            realationCountSql = """ select count(1) from wx_friend_rela where wx_main_id = '%s' and wx_id = '%s' """ %(wx_main_id, talker)
            realationCount = self.mysqlUtil.getData(realationCountSql)

            if realationCount == 0:

                self.flush_friend(wx_main_id, talker)
            else:
                headPicExitsSql = """ select head_picture from wx_friend_list where wx_id = '%s' """ %(talker)
                headPicExits = self.mysqlUtil.getData(headPicExitsSql)
                if headPicExits:
                    if not headPicExits[0][0] :
                        self.flush_friend(wx_main_id, talker)




        # 转发的暂时不做批量处理

        transpodSql = """select wx_id,group_id,(select remark from wx_friend_rela f where f.wx_id=r.wx_id 
                      and wx_main_id='%s') cust_name from wx_transpond_rule t, 
                      wx_transpond_rule_relation r where t.state='1' and t.rule_id=r.rule_id 
                      and wx_main_id='%s' and wx_id='%s'""" %(wx_main_id, wx_main_id, talker)
        transpodRet = self.mysqlUtil.getData(transpodSql)
        transpodRet = None # TODO
        if transpodRet:
            transInfo = transpodRet[0]
            group_id = ""
            cust_name = ""
            if len(transInfo) > 0:
                group_id = transInfo[1]
                cust_name = transInfo[2]

                # 写聊天历史表
                sqlcontent = """ insert into wx_chat_info_his(wx_main_id, wx_id,send_time,type,content,send_type,status)
                                     values ("%s","%s",now(),"%s","%s","1","1")
                              """ %(wx_main_id, group_id, msg_type, pymysql.escape_string(message))
                self.mysqlUtil.execSql(sqlcontent)

                taskSeq = round(time.time() * 1000 + random.randint(100, 999))

                message_head = "收到客户（%s）的咨询信息: " %(cust_name)

                sqlcontent = """ insert into wx_chat_task(taskSeq,wx_main_id,wx_id,type,content)
                                 values (%s,"%s","%s","%s","%s %s")
                                 """ %(taskSeq, wx_main_id, group_id, msg_type, message_head ,pymysql.escape_string(message))
                self.mysqlUtil.execSql(sqlcontent)

                sqlcontent = """ INSERT INTO wx_task_manage(taskSeq,uuid,actionType,createTime,status,priority)
                                                 VALUES (%s,"%s",6,now(),1,1)""" % (taskSeq, uuid)

                self.mysqlUtil.execSql(sqlcontent)

            elif message.startsWith("#"):
                transpodRule = {}
                for transpodItem in transpodRet:
                    wxId = transpodItem[0]
                    groupId = transpodItem[1]
                    custName= transpodItem[2]
                    transpodRule[wxId] = "%s;%s"%(groupId, custName)

                cust_name = message[1 : message.index(" ")]
                message = message.replace("#", "").replace(cust_name, "")
                if "%s;%s" %(talker, cust_name) in self.transpodRule.values():
                    wx_id = "0"
                    for key,value in self.transpodRule.items():
                        if value == "%s;%s" %(talker, cust_name):
                            wx_id = key
                            break

                    # 写聊天历史表
                    sqlcontent = """ insert into wx_chat_info_his(wx_main_id, wx_id,send_time,type,content,send_type,status)
                                         values ("%s", "%s", now(), "%s", "%s", '1', '1')""" %(wx_main_id, wx_id, msg_type, pymysql.escape_string(message))
                    self.mysqlUtil.execSql(sqlcontent)

                    taskSeq = round(time.time() * 1000 + random.randint(100, 999))

                    sqlcontent = """ insert into wx_chat_task(taskSeq,wx_main_id,wx_id,type,content)
                                          values (%s,"%s","%s","%s","%s")""" % (taskSeq, wx_main_id, wx_id, msg_type, pymysql.escape_string(message))
                    self.mysqlUtil.execSql(sqlcontent)

                    sqlcontent = """ INSERT INTO wx_task_manage(taskSeq,uuid,actionType,createTime,status,priority)
                                                                         VALUES (%s,"%s",6,now(),1,1)""" % (taskSeq, uuid)
                    self.mysqlUtil.execSql(sqlcontent)


        # 任务结束
        self.logger.info("%s 收到 %s : %s 处理完成" % (wx_main_id, talker, message))

    def flush_friend(self, wx_id, target_wx_id):
        # 判断是否有多余的任务
        # 判断app心跳是否正常
        self.logger.debug("flush_friend:%s  %s" % (wx_id, target_wx_id))
        sql = """ select uuid from wx_account_info w where wx_id='%s' and if_start='1' and is_first_time='0'
              and not EXISTS (select 1 from wx_task_manage t where t.status in (1,2) and t.actionType=9 
              and t.uuid=w.uuid and (t.startTime is null or t.startTime < date_sub(now(),interval 1 minute)))
              and EXISTS (select 1 from wx_status_check s where s.program_type='1' and s.wx_main_id=w.wx_id and 
              s.last_heartbeat_time >= date_sub(now(),interval 3 minute)) """ % wx_id

        wxInfoUUID = self.mysqlUtil.getData(sql)

        if wxInfoUUID and len(wxInfoUUID) > 0:
            # redis广播任务
            try:
                task_uuid = wxInfoUUID[0][0]
                redisUtil.publishFlushFriend("flush_friend", "%s:~:1#=#%s" % (wx_id, target_wx_id))
                self.logger.debug("%s:~:0#=#0" % wx_id)
                # 添加刷新任务
                taskSeq = round(time.time() * 1000 + random.randint(100, 999))
                sql = "INSERT INTO wx_task_manage(taskSeq,uuid,actionType,createTime,status,priority, startTime)" \
                      "VALUES(%s,'%s',9,now(),2,5, now())" % (taskSeq, task_uuid)
                # print(sql)
                self.mysqlUtil.execSql(sql)

            except (Exception) as e:
                self.logger.exception(e)
                # 发送告警
                common.alarm("redis连接不上，刷新好友任务自动重启不成功", self.logger)





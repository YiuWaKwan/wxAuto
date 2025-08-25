# -*- coding: UTF-8 -*-
import os
import random
from multiprocessing import Process

import pymysql
import time
import traceback
from uuid import uuid1
from lib.FinalLogger import getLogger
from tools import MysqlDbPool, redisUtil
from tools.common import alarm
import urllib.request

#根据url拉文件，存文件到
#读取文件到内存，删除文件
#获取当前所有信息，结构化分类
#对比数据找出差异
#更新、删除、添加 有差异的部分
#结束
from tools.redisUtil import repeatUpdateFriend


def updateFriend(taskQueue):
    logger = getLogger('./log/UpdateFriend.log')
    last_day = time.strftime("%Y-%m-%d", time.localtime())
    while True:
        today = time.strftime("%Y-%m-%d", time.localtime())
        if today != last_day:
            last_day = today
            logger = getLogger('./log/UpdateFriend.log')
            logger.debug("today:" + str(last_day))
        else:
            time.sleep(0.01)
        try:
            if not taskQueue.empty():
                msg_body = taskQueue.get(True)
                startUpdateFriend(msg_body,logger)
        except Exception as e:
            logger.error(traceback.format_exc())

def startUpdateFriend(msg_body,logger):
    mySqlUtil=None
    wx_main_id=None
    url=None
    try:
        logger.info("开始刷新好友")
        mySqlUtil = MysqlDbPool.MysqlConn()
        # file_path=create_file(mySqlUtil)
        msg_info = str(msg_body).split(":~:")
        if len(msg_info)>2:
            wx_main_id=msg_info[1]
            logger.info("wx_main_id:%s" %str(wx_main_id))
            #先清理不对称数据
            sql="delete from wx_friend_rela where ((wx_id not like '%@chatroom' and wx_id not in " \
                "(select distinct wx_id from wx_friend_list )) or (wx_id  like '%@chatroom' and wx_id " \
                "not in (select distinct group_id from wx_group_info ))) and wx_main_id='"+str(wx_main_id)+"'"
            mySqlUtil.execSql(sql)
            url=msg_info[2]
            logger.info("file_url:%s" % str(url))
            file_path=downloadFile(url,wx_main_id)
            file_content,result_flag=readFileContent(file_path,logger)
            if result_flag:
                wx_id=file_content.get("wx_id")
                db_content=readDbContent(wx_id,mySqlUtil,logger,file_content)
                difference=compareData(file_content,db_content,logger)
                execUpdateAction(difference,mySqlUtil,logger)
                msg="刷新好友完成"
                logger.info(msg)
                updateTaskStatus(wx_main_id, mySqlUtil, logger,4,msg)
            else:
                logger.info("文件内容不完整，此次刷新失败！")
    except Exception as e:
        msg="%s刷新好友失败(url:%s)(reason:%s)" % (str(wx_main_id),str(url),str(e))
        updateTaskStatus(wx_main_id, mySqlUtil, logger,3,pymysql.escape_string(msg))
        logger.warn(msg)
        alarm(msg)
        logger.warn(traceback.format_exc())
        # if wx_main_id and mySqlUtil:
        #     logger.info("%s将添加新的刷新好友任务" % str(wx_main_id))
        #     restartTask(wx_main_id,mySqlUtil,logger)
        # else:
        #     logger.warn("程序状态异常，不再添加任务")
    finally:
        mySqlUtil.conn.close()
#根据wx_main_id下发刷新好友任务
def restartTask(wx_main_id,mySqlUtil,logger,wx_id):
    try:
        # 判断是否有多余的任务
        # 判断app心跳是否正常
        sql = """ select uuid from wx_account_info w where wx_id='%s' and if_start='1' and is_first_time='0'
                  and not EXISTS (select 1 from wx_task_manage t where t.status in (1,2) and t.actionType=9 
                  and t.uuid=w.uuid and (t.startTime is null or t.startTime < date_sub(now(),interval 1 minute)))
                  and EXISTS (select 1 from wx_status_check s where s.program_type='1' and s.wx_main_id=w.wx_id and 
                  s.last_heartbeat_time >= date_sub(now(),interval 3 minute))""" % wx_main_id
        rs=mySqlUtil.getData(sql)
        if rs and len(rs)>0:
            if len(str(wx_id))>4:
                redisUtil.publishFlushFriend("flush_friend", "%s:~:1#=#%s" % (wx_main_id,wx_id))
            else:
                redisUtil.publishFlushFriend("flush_friend", "%s:~:0#=#0" % wx_main_id)
            task_uuid=rs[0][0]
            taskSeq = round(time.time() * 1000 + random.randint(100, 999))
            sql = "INSERT INTO wx_task_manage(taskSeq,uuid,actionType,createTime,status,priority, startTime)" \
                  "VALUES(%d,'%s',9,now(),2,5, now())" % (taskSeq, task_uuid)
            mySqlUtil.execSql(sql)
        else:
            logger.info("微信状态异常，不再刷新好友")
    except Exception as e:
        alarm("重写刷新好友任务异常，请检查日志并处理")

#根据wx_main_id更新最后一条刷新好友任务状态
def updateTaskStatus(wx_main_id,mySqlUtil,logger,status,msg):
    try:
        sql = "select uuid from wx_account_info w where wx_id='%s'" % wx_main_id
        rs = mySqlUtil.getData(sql)
        if len(rs) > 0:
            task_uuid = rs[0][0]
            sql="select taskSeq from wx_task_manage where actionType=9 and status=2 and uuid='%s ' order by createTime desc" % str(task_uuid)
            rs = mySqlUtil.getData(sql)
            if len(rs) > 0:
                taskSeq = rs[0][0]
                sql = "update wx_task_manage set remarks='%s',endTime=now(),status=%d where taskSeq=%d" % (msg,status, taskSeq)
                mySqlUtil.execSql(sql)
        else:
            logger.info("微信状态异常，不再刷新好友")
    except Exception as e:
        alarm("更新刷新好友任务状态时异常，请检查日志并处理")
#根据url获取文件，保存到data下面的updateFriend文件夹下
def downloadFile(url,wx_main_id):
    uuid=uuid1()
    downPath = './data/updateFriend/'
    if not os.path.exists(downPath):
        os.makedirs(downPath)
    filePath = downPath+'%s.txt' % uuid
    urllib.request.urlretrieve(url, filePath)
    if os.path.exists(filePath):
        return filePath
    else:
        msg="%s刷新好友时下载文件失败"% wx_main_id
        raise Exception(msg)

def is_one_line(global_line, cur_line):
    if ("wx:" in global_line or "friend:" in global_line) :
        if global_line.count("#^#") == 5:
            if cur_line.count("#^#") != 0:
                return (1, global_line)

        return (0, global_line+'@!ef1K@c'+cur_line)
    elif "member:" in global_line :
        if global_line.count("#^#") == 4:
            if cur_line.count("#^#") != 0:
                return (1, global_line)

        return (0, global_line+'@!ef1K@c'+cur_line)
    else:
        return (0, cur_line)

#读文件内容并返回
def readFileContent(filePath,logger):
    try:
        result_flag=1
        distinct_group_id_in_member=set()
        format_content = {'wx_id': None, 'wx': None, 'friend': {}, 'member': {}, 'remark': {},'group_id_list':distinct_group_id_in_member,'target_id':''}
        with open(filePath,'r',encoding='utf8') as file_obj:
            file_lines=file_obj.readlines()
            target_id='0'
            update_type='0'
            if '#=#' in file_lines[0]:
                first_line=file_lines.pop(0).replace('\n', '')
                update_type,target_id=str(first_line).split("#=#")
                format_content['target_id']=target_id
            global_line =""
            for line_str in file_lines:
                (result, global_line) = is_one_line(global_line, line_str)
                if result == 1:
                    parse_file_content(global_line, format_content)
                    global_line = line_str
            if global_line and global_line.count("#^#") in (4,5):
                parse_file_content(global_line, format_content)

        if os.path.exists(filePath):
            os.remove(filePath)
        if update_type=='1' and target_id not in format_content['friend'].keys():
            result_flag=0
            repeat_times=repeatUpdateFriend(target_id)
            if repeat_times:
                logger.info("刷新好友文件不存在%s的信息，20秒后将开始第%s次重新刷！"% (target_id,str(repeat_times)))
                newProcess = Process(target=update_one_friend, args=(target_id,format_content['wx_id']))
                newProcess.start()
            else:
                logger.info("刷新好友文件不存在%s的信息，1分钟内刷新了3次，不再刷新！" % target_id)
        return format_content,result_flag
    except Exception as e:
        logger.warn(traceback.format_exc())

def parse_file_content(line_str, format_content):
    if line_str and len(line_str) > 3:
        line_str = line_str.replace('\n', '').replace("\'", "\\\'").replace("\"", "\\\"")
        # line_str = line_str.replace("@!ef1K@c", '\n').replace("@!ef2K@c", '\r').replace("@!ef3K@c", '\r\n').replace("@!ef4K@c", '\n\r')
        if 'wx:' == line_str[:3]:
            wx_info_list = line_str[3:].split("#^#")
            if len(wx_info_list) == 6:
                format_content['wx_id'] = wx_info_list[0]
                format_content['wx'] = {'wx_id': wx_info_list[0], 'wx_name': wx_info_list[1],
                                        'sex': wx_info_list[2], 'head_picture': wx_info_list[3],
                                        'zone': wx_info_list[4], 'signature': wx_info_list[5]}
            else:
                raise Exception("wx:文件格式不正确:%s" % line_str)
        elif 'friend:' == line_str[
                          :7]:  # friend:weixin#^#微信团队#^#http://wx.qlogo.cn/mmhead/cypR72jV8BHjDwNh3Nc1YcsgzmiaZacpR1dgiaibt4QuMs/0#^#微信团队#^#3#^#
            friend_info = line_str[7:].split("#^#")
            if len(friend_info) == 6:
                format_content['friend'][friend_info[0]] = {'wx_id': friend_info[0],
                                                            'nickname': friend_info[1],
                                                            'head_picture': friend_info[2],
                                                            'remark': friend_info[3],
                                                            'notice': friend_info[4],
                                                            'group_owner': friend_info[5]}
            else:
                raise Exception("friend:文件格式不正确:%s" % line_str)
        elif 'member:' == line_str[:7]:  # member:group_id#^#wx_id#^#head_picture#^#remark#^#view_name
            member_info = line_str[7:].split("#^#")  #
            if len(member_info) == 5:
                format_content['member'][member_info[0] + "#^#" + member_info[1]] = {'group_id': member_info[0],
                                                                                     'wx_id': member_info[1],
                                                                                     'head_picture': member_info[2],
                                                                                     'view_name': member_info[4]}
                format_content['group_id_list'].add(member_info[0])#所有有群成员的群
                if member_info[3]:
                    format_content['remark'][member_info[1] + "#^#" + format_content['wx_id']] = {'wx_id': member_info[1],'remark': member_info[3]}
            else:
                raise Exception("member:文件格式不正确:%s" % line_str)
#获取数据库里面现有的数据并返回
def readDbContent(wx_id,mySqlUtil,logger,file_content):
    try:
        distinct_group_id_in_member=set()
        target_id=file_content['target_id']
        if target_id=='0':
            target_id=False
        format_content_db ={'wx_id':None,'wx':None,'friend':{},'member':{},'remark':{},'group_id_list':distinct_group_id_in_member,'target_id':target_id}
        sql = "select wx_id,wx_name,sex,head_picture,zone,signature from wx_account_info where wx_id='"+str(wx_id)+"'"
        rs = mySqlUtil.getData(sql)
        if len(rs)>0:
            result=rs[0]
            format_content_db['wx_id']=result[0]
            format_content_db['wx'] = {'wx_id': result[0], 'wx_name': result[1],
                                    'sex': result[2], 'head_picture': result[3],
                                    'zone': result[4], 'signature': result[5]}
        sql = "select ta.wx_id,tb.wx_name,tb.head_picture,ta.remark from wx_friend_rela ta " \
              " left join wx_friend_list tb on ta.wx_id=tb.wx_id " \
              " where ta.wx_main_id='"+str(wx_id)+"' and ta.wx_id not like '%@%'"
        if target_id and '@' not in target_id:
            sql="select ta.wx_id,tb.wx_name,tb.head_picture,ta.remark from wx_friend_rela ta " \
              " left join wx_friend_list tb on ta.wx_id=tb.wx_id " \
              " where ta.wx_main_id='"+str(wx_id)+"' and ta.wx_id ='"+target_id+"'"
        if not target_id or ( target_id and '@' not in target_id):
            rs = mySqlUtil.getData(sql)
            if len(rs)>0:
                for result in rs:
                    format_content_db['friend'][result[0]]={'wx_id': result[0],
                                                                  'nickname': result[1],
                                                                  'head_picture': result[2],
                                                                  'remark': result[3],
                                                                  'notice': '',
                                                                  'group_owner': ''}

        sql = "select ta.wx_id,tb.group_name,tb.head_picture,ta.remark,tb.notice,tb.wx_id from wx_friend_rela ta " \
              " left join wx_group_info tb on ta.wx_id=tb.group_id  " \
              " where ta.wx_main_id='"+str(wx_id)+"' and ta.wx_id like '%@%'"
        if target_id and '@' in target_id:
            sql="select ta.wx_id,tb.group_name,tb.head_picture,ta.remark,tb.notice,tb.wx_id from wx_friend_rela ta " \
              " left join wx_group_info tb on ta.wx_id=tb.group_id  " \
              " where ta.wx_main_id='"+str(wx_id)+"' and ta.wx_id='"+target_id+"'"
        if not target_id or ( target_id and '@' in target_id):
            rs = mySqlUtil.getData(sql)
            if len(rs) > 0:
                for result in rs:
                    format_content_db['friend'][result[0]]={'wx_id': result[0],
                                                                      'nickname': result[1],
                                                                      'head_picture': '',
                                                                      'remark': result[3],
                                                                      'notice': result[4],
                                                                      'group_owner': result[5]}
        group_id_str="','".join([item for item in file_content['friend'].keys() if '@' in item])
        sql = "select ta.group_id,ta.wx_id,ta.head_picture,IFNULL(tc.remark,''),ta.view_name from wx_group_member ta " \
              " left join wx_group_member_remark tc on tc.wx_id=ta.wx_id and tc.wx_main_id='"+str(wx_id)+"' " \
              " where ta.group_id in ('"+group_id_str+"') or ta.group_id in " \
              " (select tb.wx_id from wx_friend_rela tb where tb.wx_main_id='"+str(wx_id)+"')"
        if target_id and '@' in target_id:
            sql = "select ta.group_id,ta.wx_id,ta.head_picture,IFNULL(tc.remark,''),ta.view_name from wx_group_member ta " \
                  " left join wx_group_member_remark tc on tc.wx_id=ta.wx_id and tc.wx_main_id='" + str(wx_id) + "' " \
                  " where ta.group_id ='"+target_id+"'"
        if not target_id or (target_id and '@' in target_id):
            rs = mySqlUtil.getData(sql)
            if len(rs) > 0:
                for result in rs:
                    format_content_db['member'][result[0]+"#^#"+result[1]]={'group_id':result[0],
                                                                            'wx_id': result[1],
                                                                            'head_picture': result[2],
                                                                            'view_name': result[4]}
                    format_content_db['group_id_list'].add(result[0])
                    if result[3]:
                        format_content_db['remark'][result[1]+"#^#"+format_content_db['wx_id']] = {'wx_id': result[1],
                                                                                                   'remark': result[3]}
        return format_content_db
    except Exception as e:
        logger.warn(traceback.format_exc())
#对比数据，找出差异，按新增、修改、删除分类
def compareData(file_content,db_content,logger):
    logger.debug(file_content==db_content)
    # logger.debug(file_content)
    # logger.debug(db_content)
    compareResult={'wx'    :{'upd':{}},
                   'friend':{'del':[],'ins':[],'upd':[]},
                   'member':{'del':[],'ins':[],'upd':[]},
                   'remark':{'del':[],'ins':[],'upd':[]},
                   'wx_id':file_content['wx_id'],
                   'group_id_list':[]}
    if file_content['group_id_list']:
        compareResult['group_id_list']=file_content['group_id_list']
    if db_content['wx']!=file_content['wx']:
        compareResult['wx']['upd']=file_content['wx']
    # if file_content['friend']!=db_content['friend']:
    compareWithKey(compareResult, file_content, db_content, 'friend')
    if file_content['member']!=db_content['member']:
        compareWithKey(compareResult, file_content, db_content, 'member')
    if file_content['remark']!=db_content['remark']:
        compareWithKey(compareResult, file_content, db_content, 'remark')
    return compareResult
#对比核心算法
def compareWithKey(compareResult,file_content,db_content,keyWord):
    friend_id_list=file_content[keyWord].keys()
    if keyWord=='friend':
        #找到没有群成员的群id（被踢的群）
        ex_del_list=[item for item in file_content[keyWord].keys() if '@' in item and item not in file_content['group_id_list']]
        friend_id_list=list(set(friend_id_list) - set(ex_del_list))
        if ex_del_list:
            compareResult[keyWord]['invalid_group']=ex_del_list
    ins_id_list = list(set(friend_id_list) - set(db_content[keyWord].keys()))
    del_id_list = list(set(db_content[keyWord].keys()) - set(friend_id_list))
    exists_id_list_file = list(set(db_content[keyWord].keys()) - set(del_id_list))
    compareResult[keyWord]['ins'] = [file_content[keyWord][item] for item in ins_id_list]
    compareResult[keyWord]['del'] = [db_content[keyWord][item] for item in del_id_list]
    compareResult[keyWord]['upd'] = [file_content[keyWord][item] for item in exists_id_list_file if
                                      db_content[keyWord][item] != file_content[keyWord][item]]

#执行差异
def execUpdateAction(difference,mySqlUtil,logger):
    #{'wx': {'upd': []},
    # 'friend': {'del': [], 'ins': [], 'upd': []},
    # 'member': {'del': [], 'ins': [], 'upd': []},
    # 'remark': {'del': [], 'ins': [], 'upd': []}}
    # logger.debug(difference)
    wx_main_id=difference['wx_id']
    if difference['wx']['upd']:
        wx_info=difference['wx']['upd']
        sql="update wx_account_info set wx_name='%s',sex='%s',head_picture='%s',zone='%s',signature='%s' where wx_id='%s'"
        res_count=mySqlUtil.execSql(sql % (str(wx_info['wx_name']),str(wx_info['sex']),str(wx_info['head_picture']),str(wx_info['zone']),str(wx_info['signature']),str(wx_info['wx_id'])))
        if res_count:
            logger.info("更新了%s的主号信息" %str(wx_main_id))
    if difference['friend']['del']:
        #'wx_id': result[0],'nickname': result[1],'head_picture': result[2],'remark': result[3],
        # 'notice': result[4], 'group_owner': result[5]
        feiend_rela_list=[(wx_main_id,item["wx_id"]) for item in difference['friend']['del'] if '@' not in item["wx_id"]]
        if feiend_rela_list:
            sql="delete from wx_friend_rela where wx_main_id=%s and wx_id=%s"
            del_count=mySqlUtil.executeMany(sql,feiend_rela_list)
            if del_count>0:
                logger.info("删除了%s条好友关系信息" % str(del_count))
    if difference['friend']['ins']:
        friend_rela_list=[(item["wx_id"],wx_main_id,item["remark"]) for item in difference['friend']['ins']]
        if friend_rela_list:
            sql="insert into wx_friend_rela (wx_id,wx_main_id,remark,add_time,state) values(%s,%s,%s,now(),1)"
            ins_count = mySqlUtil.executeMany(sql, friend_rela_list)
            if ins_count and ins_count > 0:
                logger.info("添加了%s条好友关系信息" % str(ins_count))
            group_id_list=difference['group_id_list']
            if group_id_list:
                group_id_list_format=[(wx_main_id,item) for item in group_id_list]
                sql="update wx_friend_rela set state=1 where wx_main_id=%s and wx_id=%s"
                ins_count = mySqlUtil.executeMany(sql, group_id_list_format)
                if ins_count and ins_count > 0:
                    logger.info("恢复了%s条好友关系信息" % str(ins_count))
        friend_info_list=[(item["wx_id"],item["nickname"],item["head_picture"]) for item in difference['friend']['ins'] if '@' not in  item["wx_id"]]
        friend_id_list=[item["wx_id"] for item in difference['friend']['ins'] if '@' not in  item["wx_id"]]
        if friend_info_list:
            sql="select wx_id from wx_friend_list where wx_id in ('%s')" % "','".join(friend_id_list)
            rs=mySqlUtil.getData(sql)
            exists_list=[]
            if len(rs)>0:
                for result in rs:
                    exists_list.append(result[0])
            friend_info_list_final=[item for item in friend_info_list if item[0] not in exists_list]
            sql="insert into wx_friend_list (wx_id,wx_name,head_picture) values(%s,%s,%s)"
            ins_count = mySqlUtil.executeMany(sql, friend_info_list_final)
            if type(ins_count)==str and  "Duplicate entry" in ins_count:
                logger.debug("同一个好友不同的人添加，只保留一个")
                ins_count=0
            if ins_count and ins_count > 0:
                logger.info("添加了%s条好友信息" % str(ins_count))
        group_info_list=[(item["wx_id"],item["nickname"],item["head_picture"],item["notice"],item["group_owner"]) for item in difference['friend']['ins'] if '@' in  item["wx_id"]]
        group_id_list = [item["wx_id"] for item in difference['friend']['ins'] if '@' in item["wx_id"]]
        if group_info_list:
            sql = "select group_id from wx_group_info where group_id in ('%s')" % "','".join(group_id_list)
            rs = mySqlUtil.getData(sql)
            exists_list = []
            if len(rs) > 0:
                for result in rs:
                    exists_list.append(result[0])
            group_info_list_final=[item for item in group_info_list if item[0] not in exists_list]
            sql = "insert into wx_group_info (group_id,group_name,head_picture,notice,wx_id,create_date) values(%s,%s,%s,%s,%s,now())"
            ins_count = mySqlUtil.executeMany(sql, group_info_list_final)
            if type(ins_count)==str:
                if "Duplicate entry" in ins_count:
                    logger.debug("同一个群,不同主号会添加两次，忽略")
                else:
                    logger.info(ins_count)
                ins_count=0
            if ins_count and ins_count > 0:
                logger.info("添加了%s条群信息" % str(ins_count))
    if difference['friend']['upd']:
        friend_rela_list = [( item["remark"],item["wx_id"], wx_main_id) for item in difference['friend']['upd']]
        if friend_rela_list:
            sql="update wx_friend_rela set remark=%s where wx_id=%s and wx_main_id=%s"
            upd_count=mySqlUtil.executeMany(sql, friend_rela_list)
            if upd_count>0:
                logger.info("更新了%s条好友关系信息" % str(upd_count))
        friend_info_list = [( item["nickname"], item["head_picture"],item["wx_id"]) for item in
                            difference['friend']['upd'] if '@' not in item["wx_id"]]
        if friend_info_list:
            sql = "update wx_friend_list set wx_name=%s,head_picture=%s where wx_id=%s"
            upd_count = mySqlUtil.executeMany(sql, friend_info_list)
            if upd_count>0:
                logger.info("更新了%s条好友信息" % str(upd_count))
        group_info_list = [(item["nickname"],  item["notice"], item["group_owner"],item["wx_id"])
                           for item in difference['friend']['upd'] if '@' in item["wx_id"]]
        if group_info_list:
            sql = "update wx_group_info set group_name=%s, notice=%s, wx_id=%s where group_id=%s "
            upd_count = mySqlUtil.executeMany(sql, group_info_list)
            if upd_count>0:
                logger.info("更新了%s条群信息" % str(upd_count))
    if difference['member']['del']:
        del_group_list=[]
        if difference['friend'].get("del"):
            del_group_list=difference['friend'].get("del")
        group_info_list = [item["wx_id"] for item in del_group_list  if '@' in item["wx_id"]]#需要删的群
        if 'invalid_group' in difference['friend'].keys():
            group_info_list = difference['friend']['invalid_group'] + group_info_list
        #'group_id':result[0],'wx_id': result[1],'head_picture': result[2],'view_name': result[4]
        member_info_list=[(item['group_id'],item['wx_id']) for item in difference['member']['del'] if item['group_id'] not in group_info_list]
        if len(member_info_list)>0:
            sql_insert = "insert into wx_group_member_del select  *,now() from wx_group_member " \
                         " where group_id=%s and wx_id=%s and TIMESTAMPDIFF(SECOND,add_date,now())>120"
            mySqlUtil.executeMany(sql_insert, member_info_list)
            sql_del = "delete from wx_group_member where group_id=%s and wx_id=%s and TIMESTAMPDIFF(SECOND,add_date,now())>120"
            del_count = mySqlUtil.executeMany(sql_del, member_info_list)
            logger.info("删除了%s条群成员信息" % str(del_count))
    if difference['member']['ins']:
        member_info_list=[(item['group_id'],item['wx_id'],item['head_picture'],item['view_name']) for item in difference['member']['ins']]
        member_del_list=[(item['group_id'],item['wx_id']) for item in difference['member']['ins']]
        update_state_list=[(wx_main_id,item['group_id']) for item in difference['member']['ins']]
        sql_state="update wx_friend_rela set state=1 where wx_main_id=%s and wx_id=%s and state=3"
        conut_num=mySqlUtil.executeMany(sql_state, update_state_list)
        if conut_num and conut_num>0:
            logger.info("恢复了%s条群关系信息" % str(conut_num))
        sql_del="delete from wx_group_member_del where group_id=%s and wx_id=%s"
        mySqlUtil.executeMany(sql_del, member_del_list)
        sql="insert into wx_group_member (group_id,wx_id,head_picture,view_name,add_date) values(%s,%s,%s,%s,now())"
        ins_count = mySqlUtil.executeMany(sql, member_info_list)
        if type(ins_count) == str and "Duplicate entry" in ins_count:
            logger.debug("同一个群成员添加两次，忽略")
            ins_count = 0
        if ins_count and ins_count>0:
            logger.info("添加了%s条群成员信息" % str(ins_count))
    if difference['member']['upd']:
        member_info_list=[(item['head_picture'],item['view_name'],item['group_id'],item['wx_id']) for item in difference['member']['upd']]
        sql="update wx_group_member set head_picture=%s,view_name=%s where group_id=%s and wx_id=%s"
        upd_count = mySqlUtil.executeMany(sql, member_info_list)
        logger.info("更新了%s条群成员信息" % str(upd_count))
    if difference['remark']['del']:
        #[result[1]+"#^#"+format_content_db['wx_id']] = result[3]
        remark_info_list=[(item['wx_id'],wx_main_id) for item in difference['remark']['del']]
        sql="delete from wx_group_member_remark where wx_id=%s and wx_main_id=%s"
        del_count = mySqlUtil.executeMany(sql, remark_info_list)
        logger.info("删除了%s条备注信息" % str(del_count))
    if difference['remark']['ins']:
        remark_info_list=[(item['wx_id'],wx_main_id,item['remark']) for item in difference['remark']['ins']]
        sql="insert into wx_group_member_remark(wx_id,wx_main_id,remark) values(%s,%s,%s)"
        ins_count=mySqlUtil.executeMany(sql, remark_info_list)
        logger.info("添加了%s条备注信息" % str(ins_count))
    if difference['remark']['upd']:
        remark_info_list=[(item['wx_id'],wx_main_id,item['remark']) for item in difference['remark']['ins']]
        sql="update wx_group_member_remark set remark=%s where wx_id=%s and wx_main_id=%s"
        upd_count = mySqlUtil.executeMany(sql, remark_info_list)
        logger.info("更新了%s条备注信息" % str(upd_count))
    sql="select ta.seqId from wx_chat_info ta where not exists (select 1 from wx_friend_rela tb where ta.wx_id=tb.wx_id and ta.wx_main_id=tb.wx_main_id) and ta.wx_main_id='" + wx_main_id + "' order by seqId desc limit 1"
    rs=mySqlUtil.getData(sql) #
    if len(rs)>0 and len(rs[0])>0 and rs[0][0]:
        seqId=rs[0][0]
        sql_sys="select ta.seqId from wx_chat_info ta where not exists (select 1 from wx_friend_rela tb where ta.wx_id=tb.wx_id and ta.wx_main_id=tb.wx_main_id) and ta.wx_main_id='" + wx_main_id + "' and type=4 and send_time < NOW()-INTERVAL 1 HOUR "
        rs_sys=mySqlUtil.getData(sql_sys)
        sys_list=[]
        if len(rs_sys) > 0:
            for result in rs_sys:
                sys_list.append(str(result[0]))
        backup_sql = "insert into wx_chat_info_his (wx_main_id, wx_id,send_time,type,content,send_type,status,group_member_name,msgId,createTime,group_member_id,head_picture,seqId)" \
                     " select wx_main_id, wx_id,send_time,type,content,send_type,status,group_member_name,msgId,createTime,group_member_id,head_picture,seqId " \
                     " from wx_chat_info where ((seqId<="+str(seqId)+" and type!=4) or ( type=4 and seqId in ('"+"','".join(sys_list)+"')))  and wx_main_id='" + wx_main_id + "'"
        mySqlUtil.execSql(backup_sql)
        del_chat_sql = "delete from wx_chat_info where ((seqId<="+str(seqId)+" and type!=4) or ( type=4 and seqId in ('"+"','".join(sys_list)+"')))  and wx_main_id='" + wx_main_id + "'"
        mySqlUtil.execSql(del_chat_sql)

#用于开发时，没有文件进行测试的情况
def create_file(mySqlUtil):
    uuid = uuid1()
    downPath = './data/updateFriend/'
    if not os.path.exists(downPath):
        os.makedirs(downPath)
    filePath = downPath + '%s.txt' % uuid
    fine_lines=[]
    # wx_id#^#wx_name#^#sex#^#head_picture#^#zone#^#signature
    sql="select wx_id,wx_name,sex,head_picture,zone,signature from wx_account_info where wx_id='wxid_fr46gbs66khb12'"
    rs=mySqlUtil.getData(sql)
    str="wx:%s#^#%s#^#%s#^#%s#^#%s#^#%s\n" %(rs[0][0],rs[0][1],rs[0][2],rs[0][3],rs[0][4],rs[0][5])
    fine_lines.append(str)
    sql="select ta.wx_id,tb.wx_name,tb.head_picture,ta.remark from wx_friend_rela ta,wx_friend_list tb where ta.wx_id=tb.wx_id and ta.wx_main_id='wxid_fr46gbs66khb12'"
    #friend: wx_id#^# nickname#^# head_picture#^#remark#^# type
    rs=mySqlUtil.getData(sql)
    str="friend:%s#^#%s#^#%s#^#%s#^##^#\n"
    for result in rs:
        fine_lines.append(str % (result[0],result[1],result[2],result[3]))
    sql="select ta.wx_id,tb.group_name,tb.head_picture,ta.remark,tb.notice,tb.wx_id from wx_friend_rela ta,wx_group_info tb where ta.wx_id=tb.group_id and ta.wx_main_id='wxid_fr46gbs66khb12'"
    rs = mySqlUtil.getData(sql)
    str = "friend:%s#^#%s#^#%s#^#%s#^#%s#^#%s\n"
    for result in rs:
        fine_lines.append(str % (result[0], result[1], result[2], result[3], result[4], result[5]))
    sql="select ta.group_id,ta.wx_id,ta.head_picture,IFNULL(tc.remark,''),ta.view_name from wx_group_member ta left join wx_friend_rela tb  on ta.group_id=tb.wx_id  left join wx_group_member_remark tc on tc.wx_id=ta.wx_id and tc.wx_main_id=tb.wx_main_id where tb.wx_main_id='wxid_fr46gbs66khb12' "
    rs = mySqlUtil.getData(sql)
    str = "member:%s#^#%s#^#%s#^#%s#^#%s\n"
    for result in rs:
        fine_lines.append(str % (result[0], result[1], result[2], result[3], result[4]))
    file_obj = open(filePath, 'w',encoding='utf8')
    file_obj.writelines(fine_lines)
    file_obj.close()
    return filePath

#睡眠20秒后下发刷新指定好友的任务
def update_one_friend(wx_id,wx_main_id):
    time.sleep(20)
    logger = getLogger('./log/UpdateFriend.log')
    mySqlUtil = MysqlDbPool.MysqlConn()
    try:
        # 判断是否有多余的任务
        # 判断app心跳是否正常
        sql = """ select uuid from wx_account_info w where wx_id='%s' and if_start='1' and is_first_time='0'
                  and not EXISTS (select 1 from wx_task_manage t where t.status in (1,2) and t.actionType=9 
                  and t.uuid=w.uuid and (t.startTime is null or t.startTime < date_sub(now(),interval 1 minute)))
                  and EXISTS (select 1 from wx_status_check s where s.program_type='1' and s.wx_main_id=w.wx_id and 
                  s.last_heartbeat_time >= date_sub(now(),interval 3 minute))""" % wx_main_id
        rs=mySqlUtil.getData(sql)
        if rs and len(rs)>0:
            redisUtil.publishFlushFriend("flush_friend", "%s:~:1#=#%s" % (wx_main_id,wx_id))
            task_uuid=rs[0][0]
            taskSeq = round(time.time() * 1000 + random.randint(100, 999))
            sql = "INSERT INTO wx_task_manage(taskSeq,uuid,actionType,createTime,status,priority, startTime)" \
                  "VALUES(%d,'%s',9,now(),2,5, now())" % (taskSeq, task_uuid)
            mySqlUtil.execSql(sql)
        else:
            logger.info("微信状态异常，不再刷新好友")
    except Exception as e:
        alarm("重写刷新好友任务异常，请检查日志并处理")
    finally:
        mySqlUtil.conn.close()
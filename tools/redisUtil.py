import random
import traceback

import redis
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
BASEDIR = os.getcwd()

logger = getLogger('./log/redisUtil.log')
# # 初始化config
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)

# 初始化redis
redis_ip = confAllItems.getOneOptions('redis', 'ip')
redis_port = confAllItems.getOneOptions('redis', 'port')
redis_db = confAllItems.getOneOptions('redis', 'db')
redis_pwd = confAllItems.getOneOptions('redis', 'pwd')


def taskSeqSet(taskSeq,redis_db,expireTime = None):
    try:
        redisClient = redis.StrictRedis(host=redis_ip, port=redis_port, db=redis_db, password=redis_pwd)
        redisClient.set(taskSeq, int(time.time()), ex=expireTime, nx=True)
    except (Exception) as e:
        logger.warn(traceback.format_exc())
def repeatUpdateFriend(wx_id):
    try:
        redisClient = redis.StrictRedis(host=redis_ip, port=redis_port, db=redis_db, password=redis_pwd)
        repeat_times=redisClient.get(wx_id+"_repeatUpdateFriend")
        if not repeat_times:
            repeat_times = 0
        if int(repeat_times)>2:
            return 0
        else:
            redisClient.set(wx_id + "_repeatUpdateFriend", int(repeat_times)+1, ex=120)
            return int(repeat_times)+1
    except (Exception) as e:
        logger.warn(traceback.format_exc())
        return 0
def taskSeqGet(taskSeq,redis_db):
    try:
        redisClient = redis.StrictRedis(host=redis_ip, port=redis_port, db=redis_db, password=redis_pwd)
        taskSeqGetRet = redisClient.get(taskSeq)
        expireTime = 60 * 60 * 24
        redisClient.set(taskSeq, int(time.time()), ex=expireTime, nx=True)
    except (Exception) as e:
        logger.warn(traceback.format_exc())
        taskSeqGetRet = "error"

    return taskSeqGetRet

#订阅消息频道并返回对象
def subscriber(channl, only_one):
    rc = redis.StrictRedis(host=redis_ip, port=redis_port, db=redis_db, password=redis_pwd)
    if only_one :
        list = rc.pubsub_channels(channl)
        if list and len(list) > 0:
            return None
    ps = rc.pubsub()
    ps.subscribe(channl)  # 订阅消息频道
    return ps

def publishMessage(u2Con, wx_main_id, channel_id, message, timeout, taskSeq):
    try:
        redisClient = redis.StrictRedis(host=redis_ip, port=redis_port, db=redis_db, password=redis_pwd)
        redisClient.set(wx_main_id,"") #清理上次的结果
        redisClient.publish(channel_id, message)
        return "ok"
    except (Exception) as e:
        logger.exception(e)
        return "失败"

def publishMessageNew(u2Con, wx_main_id, channel_id, message, timeout, taskSeq):
    try:
        redisClient = redis.StrictRedis(host=redis_ip, port=redis_port, db=redis_db, password=redis_pwd)
        redisClient.set(wx_main_id,"") #清理上次的结果
        redisClient.publish(channel_id, message)
    except (Exception) as e:
        logger.exception(e)
        return "失败"

    taskSeq = str(taskSeq)
    timeGate = time.time()
    #start_app_flag = False app是否启动在任务分发时已判断
    while True:
        # if time.time() - timeGate >= 5 and start_app_flag == False:#5秒钟内没结果重启app
        #     if u2Con != 'type':
        #         wxUtil.appStart(u2Con, logger)
        #     start_app_flag = True
        if time.time() - timeGate >= timeout:
            return "超时"
        getResult = redisClient.get(wx_main_id)
        getResult =getResult.decode('utf-8')
        if getResult != '':
            if taskSeq != '':#验证序列号
                if taskSeq not in getResult:
                    continue
            return getResult
        else:
            time.sleep(0.1)

def publishFlushFriend(channel_id, message):
    try:
        redisClient = redis.StrictRedis(host=redis_ip, port=redis_port, db=redis_db, password=redis_pwd)
        redisClient.publish(channel_id, message)
    except (Exception) as e:
        logger.exception(e)
        return "失败"

def publishMsgGen(taskSeq,taskUuid,wxMainId, sendMsg, mysqlUtil):
    taskManageSql = """INSERT INTO `wxAuto`.`wx_task_manage` (
                            `taskSeq`,
                            `uuid`,
                            `actionType`,
                            `createTime`,
                            `heartBeatTime`,
                            `cronTime`,
                            `priority`,
                            `status`,
                            `operViewName`
                        )
                        VALUES
                            (
                                %s,
                                "%s",
                                '6',
                                now(),
                                now(),
                                now(),
                                '0',
                                '2',
                                "edent")
                            """ %(taskSeq,taskUuid)
    mysqlUtil.excSql(taskManageSql)
    wx_main_id = wxMainId
    channel_id = "send_message"
    message = sendMsg
    publishMessage("", wx_main_id, channel_id, message, 20, taskSeq)

if __name__ == '__main__':
    taskSeq = "1553681433482"
    redis_db = 3
    redisClient = redis.StrictRedis(host=redis_ip, port=redis_port, db=redis_db, password=redis_pwd)
    taskSeqGetRet = redisClient.get(taskSeq)
    print(taskSeqGetRet)
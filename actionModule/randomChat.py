import traceback, os, redis, random, base64
from tools import redisUtil
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
from lib.WxElementConf import WxElementConf

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('randomChat.log')
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
wxElementConf = WxElementConf(logger)


confAllItems = ConfAnalysis(logger, configFile)
redis_ip = confAllItems.getOneOptions('redis', 'ip')
redis_port = confAllItems.getOneOptions('redis', 'port')
redis_db = confAllItems.getOneOptions('redis', 'db')
redis_pwd = confAllItems.getOneOptions('redis', 'pwd')
emojiList = ["[尴尬]","[流泪]","[白眼]","[坏笑]","[鄙视]","[阴险]","[奸笑]","[嘿哈]"]

def getCurrentFriendList(DEV_ID,currentWx,mySqlUtil):
    '''
    聊天功能专属，获取聊天好友
    当前实现本地机器上所有有效已注册微信号
    :return:
    '''
    friendListRet = []
    exeSql = """SELECT A.wx_id FROM `wx_friend_rela` A
                    where wx_main_id = '%s' and wx_id != wx_main_id
                    and A.wx_id in (select DISTINCT(wx_id) from wx_account_info)""" %currentWx
    executeRet = mySqlUtil.fetchData(exeSql)
    if executeRet[0] == 1:
        for item in executeRet[1]:
            friendListRet.append(item[0])
    return friendListRet

def action(logger, u2Con, taskItemInfo, mySqlUtil):
    '''
        自动聊天脚本
        :param u2Con:
        :param taskItemInfo:
        :return:
        '''
    remarks = '#'
    # 初始化config
    configFile = '%s/conf/moduleConfig.conf' % BASEDIR
    confAllItems = ConfAnalysis(logger, configFile, '')
    # 设备编号
    DEV_ID = confAllItems.getOneOptions('devInfo', 'dev')
    taskSeq = taskItemInfo[0]
    devName = taskItemInfo[6]
    operViewName = taskItemInfo[7]
    try:
        currentWxSql = """SELECT  wx_id from wx_account_info where uuid = \'%s\'""" %taskItemInfo[1]
        currentWxRet = mySqlUtil.fetchData(currentWxSql)
        wx_main_id = currentWxRet[1][0][0]
        # 随机性朋友
        friendList = getCurrentFriendList(DEV_ID, wx_main_id,mySqlUtil)
        if not friendList:
            logger.warn("%s 随机聊天找不到对应好友" %(wx_main_id))
            status = 3
            remarks = "%s 随机聊天找不到对应好友" %(wx_main_id)
        else:
            if len(friendList) <= 1:
                randomFriendList = friendList
            else:
                randomFriendList = random.sample(friendList, random.randint(1, 2))
            logger.debug("%s|%s|%s|发送随机聊天消息|[task - randomChat] Source: %s , Target: %s" % (operViewName, taskSeq, devName, wx_main_id, randomFriendList))
            redisClient = redis.StrictRedis(host=redis_ip, port=redis_port, db=1, password=redis_pwd)
            for frinedId in randomFriendList:
                theline=redisClient.get(random.randint(1, 4435959)).decode('utf8').replace(' ', '')
                if random.randint(1, 5) > 3:
                    randomEmoji = random.sample(emojiList, 1)[0]
                else:
                    randomEmoji = ""
                content = '%s %s' % (theline[:-1], randomEmoji * random.randint(1, 3))

                # 发送到app处理
                taskSeqRan = round(time.time() * 1000 + random.randint(100, 999))
                logger.debug("%s|%s|%s|发送随机聊天消息|%s" % (operViewName, taskSeqRan, devName, content))

                getResult = redisUtil.publishMessage(u2Con, wx_main_id, 'send_message',
                                                  "%s:~:%d#^#%s#^#%s#^#%s#^#%d#^#1"
                                  % (wx_main_id, taskSeqRan, frinedId, base64.b64encode(content.encode('utf-8')),"", taskSeq),
                                                     20, '')
                sql = "insert into wx_chat_info(wx_main_id, wx_id,send_time,type,content,send_type,status,msgId)" \
                      "values('%s','%s',now(),'1','%s','1','1', '%d')" % \
                      ( wx_main_id, frinedId, content,round(time.time() * 1000 + random.randint(100, 999)))
                mySqlUtil.excSql(sql)
                logger.debug("%s|%s|%s|发送随机聊天消息|状态：%s" % (operViewName, taskSeq, devName, getResult))
                # time.sleep(random.randint(2, 4))

            status = 4
    except Exception as e:
        remarks = e
        logger.warn(traceback.format_exc())
        status = 3

    return (status, remarks)
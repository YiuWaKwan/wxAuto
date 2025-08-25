import redis,urllib
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('log/common.log')
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)

redis_ip = confAllItems.getOneOptions('redis', 'ip')
redis_port = confAllItems.getOneOptions('redis', 'port')
redis_db = confAllItems.getOneOptions('redis', 'db')
redis_pwd = confAllItems.getOneOptions('redis', 'pwd')
user_list = confAllItems.getOneOptions("alarm", "user_list")
alarm_server = confAllItems.getOneOptions("alarm", "alarm_server")

def messageNotice(wx_main_id, wx_id, error_msg, msgId, mySqlUtil):
    ''' 消息反馈 '''
    try:
        insert_wx_chat_info = "insert into wx_chat_info(wx_main_id,wx_id,send_time,type,content,send_type, msgId)" \
                              "values ('%s','%s',now(),'5','%s','2', '%s')" \
                              % (wx_main_id, wx_id, error_msg, msgId)
        update_wx_friend_rela = "update wx_friend_rela set last_chart_time=now(),last_chart_content='%s' where wx_main_id='%s' and wx_id='%s'" \
                                % (error_msg, wx_main_id, wx_id)
        mySqlUtil.execSql(insert_wx_chat_info)
        mySqlUtil.execSql(update_wx_friend_rela)
    except (Exception) as e:
        None

def alarm(msg):
    msg = urllib.parse.quote(msg)
    warn_msg = "%s?msg=%s&type=2&user=R_221&creator=maizq" % (alarm_server, msg)
    logger.info(warn_msg)
    warning(warn_msg)

def warning(url):
    http_client=urllib.request.urlopen(url, timeout = 5)
    print(http_client.read())
    return http_client.read()

def isApkRunning(u2Con):
    cmdResult=u2Con.adb_shell("pidof com.gz.pbs.copyfile")
    if cmdResult != None and len(cmdResult)>0:
        return True
    else:
        return False


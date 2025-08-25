import time,urllib
from lib.FinalLogger import *
from actionModule import getWxFriendList
from lib.ModuleConfig import ConfAnalysis
import traceback
from lib.FinalLogger import *
from tools import wxUtil
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.AL32UTF8'
# 初始化logger
logger = getLogger('./log/appManager.log')

BASEDIR = os.getcwd()
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)
user_list = confAllItems.getOneOptions("alarm", "user_list")
alarm_server = confAllItems.getOneOptions("alarm", "alarm_server")

def action(logger, u2ConStart, taskItemInfo, mySqlUtil):
    status = 4
    remark = "#"
    try:
        wxUtil.appStart(u2ConStart, logger)

        #发送刷新好友任务文件
        uuid = taskItemInfo[1]
        sql = "select wx_name from wx_account_info where uuid='%s' " % uuid
        wx_info = mySqlUtil.getData(sql)
        wx_name = ""
        if wx_info and len(wx_info) > 0:
            wx_name = wx_info[0][0]

        # 发送启动成功通知
        msg = "微信[%s]对应的消息接收程序停止运行，目前已经重启" % wx_name
        msg = urllib.parse.quote(msg)
        warn_url = "%s?msg=%s&type=2&user=%s&creator=maizq" % (alarm_server, msg, user_list)
        warning(warn_url)

    except Exception as e:
        status = 3
        remark = "执行消息获取app重启失败，发生未知异常"
        logger.error(traceback.format_exc())

    return (status, remark)


def warning(url):
    http_client=urllib.request.urlopen(url, timeout = 5)
    return http_client.read()
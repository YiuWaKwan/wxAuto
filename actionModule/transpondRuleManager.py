
import subprocess
import traceback
from lib.FinalLogger import getLogger
from tools import common

def action(logger, u2ConStart, taskItemInfo, mySqlUtil):
    status = 4
    remark = "#"
    try:
        sql = "select wx_id from wx_account_info where uuid='%s'" % taskItemInfo[1]
        wx_info = mySqlUtil.getData(sql)
        if wx_info and len(wx_info) > 0:
            wx_main_id = wx_info[0][0]
            message = "%s:~:transpond" % wx_main_id
            getResult = common.publishMessage(u2ConStart, wx_main_id, "transpond", message, 10, '')
            if "超时" == getResult:
                status = 3
                remark = getResult
            elif getResult == 'ok':
                logger.debug("执行成功")
            else:
                status = 3
                remark = "执行失败"
        else:
            status = 3
            remark = "微信信息有误，查询不到微信号"
    except Exception as e:
        status = 3
        remark = "刷新转发规则失败"
        logger.error(traceback.format_exc())

    return (status, remark)
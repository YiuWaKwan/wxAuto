
import traceback
from tools import wxUtil, common
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
from lib.WxElementConf import WxElementConf
# import emoji
# import datetime, random
from urllib import request

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/group_sent.log')
# 初始化config
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)
WxElementConf = WxElementConf(logger)

devId = confAllItems.getOneOptions('devInfo', 'dev')


# 群发入口方法
def action(_logger, u2ConStart, taskItemInfo, mySqlUtil):
    # if _logger:
        # logger = _logger
    rt = (3, "")

    taskSeq = taskItemInfo[0]
    (flag, gsInfo, gsReleList) = _queryMainInfo(taskSeq, mySqlUtil)
    gsId = gsInfo[0]
    (friendsId, friendsName) = _getFriendsIdAndName(gsReleList)
    if flag:
        status = 2
        _updateGsInfo(status, taskSeq, mySqlUtil)
        _updateGsRela(status, "", "", gsId, "','".join(friendsId), mySqlUtil)

        stime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        (T_or_F, remark) = _group_sent_message(u2ConStart, gsInfo[4], gsInfo[5], friendsName)
        if T_or_F:
            status = 3
        else:
            status = 4

        _updateGsInfo(status, taskSeq, mySqlUtil)
        _updateGsRela(status, remark, stime, gsId, "','".join(friendsId), mySqlUtil)

        rt = (4, "")
    else:
        msg = "群发任务：获取群发信息异常"
        rt = (3, msg)
        logger.warn(msg)

    return rt


# 推送文件到模拟器上
def _getFile(fileName, fileUrl, u2ConStart):
    remark = ""
    flag = True
    #清理模拟器文件
    u2ConStart.adb_shell("rm -rf  /storage/sdcard0/tencent/MicroMsg/WeiXin/*")
    time.sleep(0.1)
    targetFileName = 'data/%s' % fileName
    try:
        #下载文件
        fileObj = request.urlopen(fileUrl)
        fileContent = fileObj.read()
        with open(targetFileName, 'ab+') as f:#生成本地文件
            f.write(fileContent)
        #推送到模拟器
        u2ConStart.push(targetFileName, '/storage/sdcard0/tencent/MicroMsg/WeiXin/')
        time.sleep(0.2)
        #刷新文件时间
        # u2ConStart.adb_shell('touch /storage/sdcard0/tencent/MicroMsg/WeiXin/%s' % fileName[0])
        # 刷新文件
        # u2ConStart.adb_shell('am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d  file:///storage/sdcard0/tencent/MicroMsg/WeiXin/%s' % fileName[0])
        u2ConStart.adb_shell('am broadcast -a android.intent.action.MEDIA_MOUNTED -d  file:///storage/sdcard0/tencent/MicroMsg/WeiXin/')
        time.sleep(0.2)
        #删除本地文件
        os.remove(targetFileName)

    except Exception as e:
        logger.warn(traceback.format_exc())
        flag = False
        remark = "网络异常，文件从文件服务器下载失败：%s" % fileUrl

    return (flag, remark)


def _getFriendsIdAndName(gsReleList):
    wx_ids = []
    wx_names = []
    for r in gsReleList:
        wx_ids.append(r[1])
        wx_names.append(r[5])
    return (wx_ids, wx_names)


# 查询任务相关信息
def _queryMainInfo(task_seq, mySqlUtil):
    rt = (False, [], [])
    try:
        # 查询群发信息
        sql = """ select seq_id,wx_id,status,create_time,content,type,task_seq 
                  from wx_group_sent_info gsi where gsi.task_seq = %d """ % task_seq
        tlist = mySqlUtil.getData(sql)
        if tlist and len(tlist) > 0:
            gsInfo = tlist[0]
            gsInfoId = gsInfo[0]
            gsWxId = gsInfo[1]


            # 查询群发收信人信息
            sql = """ select group_sent_id,gsr.wx_id,status,gsr.remark,sent_time,case when ISNULL(fr.remark) then fl.wx_name else fr.remark end as wx_name 
                      from wx_group_sent_rela gsr 
                      LEFT JOIN wx_friend_list fl on gsr.wx_id = fl.wx_id
                      left join wx_friend_rela fr on fl.wx_id = fr.wx_id and fr.wx_main_id = '%s'
                      where status != 3 and gsr.group_sent_id = %d """ % (gsWxId, gsInfoId)
            gsReleList = mySqlUtil.getData(sql)

            rt = (True, gsInfo, gsReleList)
    except Exception as e:
        logger.error(e)
    return rt


# 更新任务相关信息
def _updateGsInfo(status, task_seq, mySqlUtil):
    rt = False
    try:
        sql = """ update wx_group_sent_info set status = '%s' where task_seq = %d """ % (status, task_seq)
        (flag, rts) = mySqlUtil.execSql(sql)
        if flag:
            rt = True
    except Exception as e:
        logger.error(e)
    return rt


# 完成状况更新
def _updateGsRela(status, remark, stime, gsId, wx_ids, mySqlUtil):
    rt = False
    try:
        sql = """ update wx_group_sent_rela set status = '%s' """ % status
        if remark:
            sql += """ ,remark = '%s' """ % remark
        if stime:
            sql += """ ,sent_time = '%s' """ % stime
        sql += """ where group_sent_id = %d and wx_id in ('%s')  """ % (gsId, wx_ids)
        (flag, rts) = mySqlUtil.execSql(sql)
        if flag:
            rt = True
    except Exception as e:
        logger.error(e)
    return rt


# 查找好友并选中
def _find_and_check(u2ConStart, friendsName):
    if wxUtil.elementExistById(u2ConStart, WxElementConf.G_Friend_Search, 2):
        for name in friendsName:
            clickFlag = True  # 首次为True
            while True:  # 循环输入
                if not clickFlag:  # 当没有需要被选中的复选框时就退出
                    break
                clickFlag = False  # 每次循环都置为False

                wxUtil.setTextById(u2ConStart, WxElementConf.G_Friend_Search, name)

                isBreak = False
                last_friend_name = ""
                while True:  # 滚屏操作循环
                    childCount = wxUtil.getCountByClass(u2ConStart, WxElementConf.G_Friend_Find_Click, "android.widget.CheckBox")
                    index = -1
                    if isBreak:
                        break
                    while index < childCount - 1:  # 好友列表循环
                        index += 1
                        friend_name_temp = wxUtil.getTextByInstanceClass(u2ConStart, WxElementConf.G_Friend_First,
                                                                         "android.widget.TextView", index)
                        if index == (childCount - 1):
                            if last_friend_name == friend_name_temp:
                                isBreak = True
                                break
                            else:
                                last_friend_name = friend_name_temp
                        if name == friend_name_temp and not u2ConStart(resourceId=WxElementConf.G_Friend_Find_Click,
                                                                       className="android.widget.CheckBox", instance=index).info["checked"]:  # 找到没有被选中的好友时进行选中操作
                            wxUtil.clickByClassAndNum(u2ConStart, WxElementConf.G_Friend_Find_Click, "android.widget.CheckBox", index)
                            clickFlag = True
                            isBreak = True
                            break
                    if not isBreak:
                        # 滚动一屏
                        wxUtil.scrollUpExistScrollable(u2ConStart)
                        time.sleep(0.1)


# 发送图片
def _sent_picture(u2ConStart, content):
    rt_flag = True
    rt_remark = ""
    filesObject = content.split(";")
    for fileObject in filesObject:
        if fileObject and len(fileObject) > 0:
            filesInfo = fileObject.split("|")
            (flag, remark) = _getFile(filesInfo[0], filesInfo[5], u2ConStart)
            if flag:
                if wxUtil.elementExistById(u2ConStart, WxElementConf.fasonggengduo, 2):
                    wxUtil.clickById(u2ConStart, WxElementConf.fasonggengduo)
                else:
                    rt_flag = False
                    rt_remark = "微信异常"
                    break
                if wxUtil.elementExistByText(u2ConStart, WxElementConf.chat_objectsend, "相册", 2):
                    wxUtil.clickByText(u2ConStart, WxElementConf.chat_objectsend, "相册")
                else:
                    rt_flag = False
                    rt_remark = "微信异常"
                    break
                if wxUtil.elementExistById(u2ConStart, WxElementConf.picture_dir, 2):
                    wxUtil.clickById(u2ConStart, WxElementConf.picture_dir)
                else:
                    rt_flag = False
                    rt_remark = "微信异常"
                    break
                idx = 0
                while idx <= 10 and not wxUtil.elementExistByText(u2ConStart, WxElementConf.picturesFolder, "WeiXin", 0.2):
                    idx += 1
                    while wxUtil.elementExistById(u2ConStart, WxElementConf.fanhui) \
                            and not wxUtil.elementExistByText(u2ConStart, WxElementConf.chat_objectsend, "相册", 0.1):
                        wxUtil.clickById(u2ConStart, WxElementConf.fanhui)
                    if wxUtil.elementExistByText(u2ConStart, WxElementConf.chat_objectsend, "相册", 2):
                        wxUtil.clickByText(u2ConStart, WxElementConf.chat_objectsend, "相册")
                    if wxUtil.elementExistById(u2ConStart, WxElementConf.picture_dir, 2):
                        wxUtil.clickById(u2ConStart, WxElementConf.picture_dir)
                if idx > 10:
                    rt_flag = False
                    rt_remark = "找不到图片"
                else:
                    wxUtil.clickByText(u2ConStart, WxElementConf.picturesFolder, "WeiXin")
                    if wxUtil.elementExistById(u2ConStart, WxElementConf.picture_first, 2):
                        wxUtil.clickById(u2ConStart, WxElementConf.picture_first)
                    else:
                        rt_flag = False
                        rt_remark = "微信异常"
                        break
                    if wxUtil.elementExistByText(u2ConStart, WxElementConf.download_picture, "完成", 2):
                        wxUtil.clickByText(u2ConStart, WxElementConf.download_picture, "完成")
                    else:
                        rt_flag = False
                        rt_remark = "微信异常"
                        break
                    if not wxUtil.elementExistByText(u2ConStart, WxElementConf.gs_new_2, "新建群发", 10):
                        rt_flag = False
                        rt_remark = "发送超时"
                        break
            else:
                rt_flag = False
                rt_remark = remark
                logger.error(remark)
    return (rt_flag, rt_remark)


def _group_sent_message(u2ConStart, content, type, friends):
    """
    使用群助手群发消息
    :param u2ConStart:
    :param content:
    :return:
    """
    rt_flag = True
    rt_remark = ""
    logger.debug("开始操作微信执行群发任务...")
    btime = time.time()
    try:
        wxUtil.backToHomeNew(u2ConStart)
        if wxUtil.elementExistByText(u2ConStart, WxElementConf.wo, "我", 5):
            wxUtil.clickByText(u2ConStart, WxElementConf.wo, "我")
        if wxUtil.elementExistByText(u2ConStart, WxElementConf.wo_shezhi, u"设置", 2):
            wxUtil.clickByText(u2ConStart, WxElementConf.wo_shezhi, u"设置")
        if wxUtil.elementExistByText(u2ConStart, WxElementConf.wo_shezhi, u"通用", 2):
            wxUtil.clickByText(u2ConStart, WxElementConf.wo_shezhi, u"通用")
        if wxUtil.elementExistByText(u2ConStart, WxElementConf.wo_shezhi, u"辅助功能", 2):
            wxUtil.clickByText(u2ConStart, WxElementConf.wo_shezhi, u"辅助功能")
        if wxUtil.elementExistByText(u2ConStart, WxElementConf.wo_shezhi, u"群发助手", 2):
            wxUtil.clickByText(u2ConStart, WxElementConf.wo_shezhi, u"群发助手")
        if wxUtil.elementExistByText(u2ConStart, WxElementConf.wo_shezhi, "启用该功能", 0.1):
            wxUtil.clickByText(u2ConStart, WxElementConf.wo_shezhi, "启用该功能")
        if wxUtil.elementExistByText(u2ConStart, WxElementConf.wo_shezhi, u"开始群发", 2):
            wxUtil.clickByText(u2ConStart, WxElementConf.wo_shezhi, u"开始群发")
        if wxUtil.elementExistByText(u2ConStart, WxElementConf.gs_new_1, "新建群发"):
            wxUtil.clickByText(u2ConStart, WxElementConf.gs_new_1, "新建群发")
        elif wxUtil.elementExistByText(u2ConStart, WxElementConf.gs_new_2, "新建群发"):
            wxUtil.clickByText(u2ConStart, WxElementConf.gs_new_2, "新建群发")

        # 查找好友并选中
        _find_and_check(u2ConStart, friends)

        if wxUtil.elementExistById(u2ConStart, WxElementConf.fabiao, 2):
            wxUtil.clickById(u2ConStart, WxElementConf.fabiao)

        if type == "2":  # 图片消息
            (rt_flag, rt_remark) = _sent_picture(u2ConStart, content)
        else:  # 一般文本消息
            if wxUtil.elementExistById(u2ConStart, WxElementConf.set_message_content, 2):
                wxUtil.setTextById(u2ConStart, WxElementConf.set_message_content, content)
            if wxUtil.elementExistById(u2ConStart, WxElementConf.RC_Con_Send, 2):
                wxUtil.clickById(u2ConStart, WxElementConf.RC_Con_Send)
            if not wxUtil.elementExistByText(u2ConStart, WxElementConf.gs_new_2, "新建群发", 10):
                rt_flag = False
                rt_remark = "发送超时"
            else:
                rt_flag = True

    except Exception as e:
        rt_flag = False
        rt_remark = "微信异常"
        logger.error(traceback.format_exc())

    logger.debug("本次群发消息耗时: %f" % (time.time() - btime))

    return (rt_flag, rt_remark)









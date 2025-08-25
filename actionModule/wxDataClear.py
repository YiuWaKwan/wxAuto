import base64
import hashlib
import datetime
import emoji
import requests

from tools import taskStatusRecorder, redisUtil
import random
from lib.WxElementConf import WxElementConf
from tools import wxUtil, taskStatusRecorder
from lib.FinalLogger import *
import os, shutil
import traceback
from lib.ModuleConfig import ConfAnalysis

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/wxDataClear.log')
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
wxElementConf = WxElementConf(logger)
confAllItems = ConfAnalysis(logger, configFile)
DEV_ID = confAllItems.getOneOptions('devInfo', 'dev')
userListAlert = confAllItems.getOneOptions("alarm", "user_list")


def md5File(devUin):
    hl = hashlib.md5()
    mm_uin = "mm" + devUin
    hl.update(mm_uin.encode(encoding='utf-8'))
    filePath = hl.hexdigest()
    return filePath


def dataVolumeGet(u2Con, logger):
    dataVolumeRet = 0
    try:
        startTime = time.time()
        while True:
            if time.time() - startTime >= 15:
                break
            if wxUtil.elementExistById(u2Con, WxElementConf.appDetail):
                wxUtil.clickById(u2Con, WxElementConf.appDetail)
                break
            else:
                u2Con.press("home")
                time.sleep(0.5)
                u2Con(text=u"微信").long_click(4)

        startTime = time.time()
        while True:
            totalVoulmeMB = 0
            if time.time() - startTime >= 60 * 2:
                break
            totalVoulme = wxUtil.getTextById(u2Con, WxElementConf.totalSize)
            if "B" in totalVoulme:  # "MB" or "GB"
                totalVoulmeInt = totalVoulme.split(" ")[0]
                if "GB" in totalVoulme:
                    totalVoulmeMB = float(totalVoulmeInt) * 1024
                else:
                    totalVoulmeMB = float(int(totalVoulmeInt))
                break
            else:
                time.sleep(1)

        dataVolumeRet = totalVoulmeMB
    except Exception as e:
        logger.warn(traceback.format_exc())

    return dataVolumeRet

def action(logger, u2Con, taskItemInfo, mySqlUtil):
    remarks = '#'
    status = 3
    taskSeq = taskItemInfo[0]
    uuidTask = taskItemInfo[1]
    taskType = taskItemInfo[2]
    devName = taskItemInfo[6]
    operViewName = taskItemInfo[7]
    try:

        # 获取容量
        dataVolume = dataVolumeGet(u2Con, logger)
        dataVolumeSql = """update wx_data_volume
                            set volume1 = %s, startTime = now()
                            where taskSeq = %s """ % (dataVolume, taskSeq)
        mySqlUtil.excSql(dataVolumeSql)

        uinGetSql = """ SELECT uin,phone_no FROM `wx_account_info`
                        where uuid = "%s" """%(uuidTask)
        infoGet = mySqlUtil.getData(uinGetSql)
        wxMd5Path = md5File(infoGet[0][0])
        wxPhone = infoGet[0][1]
        filepath = "/sdcard/tencent/MicroMsg/%s/image2/*" % (wxMd5Path)
        filepath1= "/data/media/0/tencent/MicroMsg/%s/image2/*" % (wxMd5Path)
        filepath2= "/mnt/shell/emulated/0/tencent/MicroMsg/%s/image2/*" % (wxMd5Path)
        filepath3= "/sdcard/copyfile/image2/*"
        filepath4 = "/mnt/shell/emulated/0/tencent/MicroMsg/xlog/*xlog"
        fileClearList = []
        fileClearList.append(filepath)
        fileClearList.append(filepath1)
        fileClearList.append(filepath2)
        fileClearList.append(filepath3)
        fileClearList.append(filepath4)

        # 清理图片文件
        for fileClear in fileClearList:
            try:
                u2Con.shell("rm -rf %s" % (fileClear))
                time.sleep(1)
            except Exception as e:
                pass

        try:
            if not os.path.exists("./data/dataBackup"):
                os.mkdir("./data/dataBackup")
        except:
            pass

        try:
            if not os.path.exists("./data/dataBackup/%s" % (devName)):
                os.mkdir("./data/dataBackup/%s" % (devName))
        except:
            pass

        todayDir = time.strftime('%Y%m%d', time.localtime(time.time()))
        try:
            if not os.path.exists("./data/dataBackup/%s/%s" % (devName, todayDir)):
                os.mkdir("./data/dataBackup/%s/%s" % (devName, todayDir))
        except:
            pass

        # 保存数据库
        dbFileList = ["EnMicroMsg.db", "EnMicroMsg.db-shm", "EnMicroMsg.db-wal", "EnMicroMsg.db.ini",
                      "EnMicroMsg.db.sm"]
        for fileItem in dbFileList:
            dbFileDir = "/data/data/com.tencent.mm/MicroMsg/%s/%s" % (wxMd5Path, fileItem)
            try:
                u2Con.pull(dbFileDir, "./data/dataBackup/%s/%s/%s" % (devName, todayDir, fileItem))
            except Exception as e:
                pass
        # 保存xposed日志与清空
        xposedLog = "/data/data/de.robv.android.xposed.installer/log/error.log"
        try:
            u2Con.pull(xposedLog, "./data/dataBackup/%s/%s/XposedError.log" % (devName, todayDir))
        except Exception as e:
            pass
        u2Con.shell("echo '' > %s" % (xposedLog))

        # 清理备份数据
        hasDirList = os.listdir("./data/dataBackup/%s" % (devName))
        hasDirList.sort()
        hasDirList = hasDirList[:hasDirList.index(todayDir) + 1]
        saveCount = 7
        if len(hasDirList) > saveCount:
            for willDel in hasDirList[: -saveCount]:
                shutil.rmtree("./data/dataBackup/%s/%s" % (devName, willDel))

                # 进入清理界面

        u2Con.press("home")
        time.sleep(0.5)
        u2Con(text=u"微信").click(3)
        wxUtil.backToHome(u2Con)

        # 进入"我"，因为存在点击“我”后未跳转
        startTIme = time.time()
        while True:
            if time.time() - startTIme >= 15:
                break
            if wxUtil.elementExistByText(u2Con, WxElementConf.wo_shezhi, "相册"):
                break
            else:
                wxUtil.clickByText(u2Con, WxElementConf.wo, "我")
            time.sleep(0.5)

        startTIme = time.time()
        while True:
            if time.time() - startTIme >= 15:
                break
            if wxUtil.elementExistByText(u2Con, WxElementConf.wo_shezhi, "设置"):
                wxUtil.clickByText(u2Con, WxElementConf.wo_shezhi, "设置")
                time.sleep(0.5)
                break
            else:
                # 向下拉
                wxUtil.scrollDown(u2Con)

        # 进入 “聊天”
        wxUtil.clickByText(u2Con, WxElementConf.wo_shezhi, "聊天")
        time.sleep(0.5)
        wxUtil.clickByText(u2Con, WxElementConf.wo_shezhi, "清空聊天记录")
        time.sleep(0.5)
        wxUtil.clickById(u2Con, WxElementConf.manageDataDelFin)
        startTIme = time.time()
        while True:
            if time.time() - startTIme >= 60 * 10:
                break
            try:
                if wxUtil.elementExistByText(u2Con, WxElementConf.wo_shezhi, "清空聊天记录"):
                    emptyFlag = wxUtil.getButtonInfoByText(u2Con, WxElementConf.wo_shezhi, u"清空聊天记录", "enabled")
                    if emptyFlag:
                        u2Con.press("back")
                        break
                    else:
                        time.sleep(0.5)
            except:
                pass

        startTIme = time.time()
        while True:
            if time.time() - startTIme >= 10:
                break
            if wxUtil.elementExistByText(u2Con, WxElementConf.wo_shezhi, "通用"):
                wxUtil.clickByText(u2Con, WxElementConf.wo_shezhi, "通用")
                time.sleep(0.5)
                break
            else:
                time.sleep(0.5)

        wxUtil.clickByText(u2Con, WxElementConf.wo_shezhi, "微信存储空间")

        # (resourceId="com.tencent.mm:id/auz")
        startTIme = time.time()
        while True:
            if time.time() - startTIme >= 15:
                break
            if wxUtil.elementExistById(u2Con, WxElementConf.wxDataVolume):
                wxUtil.clickById(u2Con, WxElementConf.manageDataVol)
                break
            else:
                time.sleep(1)
        time.sleep(1)
        wxUtil.clickById(u2Con, WxElementConf.manageChatData)

        delClickFlag = True
        startTIme = time.time()
        while True:
            if time.time() - startTIme >= 15:
                break
            delFlag = wxUtil.getButtonInfo(u2Con, WxElementConf.manageDataDel, "enabled")
            if delFlag:
                wxUtil.clickById(u2Con, WxElementConf.manageDataDel)
                break
            elif wxUtil.elementExistById(u2Con, WxElementConf.nothingDel):
                # 没有可清理的内容
                delClickFlag = False
                break
            else:
                wxUtil.clickById(u2Con, WxElementConf.allChckItem)

        if delClickFlag:
            wxUtil.clickById(u2Con, WxElementConf.manageDataDelFin)
            time.sleep(1)
            # 等待清理完成
            startTIme = time.time()
            while True:
                if time.time() - startTIme >= 60 * 20:
                    break
                if wxUtil.elementExistById(u2Con, WxElementConf.manageDataDelFin):
                    wxUtil.clickById(u2Con, WxElementConf.manageDataDelFin)

        # 获取容量回填
        dataVolume = dataVolumeGet(u2Con, logger)
        dataVolumeSql = """update wx_data_volume
                                    set volume2 = %s, endTime = now()
                                    where taskSeq = %s """ % (dataVolume, taskSeq)
        mySqlUtil.excSql(dataVolumeSql)

        status = 4
    except Exception as e:
        logger.warn(traceback.format_exc())
        remarks = e
    finally:
        u2Con.press("home")
        # 刷新好友
        if wxPhone:
            freshFriendSql = "insert into wx_hand_flush_task(phone_no,oper_name) values('%s','system')"%(wxPhone)
            mySqlUtil.excSql(freshFriendSql)

    return (status, remarks)


def taskGenerate(mySqlUtil, logger):
    taskUuidGetSql = """ select A.uuid , B.devName from wx_account_info A
                        join wx_machine_info B on A.uuid = B.uuid
                         where A.if_start = 1 and B.is_phone = 0
                        AND B.clientId = "%s" """%(DEV_ID)
    taskUuidList = mySqlUtil.getData(taskUuidGetSql)

    taskValue = ""
    dataVolumeValue = ""
    for taskUuidItem in taskUuidList:
        taskUuid = taskUuidItem[0]
        devName = taskUuidItem[1]
        taskSeq = round(time.time() * 1000 + random.randint(100, 999))
        randomMin = random.randint(5, 10)
        taskValue += "(%s, '%s', 37, now(), DATE_ADD(now(),INTERVAL %s MINUTE), 30, 0, 1)," % (
        taskSeq, taskUuid, randomMin)
        dataVolumeValue += "(%s, '%s', now())," % (taskSeq, devName)

    taskInsertSql = """INSERT INTO `wx_task_manage` (
                                    `taskSeq`,
                                    `uuid`,
                                    `actionType`,
                                    `createTime`,
                                    `cronTime`,
                                    `priority`,
                                    `ifKill`,
                                    `status`
                                )
                                VALUES %s""" % (taskValue[:-1])
    mySqlUtil.excSql(taskInsertSql)

    taskInsertSql = """INSERT INTO `wx_data_volume` (
                                        `taskSeq`,
                                        `devName`,
                                        `createTime`
                                    )
                                    VALUES %s""" % (dataVolumeValue[:-1])

    mySqlUtil.excSql(taskInsertSql)
    logger.info("微信清理任务下发成功")


def wxDataTaskMsg(mySqlUtil, logger):
    wxDataSql = """ select A.taskSeq, B.devName,A.`status` from wx_task_manage A
                        join wx_machine_info B on A.uuid = B.uuid
                        join wx_account_info C on C.uuid = B.uuid
                        where to_days(A.createTime) = to_days(now())
                        and A.actionType = 37
                        and C.if_start = 1 and C.wx_status=1 and B.is_phone = 0
                        and B.clientId = "%s" """%(DEV_ID)
    wxDataStatus = mySqlUtil.getData(wxDataSql)
    allLen = len(wxDataStatus)
    step12List = []
    step3List = []
    step4List = []
    step5Listt = []
    taskList = []
    summaryContent = ""
    detailContent = ""
    alarmContent = ""
    if wxDataStatus:
        for wxDataItem in wxDataStatus:
            taskSeq = wxDataItem[0]
            devName = wxDataItem[1]
            status = int(wxDataItem[2])
            taskList.append(taskSeq)
            if status in [1, 2]:
                step12List.append(devName)
            elif status in [3]:
                step3List.append(devName)
            elif status in [4]:
                step4List.append(devName)
            else:
                step5Listt.append(devName)
        if allLen == len(step4List) + len(step3List):
            summaryContent = "%s 主机下发清理微信个数：%s, 成功个数：%s, 失败个数：%s\n" % (DEV_ID, allLen, len(step4List), len(step3List))
        else:
            summaryContent = "%s 主机下发清理微信个数：%s, 成功个数：%s, 失败个数：%s, 其他状态：%s\n" % (
            DEV_ID, allLen, len(step4List), len(step3List), allLen - len(step4List) - len(step3List))

        wxDetailSql = """ SELECT devName, volume1, volume2 from wx_data_volume
                            where taskSeq in (
                            select A.taskSeq from wx_task_manage A
                            join wx_machine_info B on A.uuid = B.uuid
                            where to_days(A.createTime) = to_days(now())
                            and A.actionType = 37
                            and B.clientId = '%s') """ % (DEV_ID)
        # wxDetailSql = """ SELECT devName, volume1, volume2 from wx_data_volume """

        wxDetail = mySqlUtil.getData(wxDetailSql)
        detailContent += "微信处理详细如下，单位/MB:\n"
        detailContent += "%s|%s|%s\n" % (
            " devName", "初始容量", "变化容量")

        for wxDetailItem in wxDetail:
            devName = wxDetailItem[0]
            volume1 = wxDetailItem[1] if wxDetailItem[1] else 0
            volume2 = wxDetailItem[2] if wxDetailItem[2] else 0
            volumeDiff = volume1 - volume2 if volume1 - volume2 > 0 else 0
            detailContent += "%s|%s|%s\n" % (devName, str(volume1).center(8), str(volumeDiff).center(8))
            # detailContent += "%s,初始:%s,删减:%s\n"%(devName,volume1,volumeDiff)

    if summaryContent == "":
        alarmContent = "%s 主机未下发清理任务，需核查" % (DEV_ID)
    else:
        alarmContent += summaryContent
        alarmContent += detailContent

    # taskUuid = "0bc6c452-8e57-11e8-a2a8-ecf4bbe8d4f8"
    taskUuid = "b3332eca-0a72-11e9-bd63-246e9664f9bd"
    # wxMainId = "wxid_1ocdcrmt8rrv22"
    wxMainId = "wxid_kv82ww23z3t122"  # 红颜不祸水
    taskSeq = round(time.time() * 1000 + random.randint(100, 999))
    # wxId = "edent-yin"
    wxId = "9759241310@chatroom"  # 收消息告警群id
    actType = 1
    sendMsg = "%s:~:%d#^#%s#^#%s#^#%s#^#%s#^#%s" % (
    wxMainId, taskSeq, wxId, base64.b64encode(alarmContent.encode('utf-8')),
    "", taskSeq, actType)
    redisUtil.publishMsgGen(taskSeq, taskUuid, wxMainId, sendMsg, mySqlUtil)

def alarmMsg(alarmMsg):
    weixinAlarmRequest = """http://124.172.189.98/wechat/send_err_msg/?msg=%s&type=21&user=%s&creator=edent&jobid=123""" % (
        alarmMsg, userListAlert)
    req = requests.get(weixinAlarmRequest)

def dbClearEntry(mySqlUtil,logger):
    dbCleaStatus,remark = dbClearAction(mySqlUtil,logger)
    if dbCleaStatus == 0:
        msg = "%s : %s" %(DEV_ID, remark)
    else:
        msg = "%s : 数据库清理 %s" % (DEV_ID, remark)
    alarmMsg(msg)

def dbClearAction(mySqlUtil,logger):
    actionFlag = 0
    ########## 清理聊天信息 ##########
    # 1. 判断wx_chat_his_archive表是否存在，否->进行创建
    archiveTableSql = """CREATE TABLE if not exists `wx_chat_info_his_archive` (
                              `seq` bigint(255) NOT NULL AUTO_INCREMENT,
                              `wx_main_id` varchar(128) NOT NULL COMMENT '微信主号',
                              `wx_id` varchar(128) NOT NULL COMMENT '微信好友',
                              `send_time` datetime NOT NULL COMMENT '聊天时间',
                              `type` varchar(3) NOT NULL DEFAULT '1' COMMENT '聊天类型（图片、文字）\n1 文字 2 图片  3 文件 4、5-系统消息 6-语音 7-视频',
                              `content` varchar(4000) NOT NULL,
                              `send_type` char(1) NOT NULL DEFAULT '2' COMMENT '1 主号发送消息 2 主号接收消息',
                              `status` char(1) NOT NULL DEFAULT '0' COMMENT '0 未读消息 1 已读消息',
                              `group_member_name` varchar(64) DEFAULT NULL,
                              `msgId` varchar(32) DEFAULT NULL COMMENT '消息ID 暂定为微信的msgSvrId',
                              `createTime` bigint(32) DEFAULT NULL COMMENT '微信消息创建时间',
                              `group_member_id` varchar(32) DEFAULT NULL COMMENT '群成员编号',
                              `head_picture` varchar(256) DEFAULT NULL COMMENT '成员头像',
                              `oper_id` bigint(20) DEFAULT NULL COMMENT '处理消息的操作员ID',
                              `seqId` int(11) DEFAULT NULL COMMENT '自增字段，用于读取聊天记录时做标记',
                              PRIMARY KEY (`seq`),
                              UNIQUE KEY `CHAT_ARCHIVE_INDEX` (`seq`) USING BTREE
                            ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4"""
    archiveTableStatus = mySqlUtil.execSql(archiveTableSql)
    if archiveTableStatus[0] != 1:
        actionFlag = 1
        return (actionFlag, "阶段%s报错退出"%actionFlag)

    # 2. 将wx_chat_info表迁移至wx_chat_his表，wx_chat_info只保留2天数据
    # 2.1 获取当前时间 YYYY-MM-DD
    curDay = time.strftime("%Y-%m-%d", time.localtime())
    expireTime = 3 * 24 * 60 # 时间 3 天
    seqIdSaveSql = """ SELECT seqId from wx_chat_info where send_time < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)
                         and send_time >= DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE) """%(curDay, expireTime,curDay, expireTime*2)
    seqIdList = mySqlUtil.getData(seqIdSaveSql)
    seqIdSave = [str(i[0]) for i in seqIdList]
    seqConStr = ','.join(seqIdSave) # 拼装条件
    seqMoveLen = len(seqIdSave) # 准备迁移数量
    logger.info("wx_chat_info 转移 wx_chat_info_his 数目:%s" % seqMoveLen)
    if seqMoveLen != 0:
        oper_id = 0 # 默认系统账号为0
        transSql = """insert into wx_chat_info_his(wx_main_id, wx_id,send_time,type,content,send_type,status,group_member_name,msgId,createTime,group_member_id,head_picture,oper_id,seqId)
                        select wx_main_id, wx_id,send_time,type,content,send_type,status,group_member_name,msgId,createTime,group_member_id,head_picture,%d,seqId from wx_chat_info
                        where seqId in (%s)
                        and send_time < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)
                         and send_time >= DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)""" %(oper_id,seqConStr,curDay, expireTime,curDay, expireTime*2)
        retStatus = mySqlUtil.execSql(transSql)
        if retStatus[0] != 1:
            actionFlag = 2
            return (actionFlag, "阶段%s报错退出" % actionFlag)
        hisCountSql = """select count(1) from wx_chat_info_his where seqId in (%s)
                             and send_time < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)
                             and send_time >= DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)""" %(seqConStr,curDay, expireTime,curDay, expireTime*2)
        hisCount = mySqlUtil.getData(hisCountSql)[0][0]
        if hisCount != seqMoveLen:
            # 回滚数据
            logger.info("wx_chat_info 转移 wx_chat_info_his 数目:%s 失败，进行回滚" % seqMoveLen)
            delSql = """DELETE FROM wx_chat_info_his where seqId in (%s)
                              and send_time < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)
                             and send_time >= DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)""" %(seqConStr,curDay, expireTime,curDay, expireTime*2)
            mySqlUtil.execSql(delSql)
            actionFlag = 3
            return (actionFlag, "阶段%s报错退出" % actionFlag)
        else:
            logger.info("wx_chat_info 转移 wx_chat_info_his 数目:%s 成功" % seqMoveLen)
            delSql = """DELETE FROM wx_chat_info where seqId in (%s)
                            and send_time < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)
                             and send_time >= DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)""" %(seqConStr,curDay, expireTime,curDay, expireTime*2)
            retStatus = mySqlUtil.execSql(delSql)
            if retStatus[0] != 1:
                actionFlag = 4
                return (actionFlag, "阶段%s报错退出" % actionFlag)

    # 3. 将wx_chat_his 表迁移至 wx_chat_his_archive表，wx_chat_his只保存7天数据
    ## 3.1 获取当前时间 YYYY-MM-DD
    curDay = time.strftime("%Y-%m-%d", time.localtime())
    expireTime = 5 * 24 * 60  # 时间 5 天
    transCountSql = """SELECT count(1) from wx_chat_info_his where send_time < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)""" % (curDay, expireTime)
    transCount = mySqlUtil.getData(transCountSql)[0][0] # 准备迁移数量

    maxIndexSql = """select MAX(seq) from wx_chat_info_his_archive"""
    maxIndexStart = mySqlUtil.getData(maxIndexSql)[0][0]

    logger.info("wx_chat_info_his 转移 wx_chat_info_his_archive 数目:%s" % transCount)
    if transCount != 0:
        oper_id = 0  # 默认系统账号为0
        transSql = """insert into wx_chat_info_his_archive(wx_main_id, wx_id,send_time,type,content,send_type,status,group_member_name,msgId,createTime,group_member_id,head_picture,oper_id,seqId)
                            select wx_main_id, wx_id,send_time,type,content,send_type,status,group_member_name,msgId,createTime,group_member_id,head_picture,oper_id,seqId from wx_chat_info_his
                            where send_time < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)""" % (curDay, expireTime)
        retStatus = mySqlUtil.execSql(transSql)
        if retStatus[0] != 1:
            actionFlag = 5
            return (actionFlag, "阶段%s报错退出" % actionFlag)
        maxIndexSql = """select count(1) from wx_chat_info_his_archive where seq > %s""" %(maxIndexStart)
        maxIndexEnd = mySqlUtil.getData(maxIndexSql)[0][0]
        if maxIndexEnd  != transCount:
            # 回滚数据
            logger.info("wx_chat_info_his 转移 wx_chat_info_his_archive 数目:%s 失败,进行回滚" % transCount)
            delSql = """DELETE FROM wx_chat_info_his_archive where seq > %s""" %maxIndexStart
            mySqlUtil.execSql(delSql)
            actionFlag = 6
            return (actionFlag, "阶段%s报错退出" % actionFlag)
        else:
            logger.info("wx_chat_info_his 转移 wx_chat_info_his_archive 数目:%s 成功"%transCount)
            delSql = """DELETE FROM wx_chat_info_his  where send_time < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)""" % (curDay, expireTime)
            retStatus = mySqlUtil.execSql(delSql)
            if retStatus[0] != 1:
                actionFlag = 7
                return (actionFlag, "阶段%s报错退出" % actionFlag)

    ########## 任务信息处理 ##########
    # 1. 判断wx_task_manage_archive表是否存在，否->进行创建
    curDay = time.strftime("%Y-%m-%d", time.localtime())
    expireTime = 10 * 24 * 60  # 时间 10 天
    taskTableSql = """CREATE TABLE if not exists `wx_task_manage_archive` (
                          `taskSeq` bigint(20) NOT NULL,
                          `uuid` varchar(36) NOT NULL,
                          `actionType` int(3) NOT NULL,
                          `createTime` datetime DEFAULT NULL,
                          `startTime` datetime DEFAULT NULL,
                          `endTime` datetime DEFAULT NULL,
                          `heartBeatTime` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '心跳时间',
                          `cronTime` datetime DEFAULT CURRENT_TIMESTAMP,
                          `priority` int(2) NOT NULL DEFAULT '0' COMMENT '优先级',
                          `remarks` varchar(255) DEFAULT NULL,
                          `ifKill` int(1) DEFAULT '0' COMMENT '是否中断,非0则中断',
                          `status` int(1) NOT NULL DEFAULT '0' COMMENT '0 : 初始化；1 ： 下发中； 2 ： 执行中； 3 ：失败； 4 ： 完成； 5 ： 暂停；6 : 定时任务手工失效',
                          `alarm` char(1) DEFAULT '0' COMMENT '0-待监控 1-监控正常 2-异常',
                          `operViewName` varchar(255) DEFAULT NULL,
                          PRIMARY KEY (`taskSeq`)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    taskTablStatus = mySqlUtil.execSql(taskTableSql)
    if taskTablStatus[0] != 1:
        actionFlag = 8
        return (actionFlag, "阶段%s报错退出" % actionFlag)

    # 2. 将wx_task_manage表迁移至wx_task_manage_archive表，wx_task_manage只保留3天数据
    ## 2.1 获取当前时间 YYYY-MM-DD
    # taskseqIdSaveSql = """ SELECT taskSeq from wx_task_manage where createTime < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)
    #                              and createTime >= DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)
    #                              and status !=  1
    #                              and actionType not in (2,30,32) """ % (
    #     curDay, expireTime, curDay, expireTime * 2)

    # 清理3天前全部数据
    taskseqIdSaveSql = """SELECT taskSeq from wx_task_manage where createTime < DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)
                                     and status !=  1
                                     and actionType not in (2,30,32) """ % (
        curDay, expireTime)
    seqIdList = mySqlUtil.getData(taskseqIdSaveSql)
    seqIdSave = [str(i[0]) for i in seqIdList]
    seqConStr = ','.join(seqIdSave)  # 拼装条件
    seqMoveLen = len(seqIdSave)  # 准备迁移数量
    logger.info("wx_task_manage 转移 wx_task_manage_archive 数目: %s"%(seqMoveLen))
    if seqMoveLen != 0:
        transArchiveSql = """ insert into wx_task_manage_archive(`taskSeq`, `uuid`, `actionType`, `createTime`, `startTime`, `endTime`, `heartBeatTime`, `cronTime`, `priority`, `remarks`, `ifKill`, `status`, `alarm`, `operViewName`)
                            select `taskSeq`, `uuid`, `actionType`, `createTime`, `startTime`, `endTime`, `heartBeatTime`, `cronTime`, `priority`, `remarks`, `ifKill`, `status`, `alarm`, `operViewName`
                            from wx_task_manage
                            where taskSeq in (%s) """ %(seqConStr)

        retStatus = mySqlUtil.execSql(transArchiveSql)
        if retStatus[0] != 1:
            actionFlag = 9
            return (actionFlag, "阶段%s报错退出" % actionFlag)
        hisCountSql = """select count(1) from wx_task_manage_archive where taskSeq in (%s)""" % (seqConStr)
        hisCount = mySqlUtil.getData(hisCountSql)[0][0]
        if hisCount != seqMoveLen:
            # 回滚数据
            logger.info("wx_task_manage 转移 wx_task_manage_archive 数目: %s 失败，进行回滚" % (seqMoveLen))
            delSql = """DELETE FROM wx_task_manage_archive where taskSeq in (%s)""" % (seqConStr)
            mySqlUtil.execSql(delSql)
            actionFlag = 10
            return (actionFlag, "阶段%s报错退出" % actionFlag)
        else:
            logger.info("wx_task_manage 转移 wx_task_manage_archive 数目: %s 成功" % (seqMoveLen))
            delSql = """DELETE FROM wx_task_manage where taskSeq in (%s)""" % (seqConStr)
            retStatus = mySqlUtil.execSql(delSql)
            if retStatus[0] != 1:
                actionFlag = 11
                return (actionFlag, "阶段%s报错退出" % actionFlag)

    # 3. 清理一键加好友
    ## 3.1 创建归档表
    friendArcSql= """CREATE TABLE if not exists `OKAY_TASK_INFO_archive` (
                      `TASK_ID` varchar(100) NOT NULL COMMENT '任务编码',
                      `TASK_NAME` varchar(100) DEFAULT NULL COMMENT '任务名称',
                      `WX_USER` varchar(100) DEFAULT NULL COMMENT '好友添加微信号',
                      `GREETINGS_MSG` varchar(100) DEFAULT NULL COMMENT '招呼语信息',
                      `FILTER_ALL` varchar(10) DEFAULT NULL COMMENT '任务规模',
                      `FILTER_FACT` varchar(10) DEFAULT NULL COMMENT '实际执行规模',
                      `EXEC_TYPE` char(1) DEFAULT NULL COMMENT '执行类型(1-立即执行,2-定时执行)',
                      `EXEC_TIME` varchar(14) DEFAULT NULL COMMENT '执行时间',
                      `CREATE_TIME` varchar(14) DEFAULT NULL COMMENT '创建时间',
                      `END_TIME` varchar(14) DEFAULT NULL COMMENT '结束时间',
                      `TASK_STATE` char(1) DEFAULT NULL COMMENT '任务状态(1-进行中，2-暂停，3-终止，4-已完成)',
                      `REMARK` varchar(1000) DEFAULT NULL COMMENT '备注',
                      PRIMARY KEY (`TASK_ID`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='任务信息表'"""
    friendArcStatus = mySqlUtil.execSql(friendArcSql)
    if friendArcStatus[0] != 1:
        actionFlag = 12
        return (actionFlag, "阶段%s报错退出" % actionFlag)

    # 3.2 OKAY_TASK_INFO 归档 OKAY_TASK_INFO_archive
    curDay = time.strftime("%Y-%m-%d", time.localtime())
    expireTime = 30 * 24 * 60  # 时间 30 天
    transCountSql = """select task_id  from OKAY_TASK_INFO 
                        where str_to_date(CREATE_TIME,'%%Y%%m%%d%%H%%i%%s') <DATE_SUB("%s 00:00:30", INTERVAL %s MINUTE)
                        and TASK_STATE in (3,4)""" % (curDay, expireTime)
    transCountList = mySqlUtil.getData(transCountSql)
    taskIdSave = ["'%s'"%(i) for i in transCountList]
    taskConStr = ','.join(taskIdSave)  # 拼装条件
    taskMoveLen = len(taskIdSave)  # 准备迁移数量
    logger.info("OKAY_TASK_INFO 转移 OKAY_TASK_INFO_archive 数目:%s" % taskMoveLen)
    if taskMoveLen != 0:
        transSql = """INSERT INTO `OKAY_TASK_INFO_archive` (`TASK_ID`, `TASK_NAME`, `WX_USER`, `GREETINGS_MSG`, `FILTER_ALL`, `FILTER_FACT`, `EXEC_TYPE`, `EXEC_TIME`, `CREATE_TIME`, `END_TIME`, `TASK_STATE`, `REMARK`) 
                        select `TASK_ID`, `TASK_NAME`, `WX_USER`, `GREETINGS_MSG`, `FILTER_ALL`, `FILTER_FACT`, `EXEC_TYPE`, `EXEC_TIME`, `CREATE_TIME`, `END_TIME`, `TASK_STATE`, `REMARK` from OKAY_TASK_INFO
                        where TASK_ID in (%s)""" % (taskConStr)

        retStatus = mySqlUtil.execSql(transSql)
        if retStatus[0] != 1:
            actionFlag = 13
            return (actionFlag, "阶段%s报错退出" % actionFlag)
        hisCountSql = """select count(1) from OKAY_TASK_INFO_archive where TASK_ID in (%s)""" % (taskConStr)
        hisCount = mySqlUtil.getData(hisCountSql)[0][0]
        if hisCount != taskMoveLen:
            # 回滚数据
            logger.info("OKAY_TASK_INFO 转移 OKAY_TASK_INFO_archive 数目:%s 失败，进行回滚" % taskMoveLen)
            delSql = """DELETE FROM OKAY_TASK_INFO_archive where TASK_ID in (%s)""" % (taskConStr)
            mySqlUtil.execSql(delSql)
            actionFlag = 3
            return (actionFlag, "阶段%s报错退出" % actionFlag)
        else:
            logger.info("OKAY_TASK_INFO 转移 OKAY_TASK_INFO_archive 数目:%s 成功" % taskMoveLen)
            # 清理OKAY_TASK_LIST 和 wx_task_manage
            delSql = """DELETE FROM OKAY_TASK_LIST where TASK_ID in (%s)""" % (taskConStr)
            retStatus = mySqlUtil.execSql(delSql)
            if retStatus[0] != 1:
                actionFlag = 14
                return (actionFlag, "阶段%s报错退出" % actionFlag)
            findSeqSql = """SELECT DISTINCT(TASK_SEQ) from OKAY_TASK_LIST
                                where task_id in (%s)
                                UNION ALL
                                SELECT subTaskSeq from wx_add_friend
                                where taskSeq in (SELECT DISTINCT(TASK_SEQ) from OKAY_TASK_LIST
                                where task_id in (%s)) 
                                and subTaskSeq is not Null""" %(taskConStr,taskConStr)
            findSeq = mySqlUtil.getData(findSeqSql)
            findSeqList = [i[0] for i in findSeq]
            findSeStr = ','.join(findSeqList)  # 拼装条件
            delSeqSql = """DELETE FROM wx_task_manamge where taskSeq in (%s)"""%(findSeStr)
            retStatus = mySqlUtil.execSql(delSeqSql)
            delSql = """DELETE FROM OKAY_TASK_INFO where TASK_ID in (%s)""" % (taskConStr)
            retStatus = mySqlUtil.execSql(delSql)
            if retStatus[0] != 1:
                actionFlag = 15
                return (actionFlag, "阶段%s报错退出" % actionFlag)

    # 4. 清理相关子任务表
    try:
        taskSeqSql = """select taskSeq from wx_task_manage where actionType not in (2,30,32)"""
        seqIdList = mySqlUtil.getData(taskSeqSql)
        seqIdSave = [str(i[0]) for i in seqIdList]
        seqConStr = ','.join(seqIdSave)  # 拼装条件
        # wx_chat_task
        logger.info("清理 wx_chat_task")
        delSql = """ DELETE FROM wx_chat_task where taskSeq not in (%s)""" % (seqConStr)
        mySqlUtil.execSql(delSql)
        # wx_data_volume
        logger.info("清理 wx_data_volume")
        delSql = """ DELETE FROM wx_data_volume where taskSeq not in (%s)""" %(seqConStr)
        mySqlUtil.execSql(delSql)
        # wx_fileLoad_task
        logger.info("清理 wx_fileLoad_task")
        delSql = """ DELETE FROM wx_fileLoad_task where taskSeq not in (%s)""" % (seqConStr)
        mySqlUtil.execSql(delSql)
        # wx_group_sent_info
        logger.info("清理 wx_group_sent_info")
        delSql = """ DELETE FROM wx_group_sent_info where task_seq not in (%s)""" % (seqConStr)
        mySqlUtil.execSql(delSql)
        # wx_group_sent_rela # TODO
        # wx_group_task
        logger.info("清理 wx_group_task")
        delSql = """ DELETE FROM wx_group_task where taskSeq not in (%s)""" % (seqConStr)
        mySqlUtil.execSql(delSql)
        # wx_login_task
        logger.info("清理 wx_login_task")
        delSql = """ DELETE FROM wx_login_task where taskSeq not in (%s)""" % (seqConStr)
        mySqlUtil.execSql(delSql)
        # wx_machine_info_task
        logger.info("清理 wx_machine_info_task")
        delSql = """ DELETE FROM wx_machine_info_task where taskSeq not in (%s)""" % (seqConStr)
        mySqlUtil.execSql(delSql)
        # wx_moments_linkType
        logger.info("清理 wx_moments_linkType")
        delSql = """ DELETE FROM wx_moments_linkType where taskSeq not in (%s)""" % (seqConStr)
        mySqlUtil.execSql(delSql)
        # wx_moments_pic TODO
        # wx_moments_picType
        logger.info("清理 wx_moments_picType")
        delSql = """ DELETE FROM wx_moments_picType where taskSeq not in (%s)""" % (seqConStr)
        mySqlUtil.execSql(delSql)
        # wx_oper_logtime TODO
        # wx_transpond_task
        logger.info("清理 wx_transpond_task")
        delSql = """ DELETE FROM wx_transpond_task where taskSeq not in (%s)""" % (seqConStr)
        mySqlUtil.execSql(delSql)
        # logger.info("清理 wx_add_friend")
        # delSql = """ DELETE FROM wx_add_friend where taskSeq not in (%s)""" % (seqConStr)
        # mySqlUtil.execSql(delSql)
    except Exception as e:
        logger.warn(traceback.format_exc())

    return(actionFlag, "数据库任务清理完成")






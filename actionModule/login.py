import colorsys,subprocess,traceback,cv2,time,random
import numpy as np
from PIL import ImageChops, Image
from actionModule import handlePic
from lib.WxElementConf import WxElementConf
from tools.machinInfo import machineLoginInit
from tools.wxUtil import elementExistByText, elementExistById, pwModifySkip, clickById, judge_logout, \
    currentPackageInWx, indexJudege, elementExistOnlyByText, clickOnlyByText, clickByText, dragByIdAndText, pressBack, \
    getTextById, setTextById, clearTextById, clearTextByIdClassInstance, setTextByIdClassInstance, elementExistByDesc, \
    getCenterByDesc, elementExistByClassAndInstance, getCenterByClassAndInstance, getDeviceInfo, saveScreenShot, \
    dragByClassNameAndInstance, clickByDesc, backToHomeNew
from tools import wxUtil, common, redisUtil
import requests, os
from lib.ModuleConfig import ConfAnalysis
from lib.FinalLogger import getLogger
BASEDIR = os.getcwd()
# 初始化logger
loggerFIle = './log/multiTask.log'
logger = getLogger(loggerFIle)
loggerFIle_err = './log/multiTask_err.log'
errlogger = getLogger(loggerFIle_err)
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)
fileServiceURL = confAllItems.getOneOptions('fileSystemService', 'fileServiceURL')
appHeartBeatUrl = confAllItems.getOneOptions('fileSystemService', 'appHeartBeatUrl')
redis_ip = confAllItems.getOneOptions('redis', 'ip')
redis_port = confAllItems.getOneOptions('redis', 'port')
redis_db = confAllItems.getOneOptions('redis', 'db')
redis_pwd = confAllItems.getOneOptions('redis', 'pwd')
# 频道名称
channl_name = confAllItems.getOneOptions('redis', 'channl_name')
dev_id = confAllItems.getOneOptions("devInfo", "dev")
wxVersion = confAllItems.getOneOptions("wxVersion", "version")
user_list = confAllItems.getOneOptions("alarm", "user_list")
alarm_server = confAllItems.getOneOptions("alarm", "alarm_server")
wxElementConf=WxElementConf(logger)
click_denglu=False

#上线下线任务执行入口
def main(logger,d,taskItemInfo,mySqlUtil):
    status=4
    remark="#"
    ret=()
    taskSeq = taskItemInfo[0]
    try:
        sql = "select type from wx_login_task where taskSeq='%s'" % str(taskSeq)
        rs = mySqlUtil.getData(sql)
        type = rs[0][0]
        if str(type)=='1':
            logger.info("上线任务")
            uuid = taskItemInfo[1]
            sql = "select wx_login_id,pword,phone_no,uin,db_passwd,wx_id, is_first_time, wx_name from wx_account_info where uuid='%s'" % uuid
            detailInfo = mySqlUtil.getData(sql)
            wxLoginId = detailInfo[0][0]
            password = detailInfo[0][1]
            phone_no = detailInfo[0][2]
            uin = detailInfo[0][3]
            db_passwd = detailInfo[0][4]
            port = taskItemInfo[4]
            wxId = detailInfo[0][5]
            is_first_time = detailInfo[0][6]
            wx_name = detailInfo[0][7]
            ret=loginWx(logger, d, taskItemInfo,mySqlUtil,wxLoginId,password, phone_no)

            if ret[0] == 4 and ret[2]==1:  #登录成功
                sql = "update wx_account_info set if_start='1',last_logout_time=null where uuid='%s'" % taskItemInfo[1]
                logger.info(sql)
                mySqlUtil.excSql(sql)
                #标识模拟器登录
                sql = """update wx_machine_info set is_phone=0 where uuid='%s'""" % taskItemInfo[1]
                mySqlUtil.excSql(sql)

                if is_first_time == '1':
                    while (not elementExistByText(d,wxElementConf.wo,u"我")) or elementExistById(d,wxElementConf.zairu):
                        pwModifySkip(d,logger)
                        time.sleep(0.2)#等待微信后台数据加载完成再去获取数据
                    #time.sleep(2)#等待两秒  保证数据库加载完成
                    uin, db_passwd=machineLoginInit(d, uuid, mySqlUtil)
                    #加载用户头像
                    if elementExistByText(d, wxElementConf.wo, u"通讯录", 0.2):
                        clickByText(d, wxElementConf.wo, u"通讯录")
                        scroll_count = 0
                        logger.info("开始加载头像")
                        while scroll_count < 15 and not elementExistById(d,wxElementConf.wx_friend_end_tag):
                            scroll_count = scroll_count + 1
                            wxUtil.scrollDown(d)
                if uin:
                    updateState(str(taskSeq), '9', mySqlUtil, "系统开始获取微信好友和群信息")#系统开始获取微信好友和群信息
                    logger.info("开始刷新好友数据")
                    #refresh_status = 0
                    wxUtil.appStart(d, logger)
                    if is_first_time == '1':
                        try_time = 10
                        while try_time > 0: #一定要保证获取微信号成功
                            #改为广播
                            broadcast_in_app(port, uuid)
                            #push_conf_file('0', port, db_passwd, uin, uuid, mySqlUtil, 0)  不再需要推送文件
                            time.sleep(5)
                            sql = "select wx_id, is_first_time from wx_account_info where uuid='" + str(uuid) + "'"
                            tmp_info = mySqlUtil.getData(sql)
                            if tmp_info[0][1] == '0':  # 更新微信id
                                wxId = tmp_info[0][0]
                                break
                            else:
                                updateState(str(taskSeq), '23', mySqlUtil, "上线成功")  # 上线成功
                                common.alarm("[%s]登录账号%s首次登录获取微信号失败，正在重试" % (dev_id, wxLoginId))
                            try_time = try_time - 1
                        if try_time == 0:
                            return (4, "[%s]登录账号%s首次登录获取微信号失败" % (dev_id, wxLoginId))
                    #else:
                        #push_conf_file(wxId, port, db_passwd, uin, uuid, mySqlUtil, 0)  不再需要推送文件

                    updateState(str(taskSeq), '10', mySqlUtil, "上线成功")  # 上线成功
                    flushFriend(mySqlUtil, uuid)
                    getResult = redisUtil.publishFlushFriend("flush_friend", "%s:~:0#=#0" % wxId)
                    if "失败" == getResult:
                        common.alarm("[%s]微信[%s-%s]刷新好友redis网络异常" % (dev_id, wxId, wx_name))
                else:
                    remark="该模拟器没有初始化，无法获取uin"
                logger.info(remark)
                if str(wxVersion) == '667':
                    if elementExistByText(d, wxElementConf.yingjilianxi, "从通讯录里选择3位以上你可以随时电话联系的朋友添加成应急联系人。"):
                        clickById(d, wxElementConf.fanhui)  # 直接点击返回
                elif str(wxVersion) == '700':
                    if elementExistByText(d, wxElementConf.yingjilianxi, "请添加3位以上应急联系人，在你登录不上微信帐号的时候，可以通过应急联系人辅助登上微信。"):
                        clickById(d, wxElementConf.yingjilianxi_back)  # 直接点击返回
                ret = (status, remark, ret[2])
                # if status == 3:
                #     logoutWx(logger, d, taskItemInfo, mySqlUtil)
            else:
                ret = (ret[0], ret[1], ret[2])
        elif type=='0':
            logger.info("下线任务")
            updateState(taskSeq, '21', mySqlUtil,"正在检查微信在线状态")
            if elementExistByText(d,wxElementConf.denglu_gengduo,u"更多"):
                ret=[4,"#",1]
            else:
                ret =logoutWx(logger, d, taskItemInfo,mySqlUtil)
            if ret[0] == 4 and ret[2]==1 :  # 成功登出
                #judge_exists_cmd = "adb -s 127.0.0.1:%s shell rm  /data/data/com.gz.pbs.copyfile/files/refresh_wx_info.result" % str(taskItemInfo[4])
                #subprocess.Popen(judge_exists_cmd, shell=False, stdout=subprocess.PIPE)
                sql = "update wx_account_info set if_start='0',last_logout_time=now() where uuid='%s'" % taskItemInfo[1]
                logger.info(sql)
                mySqlUtil.excSql(sql)
                updateState(taskSeq, '20', mySqlUtil,"下线成功")
    except (Exception) as e:
        errlogger.exception(e)
    return (ret[0],ret[1])

def flushFriend(mySqlUtil, uuid):
    taskSeq = round(time.time() * 1000 + random.randint(100, 999))
    sql = "insert into wx_task_manage(taskSeq,uuid,actionType,createTime,priority,status, startTime)value " \
          "(%d, '%s', '9', now(), '5', '2', now())" \
          % (taskSeq, uuid)
    mySqlUtil.excSql(sql)
    return taskSeq

def logoutWx(logger,d,taskItemInfo,mySqlUtil):
    taskSeq=str(taskItemInfo[0])
    taskResult=4
    logoutResult=1
    msg="#"
    try:
        count=0
        while not elementExistByText(d,wxElementConf.denglu_gengduo,u"更多"):
            if count>=30:
                taskResult=3
                break
            else:
                count=count+1

            if judge_logout(d):
                break  #已下线
            if indexJudege(d,logger):
                break  # 已下线
            if elementExistById(d,wxElementConf.denglu_gengduo):
                break  # 已下线

            #if not currentPackageInWx(d):
            backToHomeNew(d)
            if elementExistOnlyByText(d, u"微信"):
                logger.info("打开微信")
                updateState(taskSeq, '1', mySqlUtil,"微信正在下线中...")
                clickOnlyByText(d,u"微信")

            if elementExistByText(d,wxElementConf.wo,u"我"):
                clickByText(d,wxElementConf.wo,u"我")
                dragByIdAndText(d, wxElementConf.wo_shezhi, u"收藏", 0, 3, 0.01)
                clickByText(d,wxElementConf.wo_shezhi,u"设置",10.0)
                dragByIdAndText(d, wxElementConf.wo_shezhi, u"隐私", 0, 3, 0.01)
                clickByText(d,wxElementConf.wo_shezhi,u"退出",10.0)
                clickByText(d,wxElementConf.wo_shezhi_tuichu,u"退出登录",10.0)
                #updateState(taskSeq, '18', mySqlUtil,"正在点击退出按钮")
                clickByText(d,wxElementConf.tuichu,u"退出",10.0)
                time.sleep(3)
                if elementExistByText(d,wxElementConf.xiugaimima,u"为了你下次能够顺利登录微信，在退出前，请为你的微信帐号先设置一个登录密码。"):
                    clickById(d,wxElementConf.fanhui)
                    msg="下线失败，用户密码是纯数字，需要修改密码"
                    updateState(taskSeq, '19', mySqlUtil,"需要修改密码才能退出微信，请用户通过手机登陆微信并修改密码！")
                    logoutResult=0
                break
            time.sleep(0.2)
    except (Exception) as e:
        taskResult=3
        msg=str(e)
        errlogger.exception(e)
    return (taskResult,msg,logoutResult)

def loginWx(logger,d,taskItemInfo,mySqlUtil,wxId,password, phone_no):
    ret=(4,"#",1,0) #任务状态、任务失败描述、登陆结果、是否首次登陆
    try:
        taskSeq = taskItemInfo[0]
        while (not elementExistByText(d,wxElementConf.weixinhao,"用微信号/QQ号/邮箱登录") and
               not elementExistByText(d,wxElementConf.weixinhao,"用手机号登录")) and \
                elementExistById(d,wxElementConf.fanhui):
            pressBack(d)

        if elementExistById(d,wxElementConf.wo) and not elementExistById(d,wxElementConf.qiehuanyuyin)\
                and not elementExistById(d,wxElementConf.biaoqing) and not elementExistById(d,wxElementConf.fasonggengduo):
            updateState(taskSeq, '9', mySqlUtil,"系统开始获取微信好友和群信息") #系统开始获取微信好友和群信息
        else:   #未登录
            ret = loginByParam(taskItemInfo, wxId, password, phone_no, d, mySqlUtil)
    except (Exception) as e:
        errlogger.exception(e)
        ret=(3,"#",0,0)
    finally:
        return ret
def loginByParam(taskItemInfo, wxId, password, phone_no, d, mySqlUtil):
    taskSeq=taskItemInfo[0]
    taskResult=4   #任务执行结果  3失败  会记录remark   4成功
    loginResult=1  #登陆结果   1登陆成功   2 密码错误  3打开微信失败
    if_first_login=0
    remark="#"
    finished_step=[]
    login_process=0
    task_time_limit = int(time.time()) #空跑超1分钟就超时
    try:
        x=0
        y=0
        open_wx_times=0
        while True:#循环直到登录成功
            if not currentPackageInWx(d):
                task_time_limit = int(time.time())  # 空跑超1分钟就超时
                backToHomeNew(d)#
            if login_process<1 and elementExistOnlyByText(d,u"微信"):
                if open_wx_times>2:
                    msg="打开微信失败，请检查"
                    logger.info(msg)
                    return (3, msg, 3, if_first_login)
                task_time_limit = int(time.time())  # 空跑超1分钟就超时
                logger.info("第一步：打开微信")
                open_wx_times+=1
                updateState(taskSeq, '1', mySqlUtil,"打开微信")
                clickOnlyByText(d,u"微信")
                reconfim_time=0
                #等待直到微信打开
                while not currentPackageInWx(d) and reconfim_time<25:
                    reconfim_time+=1
                    time.sleep(0.2)
            if login_process<2 and elementExistByText(d,wxElementConf.chushi_yuyan,u"语言") \
                    and elementExistByText(d,wxElementConf.chushi_denglu,u"登录") \
                    and elementExistByText(d,wxElementConf.chushi_zhuce,u"注册"):
                task_time_limit = int(time.time())  # 空跑超1分钟就超时
                login_process = 2
                logger.info("第二步：初始登录,点击登录按钮")
                updateState(taskSeq, '2', mySqlUtil, "正在输入账号密码")
                clickById(d, wxElementConf.chushi_denglu)  # 点击登录
                if_first_login = 1
            if login_process < 3 and (elementExistByText(d, wxElementConf.denglu_gengduo, u"更多")):
                task_time_limit = int(time.time())  # 空跑超1分钟就超时
                if str(wxVersion) == '667':
                    if elementExistByText(d, wxElementConf.mimadenglu, "用密码登录",time=2):
                        clickByText(d, wxElementConf.mimadenglu, "用密码登录")
                elif str(wxVersion) == '700':  # todo可能需要点击另一个元素退出
                    if elementExistByText(d, wxElementConf.mimadenglu, "切换验证方式",time=2):
                        clickByText(d, wxElementConf.mimadenglu, "切换验证方式")
                    if elementExistByText(d,wxElementConf.wo_shezhi_tuichu,"用密码登录",time=2):
                        clickByText(d, wxElementConf.wo_shezhi_tuichu, "用密码登录")
                if (elementExistById(d, wxElementConf.shurukuang,2) and elementExistById(d, wxElementConf.wxhao)
                        and getTextById(d, wxElementConf.wxhao) == wxId):
                    login_process = 5
                    logger.info("第五步：有账号且相同，直接输入密码并登陆")
                    updateState(taskSeq, '5', mySqlUtil, "正在登录")
                    setTextById(d, wxElementConf.shurukuang, password)
                    clickByText(d, wxElementConf.denglu, "登录")  # 点击登录
                elif (elementExistById(d, wxElementConf.shurukuang) and elementExistById(d, wxElementConf.wxhao)
                        and getTextById(d, wxElementConf.wxhao) == phone_no):#手机方式登陆
                    login_process = 5
                    logger.info("第五步：有账号且相同，直接输入密码并登陆")
                    updateState(taskSeq, '5', mySqlUtil, "正在登录")
                    setTextById(d, wxElementConf.shurukuang, password)
                    clickByText(d, wxElementConf.denglu, "登录")  # 点击登录
                else:
                    login_process = 3
                    logger.info("第三步：有账号且不相同，点击登陆其他账号")
                    updateState(taskSeq, '3', mySqlUtil, "正在输入账号密码")
                    clickByText(d, wxElementConf.denglu_gengduo, u"更多")# 更多
                    clickByText(d, wxElementConf.wo_shezhi_tuichu, u"登录其他帐号")

            if login_process < 4 and elementExistByText(d, wxElementConf.weixinhao, "用微信号/QQ号/邮箱登录"):
                task_time_limit = int(time.time())  # 空跑超1分钟就超时
                if phone_no and phone_no != '' and phone_no != "None":
                    logger.info("第四步：输入手机号码")
                    updateState(taskSeq, '5', mySqlUtil, "正在登陆")
                    clearTextById(d, wxElementConf.shurukuang)
                    setTextById(d, wxElementConf.shurukuang, phone_no)
                    clickById(d, wxElementConf.denglubyphone)  # 点击登录
                    time.sleep(1)
                    clearTextByIdClassInstance(d, wxElementConf.shurukuang, "android.widget.EditText", 1)
                    setTextByIdClassInstance(d, wxElementConf.shurukuang, "android.widget.EditText", 1, password)
                    clickById(d, wxElementConf.denglubyphone)  # 点击登录
                    login_process = 5
                else:
                    login_process = 4
                    logger.info("第四步：手机号登陆切换到微信号登陆")
                    updateState(taskSeq, '4', mySqlUtil, "正在输入账号密码")
                    clickByText(d, wxElementConf.weixinhao, "用微信号/QQ号/邮箱登录")  # 用微信号/QQ号/邮箱登录
            if login_process < 5 and elementExistById(d, wxElementConf.shurukuang) and \
                    elementExistByText(d, wxElementConf.weixinhao,"用手机号登录"):#
                task_time_limit = int(time.time())  # 空跑超1分钟就超时
                login_process = 5
                logger.info("第五步：输入账号密码并点击登陆")
                updateState(taskSeq, '5', mySqlUtil, "正在登陆")
                clearTextById(d, wxElementConf.shurukuang)
                clearTextByIdClassInstance(d, wxElementConf.shurukuang, "android.widget.EditText", 1)
                setTextById(d, wxElementConf.shurukuang, wxId)
                setTextByIdClassInstance(d, wxElementConf.shurukuang, "android.widget.EditText", 1, password)
                clickByText(d, wxElementConf.denglu, "登录")  # 点击登录
            if 1 not in finished_step and elementExistByText(d, wxElementConf.mimacuowu, "你的微信版本过低，请升级至最新版本微信后再登录微信。"):
                logger.info("其他步骤：微信版本过低，需要升级，点击取消")
                clickByText(d, wxElementConf.quxiao, "取消")  # 点击取消
                finished_step.append(1)
            if 2 not in finished_step and elementExistByDesc(d,u"参与内测"):
                logger.info("其他步骤：是否参与内测，点击关闭")
                clickById(d, wxElementConf.guanbi)  # 关闭升级提示
                finished_step.append(2)
            if login_process < 6 and elementExistByDesc(d, u"拖动下方滑块完成拼图"):  #需要拖动滑块验证
                logger.info("第六步：滑块验证")
                tag_bar_result = tag_bar_valid(d, taskSeq, mySqlUtil, wxId)
                if tag_bar_result:
                    login_process = 6
                else:
                    if elementExistByDesc(d, u"拖动下方滑块完成拼图"):
                        pressBack(d)
                        logger.info("第六步：滑块拖动失败，退到登陆界面再重新进入，刷新滑块内容")
                        #重新进入界面，刷新滑块
                        if elementExistById(d, wxElementConf.denglu, 0.5):
                            clickById(d, wxElementConf.denglu)
                        elif elementExistById(d, wxElementConf.denglubyphone, 0.5):
                            clickById(d, wxElementConf.denglubyphone)
                task_time_limit = int(time.time())  # 空跑超1分钟就超时
            #如果提示安全验证，显示二维码让用户扫描
            if login_process < 7 and (elementExistByDesc(d, u"你正在一台新设备登录微信，为了你的帐号安全，请进行安全验证") or
                                          elementExistByDesc(d, u"本次验证已失效，请重新扫码") or elementExistByDesc(d, u"通过扫码验证身份")):  #
                login_process = 7
                logger.info("第七步：二维码验证")
                qr_code_valid(d, taskSeq, mySqlUtil, wxId)
                task_time_limit = int(time.time())  # 空跑超1分钟就超时

            # 如果登录密码错误，退出循环，建议用户重建资料
            if elementExistByText(d,wxElementConf.mimacuowu,u"帐号或密码错误，请重新填写。")\
                   or elementExistByText(d,wxElementConf.mimacuowu,u"帐号或密码错误，请重新填写")\
                   or elementExistByText(d,wxElementConf.mimacuowu,u"帐号/密码错误或帐号密码组合错误。详情请查看帮助。"):#密码错误
                logger.info("密码错误")
                updateState(taskSeq, '11', mySqlUtil,"微信账号密码错误，请修改后重新上线登录")
                backToHomeNew(d)
                taskResult = 3
                loginResult=2
                remark="密码错误"
                break
            if str(wxVersion)=='667':
                if 3 not in finished_step and elementExistByText(d,wxElementConf.tishi,"看看手机通讯录里谁在使用微信？（不保存通讯录的任何资料，仅使用特征码作匹配识别）")\
                        and elementExistById(d,wxElementConf.quxiao):#是否匹配手机通讯录
                    task_time_limit = int(time.time())  # 空跑超1分钟就超时
                    logger.info("是否匹配手机通讯录")
                    clickById(d,wxElementConf.quxiao)  # 点击否
                    finished_step.append(3)
            elif str(wxVersion)=='700':#todo可能需要点击另一个元素退出
                if 3 not in finished_step and elementExistByText(d,wxElementConf.tishi,"请添加3位以上应急联系人，在你登录不上微信帐号的时候，可以通过应急联系人辅助登上微信。")\
                        and elementExistById(d,wxElementConf.quxiao):#是否匹配手机通讯录
                    task_time_limit = int(time.time())  # 空跑超1分钟就超时
                    logger.info("是否匹配手机通讯录")
                    clickById(d,wxElementConf.quxiao)  # 点击否
                    finished_step.append(3)
                if 4 not in finished_step and elementExistByText(d,wxElementConf.zitidaxiao,"微信可设置字体大小") and elementExistById(d,wxElementConf.quxiao):#提示修改微信字体大小
                    task_time_limit = int(time.time())  # 空跑超1分钟就超时
                    logger.info("是否设置字体大小")
                    clickById(d, wxElementConf.quxiao)  # 点击暂不设置
                    finished_step.append(4)
            #完成按钮： com.tencent.mm:id/hg   fabiao
            #顶端标题  resourceId="android:id/text1"
            if wxUtil.elementExistById(d, WxElementConf.fabiao): #点掉应急联系人等需要确认的场景
                wxUtil.clickById(d, WxElementConf.fabiao)
                task_time_limit = int(time.time())  # 空跑超1分钟就超时
            pwModifySkip(d,logger)
            if elementExistById(d,wxElementConf.zairu):
                task_time_limit = int(time.time())  # 空跑超1分钟就超时
                u2_text=""
                try:
                    u2_text=getTextById(d,wxElementConf.zairu)
                except:
                    pass
                logger.info(u2_text)
                if "正在载入数据" in str(u2_text):
                    logger.info("正在载入数据！")
                    updateState(taskSeq, '8',mySqlUtil,str(u2_text))
                    taskResult = 4
            if elementExistById(d,wxElementConf.wo) or elementExistById(d,wxElementConf.bottom_me):
                if elementExistById(d,wxElementConf.fasonggengduo):
                    pressBack(d)
                logger.info("登录成功！")
                updateState(taskSeq, '9', mySqlUtil, "系统开始获取微信好友和群信息")
                taskResult = 4
                break
            logger.info("循环中。。。")
            if int(time.time()) - task_time_limit > 60:
                taskResult = 3
                loginResult = 2
                remark = "登陆超时"
                updateState(taskSeq, '24', mySqlUtil, "登陆超时，请重新登陆")
                break
            #判断是否超时
        logger.info("登录完成！")
    except (Exception) as e:
        taskResult = 3
        remark=e
        errlogger.info(traceback.format_exc())
    return (taskResult,remark,loginResult,if_first_login)

def getXValue(taskSeq,mySqlUtil):
    try:
        sql="select x_value from wx_login_task where state='0' and taskSeq='%s'" %taskSeq
        xValuePercent='0'
        result=mySqlUtil.getData(sql)
        if result:
            xValuePercent=result[0][0]
        return xValuePercent
    except (Exception) as e:
        errlogger.info(e)

def updateState(taskSeq,state,mySqlUtil,remark):
    try:
        sql="update wx_login_task set x_value='',state='%s',remark='%s'  where taskSeq='%s'" %(state,str(remark),taskSeq)
        mySqlUtil.execSql(sql)
    except (Exception) as e:
        errlogger.info(e)

#查找色域
def get_dominant_color(image):
    max_score = 0.0001
    dominant_color = None
    for count, (r, g, b) in image.getcolors(image.size[0] * image.size[1]):
        # 转为HSV标准
        saturation = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)[1]
        y = min(abs(r * 2104 + g * 4130 + b * 802 + 4096 + 131072) >> 13, 235)
        y = (y - 16.0) / (235 - 16)

        # 忽略高亮色
        if y > 0.9:
            continue
        score = (saturation + 0.1) * count
        if score > max_score:
            max_score = score
            dominant_color = (r, g, b)
    return dominant_color
def tag_bar_valid(d,taskSeq,mySqlUtil,wxId):
    logger.info("第六步：需要拖动滑块图片")
    screenCutCount=0
    retry_times = 0
    while retry_times < 30 and elementExistByDesc(d,u"拖动下方滑块完成拼图"):  # 30次都点不中的，不点了
        retry_times += 1
        index = 0
        while not elementExistByDesc(d,u"tag-bar") and \
                elementExistByDesc(d,u"拖动下方滑块完成拼图")\
                and index < 100:  # 等图片加载完,最多等待20秒不加载就退出
            time.sleep(0.2)
            index += 1
        if index == 100:
            raise Exception("滑块加载失败，联系管理人员")
        x, y = getCenterByDesc(d,u"tag-bar")
        if elementExistByClassAndInstance(d,"android.widget.Image",1):
            xS, yS = getCenterByClassAndInstance(d,"android.widget.Image",1)
            logger.info("需拖动小图片的中心坐标：x:" + str(xS) + "  y:" + str(yS))
        displayWidth = getDeviceInfo(d,"display","width")
        checkCodeImgPath =os.path.join("img","checkCodeImg\\")
        checkCodeImgName = str(taskSeq) + str(screenCutCount) + ".jpg"
        checkCodeImgPathName = os.path.join(checkCodeImgPath , checkCodeImgName)
        saveScreenShot(d,checkCodeImgPathName)  # 截屏
        sizeList = [0.03693, 0.2206, 0.92612, 0.346]
        cutImgName = handlePic.cutPicByPil(checkCodeImgPath, checkCodeImgName, sizeList)  # 剪裁后的图片
        imgStr = checkCodeImgPath + cutImgName
        send_image = Image.open(imgStr)
        send_image = send_image.convert('RGB')
        img_obj = open(imgStr, "rb")
        files = {"filecontent": (cutImgName, img_obj, "image/jpg")}
        today=time.strftime("%Y%m%d")
        req = requests.post(fileServiceURL+"/uploadMsgFile/", files=files,
                            data = {"file_date": today, "wx_id": wxId, "file_path": "wx_login", "file_name": cutImgName,
                "child_path": "tag_img"})
        send_result = req.text
        logger.info("发送图片结果：" + send_result)
        picture = fileServiceURL+"/static/wx_login/" + today + "/" + wxId + "/tag_img/" + cutImgName
        img_obj.close()
        if os.path.exists(imgStr):
            os.remove(imgStr)
        if os.path.exists(checkCodeImgPathName):
            os.remove(checkCodeImgPathName)
        # 存储信息到数据库
        state = '15'  # 非第一次拖动
        if screenCutCount == 0:
            state = '6'  # 第一次拖动
        sql = "update wx_login_task set x_value='',picture_name='" + picture + "',state='" + state + "' where taskSeq='" + str(
            taskSeq) + "'"
        logger.info("存储信息到数据库:" + sql)
        mySqlUtil.execSql(sql)
        screenCutCount = screenCutCount + 1
        index = 0
        while True:  # 循环获取X值，直到获取成功
            xValuePercent =getXValue(taskSeq, mySqlUtil)#
            if xValuePercent and xValuePercent != '0':  # 等待1分钟，没点击则重新截图
                break
            elif index > 300:
                break
            else:
                time.sleep(0.2)
                index += 1
        if xValuePercent and xValuePercent != '0':
            logger.info("获取到xValuePercent:" + str(xValuePercent))
            xValue = float(displayWidth) * (float(xValuePercent) * 0.92612 + 0.047)  # 由于图片被剪切过，所以坐标需根据剪裁的比例重新处理，对应handlePic.cutPicByPil()
            if elementExistByClassAndInstance(d,"android.widget.Image",1):
                dragByClassNameAndInstance(d,"android.widget.Image",1,xValue, y, 0.1)
                result_jg_times = 0
                logger.info("开始判断是否拖动成功")
                while result_jg_times < 5:  # 判断是否滑块验证成功
                    if elementExistByDesc(d,u"请控制拼图块对齐缺口", 0.1) or \
                            elementExistByDesc(d,u"这题有点难呢，已为您更换题目", 0.1):
                        break
                    if elementExistByText(d, wxElementConf.denglu, "登录", 0.5):
                        clickByText(d, wxElementConf.denglu, "登录")
                        logger.info("滑块验证成功")
                        updateState(taskSeq, '17', mySqlUtil, "滑块验证成功，继续登录")
                        return True
                    if elementExistByText(d, wxElementConf.denglubyphone, "登录", 0.5):
                        clickByText(d, wxElementConf.denglubyphone, "登录")
                        logger.info("滑块验证成功")
                        updateState(taskSeq, '17', mySqlUtil, "滑块验证成功，继续登录")
                        return True
                    result_jg_times += 1
    return False #重做

def qr_code_valid(d,taskSeq,mySqlUtil,wxId):
    qrCutCount = 0  # 二维码图片发送次数
    reValidCount = 0  # 二维码图片重新加载次数
    retry_times = 0
    last_send_img = ""
    checkCodeImgPath = "img\\checkCodeImg\\"
    if not os.path.exists(checkCodeImgPath):
        os.makedirs(checkCodeImgPath)
    while retry_times < 150:  # 5分钟超时
        retry_times += 1
        if elementExistByDesc(d,u"开始验证"):
            updateState(taskSeq,"18",mySqlUtil,"需要扫码验证，正在截图")
            clickByDesc(d,u"开始验证") # 点击开始验证
            clickByDesc(d,u"扫二维码验证")
            pic_load_times = 0
            while not elementExistByDesc(d,u"通过扫码验证身份") and pic_load_times < 50:
                time.sleep(0.5)
                pic_load_times += 1
            time.sleep(3)  # 文字出来了 图片不一定。
        elif not elementExistByDesc(d,u"通过扫码验证身份"):
            logger.info("扫码验证成功，10秒内点击登陆按钮")
            wait_btn_times=0
            while wait_btn_times<20:  #10秒内点击登陆并跳出循环，否则再次循环
                if elementExistByText(d,wxElementConf.denglu,"登录"):
                    clickByText(d,wxElementConf.denglu,"登录")
                    updateState(taskSeq, '25', mySqlUtil, "点击了登录，后续不再验证")
                    return True
                elif elementExistByText(d,wxElementConf.denglubyphone,"登录"):
                    clickByText(d,wxElementConf.denglubyphone,"登录")
                    updateState(taskSeq, '25', mySqlUtil, "点击了登录，后续不再验证")
                    return True
                else:
                    wait_btn_times+=1
                    time.sleep(0.5)
        qrCutCount = qrCutCount + 1
        checkCodeImgName = str(taskSeq) + str(qrCutCount) + "x.jpg"
        checkCodeImgPathName = checkCodeImgPath + checkCodeImgName
        saveScreenShot(d,checkCodeImgPathName)  # 截屏
        sizeList = [0.1789, 0.1827, 0.644, 0.4224]
        # sizeList = [0.0395, 0.2193, 0.9630, 0.5647]
        cutImgName = handlePic.cutPicByPil(checkCodeImgPath, checkCodeImgName, sizeList)  # 剪裁后的图片
        if os.path.exists(checkCodeImgPathName):
            os.remove(checkCodeImgPathName)
        imgStr = checkCodeImgPath + cutImgName
        logger.info(imgStr)
        # 如果不同，发送新的图片，删除旧的图片
        diff=None
        if last_send_img:
            diff = ImageChops.difference(Image.open(last_send_img), Image.open(imgStr))
        if last_send_img == "" or diff.getbbox():
            send_image = Image.open(imgStr)
            send_image = send_image.convert('RGB')
            color_dominant = get_dominant_color(send_image)
            logger.info(color_dominant)
            if color_dominant and color_dominant == (0, 0, 0):  # 只截取二维码，二维码色域全是0
                logger.info("确认是二维码，二维码图片有变化，发送截图")
                reValidCount = reValidCount + 1
                img_obj = open(imgStr, "rb")
                files = {"filecontent": (cutImgName, img_obj, "image/jpg")}
                today=time.strftime("%Y%m%d")
                req = requests.post(fileServiceURL + "/uploadMsgFile/", files=files,
                                    data={"file_date": today, "wx_id": wxId, "file_path": "wx_login",
                                          "file_name": cutImgName,
                                          "child_path": "qr_code_img"})
                img_obj.close()
                logger.info(fileServiceURL)
                send_result = req.text
                logger.info(send_result)
                print (req)
                picture=fileServiceURL+"/static/wx_login/"+today+"/"+wxId+"/qr_code_img/"+cutImgName
                logger.info("发送二维码图片结果：" + send_result)
                if os.path.exists(last_send_img):
                    os.remove(last_send_img)
                last_send_img = imgStr
                qr_state = '7' #非首次扫码
                if reValidCount > 1:
                    qr_state = '14' #首次扫码
                sql = "update wx_login_task set x_value='',picture_name='" \
                      + picture + "',state='" + qr_state + "' where taskSeq='" + str(taskSeq) + "'"
                logger.info(sql)
                mySqlUtil.execSql(sql)
            elif  color_dominant and color_dominant == (9, 186, 7):
                logger.info("请在原来的手机上点击授权按钮")
                updateState(taskSeq, '22', mySqlUtil, "请在原来的手机上点击授权按钮")
        # 如果相同，删除新的，保留旧的
        else:
            logger.info("二维码图片无变化，删除此次截图，等待两秒")
            if os.path.exists(imgStr):
                os.remove(imgStr)
        time.sleep(2)
def distance_detect(image_name):
    screenshot = cv2.imread(image_name)
    height=len(screenshot)
    width=len(screenshot[0])
    #改成了只截掉文字部分
    screenshot = screenshot[0:int(3*height/4), 0:width]

    # 筛选出符合颜色区间的区域
    inRange = cv2.inRange(screenshot, np.array([90, 90, 90]), np.array([115, 115, 115]))
    # cv2.imwrite('maskstart3.jpg',inRange)
    # 从图中找出所有的轮廓
    #res = cv2.bitwise_and(screenshot,screenshot, mask= inRange)
    #cv2.imwrite('mask.jpg',res)
    _, cnts, _ = cv2.findContours(inRange.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # 对所有轮廓做排序，排序依据是每个轮廓包含的点的数量
    cnts.sort(key=len, reverse=True)

    # 取第一个轮廓（据说有些情况是需要两个）
    pointCounter = 0
    x =0
    for cnt in cnts[0:1]:
        pointCounter += 1
        xSum = 0
        ySum = 0
        xCounter = 0
        for position in cnt:
            xCounter += 1
            xSum += position[0][0]
            ySum += position[0][1]
            #print(position)
            # 算出所有点的X坐标和Y坐标的平均值
        x = int(xSum / xCounter - 6)
        y = int(ySum / xCounter + 15)
        print(x,y)
        # image (x,y) (x,y) color thickness
        cv2.line(screenshot, (0, y), (x, y), (0, 255, 0), 4)
        # cv2.imwrite('result1.jpg',screenshot)
        print(pointCounter)
    return x

def broadcast_in_app(port, uuid_str):
    try:
        broadcast_command = """adb -s 127.0.0.1:%s shell am broadcast -a 'HuiliaoMsg' --es act 'getWxMainId' --es type '0' --es uuid '%s' """\
                            %(str(port), uuid_str)
        logger.debug(broadcast_command)
        p = subprocess.Popen(broadcast_command)
        p.wait()
    except Exception as e:
        errlogger.info(traceback.format_exc())

# def push_conf_file(wx_id,port,db_pwd,uin,uuid,mySqlUtil,if_first_login):
#     try:
#         port=str(port)
#         #wx_id;dm5_path;uuid
#         from actionModule.getWxFriendList import md5_file
#         dm5_path=md5_file(uin)
#         local_path="data/%s/" % str(wx_id)
#         file_name=local_path+"huiliao.conf"
#         if not os.path.exists(local_path):
#             os.makedirs(local_path)
#         file_obj = open(file_name, 'w')  # 若是'wb'就表示写二进制文件
#         input_list = [wx_id, str(dm5_path), str(uuid)]
#         file_obj.write(";".join(input_list))
#         file_obj.close()
#         judge_exists_cmd = "adb -s 127.0.0.1:%s shell ls -d /sdcard/copyfile/" % port
#         judge_exists_ret = subprocess.Popen(judge_exists_cmd, shell=False, stdout=subprocess.PIPE).stdout.read()
#         if "No such file or directory" in str(judge_exists_ret):
#             logger.info("没有找到app路径")
#         else:
#             push_command = "adb -s 127.0.0.1:%s push %s /sdcard/copyfile/" % (port,file_name)
#             p = subprocess.Popen(push_command)
#             p.wait()
#     except Exception as e:
#         errlogger.info(traceback.format_exc())
# def update_wx_oper_wx(mysqlUtils,wxLoginId,logger):
#     sql_get_wx_id="select wx_id from wx_account_info where wx_login_id='"+wxLoginId+"' and wx_id is not null and wx_id != wx_login_id"
#     rs_get_wx_id = mysqlUtils.getData(sql_get_wx_id)
#     if len(rs_get_wx_id)==0 or  not rs_get_wx_id[0][0]:
#         logger.info("无法找到正确的wxId")
#     else:
#         wxId=rs_get_wx_id[0][0]
#         sql_wx_login_id = "select oper_id from wx_oper_wx where object_id='" + wxLoginId + "'"
#         rs_wx_login_id = mysqlUtils.getData(sql_wx_login_id)
#         if len(rs_wx_login_id)==0:#没有需要更新的，直接返回
#             return 0
#         else:
#             sql_wx_id="select oper_id from wx_oper_wx where object_id='"+wxId+"'"
#             rs_wx_id=mysqlUtils.getData(sql_wx_id)
#             if len(rs_wx_id) > 0:  # 有需要更新的且有历史数据，需要先删除历史数据再更新
#                 sql_delete = "delete from wx_oper_wx where object_id ='" + wxId + "'"
#                 mysqlUtils.excSql(sql_delete)
#             sql_update = "update wx_oper_wx set object_id='" + wxId + "' where  object_id='" + wxLoginId + "'"
#             mysqlUtils.excSql(sql_update)
#             logger.info("更新wx_login_id为wx_id：" + sql_update)


import time
import os, re
import signal
import random
import linecache
from lib.WxElementConf import WxElementConf
from lib.FinalLogger import *

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/wxUtil.log')
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
wxElementConf = WxElementConf(logger)


# 返回到微信首页
def backToHome(u2Con):
    while True:
        try:
            time.sleep(1)
            if not elementExistById(u2Con,wxElementConf.home_page_wx) or elementExistById(u2Con,wxElementConf.change_to_keyboard):
                time.sleep(0.2)
                if elementExistById(u2Con,wxElementConf.remark_save_tips):
                    clickById(u2Con,wxElementConf.not_save_edit_result)
                pressBack(u2Con)
            else:
                clickById(u2Con,wxElementConf.home_page_wx)
                break
        except Exception as e:
            pass
#优化版
def backToHomeNew(u2Con):
    index=0
    while index<10:
        try:
            time.sleep(1)
            if not elementExistById(u2Con,wxElementConf.home_page_wx) or elementExistById(u2Con,wxElementConf.change_to_keyboard):
                time.sleep(0.2)
                if elementExistById(u2Con,wxElementConf.remark_save_tips) and elementExistById(u2Con,wxElementConf.not_save_edit_result):
                    clickById(u2Con, wxElementConf.not_save_edit_result)
                pressBack(u2Con)
            else:
                clickById(u2Con, wxElementConf.home_page_wx)
                break
            if elementExistOnlyByText(u2Con, u"微信"):
                logger.info("当前在桌面，不需要返回了")
                break
        except Exception as e:
            pass
        index+=1
    if index>9:
        logger.info("返回10次，可能不需要再点返回了")

def pwModifySkip(d, logger):
    logger.debug("忽略告警框")
    if elementExistById(d,wxElementConf.quxiao):
        clickById(d, wxElementConf.quxiao)  # 点击确定
    # if elementExistByText(d,wxElementConf.yourendenglu,
    #          "有人正通过微信密码登录你的微信，如果这不是你本人操作，你的密码已经泄漏。如果对方登录成功，本设备将会被强制退出登录。请立刻修改微信密码，慎防盗号。"):  # 有人正通过QQ密码登录你的微信，如果这不是你本人操作，你的QQ密码已经泄露。如果对方登录成功，本设备将会被强制退出。请立刻到设置-帐号与安全解绑QQ，慎防盗号。
    #     logger.info("有人正通过微信密码登录你的微信")
    #     clickById(d,wxElementConf.quxiao)  # 点击确定
    # elif elementExistByText(d,wxElementConf.mimacuowu,
    #            "有人正通过微信密码登录你的微信，如果这不是你本人操作，你的密码已经泄漏。如果对方登录成功，本设备将会被强制退出登录。请立刻修改微信密码，慎防盗号。"):  # 有人正通过QQ密码登录你的微信，如果这不是你本人操作，你的QQ密码已经泄露。如果对方登录成功，本设备将会被强制退出。请立刻到设置-帐号与安全解绑QQ，慎防盗号。
    #     logger.info("有人正通过微信密码登录你的微信")
    #     clickById(d, wxElementConf.quxiao)  # 点击确定
    # elif elementExistByText(d,wxElementConf.yourendenglu,
    #            "有人正通过QQ密码登录你的微信，如果这不是你本人操作，你的QQ密码已经泄露。如果对方登录成功，本设备将会被强制退出。请立刻到设置-帐号与安全解绑QQ，慎防盗号。"):  # 有人正通过QQ密码登录你的微信，如果这不是你本人操作，你的QQ密码已经泄露。如果对方登录成功，本设备将会被强制退出。请立刻到设置-帐号与安全解绑QQ，慎防盗号。
    #     logger.info("有人正通过QQ密码登录你的微信")
    #     clickById(d, wxElementConf.quxiao)  # 点击确定
    # elif elementExistByText(d,wxElementConf.mimacuowu,
    #            "有人正通过QQ密码登录你的微信，如果这不是你本人操作，你的QQ密码已经泄露。如果对方登录成功，本设备将会被强制退出。请立刻到设置-帐号与安全解绑QQ，慎防盗号。"):  # 有人正通过QQ密码登录你的微信，如果这不是你本人操作，你的QQ密码已经泄露。如果对方登录成功，本设备将会被强制退出。请立刻到设置-帐号与安全解绑QQ，慎防盗号。
    #     logger.info("有人正通过QQ密码登录你的微信")
    #     clickById(d, wxElementConf.quxiao)  # 点击确定

# 返回到微信首页 -- 有问题 停用
def backToHomeMsg(u2Con):
    while True:
        try:
            if elementExistByText(u2Con, wxElementConf.home_page_wx, u"微信", 0.5) \
                    and not elementExistById(u2Con,wxElementConf.change_to_keyboard):
                clickByText(u2Con, wxElementConf.home_page_wx, u"微信")
                break
            elif elementExistOnlyByText(u2Con, u"微信"):
                clickByDesc(u2Con, u"微信")
            else:
                #提示窗口点掉
                if elementExistById(u2Con, wxElementConf.remark_save_tips): #信息提示框
                    clickById(u2Con, wxElementConf.remark_save_tips)
                elif elementExistById(u2Con, wxElementConf.quxiao): #取消或确定按钮
                    clickById(u2Con, wxElementConf.quxiao)
                elif elementExistById(u2Con, wxElementConf.tuichu): #确定按钮
                    clickById(u2Con, wxElementConf.tuichu)
                elif elementExistById(u2Con, "android:id/message"): #Android对话框
                    if "很抱歉" in getTextById(u2Con, "android:id/message"): #Android对话框
                        clickById(u2Con, "android:id/button1") #Android对话框
                    if "无响应" in getTextById(u2Con, "android:id/message"): #Android对话框
                        clickById(u2Con, "android:id/button2")  # Android对话框
                u2Con.press("back") #Android回退按钮
        except Exception as e:
            pass

def indexJudege(u2Con, logger):

    ## 20190325 修改
    retFlag = False
    findPassFlag = u2Con.xpath("//android.widget.Button[@text='找回密码']").exists
    freezeFlag = u2Con.xpath("//android.widget.Button[@text='紧急冻结']").exists
    if findPassFlag and freezeFlag:
        retFlag = True
    else:
        retFlag = False

    return retFlag

    # # logger.debug("微信登陆退出检查")
    # # time.sleep(0.5) # 20181207
    # # 判断是否为登陆页
    # indexExist = False
    # # 登陆与注册首页
    # logger.debug("检查微信登出")
    # loginExist = 0
    # regExist = 0
    # loginNum = u2Con(resourceId="com.tencent.mm:id/d1w").count
    # regNum = u2Con(resourceId="com.tencent.mm:id/d1v").count
    # if loginNum > 0:
    #     loginText = u2Con(resourceId="com.tencent.mm:id/d1w").get_text()
    #     if loginText in ["登录"]:
    #         loginExist = 1
    # if regNum > 0:
    #     regText = u2Con(resourceId="com.tencent.mm:id/d1v").get_text()
    #     if regText in ["注册"]:
    #         regExist = 1
    # if loginExist == 1 and regExist == 1:
    #     indexExist = True
    #
    #     return indexExist
    #
    # # 登陆页判断
    # LoginTypeExist = 0
    # mulLoginExist = 0
    # LoginIndexExist = False
    # # 手机号登陆
    # LoginTypeNum = u2Con(resourceId="com.tencent.mm:id/bwm").count
    # # 用微信号/QQ号/邮箱登陆判定
    # mulLoginNum = u2Con(resourceId="com.tencent.mm:id/kk").count
    # if LoginTypeNum > 0 and mulLoginNum > 0:
    #     LoginTypeNumText = u2Con(resourceId="com.tencent.mm:id/kk").get_text()
    #     mulLoginText = u2Con(resourceId="com.tencent.mm:id/bwm").get_text()
    #     if LoginTypeNumText in ["手机号登录", "微信号/QQ/邮箱登录"]:
    #         LoginTypeExist = 1
    #     if mulLoginText in ["用微信号/QQ号/邮箱登录", "用手机号登录"]:
    #         mulLoginExist = 1
    #     if LoginTypeExist == 1 and mulLoginExist == 1:
    #         LoginIndexExist = True
    #         return LoginIndexExist
    #
    # # 注册页判断
    # regIndexExist = False
    # regTypeNum = u2Con(resourceId="com.tencent.mm:id/cu8").count
    # if regTypeNum > 0:
    #     regButtonText = u2Con(resourceId="com.tencent.mm:id/cu8").get_text()
    #     if regButtonText == "注册":
    #         regIndexExist = True
    #         return regIndexExist
    #
    # # 判断是否为登录页，包含密码登录和短信验证登录
    # indexExit = False
    # # 密码登录验证页
    # pwdExit = 0
    # msgJudgeExit = 0
    # pwdNum = u2Con(resourceId="com.tencent.mm:id/ge").count
    #
    # msgJudgeNum = u2Con(resourceId="com.tencent.mm:id/c29").count
    # if pwdNum > 0:
    #     pwdText = u2Con(resourceId="com.tencent.mm:id/ge").get_text()
    #     if pwdText.replace(" ", "") in ["密码", "验证码"]:
    #         pwdExit = 1
    # if msgJudgeNum > 0:
    #     msgJudgeText = u2Con(resourceId="com.tencent.mm:id/c29").get_text()
    #     if msgJudgeText.replace(" ", "") in ["用短信验证码登录", "用密码登录"]:
    #         msgJudgeExit = 1
    # if pwdExit == 1 and msgJudgeExit == 1:
    #     indexExit = True
    #     return indexExit
    #
    # # 其他登陆方式
    # loginFlag = 0
    # pwSb = u2Con(resourceId="com.tencent.mm:id/c1y").count
    # emeCon = u2Con(resourceId="com.tencent.mm:id/c20").count
    # moreCon = u2Con(resourceId="com.tencent.mm:id/c21").count
    # if pwSb > 0:
    #     if u2Con(resourceId="com.tencent.mm:id/c1y").get_text() == "找回密码":
    #         loginFlag += 1
    # if emeCon > 0:
    #     if u2Con(resourceId="com.tencent.mm:id/c20").get_text() == "紧急冻结":
    #         loginFlag += 1
    # if moreCon > 0:
    #     hereText = u2Con(resourceId="com.tencent.mm:id/c21").get_text()
    #     if hereText == "更多" or hereText == "微信安全中心":
    #         loginFlag += 1
    # if loginFlag == 3:
    #     return True
    # return False


def updateSkip(u2Con):
    # 更新页忽略
    updateExist = u2Con(resourceId="com.tencent.mm:id/c8y").count
    if updateExist > 0:
        updateTitle = u2Con(resourceId="com.tencent.mm:id/c8y").get_text()
        if updateTitle == "更新":
            u2Con(resourceId="com.tencent.mm:id/alk").long_click()
            time.sleep(1)
            u2Con(resourceId="com.tencent.mm:id/all").long_click()


def wxUpdateSkip(u2ConStart, logger):
    logger.debug("微信更新检查")
    try:
        if elementExistById(u2ConStart, wxElementConf.needUpdate):
            while True:
                time.sleep(0.5)
                if "更新" in getTextById(u2ConStart, wxElementConf.needUpdate):
                    if "是否取消安装" in getTextById(u2ConStart, wxElementConf.cancelTips):
                        clickById(u2ConStart, wxElementConf.cancelUpdateConfirm)
                    else:
                        clickById(u2ConStart, wxElementConf.cancelUpdate)
                elif "提示" in getTextById(u2ConStart, wxElementConf.needUpdate):
                    if "是否取消安装" in getTextById(u2ConStart, wxElementConf.cancelTips):
                        clickById(u2ConStart, wxElementConf.cancelUpdateConfirm)
                else:
                    break

        if any(u2ConStart(description=u"参与内测")):
            u2ConStart(resourceId="com.tencent.mm:id/i2").click_exists(10.0)  # 关闭升级提示
    except Exception:
        pass




def machineBrowSkip(u2ConStart, logger):
    while True:
        if elementExistById(u2ConStart, "android:id/message"):
            if "很抱歉" in getTextById(u2ConStart, "android:id/message"):
                clickById(u2ConStart, "android:id/button1")
                logger.info("模拟器故障，已恢复")
        else:
            break

# 页面监控
def watcherRegister(u2Con):
    try:
        u2Con.watchers.reset()
        u2Con.watcher("SKIP_UPDATE_CANCEL").when(text=u"更新").click(text=u"取消") # 提示需要更新
        u2Con.watcher("SKIP_UPDATE_CONFIRN").when(text=u"提示").click(text=u"是")  # 确认取消
        u2Con.watcher("OFFLINR_BY_USER").when(text=u"提示").click(text=u"确定") # 挤下线
        u2Con.watcher("NOT_SET_SIZE").when(text=u"暂不设置").click(text=u"暂不设置")  # 设置字体
    except Exception as e:
        pass

# 判断微信是否被挤下线
def judge_logout(d):
    logger.debug("检查微信挤下线")
    if elementExistByText(d, wxElementConf.yourendenglu, u"提示") \
            and elementExistById(d, wxElementConf.mimacuowu) and elementExistById(d, wxElementConf.tuichu):
        if "你的微信帐号于" in getTextById(d, wxElementConf.mimacuowu):
            clickById(d, wxElementConf.tuichu)
            index = 0
            while elementExistById(d, wxElementConf.wo):
                if index >= 50:  # 15秒超时
                    raise Exception("微信账号被挤下线，点击退出后模拟器超过15秒没反应")
                index += 1
                time.sleep(0.3)
            return True
    return False

# 随机聊天
def msgSendByViewChat(u2Con, frinedId):
    emojiList = ["[尴尬]", "[流泪]", "[白眼]", "[坏笑]", "[鄙视]", "[阴险]", "[奸笑]", "[嘿哈]"]
    u2Con(resourceId=wxElementConf.set_nickname).set_text(frinedId)  # RC_Set_Text
    time.sleep(0.5)
    if any(u2Con(resourceId=wxElementConf.RC_Friend_Find)) or u2Con(
            resourceId=wxElementConf.RC_Friend_Find).exists:  # RC_Friend_Find
        u2Con(resourceId=wxElementConf.RC_Friend_Find).click()  # RC_Friend_Find
        theline = linecache.getline(r'data\stc_weibo_train_response.txt', random.randrange(1, 4435959)).replace(' ', '')
        if random.randint(1, 5) > 3:
            randomEmoji = random.sample(emojiList, 1)[0]
        else:
            randomEmoji = ""
        time.sleep(0.2)
        if not u2Con(resourceId=wxElementConf.RC_Con_Set_Text):  # RC_Con_Set_Text
            u2Con(resourceId=wxElementConf.RC_Change_Voice).click_exists(timeout=10.0)  # RC_Change_Voice
            if any(u2Con(resourceId=wxElementConf.RC_Voice_Say)):  # RC_Voice_Say
                if u2Con(resourceId=wxElementConf.RC_Voice_Say).get_text() == "按住 说话":  # RC_Voice_Say
                    u2Con(resourceId=wxElementConf.RC_Change_Voice).click_exists(timeout=10.0)  # RC_Change_Voice
        u2Con(resourceId=wxElementConf.RC_Con_Set_Text).set_text(
            '%s %s' % (theline[:-1], randomEmoji * random.randint(1, 3)))  # RC_Con_Set_Text
        u2Con(resourceId=wxElementConf.RC_Con_Send).click_exists(timeout=10.0)  # RC_Con_Send
        u2Con.press("back")

# 发送消息判断，如果当前处于搜索好友名称页面，则继续搜索好友发送消息，如果不在该页面，则返回主页面
def backToSearch(u2Con, wxName):
    try:
        # 判断搜索页面是否在（朋友圈/文章/公众号/小程序/音乐/表情）界面，而不是在搜索文件界面，次flag采用"朋友圈"标志位
        if elementExistById(u2Con, wxElementConf.searchPageFlag, 0.5):
            return 0

        backToHome(u2Con)
        if(wxElementConf.wxVersion=='700'):
            clickByIdAndNum(u2Con,wxElementConf.index_search,0)
        else:
            clickByDesc(u2Con, u"搜索")  # 搜索
        time.sleep(0.2)
    except Exception as e:
        logger.exception(e)
    return 0

# 跳转到目标聊天页面
def jumpToCurrentWx(u2ConStart, wxName):
    if not (elementExistById(u2ConStart, wxElementConf.chat_nickname)):  # 昵称不存在
        backToSearch(u2ConStart, wxName)
    elif elementExistById(u2ConStart, wxElementConf.chat_nickname):  # 昵称存在
        currentWxName = getTextById(u2ConStart, wxElementConf.chat_nickname)
        groupExit = re.findall('(\(\d+\))$', currentWxName)
        if groupExit:
            currentWxNameReal = currentWxName[:currentWxName.find(re.findall('(\(\d+\))', currentWxName)[-1])]
        else:
            currentWxNameReal = currentWxName

        if wxName == currentWxNameReal:
            return ""
        if elementExistById(u2ConStart, wxElementConf.chat_back_btn):#pressBack()
            clickById(u2ConStart, wxElementConf.chat_back_btn)
            if elementExistById(u2ConStart, wxElementConf.searchText, 0.5):
                clearTextById(u2ConStart, wxElementConf.searchText)  # 清理搜索框的文本
        backToSearch(u2ConStart, wxName)

    setTextById(u2ConStart, wxElementConf.searchText, wxName)  # 设置搜索框的文本
    time.sleep(1)
    if elementExistByText(u2ConStart, wxElementConf.searchNickname, u"%s" % (wxName), 10):
        clickByText(u2ConStart, wxElementConf.searchNickname, u"%s" % (wxName))  # 找到指定用户
    elif elementExistByResIdTextClassInstence(u2ConStart, wxElementConf.searchNickname,  u"%s" % (wxName), wxElementConf.textViewClassName, 1):
        clickByTextClassAndNum((u2ConStart, wxElementConf.searchNickname,  u"%s" % (wxName), wxElementConf.textViewClassName, 1))
    else:
        return "群/好友(%s)不存在" % wxName

    return ""

#跳转到查找聊天记录界面
def openWxChatWindow(u2Con, wxName):
    wxNameFindFlag = False
    msg = jumpToCurrentWx(u2Con, wxName)  #跳当前聊天界面
    # 反馈到前台
    if msg != "":
        return wxNameFindFlag

    if elementExistById(u2Con, WxElementConf.friend_more, 1): #聊天界面的更多按钮 ...
        clickById(u2Con, WxElementConf.friend_more)
        num = 7
        while num >= 1:
            if elementExistByText(u2Con, WxElementConf.detail_title, u"查找聊天记录", 0.5):
                clickByText(u2Con, WxElementConf.detail_title, u"查找聊天记录") #打开聊天记录界面
                wxNameFindFlag = True
                break
            else:
                scrollDown(u2Con)
            num = num - 1

    return wxNameFindFlag

##以下为可共用的方法开始

# 通过描述判断元素是否存在
def elementExistByDesc(u2ConStart, desc, time=0):
    if time != 0:
        if any(u2ConStart(description=desc)) or u2ConStart(description=desc).exists(time):
            return True
        return False
    else:
        if any(u2ConStart(description=desc)) or u2ConStart(description=desc).exists():
            return True
        return False

# 通过判断资源编号和描述判断元素是否存在
def elementExistByResourceIdAndDesc(u2ConStart,resourceIdStr,desc):
    if u2ConStart(resourceId=resourceIdStr, description=desc).exists or any(
            u2ConStart(resourceId=resourceIdStr, description=desc)):
        return True
    return False


# 通过资源编号判断界面上是否存在该资源
def elementExistById(u2ConStart, resourceIdStr, time=0):
    if time != 0:
        if u2ConStart(resourceId=resourceIdStr).exists(time) or any(u2ConStart(resourceId=resourceIdStr)):
            return True
        else:
            return False
    elif u2ConStart(resourceId=resourceIdStr).exists() or any(u2ConStart(resourceId=resourceIdStr)):
        return True
    return False


# 通过资源编号和Text判断界面上是否存在该资源
def elementExistByText(u2ConStart, resourceIdStr, textStr, time=0):
    if time != 0:
        if u2ConStart(resourceId=resourceIdStr, text=textStr).exists(time) or any(
                u2ConStart(resourceId=resourceIdStr, text=textStr)):
            return True
        else:
            return False
    elif u2ConStart(resourceId=resourceIdStr, text=textStr).exists() or any(
            u2ConStart(resourceId=resourceIdStr, text=textStr)):
        return True
    return False


# 通过类名和变量序号判断界面上是否存在该资源
def elementExistByClassAndInstance(u2ConStart, className, instance):
    if u2ConStart(className=className, instance=instance).exists(5) or any(
            u2ConStart(className=className, instance=instance)):
        return True
    return False

# 通过资源编号和文本及类名判断是否存在该资源
def elementExistByResIdTextAndClass(u2ConStart, resourceIdStr,textStr, className):
    if u2ConStart(resourceId=resourceIdStr,text=textStr,className= className).exists:
        return True
    return False
# 通过资源编号、文本、类名和变量序号判断是否存在该资源
def elementExistByResIdTextClassInstence(u2ConStart, resourceIdStr,textStr,className,instance):
    if u2ConStart(resourceId=resourceIdStr,text=textStr,className=className,instance=instance).exists or any(
            u2ConStart(resourceId=resourceIdStr,text=textStr,className=className,instance=instance)):
        return True
    return False

# 通过资源编号、类名和变量序号判断是否存在该资源
def elementExistByResIdClassInstence(u2ConStart, resourceIdStr, className,instance):
    if u2ConStart(resourceId=resourceIdStr, className=className, instance=instance).exists or any(
            u2ConStart(resourceId=resourceIdStr, className=className, instance=instance)):
        return True
    return False

# 通过资源Text判断界面上是否存在该资源
def elementExistOnlyByText(u2ConStart, textStr, time=0):
    if time != 0:
        if u2ConStart(text=textStr).exists(time) or any(u2ConStart(text=textStr)):
            return True
        else:
            return False
    elif u2ConStart(text=textStr).exists() or any(u2ConStart(text=textStr)):
        return True
    return False


# 通过资源编号获取文本
def getTextById(u2ConStart, resourceIdStr):
    return u2ConStart(resourceId=resourceIdStr).get_text()

# 通过资源编号和顺序号获取文本
def getTextByInstance(u2ConStart,resourceIdStr,instance):
    return u2ConStart(resourceId=resourceIdStr,instance=instance).get_text()

# 通过资源编号、顺序号、类名获取文本
def getTextByInstanceClass(u2ConStart,resourceIdStr,ClassMame, instance):
    return u2ConStart(resourceId=resourceIdStr,className=ClassMame , instance=instance).get_text()

# 通过资源编号清理文本
def clearTextById(u2ConStart, resourceIdStr):
    u2ConStart(resourceId=resourceIdStr).clear_text()


# 通过资源编号+类名+变量序号清理文本
def clearTextByIdClassInstance(u2ConStart, resourceIdStr, className, instance):
    u2ConStart(resourceId=resourceIdStr, className=className, instance=instance).clear_text()


# 通过资源编号设置文本
def setTextById(u2ConStart, resourceIdStr, textStr):
    u2ConStart(resourceId=resourceIdStr).set_text(textStr)


# 通过资源编号+类名+变量序号设置文本
def setTextByIdClassInstance(u2ConStart, resourceIdStr, className, instance, textStr):
    u2ConStart(resourceId=resourceIdStr, className=className, instance=instance).set_text(textStr)


# 通过资源编号 点击
def clickById(u2ConStart, resourceIdStr):
    u2ConStart(resourceId=resourceIdStr).click_exists(timeout=10.0)

# 通过资源编号 点击
def clickByIdAndNum(u2ConStart, resourceIdStr, num):
    u2ConStart(resourceId=resourceIdStr, instance=num).click_exists(timeout=10.0)

# 通过资源编号 长按
def longclickById(u2ConStart, resourceIdStr):
    u2ConStart(resourceId=resourceIdStr).long_click()


# 通过资源编号+文本 点击
def clickByText(u2ConStart, resourceIdStr, textStr,time=10.0):
    if time==10.0:
        u2ConStart(resourceId=resourceIdStr, text=textStr).click_exists(timeout=10.0)
    else:
        u2ConStart(resourceId=resourceIdStr, text=textStr).click_exists(timeout=time)

def longclickByText(u2ConStart, resourceIdStr, textStr):
    u2ConStart(resourceId=resourceIdStr, text=textStr).long_click()


# 通过资源编号+类名+顺序号 点击
def clickByClassAndNum(u2ConStart, resourceIdStr, classStr, num):
    u2ConStart(resourceId=resourceIdStr, className=classStr, instance=num).click_exists(timeout=10.0)


# 通过资源编号+文本+类名+顺序号 点击
def clickByTextClassAndNum(u2ConStart, resourceIdStr, textStr, classStr, num):
    u2ConStart(resourceId=resourceIdStr, text=textStr, className=classStr, instance=num).click_exists(timeout=10.0)

# 通过资源编号+ 描述+ 类名 + 顺序号 点击
def clickByDescClassAndNum(u2ConStart, resourceIdStr, descStr, classStr, num):
    u2ConStart(resourceId=resourceIdStr, description=descStr, className=classStr, instance=num).click_exists(timeout=10.0)

# 通过描述点击
def clickByDesc(u2ConStart, desc):
    u2ConStart(description=desc).click_exists(timeout=10.0)

# 通过资源编号和描述点击
def clickByResouceIdAndDesc(u2ConStart,resourceIdStr, desc):
    u2ConStart(resourceId = resourceIdStr ,description=desc).click_exists(timeout=10.0)

# 通过文本点击
def clickOnlyByText(u2ConStart, text):
    u2ConStart(text=text).click_exists(timeout=10.0)


# 通过资源编号获取控件数量
def getCountById(u2ConStart, resourceIdStr):
    return u2ConStart(resourceId=resourceIdStr).count

# 通过资源文本获取控件数量
def getCountByText(u2ConStart, resourceIdStr, textStr):
    return u2ConStart(resourceId=resourceIdStr, text=textStr).count

# 通过资源编号+类名获取控件数量
def getCountByClass(u2ConStart, resourceIdStr, className):
    return u2ConStart(resourceId=resourceIdStr, className=className).count

# 通过资源编号 + 描述 获取控件数量
def getCountByDescription(u2ConStart, resourceIdStr,descStr):
    return u2ConStart(resourceId=resourceIdStr, description=descStr).count

# 通过资源编号 + 文本 获取控件数量
def getCountByText(u2ConStart, resourceIdStr,text):
    return u2ConStart(resourceId=resourceIdStr,text=text).count

# 根据资源编号+类名+索引长按
def longClickByIdClassIndex(c, resourceIdStr, className, index):
    c(resourceId=resourceIdStr, className=className)[index].long_click()


# 通过资源编号+文本拖动
def dragByIdAndText(u2ConStart, resourceIdStr, text, pos_x, pox_y, dur_time):
    u2ConStart(resourceId=resourceIdStr, text=text).drag_to(pos_x, pox_y, duration=dur_time,timeout=10.0)


# 通过类名+变量序号拖动
def dragByClassNameAndInstance(u2ConStart, className, instance, pos_x, pox_y, dur_time):
    u2ConStart(className=className, instance=instance).drag_to(pos_x, pox_y, duration=dur_time,timeout=10.0)


# 搜索
def seachByText(c, text):
    if (wxElementConf.wxVersion == '700'):
        clickByIdAndNum(c, wxElementConf.index_search, 0)
    else:
        clickByDesc(c, "搜索")
    clickById(c, wxElementConf.searchText)
    setTextById(c, wxElementConf.searchText, text)


# 聊天窗口 输入文字内容 并发送
def sendMsgContent(c, content):
    setTextById(c, wxElementConf.set_message_content, content)  # 设置发送内容
    clickByText(c, wxElementConf.send_message, "发送")


# 判断当前界面是否在微信app界面
def currentPackageInWx(u2ConStart):
    if u2ConStart.info.get('currentPackageName') == 'com.tencent.mm':
        return True
    return False

# 获取按键info
def getButtonInfo(u2Con, resourceIdStr, getKey):
    buttonInfoRet = u2Con(resourceId=resourceIdStr).info.get(getKey,"")
    return buttonInfoRet

def getButtonInfoByText(u2Con, resourceIdStr, textValue,  getKey):
    buttonInfoRet = False
    try:
        buttonInfoRet = u2Con(resourceId=resourceIdStr, text=textValue).info.get(getKey,"")
    except Exception as e:
        pass
    return buttonInfoRet

# 点击模拟器的返回按钮
def pressBack(u2ConStart):
    u2ConStart.press("back")


# 根据描述获取元素的中心点坐标
def getCenterByDesc(u2ConStart, description):
    return u2ConStart(description=description).center()


# 根据类名和变量序号获取元素的中心点坐标
def getCenterByClassAndInstance(u2ConStart, className, instance):
    return u2ConStart(className=className, instance=instance).center()


# 获取模拟器参数
def getDeviceInfo(u2ConStart, param1=None, param2=None):
    if not param2:
        return u2ConStart.device_info[param1]
    elif param1 and param2:
        return u2ConStart.device_info[param1][param2]
    else:
        return None


# 保存屏幕截图
def saveScreenShot(u2ConStart, filename):
    u2ConStart.screenshot(filename)

#拉动屏幕往下滚动3/4屏幕距离
def scrollDown(u2ConStart, sleep_time=1):
    fromX = u2ConStart.window_size()[0] / 2
    fromY = u2ConStart.window_size()[1] / 2
    toX = u2ConStart.window_size()[0] / 2
    toY = 0
    u2ConStart.swipe(fromX, fromY, toX, toY, 0.1)
    time.sleep(sleep_time)

#拉动屏幕往上滚动1/2屏幕距离
def scrollUp(u2ConStart, sleep_time=1):
    fromX = u2ConStart.window_size()[0] / 2
    fromY = u2ConStart.window_size()[1] / 2
    toX = u2ConStart.window_size()[0] / 2
    toY = u2ConStart.window_size()[1]
    u2ConStart.swipe(fromX, fromY, toX, toY, 0.1)
    time.sleep(sleep_time)

#拉动屏幕往上滚动屏幕
def scrollUpExistScrollable(u2ConStart, sleep_time=1):
    if u2ConStart(scrollable=True).exists() or any(u2ConStart(scrollable=True)):
        scrollableElInfo = u2ConStart(scrollable=True).info
        fromX = u2ConStart.window_size()[0] / 2
        fromY = scrollableElInfo["bounds"]["bottom"] - 50
        toX = u2ConStart.window_size()[0] / 2
        toY = scrollableElInfo["bounds"]["top"] + 50
        u2ConStart.swipe(fromX, fromY, toX, toY, 0.1)
        time.sleep(sleep_time)
##以上为可共用的方法结束

def appStart(u2ConStart, logger):
    # 执行点击启动操作
    u2ConStart.press("home")
    time.sleep(0.5)
    # 点掉模拟器挂死提示
    machineBrowSkip(u2ConStart, logger)
    if elementExistOnlyByText(u2ConStart, u"CopyFile", 1):
        clickOnlyByText(u2ConStart, u"CopyFile")
        time.sleep(0.5)
        u2ConStart.press("home")
        time.sleep(0.5)
        machineBrowSkip(u2ConStart, logger)
        if elementExistOnlyByText(u2ConStart, u"微信", 1):
            clickOnlyByText(u2ConStart, u"微信")
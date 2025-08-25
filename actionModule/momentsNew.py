import time
import traceback

from lib.WxElementConf import WxElementConf
from . import handlePic
from tools import wxUtil
import os
# 初始化config
from lib.ModuleConfig import ConfAnalysis
from lib.FinalLogger import *
import uiautomator2 as u2

BASEDIR = os.getcwd()
# 初始化logger
logger = getLogger('./log/momentsNew.log')
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)

# 朋友圈图片路径
momentsImgPath = confAllItems.getOneOptions('moments_image_path', 'momentsImgPath')
wxElementConf=WxElementConf(logger)
#供任务执行程序调用：从数据库获取任务信息执行-发朋友圈文字图片
def sendMomentsDB(logger,c,taskItemInfo,mySqlUtil):
    remarks = '#'
    try:
        # c(text=u"微信").click()
        # while True:
        #     if not c(resourceId="com.tencent.mm:id/c9f"):
        #         c.press("back")
        #     else:
        #         break

        sql="SELECT  C.picRoot, C.picNames, C.momentContents,C.picTaskSeq from wx_moments_picType C where C.taskSeq= \'%s\'" %taskItemInfo[0]
        detailInfo=mySqlUtil.getData(sql)
        picRoot=momentsImgPath
        momentContents=detailInfo[0][2]
        picTaskSeq=detailInfo[0][3]
        picNames=getPicNames(picTaskSeq,mySqlUtil)
        status=sendMoments(c, picRoot, picNames, momentContents)
        return (status, remarks)
    except (Exception) as e:
        remarks = e
        status = 3
        logger.warn(traceback.format_exc())
        return (status, remarks)

def getPicNames(picTaskSeq,mySqlUtil):
    picNames = ""
    try:
        sql = "select picture, picture_name from wx_moments_pic where picTaskSeq='%s' order by seq desc" % picTaskSeq  # picTaskSeq 从任务子表来
        imgInfo = mySqlUtil.getData(sql)

        for imgitem in imgInfo:
            img = imgitem[0]
            imgname = imgitem[1]
            if(picNames==""):
                picNames=imgname
            else:
                picNames = picNames+"|"+imgname
            fwrite = open(momentsImgPath + imgname, 'wb')  # imgsavepath 本地定义的路径
            fwrite.write(img)
            fwrite.close()
            handlePic.readAndSavePic(momentsImgPath + imgname) #读写一遍图片，去掉拍摄时间，微信相册已拍摄时间排序的
    except (Exception) as e:
        logger.warn(traceback.format_exc())
    return picNames
#供任务执行程序调用：从数据库获取任务信息执行-发朋友圈链接
def forwardMomentsDB(logger,c,taskItemInfo,mySqlUtil):
    remarks = '#'
    try:
        sql = "SELECT C.linkUrl,C.momentContents from wx_moments_linkType C where C.taskSeq= \'%s\'" % taskItemInfo[0]
        detailInfo = mySqlUtil.getData(sql)
        linkUrl=detailInfo[0][0]
        momentContents=detailInfo[0][1]
        status =forwardMomentsSC(c,linkUrl, momentContents)
        return (status,remarks)
    except (Exception) as e:
        remarks = e
        logger.warn(traceback.format_exc())
        status = 3
        return (status, remarks)


#发送朋友圈方法picRoot：图片文件存放路径,picNames：图片文件名以|相隔， picNum:定义发送最新几张照片的数量; content:发朋友圈的文字描述
def sendMoments(c,picRoot,picNames,momentsContent):
    result=3
    try:
        picNameArr=[]
        picNum=0
        if not picNames is  None and picNames!='':
            picNameArr = picNames.split("|")
            picNum = len(picNameArr)
            for picName in picNameArr:
                pushFileAndBroadcast(c, picRoot, picName, '/storage/sdcard0/Pictures/')#上传图片至模拟器并广播

        openMoments(c)#点开 发现-朋友圈
        i=0
        while(i<10):  # 判断朋友圈页面的 相机 按钮是否存在，不存在则循环10次继续等待，直到出现为止
            if isMomentsCtrlExist:
                break
            else:
                time.sleep(0.5)
                i=i+1
        if isMomentsCtrlExist:
            if(picNum>0):#带图片朋友圈
                selectFromAlbum(c)
                time.sleep(2)
                judgeAndClearFirstWarn(c) # 判断是否首次安装微信后发朋友圈，首次安装发朋友圈会有 '拍照，记录生活'文字提醒,去掉文字提醒：
                selectPics(c, picNum)#选择图片

            else:#纯文字朋友圈
                time.sleep(2)
                longClickMoments(c) #长按发朋友圈按钮
                time.sleep(2)
                judgeAndClearContentWarn(c)#消除首次发文字提醒
            submitMoments(c, momentsContent)# 填写文字并发布朋友圈
            wxUtil.backToHome(c)  # 返回聊天主界面
            result = 4
    except (Exception) as e:
        result = 3
        print(e)
    return result


#通过收藏夹实现：发送链接到收藏，转发朋友圈
def forwardMomentsSC(c,url,momentContents):
    result = 3
    try:
        searchAndClickFileHelper(c) #查找并打开 文件传输助手
        openFileHelperDialog(c) #打开文件传输助手对话框
        wxUtil.sendMsgContent(c, url) #设置发送内容并发送
        view_len =getMsgCount(c)#获取当前窗口聊天记录数
        print("文件传输助手消息总数：" + str(view_len))
        longClickMsgByIndex(c, view_len - 1) #根据索引长按某一条消息
        favMsgByIndex(c, view_len - 1) #根据索引收藏某条消息
        wxUtil.backToHome(c)  # 返回聊天主界面
        openFav(c)#打开收藏夹
        openFirstFav(c)#打开收藏夹中第一个收藏内容中的链接
        time.sleep(1)
        shareLink(c)#点击链接页面右上角，并在弹出层中选择分享到朋友圈
        submitMoments(c, momentContents)  # 填写文字并发布朋友圈
        delFav(c) ##关闭浏览并删除收藏夹内容
        wxUtil.backToHome(c) #返回聊天主界面
        result = 4
    except (Exception) as e:
        result = 3
        print(e)
    return result
#forwardMomentsSC("https://mp.weixin.qq.com/s/qM5D3OQ22lnYP-2LS2cWig","好消息好消息")
#forwardMomentsSC("http://www.qq.com","好消息好消息")

#一、发送图片或文字朋友圈
#传送图片等文件到模拟器目录，并进行广播，以便在浏览图片等界面显示传送的图片或文件
#参数说明：c：u2连接 ,sourceFileRoot:上传文件所在目录,fileName：上传文件名,destRoot：模拟器上传目标目录
def pushFileAndBroadcast(c,sourceFileRoot,fileName,destRoot):
    c.push(sourceFileRoot + fileName, destRoot)
    c.adb_shell('touch '+destRoot + fileName + '')
    c.adb_shell('am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://'+destRoot + fileName + '')

#点开 发现-朋友圈
def openMoments(c):
    wxUtil.clickByText(c, wxElementConf.wo, "发现")
    wxUtil.clickByText(c, wxElementConf.wo_shezhi, "朋友圈")

#判断朋友圈页面的 发朋友圈相机 按钮是否存在
def isMomentsCtrlExist(c):
    wxUtil.elementExistById(c, wxElementConf.tianjiashoucang)

#点击发圈按钮-从相册选择
def selectFromAlbum(c):
    wxUtil.clickById(c, wxElementConf.tianjiashoucang) # 右上角  发圈按钮
    wxUtil.clickByText(c, wxElementConf.zhiding, "从相册选择")

#判断是否首次安装微信后发带图片朋友圈，首次安装发朋友圈会有 '拍照，记录生活'文字提醒,去掉文字提醒：
def judgeAndClearFirstWarn(c):
    if wxUtil.elementExistById(c, wxElementConf.tixing):
        if wxUtil.getTextById(c, wxElementConf.tixing) == '拍照，记录生活':
            wxUtil.clickByText(c, wxElementConf.queding, "我知道了")

#选择图片
def selectPics(c,picNum):
    wxUtil.clickById(c, wxElementConf.picAndVideo)   # 点击图片和视频
    wxUtil.clickByText(c, wxElementConf.picturesFolder, "Pictures")   # 点击Pictures
    instanceCount = 0  # 控制发送前几张照片
    while (instanceCount < picNum):
        wxUtil.clickByClassAndNum(c, wxElementConf.wenzitixing, "android.widget.CheckBox", instanceCount)
        instanceCount = instanceCount + 1
    wxUtil.clickById(c, wxElementConf.fabiao)
    wxUtil.clickById(c, wxElementConf.shoucangneirong)

#长按发朋友圈按钮
def longClickMoments(c):
    c(resourceId=wxElementConf.tianjiashoucang).long_click()

#判断是否首次安装微信后发带文字朋友圈 ，首次安装发文字朋友圈会有 文字提醒,去掉文字提醒：
def judgeAndClearContentWarn(c):
    if wxUtil.elementExistById(c, wxElementConf.wztx):
        if wxUtil.getTextById(c, wxElementConf.wztx) == '我知道了':
            time.sleep(2)
            wxUtil.clickById(c, wxElementConf.wztx)

# 填写文字并发布朋友圈
def submitMoments(c,momentsContent):
    c(resourceId=wxElementConf.shoucangneirong).set_text(momentsContent)
    wxUtil.clickByText(c, wxElementConf.fabiao, "发表")

#二、转发链接至朋友圈
#查找并打开 文件传输助手
def searchAndClickFileHelper(c):
    wxUtil.seachByText(c,"文件传输助手")
    time.sleep(1)
    wxUtil.clickByText(c, wxElementConf.fileHelper, "文件传输助手")

#打开文件传输助手对话框
def openFileHelperDialog(c):
   # if wxUtil.elementExistById(c, wxElementConf.addToFriendList):
   #      if wxUtil.getTextById(c, wxElementConf.addToFriendList) == '添加到通讯录':
   #          wxUtil.clickById(c, wxElementConf.addToFriendList)
   #          time.sleep(1)
   if wxUtil.elementExistById(c, wxElementConf.sendMsg,0.5):
        wxUtil.clickById(c, wxElementConf.sendMsg)  # 打开聊天窗口

#获取当前窗口聊天记录数
def getMsgCount(c):
    return wxUtil.getCountByClass(c, wxElementConf.msgList,"android.view.View")

#根据索引长按某一条消息
def longClickMsgByIndex(c,index):
    wxUtil.longClickByIdClassIndex(c, wxElementConf.msgList, "android.view.View", index)

#根据索引收藏某条消息
def favMsgByIndex(c,index):
    i = 0
    while (i < 10):
        if any(c(text=u"收藏")) or c(text=u"收藏").exists:
            c(text=u"收藏").click_exists(timeout=10.0)  # 收藏
            break
        else:
            wxUtil.longClickMsgByIndex(c, index)  # 根据索引长按某一条消息
            time.sleep(0.5)
            i = i + 1

#打开收藏夹
def openFav(c):
    j = 0
    while (j < 10):
        if any(c(resourceId=wxElementConf.wo, text=u"我")) or c(resourceId=wxElementConf.wo, text=u"我").exists:
            wxUtil.clickByText(c, wxElementConf.wo, "我")
            break
        else:
            time.sleep(0.5)
            j = j + 1
    wxUtil.clickByText(c, wxElementConf.wo_shezhi, "收藏")

#打开收藏夹中第一个收藏内容中的链接：
def openFirstFav(c):
    wxUtil.clickById(c, wxElementConf.firstFav)# 点开第一个收藏的内容
    wxUtil.clickById(c, wxElementConf.favLink) # 点开链接

#点击链接页面右上角，并在弹出层中选择分享到朋友圈
def shareLink(c):
    k = 0
    while (k < 10):
        if wxUtil.elementExistById(c, wxElementConf.tianjiashoucang):
            wxUtil.clickById(c, wxElementConf.tianjiashoucang)
            break
        else:
            time.sleep(0.5)
            k = k + 1
    wxUtil.clickByText(c, wxElementConf.zhiding, "分享到朋友圈")

#关闭浏览并删除收藏夹内容
def delFav(c):
    wxUtil.clickById(c, wxElementConf.closeLink)  # 关闭浏览
    time.sleep(1)
    wxUtil.clickById(c, wxElementConf.tianjiashoucang)# 右上角弹出当前收藏内容的管理菜单
    wxUtil.clickByText(c, wxElementConf.zhiding, "删除")
    wxUtil.clickByText(c, wxElementConf.queding, "确定")
#朋友圈相关功能结束
if __name__ == '__main__':
    # getPicNames('1531477771959')
    u2Con = u2.connect('127.0.0.1:21513')
    u2Con(text=u"微信").click()
    #forwardMomentsSC(u2Con,"https://mp.weixin.qq.com/s/qM5D3OQ22lnYP-2LS2cWig", "好消息好消息")
    #sendMoments(u2Con, "D:\pictures\\", "3.jpg|8.jpg", "小光棍")

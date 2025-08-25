from tools import MysqlDbPool
import uiautomator2 as u2
from tools.machinInfo import *
import subprocess

def apkInstall(devId,mysql,apkName,wxName,ifWxInstall):
    devInfoSql1 = """SELECT
                        B.devName,
                        B.devPort,
                     B.devDir   
                    FROM
                        wx_account_info A
                    join wx_machine_info B
                    on A.uuid = B.uuid
                    WHERE
                        A.wx_status = 1
                    AND B.clientId = '%s'""" %(devId)
    devInfo1 = mysql.getData(devInfoSql1)

    devInfoSql2 = """SELECT devName,devPort,devDir from wx_machine_info
                    where clientId = "%s"
                    and uuid = ""
                    and `status` = 0
                    and if_ready = 1""" % (devId)
    devInfo2 = mysql.getData(devInfoSql2)

    devInfo = []
    devInfo.extend(list(devInfo1))
    devInfo.extend(list(devInfo2))

    devInfoList = []
    # 指定
    # defiList = ['7015','7008','7009','17171151964','17063200996','7201-21503']
    defiList = []

    # 过滤
    filterList = ['712', '6522', '6528', '6537', '6538', '6539', '6541','6542','17171151974']
    if defiList:
        for i in devInfo:
            if i[0] in defiList:
                devInfoList.append(i)

    elif filterList:
        for i in devInfo:
            if i[0] not  in filterList:
                devInfoList.append(i)
    else:
        devInfoList = devInfo

    if devInfoList:
        print(devInfoList)
        print("当前有效主机信息：%s" % ([i[0] for i in devInfoList]))

        for devItemInfo in devInfoList:
            apkInstallAction(devItemInfo,apkName,wxName,ifWxInstall)
    else:
        print("无有效模拟器信息，请确认wx_account_info.wx_status=1,为有效信息")

def updateConfigFile(devItemInfo):
    devName = devItemInfo[0]
    devPort = devItemInfo[1]


def apkInitAciton(devId, mysql):
    devInfoSql1 = """SELECT
                            B.devName,
                            B.devPort,
                         B.devDir   
                        FROM
                            wx_account_info A
                        join wx_machine_info B
                        on A.uuid = B.uuid
                        WHERE
                            A.wx_status = 1
                        AND client_id = '%s'""" % (devId)
    devInfo1 = mysql.getData(devInfoSql1)

    devInfoSql2 = """SELECT devName,devPort,devDir from wx_machine_info
                        where clientId = "%s"
                        and uuid = ""
                        and `status` = 0
                        and if_ready = 1""" % (devId)
    devInfo2 = mysql.getData(devInfoSql2)

    devInfo = []
    devInfo.extend(list(devInfo1))
    devInfo.extend(list(devInfo2))

    devInfoList = []
    # 指定
    defiList = []
    # 过滤
    filterList = []
    if defiList:
        for i in devInfo:
            if i[0] in defiList:
                devInfoList.append(i)
    elif filterList:
        for i in devInfo:
            if i[0] not in filterList:
                devInfoList.append(i)
    else:
        devInfoList = devInfo
    print(devInfoList)
    for i in devInfoList:
        devName = i[0]
        devPort = i[1]
        devDir = i[2]

        try:
            startTime = time.time()
            startDeadLine = startTime + TIMEOUT
            outTimeLoop = 1
            reconnectLoop = 0
            machineStartStatus = False
            reConnectFlag = False
            devRestartFlag = False

            while True:
                try:
                    adbDevAction = subprocess.check_output('adb devices').decode(encoding="utf-8")
                except Exception as e:
                    print(traceback.format_exc())
                    break
                if time.time() >= startDeadLine:
                    break
                hwnd = win32gui.FindWindow(None, devName)
                # adb断连已连上
                if '%s\tdevice' % (devPort) in adbDevAction:
                    # 进行adb初始化
                    statusDevCheckCommand = """adb -s 127.0.0.1:%s shell dumpsys activity activities""" % (devPort)
                    try:
                        statusDevCheck = [i for i in
                                          subprocess.check_output(statusDevCheckCommand).decode(encoding="utf-8").split(
                                              '\r\r\n')
                                          if "idle=true" in i and "visible=true" in i]
                    except Exception as e:
                        statusDevCheck = []

                    if len(statusDevCheck) > 0:
                        print("%s 初始化正常" % devName)
                        machineStartStatus = True
                        break
                    else:
                        time.sleep(3)
                elif hwnd != 0 and not devRestartFlag:  # adb断连，需要重连
                    print("%s 设备开启，adb 重连" % devName)
                    adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                    subprocess.check_call(adbReconnectCommand)
                    time.sleep(2)
                elif hwnd == 0:  # 模拟器未启动
                    print("%s 设备未开启，即将启动" % devName)
                    subprocess.check_call("MEmuConsole.exe %s" % devDir)
                    devRestartFlag = True
                    time.sleep(5)
                elif '%s\toffline' % (
                devPort) in adbDevAction and not reConnectFlag and not devRestartFlag:  # adb offline
                    print("%s 设备 offline，adb 重连" % devName)
                    adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                    subprocess.check_call(adbReconnectCommand)
                    reconnectLoop += 1
                    if reconnectLoop > 3:
                        print("%s 设备adb重连失败" % devName)
                        reConnectFlag = True
                    time.sleep(1)
                elif reConnectFlag:  # 重连失败，重启模拟器
                    print("%s 设备重启" % devName)
                    hwnd = win32gui.FindWindow(None, devName)
                    if hwnd != 0:
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    subprocess.check_call("MEmuConsole.exe %s" % devDir)
                    devRestartFlag = True
                    reConnectFlag = False
                    time.sleep(5)
                elif (time.time() - startTime) / (120 * outTimeLoop) > 1:  # 50秒内无响应，重连adb
                    print("%s 模拟器重启后50s内连不上adb，尝试重连" % devName)
                    adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                    subprocess.check_call(adbReconnectCommand)
                    outTimeLoop += 1
                    time.sleep(1)
                else:
                    print("%s 设备启动中" % devName)
                    time.sleep(5)
        except Exception as e:
            machineStartStatus = False
            logger.warn(traceback.format_exc())

        if machineStartStatus:
            u2Con = u2.connect("127.0.0.1:%s" % (devPort))

            u2Con.press("home")
            u2Con(text=u"微信").click()
            time.sleep(1)
            u2Con.press("home")
            u2Con(text=u"CopyFile").click()
            time.sleep(1)
            u2Con.press("home")
            u2Con(text=u"Xposed Installer").click()
            time.sleep(0.5)
            u2Con(description=u"打开导航抽屉").click()
            time.sleep(0.5)
            u2Con(resourceId="de.robv.android.xposed.installer:id/disableSwitch").click()


def apkInstallAction(itemInfo,apkName,wxName,ifWxInstall):
    devName = itemInfo[0]
    devPort = itemInfo[1]
    devDir = itemInfo[2]
    if '_' in devDir:
        devIndex = devDir.split('_')[1]
    else:
        devIndex = 0

    if ifWxInstall:
        # print("%s 卸载微信" % (devName))
        # uninstallComm = "memuc  uninstallapp -i %s com.tencent.mm" % (devIndex)
        # subprocess.check_output(uninstallComm)
        # time.sleep(1)
        # 安装apk
        print("%s 安装微信" % (devName))
        installComm = 'adb -s  127.0.0.1:%s install -r data/%s' % (devPort, wxName)
        subprocess.check_output(installComm)

    try:
        startTime = time.time()
        startDeadLine = startTime + TIMEOUT
        outTimeLoop = 1
        reconnectLoop = 0
        machineStartStatus = False
        reConnectFlag = False
        devRestartFlag = False

        while True:
            try:
                adbDevAction = subprocess.check_output('adb devices').decode(encoding="utf-8")
            except Exception as e:
                print(traceback.format_exc())
                break
            if time.time() >= startDeadLine:
                break
            hwnd = win32gui.FindWindow(None, devName)
            # adb断连已连上
            if '%s\tdevice' % (devPort) in adbDevAction:
                # 进行adb初始化
                statusDevCheckCommand = """adb -s 127.0.0.1:%s shell dumpsys activity activities"""%(devPort)
                try:
                    statusDevCheck = [i for i in
                                      subprocess.check_output(statusDevCheckCommand).decode(encoding="utf-8").split(
                                          '\r\r\n')
                                      if "idle=true" in i and "visible=true" in i]
                except Exception as e:
                    statusDevCheck = []

                if len(statusDevCheck) > 0:
                    print("%s 初始化正常" % devName)
                    machineStartStatus = True
                    break
                else:
                    time.sleep(3)
            elif hwnd != 0 and not devRestartFlag:#adb断连，需要重连
                print("%s 设备开启，adb 重连" % devName)
                adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                subprocess.check_call(adbReconnectCommand)
                time.sleep(2)
            elif hwnd == 0:#模拟器未启动
                print("%s 设备未开启，即将启动" % devName)
                subprocess.check_call("MEmuConsole.exe %s" % devDir)
                devRestartFlag = True
                time.sleep(5)
            elif '%s\toffline' % (devPort) in adbDevAction and not reConnectFlag and not devRestartFlag:#adb offline
                print("%s 设备 offline，adb 重连" % devName)
                adbReconnectCommand = "adb connect 127.0.0.1:%s" %(devPort)
                subprocess.check_call(adbReconnectCommand)
                reconnectLoop += 1
                if reconnectLoop > 3:
                    print("%s 设备adb重连失败" % devName)
                    reConnectFlag = True
                time.sleep(1)
            elif reConnectFlag: #重连失败，重启模拟器
                print("%s 设备重启" % devName)
                hwnd = win32gui.FindWindow(None, devName)
                if hwnd != 0:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                subprocess.check_call("MEmuConsole.exe %s" % devDir)
                devRestartFlag = True
                reConnectFlag = False
                time.sleep(5)
            elif (time.time() - startTime) / (120 * outTimeLoop) > 1:#50秒内无响应，重连adb
                print("%s 模拟器重启后50s内连不上adb，尝试重连"% devName)
                adbReconnectCommand = "adb connect 127.0.0.1:%s" % (devPort)
                subprocess.check_call(adbReconnectCommand)
                outTimeLoop += 1
                time.sleep(1)
            else:
                print("%s 设备启动中" % devName)
                time.sleep(5)
    except Exception as e:
        machineStartStatus = False
        logger.warn(traceback.format_exc())

    if machineStartStatus:

        u2Con = u2.connect("127.0.0.1:%s" % (devPort))

        # 修改配置文件
        print("%s (%s)修改配置文件开始" %(devName, devPort))
        confInfo = u2Con.shell('cat /sdcard/copyfile/huiliao.conf').output
        print("更改前信息：%s" % (confInfo))
        if "No such file or directory" not in confInfo:
            confList = confInfo.split(";")
            if len(confList) == 15:
                index = 0
                confTmp = []
                for i in confList:
                    if index in [4, 5, 6]:
                        index += 1
                        continue
                    elif index in [1]:
                        i = "async_task"
                    confTmp.append(i)
                    index += 1

                confNew = ";".join(confTmp)
                print(confNew)
                u2Con.shell('echo "%s" > /sdcard/copyfile/huiliao.conf' % (confNew))
                confCurr = u2Con.shell('cat /sdcard/copyfile/huiliao.conf').output
                confCurrLen = len(confCurr.split(";"))
                if confCurrLen == 12:
                    print("配置参数字段数：%s"%(confCurrLen))
                else:
                    print("配置参数错误，需人工干预")
                print("更改后信息：%s" % (confCurr))
            elif len(confList) == 12:
                index = 0
                confTmp = []
                for i in confList:
                    if index in [1]:
                        i = "async_task"
                    confTmp.append(i)
                    index += 1

                confNew = ";".join(confTmp)
                print(confNew)
                u2Con.shell('echo "%s" > /sdcard/copyfile/huiliao.conf' % (confNew))
                confCurr = u2Con.shell('cat /sdcard/copyfile/huiliao.conf').output
                confCurrLen = len(confCurr.split(";"))
                if confCurrLen == 12:
                    print("配置参数字段数：%s"%(confCurrLen))
                else:
                    print("配置参数错误，需人工干预")
            else:
                print("配置文件槽位异常 :%s " % (confList))
        else:
            print("无相关配置文件")
        print("%s (%s)修改配置文件完成" % (devName, devPort))
        # 卸载
        print("%s 卸载apk" %(devName))
        uninstallComm = "memuc  uninstallapp -i %s com.gz.pbs.copyfile" %(devIndex)
        subprocess.check_output(uninstallComm)
        time.sleep(1)
        # 安装apk
        print("%s 安装apk开始" % (devName))
        installComm = 'adb -s  127.0.0.1:%s install -r data/%s' % (devPort, apkName)
        subprocess.check_output(installComm)

        # 安装xposed



        u2Con.press("home")
        time.sleep(0.5)

        if not u2Con(text=u"Xposed Installer").exists(3):
            print("%s 安装Xposed" % (devName))
            installComm = 'adb -s  127.0.0.1:%s install -r data/XposedInstaller_3.1.5.apk' % (devPort)
            subprocess.check_output(installComm)
            time.sleep(2)
            u2Con(text=u"Xposed Installer").click()
            time.sleep(1)
            u2Con(resourceId="de.robv.android.xposed.installer:id/md_promptCheckbox").click(2)
            u2Con(resourceId="de.robv.android.xposed.installer:id/md_buttonDefaultPositive").click(2)
            time.sleep(0.5)
            u2Con(resourceId="android:id/title", text=u"Version 89").click(2)
            time.sleep(5)
            u2Con(resourceId="de.robv.android.xposed.installer:id/md_title", text=u"Install").click(2)

            while True:
                if u2Con(resourceId="de.robv.android.xposed.installer:id/cancel").exists(3):
                    u2Con(resourceId="de.robv.android.xposed.installer:id/cancel").click(2)
                    break

        u2Con.press("home")
        u2Con(text=u"Xposed Installer").click()
        time.sleep(1)

        while True:
            if u2Con(description=u"打开导航抽屉").exists:
                break
        # if not u2Con(text=u"Xposed Installer").exists():
        #     u2Con(description=u"打开导航抽屉").click(3)
        #     time.sleep(0.5)
        #     u2Con(resourceId="de.robv.android.xposed.installer:id/design_menu_item_text").click(3)
        try:
            if "未安装" in u2Con(resourceId="de.robv.android.xposed.installer:id/framework_install_errors").get_text():
                u2Con(resourceId="android:id/title", text=u"Version 89").click(3)
                time.sleep(1)
                u2Con(resourceId="de.robv.android.xposed.installer:id/md_title", text=u"Install").click(3)

                while True:
                    if u2Con(resourceId="de.robv.android.xposed.installer:id/cancel").exists():
                        u2Con(resourceId="de.robv.android.xposed.installer:id/cancel").click(3)
                        break
                    time.sleep(1)
        except :
            pass

        wxUtil.clickByDesc(u2Con, u"打开导航抽屉")
        time.sleep(0.5)
        wxUtil.clickByText(u2Con, "de.robv.android.xposed.installer:id/design_menu_item_text", u"模块")
        time.sleep(3)
        moduleCount = u2Con(resourceId="de.robv.android.xposed.installer:id/title").count
        copyFileIndex = 0
        runFlag = False
        while True:
            for index in range(0, moduleCount):
                moduleName = u2Con(resourceId="de.robv.android.xposed.installer:id/title",instance=index).get_text()
                if moduleName == "CopyFile":
                    copyFileIndex = index
                    runFlag = True
                    break
                else:
                    time.sleep(0.5)
            if runFlag:
                break

        time.sleep(1)
        u2Con(resourceId="de.robv.android.xposed.installer:id/checkbox", className="android.widget.CheckBox", instance=copyFileIndex).click()
        time.sleep(1)
        rebootComm = "memuc reboot -i %s" %(devIndex)
        subprocess.check_call(rebootComm)

        print("%s apk 安装完成" %(devName))


    else:
        print("%s 初始化失败 " %(devName))



    # for devItem in devInfo:
    #     devName = devItem[0]
    #     devPort = devItem[1]
    #     print(
    #         '%s 安装apk： adb -s 127.0.0.1:%s install data/%s' % (str(devName) , devPort, apkName))
    #     subprocess.check_output('adb -s  127.0.0.1:%s install data/%s' % (devPort, apkName))



if __name__ == '__main__':
    mysql = MysqlDbPool.MysqlDbPool()
    devId = '124.172.188.65'


    # # 初始化安装模拟器环境
    # maxNum = 1 # 最大个数
    # vmsInit(devId, maxNum, mysql, '173', 'Wechat_V7.0.0.apk', 'CopyFile-v1.6.7.apk', 'XposedInstaller_3.1.5.apk')

    # 安装apk
    # apkName = 'CopyFile-v2.0.7.apk'
    # wxName = "Wechat_V7.0.0.apk"
    # apkInstall(devId, mysql, apkName,wxName,False)

    # 点击启动
    apkInitAciton(devId, mysql)


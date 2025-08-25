from actionModule.updateFriendList import updateFriend
from tools import redisUtil
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
import traceback, multiprocessing, signal
from actionModule import  msgResultProcess
logger = getLogger('./log/AsyncTask.log')
BASEDIR = os.getcwd()

# # 初始化config
configFile = '%s/conf/moduleConfig.conf' % BASEDIR
confAllItems = ConfAnalysis(logger, configFile)

# 频道名称
channl_name = confAllItems.getOneOptions('redis', 'channl_name')

RunFlag = 1
processesNum=20
def programExit(signalFlag, local_pid):
    global RunFlag
    if RunFlag != None :
        RunFlag=0
    logger.info("接收到退出信号，进程(%s)准备退出！" % os.getpid())

#信号触发函数。SIGTERM = 2 ；SIGINT = 15
signal.signal(signal.SIGTERM, programExit)  # program terminate
signal.signal(signal.SIGINT, programExit)  # control+c

def run():
    try:
        global logger
        pool = multiprocessing.Pool(processes=processesNum)
        logger.info("启动%d个处理进程"%processesNum)
        manager = multiprocessing.Manager()
        taskQueue = manager.Queue()
        pool.apply_async(updateFriend, args=(taskQueue,))
        ps = redisUtil.subscriber(channl=channl_name, only_one=True)  #从async_task订阅消息
        last_day = time.strftime("%Y-%m-%d", time.localtime())
        if ps is None:
            logger.info("启动失败")
            return
        logger.info("订阅成功，现在开始收消息")
        for item in ps.listen():        #监听状态：有消息发布了就拿过来
            today = time.strftime("%Y-%m-%d", time.localtime())
            if today != last_day:
                last_day = today
                logger = getLogger('./log/AsyncTask.log')
                logger.debug("today:" + str(last_day))
            #logger.debug("收到一条消息")
            #logger.debug(item)
            if item['type'] == 'message' and 'async_task' in item['channel'].decode('utf-8'):
                msg_body=item['data'].decode('utf-8')
                if msg_body.startswith("FR:~:"):  # 好友信息同步处理
                    logger.info("收到一条消息: %s", msg_body)
                    taskQueue.put(msg_body)
                else:
                    pool.apply_async(taskDispatch, args=(msg_body,))
            if RunFlag == 0 :  #程序退出
                break

        logger.info("异步任务主进程正常退出")
        pool.close()
        pool.join()
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error("异步任务进程异常退出")

def taskDispatch(msg_body):
    try:
        logger.info("收到一条消息: %s", msg_body)

        if msg_body.startswith("MS:~:"): #消息发送结果处理
            msg_body = msg_body.replace("MS:~:","")
            msgResultProcess.msgSendaction(logger, msg_body, None)
        elif msg_body.startswith("MR:~:"): #消息获取处理
            msg_body = msg_body.replace("MR:~:", "")
            msgResultProcess.msgFetchProcess(logger, msg_body, None)
        elif msg_body.startswith("UW:~:"): #微信ID更新处理
            msg_body = msg_body.replace("UW:~:", "")
            msgResultProcess.wxIdUpateProcess(logger, msg_body, None)
        elif msg_body.startswith("UP:~:"):  # 微信ID更新处理
            msg_body = msg_body.replace("UP:~:", "")
            msgResultProcess.hdPicUploadProcess(logger, msg_body, None)
        else:
            logger.info("消息格式有误")
    except Exception as e:
        logger.error(traceback.format_exc())

if __name__ == '__main__':
    run()
#!/usr/bin/python
# -*- coding: UTF-8 -*-
'''
  log out level
    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10
    NOTSET = 0
'''
import configparser,logging,logging.handlers,os
from concurrent_log_handler import ConcurrentRotatingFileHandler
from numpy.core.defchararray import isdigit

#按文件大小分割时，可以支持多进程   按时间分割时不支持
#fileName:日志文件路径和名称，路径不存在时，会主动创建
#maxByte：日志文件大小,整数，单位Byte,超过大小后切分文件
#timeType：按时间类型切分时的单位，默认天， s秒  m分钟 h小时 d天 midnight午夜   w{0-6} 星期   大小写都支持
#backupCount：保留的文件数量，整数，默认10个，超过十个会删除历史文件
#console：布尔类型，True or False  是否显示在console中
#fileLogLevel:整数，日志文件保存的日志级别 0，10，20，30，40，50
#conLogLevel：整数，命令行显示的日志级别  0，10，20，30，40，50
#type：'size'表示按文件大小切分，'time'表示按时间类型切分
def getLogger(fileName,maxByte=700*1024*1024,timeType='d',backupCount=10,console=True,fileLogLevel=-1,conLogLevel=-1,type='time'):
    FILE_LOGGING_MSG_FORMAT = logging.Formatter("%(asctime)s %(levelname)s[%(message)s]")
    CONSOLE_LOGGING_MSG_FORMAT = logging.Formatter("%(asctime)s %(levelname)s[%(message)s]")
    logger = logging.Logger("")
    log_path = os.path.split(fileName)[0]
    if not os.path.exists(log_path+'/'):
        os.makedirs(log_path)
    if str.lower(type)=='size':
        log_handler = ConcurrentRotatingFileHandler(filename=fileName,maxBytes=maxByte,backupCount=backupCount,encoding='utf8')
    else:
        # when:  s秒  m分钟 h小时 d天 midnight午夜   w{0-6} 星期   大小写都支持
        log_handler = ConcurrentTRFileHandler(fileName, when=timeType, interval=1,backupCount=backupCount,encoding='utf8',delay=True)
    fileLogLevel = get_log_level(fileLogLevel, 1)  # 先后顺序  参数、配置、默认
    log_handler.setLevel(fileLogLevel)
    log_handler.setFormatter(FILE_LOGGING_MSG_FORMAT)
    logger.addHandler(log_handler)
    if console:
        console = logging.StreamHandler()
        conLogLevel = get_log_level(conLogLevel,2)  # 先后顺序  参数、配置、默认
        console.setLevel(conLogLevel)
        console.setFormatter(CONSOLE_LOGGING_MSG_FORMAT)
        logger.addHandler(console)
    logger.handlers[0].baseFilename += ('.'+time.strftime("%Y-%m-%d", time.localtime()))
    return logger

#根据参数、配置文件情况，合理配置日志显示级别
def get_log_level(logLevel,type):
    if logLevel==-1:
        sec = "logger"
        opt = ""
        if type == 1:
            opt = "file_log_level"
            logLevel = 10
        else:
            opt = "con_log_level"
            logLevel = 10
        confDir = ""
        if os.path.exists("./conf/moduleConfig.conf"):
            confDir = "./conf/moduleConfig.conf"
        elif os.path.exists("./../conf/moduleConfig.conf"):
            confDir = "./../conf/moduleConfig.conf"
        elif os.path.exists("./../../conf/moduleConfig.conf"):
            confDir = "./../../conf/moduleConfig.conf"
        if confDir:
            conf = configparser.ConfigParser()
            conf.read(confDir, encoding="utf-8")
            if conf.has_option(sec,opt ):
                logLevel = conf.get(sec, opt)
                if isdigit(logLevel):
                    logLevel=int(logLevel)
                else:
                    logLevel = 10
    return logLevel


import os, time
from logging.handlers import TimedRotatingFileHandler


class ConcurrentTRFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False,
                 atTime=None):
        TimedRotatingFileHandler.__init__(self, filename, when, interval, backupCount, encoding, delay, utc, atTime)

        self.origin_filename = filename

    def getFilesToDelete(self):
        """
        Determine the files to delete when rolling over.
        More specific than the earlier method, which just used glob.glob().
        """
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix = self.origin_filename + "."  # 这里就不能用 baseName 了
        plen = len(prefix)
        for fileName in fileNames:
            if fileName[:plen] == prefix:
                suffix = fileName[plen:]
                if self.extMatch.match(suffix):
                    result.append(os.path.join(dirName, fileName))
        result.sort()
        if len(result) < self.backupCount:
            result = []
        else:
            result = result[:len(result) - self.backupCount]
        return result

    def doRollover(self):
        """
        do a rollover; in this case, a date/time stamp is appended to the filename
        when the rollover happens.  However, you want the file to be named for the
        start of the interval, not the current time.  If there is a backup count,
        then we have to get a list of matching filenames, sort them and remove
        the one with the oldest suffix.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        # get the time that this sequence started at and make it a TimeTuple
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        if self.utc:
            timeTuple = time.gmtime()
        else:
            timeTuple = time.localtime()

        # 以追加方式打开新的日志文件，没有改名和删除操作就不会冲突报错了。
        self.baseFilename = self.rotation_filename(os.path.abspath(self.origin_filename) + "." +
                                                   time.strftime(self.suffix, timeTuple))
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        # If DST changes and midnight or weekly rollover, adjust for this.
        if (self.when == 'MIDNIGHT' or self.when.startswith('W')) and not self.utc:
            dstAtRollover = time.localtime(newRolloverAt)[-1]
            if dstNow != dstAtRollover:
                if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                    addend = -3600
                else:  # DST bows out before next rollover, so we need to add an hour
                    addend = 3600
                newRolloverAt += addend
        self.rolloverAt = newRolloverAt
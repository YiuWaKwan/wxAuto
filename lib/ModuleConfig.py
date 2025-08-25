# -*- coding=utf-8 -*-
# import ConfigParser
import configparser
import os

class ConfAnalysis():
    def __init__(self,logger,confDir, logConf=0):
        # logger.info("#MAIN# 使用配置模块, 模块配置文件： %s ,日志配置文件：%s"  %((confDir.split('/')[-1]),logConf.split('/')[-1]))
        if os.path.exists(confDir):
            self.confDir = confDir
            self.conf=configparser.ConfigParser()
            self.conf.read(self.confDir,encoding="utf-8")
        else:
            logger.warn("the config file does not exit")
            return
    ##返回全部sections
    def getAllSections(self):
        return self.conf.sections()
    #返回某个sections的全部options
    def getAllOptions(self,section):
        return self.conf.options(section)
    #返回某个sections下的全部键值对
    def getAllItems(self,section):
        return self.conf.items(section)
    #返回某个sections下的options键值
    def getOneOptions(self,section,options):
        return self.conf.get(section,options)
    def getOneOptionByInt(self, section,options):
        return self.conf.getint(section,options)


if __name__  == "__main__":
#调用deamon
    #测试配置模块配置文件"../test/conf/test.conf"
    confTest = ConfAnalysis('../conf/moduleConfig.conf',"../conf/logger.conf")
    # conf.sections()
    print(confTest.getAllSections())
    print(confTest.getAllOptions("distcpTrans"))
    print(confTest.getAllItems("distcpTrans"))
    print(confTest.getOneOptions("distcpTrans","restart_methods"))



# -*- coding: utf-8 -*-
import hashlib
import os
import shutil
import time
import traceback
import uuid
import subprocess
import datetime
import os
from tools import MysqlDbPool


# 解密数据库 返回数据库文件路径
def get_encrypt_sqlite_file(logger, deviceInfo, devUin, dbPassword, wx_id, flag=0,seq=0):
    try:
        # TODO 系统文件分隔符
        local_wechat_db_path = "D:\\WeChatLocalDB\\%s" % wx_id
        decypt_path = local_wechat_db_path + "\\decypt"
        if not os.path.exists(local_wechat_db_path):
            os.makedirs(local_wechat_db_path)
        if not os.path.exists(decypt_path):
            os.makedirs(decypt_path)
        if flag != 1:
            wechat_path_tmp1 = decypt_path + "\\wechat.dbing-journal"  # 中间文件
            wechat_path_tmp2 = decypt_path + "\\wechat.dbing"  # 中间文件
            # wechat_path_tmp1  wechat_path_tmp2  运行没完成的中间文件会导致报错 这里直接干掉
            if os.path.exists(wechat_path_tmp1):
                os.remove(wechat_path_tmp1)
            if os.path.exists(wechat_path_tmp2):
                os.remove(wechat_path_tmp2)
        if flag == 1:
            wechat_path = decypt_path + "\\wechat.db"
            wechat_path2 = decypt_path + "\\wechat2.db"
            try:
                if os.path.exists(wechat_path2):
                    os.remove(wechat_path2)
                index = 0
                while not os.path.exists(wechat_path):
                    index = index + 1
                    time.sleep(0.1)
                    if index % 20 == 0:
                        logger.info("等待解密中。。")
                    if index > 600:
                        wechat_path2 = -1
                        break
                if os.path.exists(str(wechat_path)):
                    shutil.copy2(wechat_path, wechat_path2)
            except(Exception) as e:
                logger.info(traceback.format_exc())
            finally:
                return wechat_path2
        mysqlPool = MysqlDbPool.MysqlDbPool()
        wechat_db_file_list = ["EnMicroMsg.db", "EnMicroMsg.db-shm", "EnMicroMsg.db-wal",
                               "EnMicroMsg.db.ini", "EnMicroMsg.db.sm"]
        localdb = wechat_db_file_list[0]
        shmfile = wechat_db_file_list[1]
        walfile = wechat_db_file_list[2]
        inifile = wechat_db_file_list[3]
        smfile = wechat_db_file_list[4]

        execFilePath = os.getcwd() + "\\data\\sqlcipher-shell64.exe"
        sqlite_path = md5_file(devUin)

        localdb_modify_time = check_wechat_db_time(deviceInfo, sqlite_path, localdb)
        shmfile_modify_time = check_wechat_db_time(deviceInfo, sqlite_path, shmfile)
        query_time_sql = "select localdbtime,shmfileTime from wx_message_timestamp where wx_main_id = '%s'" % wx_id
        query_result_set = mysqlPool.getData(query_time_sql)
        localdbTime = None
        shmfileTime = None
        if len(query_result_set) > 0:
            query_result = query_result_set[0]
            localdbTime = query_result[0]
            shmfileTime = query_result[1]
        # 获取本地数据库开始时间
        this_time = datetime.datetime.now()
        update_log_sql = "update wx_decypt_log set get_localdb_starttime = '%s'where wx_main_id = '%s' and taskseq = '%s'" % (
            this_time, wx_id, seq)
        mysqlPool.excSql(update_log_sql)
        if localdb_modify_time is not None and shmfile_modify_time is not None \
                and localdbTime is not None and shmfileTime is not None:
            if shmfile_modify_time > shmfileTime and localdbTime == localdb_modify_time:
                # adb_pull_file(deviceInfo, sqlite_path, localdb, local_wechat_db_path)
                adb_pull_file(deviceInfo, sqlite_path, shmfile, local_wechat_db_path)
                adb_pull_file(deviceInfo, sqlite_path, walfile, local_wechat_db_path)
                # adb_pull_file(deviceInfo, sqlite_path, inifile, local_wechat_db_path)
                # adb_pull_file(deviceInfo, sqlite_path, smfile, local_wechat_db_path)

                # 获取本地数据库结束时间
                this_time = datetime.datetime.now()
                update_log_sql = "update wx_decypt_log set get_localdb_endtime = '%s'where wx_main_id = '%s' and taskseq = '%s'" % (
                    this_time, wx_id, seq)
                mysqlPool.excSql(update_log_sql)
                wechat_path = decypt_sqlite_file(logger, execFilePath, local_wechat_db_path, dbPassword,
                                                 decypt_path, wx_id, seq, mysqlPool)
                update_time_sql = "update wx_message_timestamp set shmfileTime='%s' where wx_main_id='%s'" \
                                  % (shmfile_modify_time, wx_id)
                mysqlPool.excSql(update_time_sql)
            elif shmfile_modify_time > shmfileTime and localdb_modify_time > localdbTime:
                adb_pull_file(deviceInfo, sqlite_path, localdb, local_wechat_db_path)
                adb_pull_file(deviceInfo, sqlite_path, shmfile, local_wechat_db_path)
                adb_pull_file(deviceInfo, sqlite_path, walfile, local_wechat_db_path)
                adb_pull_file(deviceInfo, sqlite_path, inifile, local_wechat_db_path)
                adb_pull_file(deviceInfo, sqlite_path, smfile, local_wechat_db_path)
                # 获取本地数据库结束时间
                this_time = datetime.datetime.now()
                update_log_sql = "update wx_decypt_log set get_localdb_endtime = '%s'where wx_main_id = '%s' and taskseq = '%s'" % (
                    this_time, wx_id, seq)
                mysqlPool.excSql(update_log_sql)
                wechat_path = decypt_sqlite_file(logger, execFilePath, local_wechat_db_path, dbPassword,
                                                 decypt_path, wx_id, seq, mysqlPool)
                update_time_sql = "update wx_message_timestamp set localdbtime = '%s',shmfileTime='%s' where wx_main_id='%s'" \
                                  % (localdb_modify_time, shmfile_modify_time, wx_id)
                mysqlPool.excSql(update_time_sql)
            else:
                wechat_path = decypt_path + "\\wechat.db"
        else:
            adb_pull_file(deviceInfo, sqlite_path, localdb, local_wechat_db_path)
            adb_pull_file(deviceInfo, sqlite_path, shmfile, local_wechat_db_path)
            adb_pull_file(deviceInfo, sqlite_path, walfile, local_wechat_db_path)
            adb_pull_file(deviceInfo, sqlite_path, inifile, local_wechat_db_path)
            adb_pull_file(deviceInfo, sqlite_path, smfile, local_wechat_db_path)
            # 获取本地数据库结束时间
            this_time = datetime.datetime.now()
            update_log_sql = "update wx_decypt_log set get_localdb_endtime = '%s'where wx_main_id = '%s' and taskseq = '%s'" % (
                this_time, wx_id, seq)
            mysqlPool.excSql(update_log_sql)
            wechat_path = decypt_sqlite_file(logger, execFilePath, local_wechat_db_path, dbPassword, decypt_path, wx_id,
                                             seq, mysqlPool)
            update_time_sql = "update wx_message_timestamp set localdbtime = '%s',shmfileTime='%s' where wx_main_id='%s'" \
                              % (localdb_modify_time, localdb_modify_time, wx_id)
            mysqlPool.excSql(update_time_sql)
        return wechat_path
    except(Exception) as e:
        logger.info(traceback.format_exc())


# 解密sqlite方法
def decypt_sqlite_file(logger, execFilePath, local_wechat_db_path, dbPassword, decypt_path, wx_id, seq, mysqlPool):
    print("解密文件-start_time: %s %s" % (datetime.datetime.now(), wx_id))
    this_time = datetime.datetime.now()
    update_log_sql = "update wx_decypt_log set decypt_starttime = '%s'where wx_main_id = '%s' and taskseq = '%s'" % (
        this_time, wx_id, seq)
    mysqlPool.excSql(update_log_sql)

    decypt_path = decypt_path + "\\wechat.db"
    if os.path.exists(decypt_path):
        os.remove(decypt_path)
    local_db_path = local_wechat_db_path + "\\EnMicroMsg.db"
    decypt_path_ing = decypt_path + "ing"
    decrypt_command = "%s %s " \
                      "\"PRAGMA key = '%s'; PRAGMA cipher_use_hmac = off; PRAGMA kdf_iter = 4000; " \
                      "ATTACH DATABASE '%s' AS wechat2 KEY ''; SELECT sqlcipher_export('wechat2');" \
                      "DETACH DATABASE wechat2 \" " % (execFilePath, local_db_path, dbPassword, decypt_path_ing)
    p = subprocess.Popen(decrypt_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.stdout.close()
    p.stderr.close()
    p.wait()
    os.rename(decypt_path_ing, decypt_path)
    print("解密结束-end_time: %s %s" % (datetime.datetime.now(), wx_id))
    this_time = datetime.datetime.now()
    update_log_sql = "update wx_decypt_log set decypt_endtime = '%s'where wx_main_id = '%s' and taskseq = '%s'" % (
        this_time, wx_id, seq)
    mysqlPool.excSql(update_log_sql)
    # logger.info("解密结束-end_time: %s %s" % (datetime.datetime.now(), wx_id))
    return decypt_path


# adb pull 文件公共方法
# deviceInfo:127.0.0.1:21503 sqlite_path:41e5a1f4dd2f8e6ce71034af57d9775a
def adb_pull_file(deviceInfo, sqlite_path, file_name, local_wechat_db_path):
    judgeFileExistCommand = "adb -s %s shell ls /data/data/com.tencent.mm/MicroMsg/%s/%s | wc -l" % (
        deviceInfo, sqlite_path, file_name)
    judge = subprocess.Popen(judgeFileExistCommand, shell=False, stdout=subprocess.PIPE).stdout.readlines()
    if len(judge) == 1:
        pull_command = "adb -s %s pull /data/data/com.tencent.mm/MicroMsg/%s/%s %s" % (
            deviceInfo, sqlite_path, file_name, local_wechat_db_path)
        print(pull_command)
        p = subprocess.Popen(pull_command)
        p.wait()


# md5加密结果
def md5_file(devUin):
    hl = hashlib.md5()
    mm_uin = "mm" + devUin
    hl.update(mm_uin.encode(encoding='utf-8'))
    sqlite_path = hl.hexdigest()
    return sqlite_path


# 判断时间数据库文件时间
def check_wechat_db_time(deviceInfo, sqlite_path, filename):
    judgeFileExistCommand = "adb -s %s shell ls /data/data/com.tencent.mm/MicroMsg/%s/%s | wc -l" % (
        deviceInfo, sqlite_path, filename)
    judge = subprocess.Popen(judgeFileExistCommand, shell=False, stdout=subprocess.PIPE).stdout.readlines()
    if len(judge) == 1:
        command = "adb -s %s shell stat /data/data/com.tencent.mm/MicroMsg/%s/%s | " \
                  "grep \"Modify:\"" % (deviceInfo, sqlite_path, filename)
        result = subprocess.Popen(command, shell=False,
                                  stdout=subprocess.PIPE).stdout.readlines()
        modify_time = string_to_datetime(str(result[0]).split(": ")[1].split(".")[0])
        return modify_time
    else:
        return str(datetime.datetime.now())


# 将字符串格式的时间转为datetime类型
def string_to_datetime(string):
    format_datetime = datetime.datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
    return format_datetime


# 将datetime类型转换为字符串格式
def datetime_to_string(string):
    return int(string.strftime("%Y%m%d%H%M%S"))

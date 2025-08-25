import random
import time


def taskHeartBeatRefresh(taskSeq, mysqlUtil):
    heartBeatRefreshSql = """update wx_task_manage
                                set heartBeatTime = now()
                                where taskSeq = \"%s\"""" %(taskSeq)
    mysqlUtil.excSql(heartBeatRefreshSql)

def taskInfoInsert(uuidMachine, actionType, priority, mysqlUtil, cronTime = "now()", *taskInfoList, **taskDict):
    taskSeq = round(time.time() * 1000 + random.randint(100, 999))
    subTaskInfoSql = ""
    if int(actionType) == 32:
        # 通讯录补充搜索
        mainTaskSeq = taskDict['taskSeq']
        subTaskInfoSql ="""UPDATE `wx_add_friend`
                            SET `subTaskSeq` = \'%s\'
                            WHERE `taskSeq` = \'%s\'"""%(taskSeq,mainTaskSeq)
    if subTaskInfoSql:
        mysqlUtil.excSql(subTaskInfoSql)
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
                        VALUES
                            (
                                \'%s\',
                                \'%s\',
                                \'%s\',
                                now(),
                                %s,
                                \'%s\',
                                0,
                                1
                            )""" %(taskSeq, uuidMachine, actionType, cronTime, priority)
    mysqlUtil.excSql(taskInsertSql)

def taskReset(mysqlUtil, taskSeq, taskStatus):
    sql = """UPDATE `wx_task_manage`
                SET `startTime` = NULL,
                 `endTime` = NULL,
                 `heartBeatTime` = DATE_ADD( now(), INTERVAL 1 DAY ),
                 `cronTime` = now(),
                 `status` = \'%s\',
                WHERE
                    (
                        `taskSeq` = \'%s\'
                    );
                 """ %(taskSeq,taskStatus)
    mysqlUtil.excSql(sql)

def taskDisable(mysqlUtil, taskSeq):
    sql = """ update wx_task_manage
                set `status` = 3,
                remarks = \"任务执行时间超20min\"
                where taskSeq=\"%s\" """%(taskSeq)
    mysqlUtil.excSql(sql)

if __name__ == '__main__':
    taskSeq = "1535441727651"
    from tools import MysqlDbPool
    mysqlUtil = MysqlDbPool.MysqlDbPool(1, 10)
    taskHeartBeatRefresh(taskSeq, mysqlUtil)
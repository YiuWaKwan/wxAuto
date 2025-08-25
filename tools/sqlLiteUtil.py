import sqlite3


def queueRecordAction(type,taskSeq = "",pid = ""):
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    if type == 'selete':
        # 查询
        exeSql = """select * from taskQueue"""
        cursor.execute(exeSql)
        result = cursor.fetchall()
        return result
    elif type == 'insert':
        # insert
        exeSql = """INSERT INTO taskQueue (taskSeq, pid) VALUES (\'%s\',\'%s\');""" %(taskSeq,pid)
        cursor.execute(exeSql)
        conn.commit()
    elif type == 'delete':
        # delete
        exeSql = """DELETE from taskQueue where taskSeq=\'%s\';""" %(taskSeq)
        cursor.execute(exeSql)
        conn.commit()

# def queueCreate():
#     # conn = sqlite3.connect(':memory:')
#
#
#     # cursor.execute('CREATE TABLE taskQueue(taskSeq, pid)')
#     return cursor

# def queueClose(cursor):
#
#     cursor.close()
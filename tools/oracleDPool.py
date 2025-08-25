import cx_Oracle
import os
from lib.ModuleConfig import ConfAnalysis
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'

class oracleDbAction():
    def __init__(self,logger):
        self.logger = logger
        __baseDir = os.getcwd()
        __configFile = '%s/conf/moduleConfig.conf' % __baseDir
        __confAllItems = ConfAnalysis(logger, __configFile)
        self.username = __confAllItems.getOneOptions('ORACLEDB', 'oracle.username')
        self.password = __confAllItems.getOneOptions('ORACLEDB', 'oracle.pwd')
        self.dsn_tns = __confAllItems.getOneOptions('ORACLEDB', 'oracle.dsn')

    def queryData(self,exc_sql):
        try:
            conn = cx_Oracle.connect(self.username, self.password, self.dsn_tns)
            cur = conn.cursor()
            cur.execute(exc_sql)
            rows = cur.fetchall()
            keys = map(lambda k: k[0].lower(), cur.description)
            results = [dict(zip(keys, row)) for row in rows if row is not None]
            conn.close()
            return results
        except(Exception) as error:
            self.logger.exception(error)
        finally:
            pass


    def insertData(self,excSql):
        try:
            conn = cx_Oracle.connect(self.username, self.password, self.dsn_tns)
            cur = conn.cursor()
            cur.execute(excSql)
            conn.commit()
            conn.close()
        except(Exception) as error:
            self.logger.exception(error)
        finally:
            pass
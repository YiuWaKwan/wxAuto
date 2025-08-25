import os, math, time
import PIL.Image as Image
from urllib import request
import requests
from lib.FinalLogger import *
from lib.ModuleConfig import ConfAnalysis
from tools import MysqlDbPool

# 初始化logger
logger = getLogger('./log/taskMonitor.log')
configFile = '%s/conf/moduleConfig.conf' % os.getcwd()
confAllItems = ConfAnalysis(logger, configFile)

fileServiceURL = confAllItems.getOneOptions("fileSystemService", "fileserviceurl")

def scanGroupInfo(mySqlUtil):
    sql = u"select group_id, head_picture " \
          u" from wx_group_info l " \
          u" where group_name is not null and group_name != '' " \
          u" and exists (select 1 from wx_group_member where group_id=l.group_id)"
    logger.info(sql)
    groupInfoList = mySqlUtil.getData(sql)
    for info in groupInfoList:
        if info[1] is None or info[1] == '':
            logger.info("update group_id(%s) ... " % info[0])
            updateHeadPic(mySqlUtil, info[0])

def updateHeadPic(mySqlUtil, group_id):
    sql = "select head_picture from wx_group_member where group_id='%s' limit 9 " % group_id
    picListInfo = mySqlUtil.getData(sql)
    if picListInfo is not None and len(picListInfo) > 2:
        picList = []
        for pic in picListInfo:
            picList.append(pic[0])
        head_picture = createGroupHeadPic(picList, group_id)
        if head_picture is not None and len(head_picture) > 0:
            sql = "update wx_group_info set head_picture='%s' where group_id='%s'" % (head_picture, group_id)
            mySqlUtil.excSql(sql)

def getTargetFile(path, filterColumn):
    filelist = os.listdir(path)
    targetFileList = []
    for file in filelist :
        if filterColumn in file:
            targetFileList.append(file)
    return targetFileList

def createGroupHeadPic(picList, chatRoomId):
    try:
        locate_file_path = "data/group_head/"
        if os.path.exists(locate_file_path) == False:
            os.makedirs(locate_file_path)
        index = 1
        for pic in picList :
            if pic != '' and pic is not None:
                fileObj = request.urlopen(pic)
                fileContent = fileObj.read()
                with open("%s%s_%d.jpg" % (locate_file_path, chatRoomId, index), 'ab+') as f:  # 生成本地文件
                    f.write(fileContent)
                index = index + 1

        picturelist = getTargetFile(locate_file_path, chatRoomId)
        if len(picturelist) == 0:
            return ''

        each_size = int(math.sqrt(float(640 * 640) / 9)) - 16
        each_space = 12
        lost_space_y = 0  # 不足9张图片的补位方案
        lost_space_x = 0  # 一行不足图片的补位方案
        lines = 3
        y = 0
        x = 0
        if len(picturelist) == 5 or len(picturelist) == 6:
            lost_space_y = int((each_size + 16) / 2)
            y = 1
        else:
            y = 2
        if len(picturelist) == 5 or len(picturelist) == 8:
            lost_space_x = int((each_size + 16) / 2)
        elif len(picturelist) == 7:
            lost_space_x = each_size + 16

        if len(picturelist) <= 4:
            lines = 2
            y = 1
            each_size = int(math.sqrt(float(640 * 640) / 4)) - 18
            if len(picturelist) < 3:
                y = 0
                lost_space_y = int((each_size + 18) / 2)
            if len(picturelist) == 3:
                lost_space_x = int((each_size + 18) / 2)

        image = Image.new('RGB', (640, 640), "#DCE0E0")

        for filename in picturelist:
            try:
                img = Image.open("%s%s" % (locate_file_path, filename))
            except IOError:
                print("Error")
            else:
                img = img.resize((each_size, each_size), Image.ANTIALIAS)
                if y == 0:
                    posi_x = x * (each_size + each_space) + each_space + lost_space_x if x > 0 else each_space +lost_space_x
                else:
                    posi_x = x * (each_size + each_space) + each_space if x > 0 else each_space
                posi_y = y * (each_size + each_space) + each_space + lost_space_y if y > 0 else each_space + lost_space_y

                image.paste(img, (posi_x, posi_y))
                x += 1
                if x == lines:
                    x = 0
                    y -= 1

        filename = "%s.jpg" % chatRoomId
        file_path = "group_head_picture"
        image.save("%s%s" % (locate_file_path, filename))
        uploadpicture = open("%s%s" % (locate_file_path, filename), "rb")
        files = {"filecontent": (filename, uploadpicture, "image/jpg")}
        today = time.strftime("%Y%m%d")
        req = requests.post(fileServiceURL + "/uploadGroupPic/", files=files,
                            data={"file_date": today, "file_path": file_path, "file_name": filename})
        #send_result = req.text
        uploadpicture.close()

        for deletename in picturelist:
            os.unlink("%s%s" % (locate_file_path, deletename))
        os.unlink("%s%s" % (locate_file_path, filename))

        return "%s/%s/%s/%s/%s" % (fileServiceURL, "static", file_path, today, filename)
    except(Exception) as e:
            print(e)
    return ''

if __name__ == '__main__':
    mysqlPool = MysqlDbPool.MysqlDbPool()
    scanGroupInfo(mysqlPool)
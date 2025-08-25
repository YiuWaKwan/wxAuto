import cv2
import imutils
from PIL import Image


def handle():
    img = cv2.imread('img\\checkCodeImg\\ori\\1-1.jpg')
    imgray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(imgray, 80, 200, 0)
    image, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # 绘制独立轮廓，如第四个轮廓
    imag = cv2.drawContours(img,contours,-1,(0,255,0),3)
    # 但是大多数时候，下面方法更有用q
    #imag = cv2.drawContours(img, contours, 3, (0, 255, 0), 3)

    '''while (1):
        cv2.imshow('img', img)
        cv2.imshow('imgray', imgray)
        cv2.imshow('image', image)
        cv2.imshow('imag', imag)
        cv2.imwrite("img\checkCodeImg\pintuCVHH.jpg", imag, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        if cv2.waitKey(1) == ord('q'):
            break
    cv2.destroyAllWindows()'''

    # find contours in the thresholded image
    cnts =contours

    # loop over the contours
    for c in cnts:
        try:
            area=cv2.contourArea(c)
            if(area>1700):
                print("area:" + str(area))
                length = cv2.arcLength(c, True)
                print("length:" + str(length))
                # compute the center of the contour
                M = cv2.moments(c)
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                print("cX:" + str(cX)+"   cY:"+str(cY))
                # draw the contour and center of the shape on the image
                cv2.drawContours(imag, [c], -1, (0, 255, 0), 3)
                cv2.circle(imag, (cX, cY), 7, (255, 255, 255), -1)
                cv2.putText(imag, "center", (cX - 20, cY - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                # show the image
                cv2.imshow("imag1", imag)
                cv2.waitKey(0)
        except (Exception) as e:
            print(e)

def handleByIm():

    image = cv2.imread('img\checkCodeImg\pintuCVHH.jpg')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY)[1]

    # find contours in the thresholded image
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                            cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]

    # loop over the contours
    for c in cnts:
        # compute the center of the contour
        M = cv2.moments(c)
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])

        # draw the contour and center of the shape on the image
        cv2.drawContours(image, [c], -1, (0, 255, 0), 2)
        cv2.circle(image, (cX, cY), 7, (255, 255, 255), -1)
        cv2.putText(image, "center", (cX - 20, cY - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # show the image
        cv2.imshow("Image", image)
        cv2.waitKey(0)

def cutPicByCv2(picName):
    image = cv2.imread("img\\checkCodeImg\\ori\\"+picName+".jpg") # 从指定路径读取图像
    imgShap=image.shape
    sz1 = imgShap[0]  # height(rows) of image
    sz2 = imgShap[1]  # width(colums) of image

    print("shap:%s,%s:" %(str(imgShap[0]),str(imgShap[1])))
    a = int(0)  # x start
    b = int(sz2)  # x end
    c = int(0)  # y start
    d = int(sz1)  # y end
    cropImg = image[a:b, c:d]  # crop the image
    cv2.imwrite("img\\checkCodeImg\\ori\\"+picName+"Cut.jpg", cropImg) # 保存到指定目录

def cutPicByPil(picPath,picName,sizeList):
    resultPicName=picName
    im = Image.open(picPath+picName)
    # 图片的宽度和高度
    img_size = im.size
    imgWidth=img_size[0]
    imgHeight=img_size[1]
    print("图片宽度和高度分别是{}".format(img_size))
    '''
    裁剪：传入一个元组作为参数
    元组里的元素分别是：（距离图片左边界距离x， 距离图片上边界距离y，距离图片左边界距离+裁剪框宽度x+w，距离图片上边界距离+裁剪框高度y+h）
    '''
    # 截取图片中一块
    # x = 18
    # y = 134
    # w = 346
    # h = 200
    x = int(imgWidth*sizeList[0])
    y =  int(imgHeight*sizeList[1])
    w = int(imgWidth*sizeList[2])
    h = int(imgHeight*sizeList[3])
    resultPicName="cut_"+picName
    region = im.crop((x, y, x + w, y + h))             # 截取图片中一块宽是250和高都是300的
    region.save(picPath +resultPicName)
    return resultPicName

def readAndSavePic(pic): # #读写一遍图片，去掉拍摄时间，微信相册已拍摄时间排序的
    img = cv2.imread(pic)
    cv2.imwrite(pic, img)
    #img = cv2.imread("D:\\WXCRM\\WXCRM\\static\\img\\momentsImg\\47a46a1c-8719-11e8-95fc-246e9664fa1d.jpg")
    #cv2.imwrite("D:\\WXCRM\\WXCRM\\static\\img\\momentsImg\\47a46a1c-8719-11e8-95fc-246e9664fa1d.jpg", img)
if __name__ == '__main__':
    #handleByIm()
    #handle()
    #cutPicByCv2("13")
    #cutPicByPil("img\\checkCodeImg\\ori\\","13.jpg")
    readAndSavePic()
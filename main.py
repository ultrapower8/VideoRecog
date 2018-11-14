# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 17:34:09 2018

@author: 98089
"""

from aip import AipOcr
from PIL import Image
import pymysql,datetime
import re,os
import numpy as np
        

class GasReader(object):
    
    # 日期的基本格式
    DatePattern = re.compile('(\d{2})-(\d{2})(\d{2}):(\d{2}):(\d{2})')
    
    def __init__(self,initValue,Index,
                 APP_ID,API_KEY,SECRET_KEY,
                 x_p,y_p,x_w_p,y_w_p,
                 host='localhost',user='root',passwd='azwj5718265',db='gasreading',
                 date_x_p=0.7,date_y_p=0.93,date_x_w_p=0.26,date_y_w_p=0.05,
                 ):
        self.x_p = x_p
        self.y_p = y_p
        self.x_w_p = x_w_p
        self.y_w_p = y_w_p
        self.dateXP = date_x_p
        self.dateYP = date_y_p
        self.dateXWP = date_x_w_p
        self.dateYWP = date_y_w_p
        self.APP_ID = APP_ID
        self.API_KEY = API_KEY
        self.SECRET_KEY = SECRET_KEY
        self.Index = Index
        self.host = host
        self.user = user
        self.passwd = passwd
        self.db = db
        self.currentValue = self.searchInitValue(initValue)
        # 建立百度云代理机
        self.client = AipOcr(APP_ID,API_KEY,SECRET_KEY)
        
    def searchInitValue(self,initValue):
        conn = pymysql.connect(self.host,self.user,self.passwd,self.db)
        cursor = conn.cursor()
        SQL_1 = 'SELECT TimeIndex,GasValue FROM gas_%d'%self.Index + \
                 ' ORDER BY ID DESC LIMIT 5'
        cursor.execute(SQL_1)
        r = cursor.fetchall()
        cursor.close()
        conn.close()
        if len(r) < 5:
            return initValue
        else:
            return r[0][1]
    def validPoints(self):
        # 连接数据库
        conn = pymysql.connect(self.host,self.user,self.passwd,self.db)
        cursor = conn.cursor()
        SQL_1 = 'SELECT TimeIndex,GasValue FROM gas_%d'%self.Index + \
                 ' ORDER BY ID DESC LIMIT 5'
        cursor.execute(SQL_1)
        r = cursor.fetchall()[::-1]
        cursor.close()
        conn.close()
        if len(r) < 5:
            return [i+self.currentValue for i in range(1,4)]
        else:
            r = [[i[0],i[1]] for i in r]
            temp = []
            for k in range(1,5):
                if r[k][0] > r[k-1][0]:
                    crementTime = (r[k][0] - r[k-1][0]).seconds
                    crementGas = r[k][1] - r[k-1][1]
                    GasPerSecond = crementGas/crementTime
                    temp.append(GasPerSecond)
                else:
                    pass
            if len(temp) < 2:
                return [i+self.currentValue for i in range(1,4)]
            mean_GasPerSecond = np.mean(temp)
            currentTime = datetime.datetime.now()
            MaxGas = (currentTime - r[-1][0]).seconds * mean_GasPerSecond * 1.6
            return [i + self.currentValue for i in range(1,int(MaxGas+2))]
        
    def writeGas(self,Date,GasNum):
        conn = pymysql.connect(self.host,self.user,self.passwd,self.db)
        cursor = conn.cursor()
        SQL_1 = 'INSERT INTO gas_%d'%self.Index + '(TimeIndex,GasValue) Values("%s",%d)'
        SQL_1 = SQL_1%(Date,GasNum)
        cursor.execute(SQL_1)
        conn.commit()
        cursor.close()
        conn.close()
        print('  数据插入成功')
    
    def ImgReader(self,ImgPath):
        # 接收图片
        targetImgPath = ImgPath
        # 裁剪图片(燃气读数)
        img = Image.open(targetImgPath)
        img_size = img.size
        h = img_size[1]; w = img_size[0]
        x = self.x_p * w
        y = self.y_p * h
        x_w = self.x_w_p * w
        y_w = self.y_w_p * h
        GasImg = img.crop((x,y,x+x_w,y+y_w))
        GasImg.save('temp/gas_%02d.jpg'%self.Index)
        # 裁剪图片（日期）
        DX = self.dateXP * w
        DY = self.dateYP * h
        DXW = self.dateXWP * w
        DYW = self.dateYWP * h
        DateImg = img.crop((DX,DY,DX+DXW,DY+DYW))
        DateImg.save('temp/Date_%02d.jpg'%self.Index)
        # 对图片进行识别
        with open('temp/gas_%02d.jpg'%self.Index,'rb') as imgFile:
            GasImg = imgFile.read()
        GasOutCome = self.client.basicGeneral(GasImg)
        GasNum = GasOutCome['words_result'][0]['words']
        try:
            GasNum = int(GasNum)
        except:
            GasNum = -1
        print('  本次识别的燃气读数为：%d'%GasNum)
        with open('temp/Date_%02d.jpg'%self.Index,'rb') as imgFile:
            DateImg = imgFile.read()
        DateOutCome = self.client.basicGeneral(DateImg)
        Date = DateOutCome['words_result'][0]['words']
        if re.search(self.DatePattern,Date):
            month,day,hour,minute,second = re.findall(self.DatePattern,
                                                    Date)[0]
            year = datetime.datetime.now().year
            Date = '%s-%s-%s %s:%s:%s'%(year,month,day,hour,minute,second)
        else:
            Date = '《日期识别错误》'
        print('  本次识别的日期为：%s'%Date)
        if GasNum in self.validPoints() and Date != '《日期识别错误》':
            print('    该燃气读数被接受：%s: %d'%(Date,GasNum))
            self.writeGas(Date,GasNum)
            self.currentValue = GasNum
            print(' +++++++++++++++++++++++ ')
        else:
            pass
        
    def main(self):
        pass
    
    def test(self,imgDir):
        for i in range(1,10000,40):
            try:
                imgPath = os.path.join(imgDir,"%d.jpg"%i)
                self.ImgReader(imgPath)
            except:
                pass
        
if __name__ == '__main__':
    GasReader_1 = GasReader(1866,1,'11501005','SRyM8lK0VplrZY0KINEwCYGl',
                    '0BYs2KnoNaubToz3Gg3tBDGQ4H3lV5Ko',0.45,0.67,0.35,0.156)
    GasReader_1.test('testPictures')
    
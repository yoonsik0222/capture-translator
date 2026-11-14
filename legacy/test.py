import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import * #setWindowIcon 라이브러리
from PyQt5 import uic #Ui module

from io import BytesIO
import win32clipboard
from PIL import Image
import pyautogui as pag
import time
import keyboard
from datetime import datetime
import cv2
import os
import pytesseract
import requests
import urllib.request
import json


def get_translate(text, source, target):
    client_id = "YOUR_CLIENT_ID" # <-- client_id 기입
    client_secret = "YOUR_CLIENT_SECRET" # <-- client_secret 기입

    data = {'text' : text,
            'source' : '{}'.format(source),
            'target': '{}'.format(target)}

    url = "https://openapi.naver.com/v1/papago/n2mt"

    header = {"X-Naver-Client-Id":client_id,
              "X-Naver-Client-Secret":client_secret}

    response = requests.post(url, headers=header, data=data)
    rescode = response.status_code

    if(rescode==200):
        send_data = response.json()
        trans_data = (send_data['message']['result']['translatedText'])
        return trans_data
    else:
        print("Error Code:" , rescode)

def langDetect(text):
    client_id = "YOUR_CLIENT_ID"
    client_secret = "YOUR_CLIENT_SECRET"
    data = "query=" + text
    url = "https://openapi.naver.com/v1/papago/detectLangs"
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id",client_id)
    request.add_header("X-Naver-Client-Secret",client_secret)
    response = urllib.request.urlopen(request, data=data.encode("utf-8"))
    rescode = response.getcode()
    if(rescode==200):
        response_body = response.read()
        detect_lang = json.loads(response_body.decode('utf-8'))
        return detect_lang['langCode']
        # print(response_body.decode('utf-8'))
    else:
        print("Error Code:" + rescode)


def send_to_clipboard(clip_type, data):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(clip_type, data)
    win32clipboard.CloseClipboard()
    
pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract'

UI_class = uic.loadUiType("PyqtTranslater.ui")[0]

captureModeFlag = 0
loadTextFlag = 0

filepath = f'{os.getcwd()}/DO_NOT_TOUCH_THIS_IMAGE.png'
start = []
end = []


class MyWindow(QMainWindow, UI_class):
    def __init__(self):
        super().__init__() 
        self.setupUi(self)
        self.setWindowTitle("캡쳐 번역기")
        self.setWindowIcon(QIcon("asdf.png")) 
        # Button click signal
        self.captureButton.clicked.connect(self.captureMode)
        self.LoadButton.clicked.connect(self.LoadText)
        self.toLangKor.clicked.connect(self.toKor)
        self.toLangEng.clicked.connect(self.toEng)
        self.toLangJpn.clicked.connect(self.toJpn)

        # self.setWindowTitle("test") #GUI screen name
        # self.setGeometry(300,300,400,400) #GUI geometry
        # self.setWindowIcon(QIcon('asdf.png')) #GUI Icon -- need QtGui library   
        

        
    def captureMode(self):

        QApplication.processEvents()

        global captureModeFlag, filepath, start, end
        if captureModeFlag == 0:
            captureModeFlag = 1
            self.captureLabel.setText("캡쳐 모드 ON")
            self.alert.setPlainText("왼쪽 위 > 오른쪽 아래 순으로 쉬프트키를 누르면 캡쳐 가능.")

        else:
            captureModeFlag = 0
            self.captureLabel.setText("캡쳐 모드 OFF")
            self.alert.setPlainText("")
            print("Capture Mod OFF")

        while captureModeFlag == 1:
            print("Capture Mod ON")
            QApplication.processEvents()

            fail = 0
            #print("Program is working NOW!!!!")

            while True: # 캡쳐 shift first 
                QApplication.processEvents()
                if captureModeFlag != 0:
                    QApplication.processEvents()
                    if keyboard.is_pressed("shift"):
                        start_T = datetime.now()
                        start = pag.position()
                        time.sleep(0.2)
                        QApplication.processEvents()
                        break
            while True: # 캡쳐 shift second
                QApplication.processEvents()
                if captureModeFlag != 0:
                    QApplication.processEvents()
                    now_t = datetime.now()
                    if keyboard.is_pressed("shift"):
                        if (now_t-start_T).total_seconds() >= 3:
                            break
                        end = pag.position()
                        print("Successfully captured image.") #이미지 캡처 완료시 message send
                        self.alert.setPlainText("정상적으로 캡쳐를 완료 했습니다.")
                        time.sleep(0.2)
                        QApplication.processEvents()
                        break
            QApplication.processEvents()     
            # 왼쪽 위 > 오른쪽 아래 확인 구문
            if (fail == 0) and (start[0] < end[0]) and (start[1] < end[1]):
                xx = start[0] 
                yy = start[1]
                ww = end[0] - start[0]
                hh = end[1] - start[1]
                pag.screenshot(filepath, region = (xx, yy, ww, hh))

                image = Image.open(filepath)
                output = BytesIO()
                image.convert("RGB").save(output, "BMP")
                data = output.getvalue()[14:]
                output.close()
                send_to_clipboard(win32clipboard.CF_DIB, data)
                #여기까지가 캡쳐 이미지 사본을 test.png로 저장하는 구문
                self.alert.setPlainText("정상적으로 캡쳐를 완료 했습니다.\nDO_NOT_TOUCH_THIS_IMAGE.png 를 통해 확인이 가능합니다.")

            else:
                self.alert.setPlainText("ERROR: 캡쳐 순서가 잘못 되었습니다.\n왼쪽 위 > 오른쪽 아래 순으로 진행해주세요.")
                #print('error: 캡처 순서가 잘못되었습니다.\n왼쪽 위 > 오른쪽 아래 순으로 진행해주세요.')
                pass
        else:
            QApplication.processEvents()
            pass

            QApplication.processEvents()
        QApplication.processEvents()

    def LoadText(self):
        global loadTextFlag, whatlang, text

        iimage = cv2.imread("DO_NOT_TOUCH_THIS_IMAGE.png")
        gray = cv2.cvtColor(iimage, cv2.COLOR_BGR2GRAY)

        filename = "{}.png".format(len(os.listdir(f'{os.getcwd()}/captured screenshot')))
        checkimage = "DO_NOT_TOUCH_THIS_IMAGE.png"
        cv2.imwrite(checkimage,gray)    

        cv2.imwrite('{}/captured screenshot/{}'.format(os.getcwd(),filename), iimage)

        # 04. PAPAGO API와 Tesseract를 이용해 캡쳐한 이미지 내 언어 텍스트 변환 후 번역하기
        
        text = pytesseract.image_to_string(Image.open('{}/captured screenshot/{}'.format(os.getcwd(),filename)), lang='kor+eng+jpn')
        text.replace(r"\n"," ")
        whatlang = langDetect(text)

        self.asdf2.setPlainText(f"{text}")
        self.asdf2_2.setPlainText("")

        loadTextFlag = 1

    def toKor(self):
        global loadTextFlag, whatlang, text

        if loadTextFlag == 1:
            self.asdf2_2.setPlainText(f"{get_translate(text, whatlang, 'ko')}")
            loadTextFlag = 0
            self.asdf2.setPlainText("")
            #pass
        else:
            self.alert.setPlainText("불러온 텍스트가 없습니다.")

    def toEng(self):
        global loadTextFlag, whatlang, text

        if loadTextFlag == 1:
            self.asdf2_2.setPlainText(f"{get_translate(text, whatlang, 'en')}")
            loadTextFlag = 0
            self.asdf2.setPlainText("")
            #pass
        else:
            self.alert.setPlainText("불러온 텍스트가 없습니다.")
    
    def toJpn(self):
        global loadTextFlag, whatlang, text

        if loadTextFlag == 1:
            self.asdf2_2.setPlainText(f"{get_translate(text, whatlang, 'ja')}")
            loadTextFlag = 0
            self.asdf2.setPlainText("")
            #pass
        else:
            self.alert.setPlainText("불러온 텍스트가 없습니다.")

app = QApplication(sys.argv)

window = MyWindow()
window.show()


app.exec_()


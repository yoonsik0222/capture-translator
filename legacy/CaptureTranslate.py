
# 01. 라이브러리 임포트
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
#import googletrans


filepath = 'C:/Users/yoons/Desktop/Python_files/image capture/DO_NOT_TOUCH_THIS_IMAGE.png'
start = []
end = []

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
        #print(response_body.decode('utf-8'))
    else:
        print("Error Code:" + rescode)


def send_to_clipboard(clip_type, data):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(clip_type, data)
    win32clipboard.CloseClipboard()
    
pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract'

# 02. 이미지 캡쳐 작동 구문
while True:
    fail = 0
    print("Program is working NOW!!!!")
    while True:
        if keyboard.is_pressed("shift"):
            start_T = datetime.now()
            start = pag.position()
            time.sleep(0.2)
            break

    while True:
        now_t = datetime.now()
        if keyboard.is_pressed("shift"):
            if (now_t-start_T).total_seconds() >= 3:
                break
            end = pag.position()
            print("Successfully captured image.") #이미지 캡처 완료시 message send
            time.sleep(0.2)
            break
            
    if (fail == 0) and (start[0] < end[0]) and (start[1] < end[1]):    #왼쪽 위 -> 오른쪽 아래 순으로 위치 설정 하지 않은 경우 거르는 제어    
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
        send_to_clipboard(win32clipboard.CF_DIB, data)  #여기까지가 캡쳐 이미지 사본을 test.png로 저장하는 구문
        
        # 03. 저장된 이미지를 tesseract를 이용해서 읽어들이기
        iimage = cv2.imread("DO_NOT_TOUCH_THIS_IMAGE.png")
        gray = cv2.cvtColor(iimage, cv2.COLOR_BGR2GRAY)

        filename = "{}.png".format(len(os.listdir('C:/Users/yoons/Desktop/Python_files/image capture/captured screenshot')))
        checkimage = "DO_NOT_TOUCH_THIS_IMAGE.png"
        cv2.imwrite(checkimage,gray)    

        cv2.imwrite('C:/Users/yoons/Desktop/Python_files/image capture/captured screenshot/{}'.format(filename), iimage)

        # 04. PAPAGO API와 Tesseract를 이용해 캡쳐한 이미지 내 언어 텍스트 변환 후 번역하기
        
        text = pytesseract.image_to_string(Image.open('C:/Users/yoons/Desktop/Python_files/image capture/captured screenshot/{}'.format(filename)), lang='jpn')
        text.replace(r"\n"," ")
        whatlang = langDetect(text)

        print('인식된 텍스트 : \n{}'.format(text))
        print('인식된 언어 : {}'.format(whatlang))
       
        #translator = googletrans.Translator()
        langselect = input('Which language do u want to see as the result? choose one. (Kor, Eng, Jpn)')

        if langselect == "Kor" or langselect == "KOR" or langselect == "kor":
            #result = translator.translate(text, dest='ko') 
            print()
            print()
            print('번역 결과 : \n')
            print(get_translate(text, whatlang, 'ko'))
            #print (result.text)

        if langselect == "eng" or langselect == "Eng" or langselect == "ENG":
            
            #result = translator.translate(text, dest='en') 
            print()
            print()
            print('번역 결과 : \n')
            print(get_translate(text, whatlang, 'en'))
            #print (result.text)
        
        if langselect == "Jpn" or langselect == 'jpn' or langselect == "JPN":
            
            #result = translator.translate(text, dest='en') 
            print()
            print()
            print('번역 결과 : \n')
            print(get_translate(text, whatlang, 'ja'))
            #print (result.text)
    else:
        print('error: 캡처 순서가 잘못되었습니다. 왼쪽 위 > 오른쪽 아래 순으로 진행해주세요.')
        pass
        
    


#!/usr/bin/python3

"""
This script should give status message on boot then goto logging mode

Free space:
df -h / | tail -n1 | xargs | cut -d" " -f4

using i2c si7021,usb->uart sds011, 4bit-mode jhd162a lcd
relies on adafruit circuitpython libraries

sudo pip3 install adafruit-circuitpython-si7021 RPLCD
sudo raspi-config nonint do_i2c 0


############
Example sketch to connect to PM2.5 sensor with either I2C or UART.
"""
# pylint: disable=unused-import

from RPi import GPIO
from RPLCD.gpio import CharLCD

import time
import subprocess
import blynklib

import aqi_py3_win

import board
import busio
import serial
from digitalio import DigitalInOut, Direction, Pull
import adafruit_si7021



pin_TEMP    =0
pin_HUMIDITY=1
pin_ppm25   =2
pin_ppm10   =3
pin_aqi25   =4
pin_aqi10   =5

lcd = CharLCD(cols=16, rows=2, pin_rs=14, pin_e=15, pins_data=[18, 23, 24, 25], numbering_mode=GPIO.BCM) 
i2c=None
sensor=None
currentValues=None
lcdString=None
blynk = None
ppm25=-1
ppm10=-1
temp=-99
humidity=-1

BLYNK_AUTH = '6pCMihwTj9roRtnn-cxkYJkd23iFXr64'
blynk = blynklib.Blynk(BLYNK_AUTH)
blynk.run()
def updateBlynk(virtualPin,updatedValue, attribute='color'):
    global blynk
    global BLYNK_AUTH
    try:
        if(blynk==None): blynk = blynklib.Blynk(BLYNK_AUTH)
    except:
        print("Failed to login to blynk, check auth key")
        return

    try:
        print("Updating Blynk VPin:%s Attr:%s Value:%s" % (virtualPin,attribute,updatedValue))
        blynk.virtual_write(virtualPin,updatedValue)
        blynk.run()
    except Exception as identifier:
        print("Failed", identifier)

def buildStatusMessageAndDisplay():
    global blynk
    formatString = "T: %0.2f H:%0.2f%% PPM2.5: %0.1f"
    if(not blynk==None): formatString = "T: %0.1f" + chr(223) + "C H:%d%% PPM2.5: %0.1f" # + chr(165)
    updateLCD(formatString % (temp,humidity,ppm25))

def displayDateAndTime(formatTime=r"   %Y-%m-%d       %H:%M:%S"):
    updateLCD(time.strftime(formatTime))
    time.sleep(0.5)

def updateLCD(newString):
    global lcdString
    global lcd
    print("UpdateLCD called with %s" % newString)
    if(newString==lcdString):
        return
    print("Updating LCD from %s to %s" % (lcdString,newString))
    lcdString = newString
    lcd.clear()
    lcd.write_string(lcdString)


def diskSpace():
    process = subprocess.Popen(['df', '-h', '/'],
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE,
                     universal_newlines=True)
    stdout, stderr = process.communicate()
    disk_free = stdout.split('\n')[1].split()[3]
    outString = "Free Space:\n%s" % disk_free
    updateLCD(outString)
    time.sleep(2)

def writeToFile():
    with open("data.csv","a+") as f:
        f.write("\r\n%0.3f,%0.3f,%0.1f,%0.1f,%s" % (temp,humidity,ppm25,ppm10, time.strftime("%Y-%m-%d %H:%M:%S")))

def doPmReading():
    global ppm25
    global ppm10
    ppm25,ppm10 = aqi_py3_win.cmd_query_data()
    aqi25 = calcAQIpm25(ppm25)
    aqi10 = calcAQIpm10(ppm10)
    try:
        print("Updating blynk with PPM 2.5...")
        updateBlynk(pin_ppm25, ppm25)
        print("Updating blynk with PPM 10...")
        updateBlynk(pin_ppm10, ppm10)
        print("Updating blynk with AQI 2.5...")
        updateBlynk(pin_aqi25, aqi25)
        print("Updating blynk with AQI 10...")
        updateBlynk(pin_aqi10, aqi10)
    except Exception as e:
        print("failed to update blynk with ppm")
        print(e)

def doTemperatureHumidityReading():
    global temp
    global humidity
    global sensor
    if(sensor==None):
        print("No Temp/Humidity Sensor!")
        return -1
    time.sleep(1)
    temp=sensor.temperature
    print("Temperature: %0.1f C" % temp)
    humidity=sensor.relative_humidity
    print("Humidity: %0.1f %%" % humidity)
    print("Updating blynk with temperature & humidity")
    updateBlynk(pin_TEMP,temp)
    updateBlynk(pin_HUMIDITY,humidity)

def  calcAQIpm10(pm10):
    pm1 = 0
    pm2 = 54
    pm3 = 154
    pm4 = 254
    pm5 = 354
    pm6 = 424
    pm7 = 504
    pm8 = 604
    aqi1 = 0
    aqi2 = 50
    aqi3 = 100
    aqi4 = 150
    aqi5 = 200
    aqi6 = 300
    aqi7 = 400
    aqi8 = 500
    aqipm10 = 0

    if (pm10 >= pm1 and pm10 <= pm2) :
        aqipm10 = ((aqi2 - aqi1) / (pm2 - pm1)) * (pm10 - pm1) + aqi1
    elif (pm10 >= pm2 and pm10 <= pm3) :
        aqipm10 = ((aqi3 - aqi2) / (pm3 - pm2)) * (pm10 - pm2) + aqi2
    elif (pm10 >= pm3 and pm10 <= pm4) :
        aqipm10 = ((aqi4 - aqi3) / (pm4 - pm3)) * (pm10 - pm3) + aqi3
    elif (pm10 >= pm4 and pm10 <= pm5) :
        aqipm10 = ((aqi5 - aqi4) / (pm5 - pm4)) * (pm10 - pm4) + aqi4
    elif (pm10 >= pm5 and pm10 <= pm6) :
        aqipm10 = ((aqi6 - aqi5) / (pm6 - pm5)) * (pm10 - pm5) + aqi5
    elif (pm10 >= pm6 and pm10 <= pm7): 
        aqipm10 = ((aqi7 - aqi6) / (pm7 - pm6)) * (pm10 - pm6) + aqi6
    elif (pm10 >= pm7 and pm10 <= pm8) :
        aqipm10 = ((aqi8 - aqi7) / (pm8 - pm7)) * (pm10 - pm7) + aqi7
    elif (pm10 > pm8) :
        aqipm10 = 500
    
    return format(aqipm10, ".2f") #.toFixed(0)



    # https://www.airnow.gov/sites/default/files/2020-05/aqi-technical-assistance-document-sept2018.pdf 

def getColor(aqi) :
    color=None
    if (aqi < 50):
        color = "Lime"
    elif (aqi >= 50 and aqi < 100):
        color = "yellow"
    elif (aqi >= 100 and aqi < 150):
        color = "orange"
    elif (aqi >= 150 and aqi < 200):
        color = "red"
    elif (aqi >= 200 and aqi < 300):
        color = "purple"
    elif (aqi >= 300):
        color = "rgb(126,0,35)" #/* was brown, should be maroon, rgb(126,0,35) */
    else:
        color = "black"
    
    return {"bg": color, "text": "white" if (aqi > 200) else "black"} 

def calcAQIpm25(pm25):
    pm1 = 0.0
    pm2 = 12.0
    pm3 = 35.4
    pm4 = 55.4
    pm5 = 150.4
    pm6 = 250.4
    pm7 = 350.4
    pm8 = 500.4

    aqi1 = 0
    aqi2 = 50
    aqi3 = 100
    aqi4 = 150
    aqi5 = 200
    aqi6 = 300
    aqi7 = 400
    aqi8 = 500

    aqipm25 = 0

    if (pm25 >= pm1 and pm25 <= pm2):
        aqipm25 = ((aqi2 - aqi1) / (pm2 - pm1)) * (pm25 - pm1) + aqi1
    elif (pm25 >= pm2 and pm25 <= pm3):
        aqipm25 = ((aqi3 - aqi2) / (pm3 - pm2)) * (pm25 - pm2) + aqi2
    elif (pm25 >= pm3 and pm25 <= pm4):
        aqipm25 = ((aqi4 - aqi3) / (pm4 - pm3)) * (pm25 - pm3) + aqi3
    elif (pm25 >= pm4 and pm25 <= pm5):
        aqipm25 = ((aqi5 - aqi4) / (pm5 - pm4)) * (pm25 - pm4) + aqi4
    elif (pm25 >= pm5 and pm25 <= pm6):
        aqipm25 = ((aqi6 - aqi5) / (pm6 - pm5)) * (pm25 - pm5) + aqi5
    elif (pm25 >= pm6 and pm25 <= pm7):
        aqipm25 = ((aqi7 - aqi6) / (pm7 - pm6)) * (pm25 - pm6) + aqi6
    elif (pm25 >= pm7 and pm25 <= pm8):
        aqipm25 = ((aqi8 - aqi7) / (pm8 - pm7)) * (pm25 - pm7) + aqi7
    elif (pm25 > pm8):
        aqipm25 = 500

    return format(aqipm25, ".2f") #.toFixed(0)

diskSpace()
displayDateAndTime()
try:
    print("Loading Si7021 Temp/Humidity Sensor")
    # Create library object using our Bus I2C port
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_si7021.SI7021(i2c)

    print("Found Si7021 sensor, reading data...")
    doTemperatureHumidityReading()
except Exception as e:
    print("failed to load si7021")
    print(e)

reset_pin = None

try:
    print("Now PPM2.5 sensor, reading data...")
    doPmReading()
except Exception as e:
    print("PM Sensor error", e)


while True:
    displayDateAndTime(r"   %Y-%m-%d   TH< %H:%M:%S")
    doPmReading()
    displayDateAndTime(r"   %Y-%m-%d       %H:%M:%S >PS")
    doTemperatureHumidityReading()
    buildStatusMessageAndDisplay()
    writeToFile()
    if(not blynk==None): blynk.run()
    time.sleep(5)


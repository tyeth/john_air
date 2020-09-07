#!/usr/bin/python3

"""
This script should give status message on boot then goto logging mode

Free space:
df -h / | tail -n1 | xargs | cut -d" " -f4

using i2c si7021,usb->uart sds011, 4bit-mode jhd162a lcd
relies on adafruit circuitpython libraries

sudo pip3 install adafruit-circuitpython-pm25 adafruit-circuitpython-si7021 RPLCD
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

import board
import busio
import serial
from digitalio import DigitalInOut, Direction, Pull
import adafruit_pm25
import adafruit_si7021



pin_TEMP    =0
pin_HUMIDITY=1
pin_ppm25   =3
pin_ppm10   =4
pin_aqi25   =5

lcd = CharLCD(cols=16, rows=2, pin_rs=14, pin_e=15, pins_data=[18, 23, 24, 25], numbering_mode=GPIO.BCM) 
i2c=None
sensor=None
uart=None
pm25=None
currentValues=None
lcdString=None
blynk = None
ppm25=-1
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
    formatString = "T: %0.1f H:%0.1f%% PPM2.5: %0.1f"
    if(not blynk==None): formatString = "T: %0.1f" + chr(223) + "C H:%d%% PPM2.5: %0.1f"
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

def doPmReading():
    global pm25
    global ppm25
    if(pm25==None):
        print("No PM Sensor!")
        return -1
    
    time.sleep(1)

    try:
        aqdata = pm25.read()
        # print(aqdata)
        print()
        print("Concentration Units (standard)")
        print("---------------------------------------")
        print(
            "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
            % (aqdata["pm10 standard"], aqdata["pm25 standard"], aqdata["pm100 standard"])
        )
        print("Concentration Units (environmental)")
        print("---------------------------------------")
        print(
            "PM 1.0: %d\tPM2.5: %d\tPM10: %d"
            % (aqdata["pm10 env"], aqdata["pm25 env"], aqdata["pm100 env"])
        )
        print("---------------------------------------")
        print("Particles > 0.3um / 0.1L air:", aqdata["particles 03um"])
        print("Particles > 0.5um / 0.1L air:", aqdata["particles 05um"])
        print("Particles > 1.0um / 0.1L air:", aqdata["particles 10um"])
        print("Particles > 2.5um / 0.1L air:", aqdata["particles 25um"])
        print("Particles > 5.0um / 0.1L air:", aqdata["particles 50um"])
        print("Particles > 10 um / 0.1L air:", aqdata["particles 100um"])
        print("---------------------------------------")
    except RuntimeError:
        print("Unable to read from sensor, retrying on next round...")

    try:
        print("Updating blynk with PPM...")
        ppm25=aqdata["pm25 standard"]
        aqi25 = calcAQIpm25(ppm25)
        updateBlynk(pin_ppm25, ppm25)
        updateBlynk(pin_aqi25, aqi25)
    except:
        print("failed to update blynk with ppm")

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

    if (pm10 >= pm1 & pm10 <= pm2) :
        aqipm10 = ((aqi2 - aqi1) / (pm2 - pm1)) * (pm10 - pm1) + aqi1
    elif (pm10 >= pm2 & pm10 <= pm3) :
        aqipm10 = ((aqi3 - aqi2) / (pm3 - pm2)) * (pm10 - pm2) + aqi2
    elif (pm10 >= pm3 & pm10 <= pm4) :
        aqipm10 = ((aqi4 - aqi3) / (pm4 - pm3)) * (pm10 - pm3) + aqi3
    elif (pm10 >= pm4 & pm10 <= pm5) :
        aqipm10 = ((aqi5 - aqi4) / (pm5 - pm4)) * (pm10 - pm4) + aqi4
    elif (pm10 >= pm5 & pm10 <= pm6) :
        aqipm10 = ((aqi6 - aqi5) / (pm6 - pm5)) * (pm10 - pm5) + aqi5
    elif (pm10 >= pm6 & pm10 <= pm7): 
        aqipm10 = ((aqi7 - aqi6) / (pm7 - pm6)) * (pm10 - pm6) + aqi6
    elif (pm10 >= pm7 & pm10 <= pm8) :
        aqipm10 = ((aqi8 - aqi7) / (pm8 - pm7)) * (pm10 - pm7) + aqi7
    elif (pm10 > pm8) :
        aqipm10 = 500
    
    return aqipm10.toFixed(0)



    # https://www.airnow.gov/sites/default/files/2020-05/aqi-technical-assistance-document-sept2018.pdf 

def getColor(aqi) :
    color=None
    if (aqi < 50):
        color = "Lime"
    elif (aqi >= 50 & aqi < 100):
        color = "yellow"
    elif (aqi >= 100 & aqi < 150):
        color = "orange"
    elif (aqi >= 150 & aqi < 200):
        color = "red"
    elif (aqi >= 200 & aqi < 300):
        color = "purple"
    elif (aqi >= 300):
        color = "rgb(126,0,35)" #/* was brown, should be maroon, rgb(126,0,35) */
    else:
        color = "black"
    
    return {"bg": color, "text": "white" if (aqi > 200) else "black"} 

def calcAQIpm25(pm25):
    pm1 = 0
    pm2 = 12
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

    if (pm25 >= pm1 & pm25 <= pm2):
        aqipm25 = ((aqi2 - aqi1) / (pm2 - pm1)) * (pm25 - pm1) + aqi1
    elif (pm25 >= pm2 & pm25 <= pm3):
        aqipm25 = ((aqi3 - aqi2) / (pm3 - pm2)) * (pm25 - pm2) + aqi2
    elif (pm25 >= pm3 & pm25 <= pm4):
        aqipm25 = ((aqi4 - aqi3) / (pm4 - pm3)) * (pm25 - pm3) + aqi3
    elif (pm25 >= pm4 & pm25 <= pm5):
        aqipm25 = ((aqi5 - aqi4) / (pm5 - pm4)) * (pm25 - pm4) + aqi4
    elif (pm25 >= pm5 & pm25 <= pm6):
        aqipm25 = ((aqi6 - aqi5) / (pm6 - pm5)) * (pm25 - pm5) + aqi5
    elif (pm25 >= pm6 & pm25 <= pm7):
        aqipm25 = ((aqi7 - aqi6) / (pm7 - pm6)) * (pm25 - pm6) + aqi6
    elif (pm25 >= pm7 & pm25 <= pm8):
        aqipm25 = ((aqi8 - aqi7) / (pm8 - pm7)) * (pm25 - pm7) + aqi7
    elif (pm25 > pm8):
        aqipm25 = 500

    return aqipm25.toFixed(0)

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
    # Connect to a PM2.5 sensor over UART
    uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=0.25)
    pm25 = adafruit_pm25.PM25_UART(uart, reset_pin)

    print("Found PM2.5 sensor, reading data...")
    doPmReading()
except Exception as e:
    print("PM Sensor error", e)


while True:
    displayDateAndTime(r"   %Y-%m-%d   TH< %H:%M:%S")
    doPmReading()
    displayDateAndTime(r"   %Y-%m-%d       %H:%M:%S >PS")
    doTemperatureHumidityReading()
    buildStatusMessageAndDisplay()
    if(not blynk==None): blynk.run()
    time.sleep(5)


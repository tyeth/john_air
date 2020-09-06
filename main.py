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
import time
import subprocess

import board
import busio
import serial
from digitalio import DigitalInOut, Direction, Pull
import adafruit_pm25
import adafruit_si7021


def diskSpace():
    process = subprocess.Popen(['df', '-h', '/'],
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE,
                     universal_newlines=True)
    stdout, stderr = process.communicate()
    disk_free = stdout.split('\n')[1].split()[3]
    print("Free Space:")
    print(disk_free)
    time.sleep(2)

i2c=None
sensor=None
uart=None
pm25=None
currentValues=None
lcdString=None

def doPmReading():
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

def doTemperatureHumidityReading():
    time.sleep(1)
    print("\nTemperature: %0.1f C" % sensor.temperature)
    print("Humidity: %0.1f %%" % sensor.relative_humidity)


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
    time.sleep(0.5)

reset_pin = None

try:
    # Connect to a PM2.5 sensor over UART
    uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=0.25)
    pm25 = adafruit_pm25.PM25_UART(uart, reset_pin)

    print("Found PM2.5 sensor, reading data...")
    doPmReading()
except:
    print("PM Sensor error")


while True:
    doPmReading()
    doTemperatureHumidityReading()
    time.sleep(2)




from machine import Pin
import rp2
import time
import FineOffsetWeatherStation
from FineOffsetWeatherStation import FineOffsetWeatherStationManager
import WifiMqtt
from WifiMqtt import WifiManager, MqttManager
import json


def restart_and_reconnect():
  print('Failed to connect to MQTT broker. Reconnecting...')
  time.sleep(10)
  machine.reset()

led = Pin(25, Pin.OUT)
led.on()

rfpin = Pin(16, Pin.IN)

print("about to connect to..")
try:
    wifi = WifiManager()
    wifi.Connect(led)
    mqtt = MqttManager()
    mqtt.Connect()
except OSError as e:
    restart_and_reconnect()

sm0 = FineOffsetWeatherStation.SetupPIOStateMachine(rfpin)

weatherStation = FineOffsetWeatherStationManager()
loopCounter = 0
led.off()

while (1):
    try:
        receivedWord = sm0.get()	# waits for a 32bit word to be pushed through FIFO from PIO (+- 3ms)
        if weatherStation.ProcessRfPulseWord(receivedWord):
            msg = json.dumps(weatherStation.GetValues())
            mqtt.PublishValues(msg)
            weatherStation.NewValuesAcknowledged()
            
        time.sleep_ms(1)
        loopCounter += 1
        
        if loopCounter & 0x00FF == 0: # Every 256 cycles +- 0.8s
            mqtt.CheckMessage()	# Possibly necessary for Ping
            
        if loopCounter & 0x0FFF == 0: # Every 4096 cycles +- 13s
            if wifi.IsConnected() == False:
                wifi.Connect()
                mqtt.Connect()
            else:
                mqtt.Ping()		# Last Will message was set on connect, KeepAlive=30s therefore Ping the MQTT server at least every 30s*1.5 to prove a good connection.
            
        if loopCounter & 0xFFFF == 0: # Every 65535 cycles +- 0:03:20. When MQTT server restarts if loses this status.
            mqtt.PublishConnected()
            
    except OSError as e:
        restart_and_reconnect()

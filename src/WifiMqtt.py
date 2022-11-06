import machine
import time
import rp2
import network
#https://github.com/danjperron/PicoWMqttDs18b20/blob/main/mqtt_ds18B20.py
from UmqttSimple import MQTTClient
from Secrets import secrets

class WifiManager():
    
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)


    def Connect(self, ledPin):
        self.wlan.active(True)

        #connect using ssid
        self.wlan.connect(secrets['wifi_ssid'],secrets['wifi_pw'])
        while not self.wlan.isconnected():
            time.sleep(0.5)
            machine.idle() # save power while waiting
            #print(self.wlan.status())

        # Wait for connection with 60 second timeout
        timeout = 60
        while timeout > 0:
            if self.wlan.status() < 0 or self.wlan.status() >= 3:
                break
            timeout -= 1
            print('Waiting for connection...')
            ledPin.on()
            time.sleep(0.5)
            ledPin.off()
            time.sleep(0.5)
        
        # Handle connection error
        # Error meanings
        # 0  Link Down
        # 1  Link Join
        # 2  Link NoIp
        # 3  Link Up
        # -1 Link Fail
        # -2 Link NoNet
        # -3 Link BadAuth

        if self.wlan.status() != 3:
            raise RuntimeError('Wi-Fi connection failed')
        else:
            for i in range(self.wlan.status()):
                ledPin.on()
                time.sleep(.1)
                ledPin.off()
                time.sleep(.1)
                
            print('Connected')
            status = self.wlan.ifconfig()
            print('ip = ' + status[0])
    
    def IsConnected(self):
        return self.wlan.isconnected()
    
    
class MqttManager():
    
    def Connect(self):
        self.client = MQTTClient(secrets['mqtt_clientid'],secrets['mqtt_broker'],secrets['mqtt_port'],secrets['mqtt_user'],secrets['mqtt_pw'],keepalive=30)
        self.client.set_last_will(secrets['mqtt_will_topic'], secrets['mqtt_will_message'], retain=False, qos=0)
        print("connecting to MQTT")
        result = self.client.connect()
        print(result)
        self.PublishConnected()
        return self.client

    def PublishConnected(self):
        self.client.publish(secrets['mqtt_will_topic'], secrets['mqtt_online_message'], retain=True, qos=0)
        
    def Publish(self, topic, value):
        self.client.publish(topic, value, retain=False, qos=0)
        
        
    def PublishValues(self, values):
        self.Publish(secrets['mqtt_topic'], values)

    def Ping(self):
        self.client.ping()	# Necessary for Last Will and KeepAlive to work
        
    def CheckMessage(self):
        self.client.check_msg()

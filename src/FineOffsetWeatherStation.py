import machine
from machine import Pin
import rp2
import onewire, ds18x20
#https://github.com/robert-hh/BME280
import bme280_float as bme280

# I use a seperate DS18B20 for inside temperature, as well as a BMP280 sensor for air pressure.
# The BMP280 sensor heats up by 2 degrees C after running a while, this made me decide to use a seperate DS18B20 for temperature readings.

# Fine Offset Electronics WH1080 Weather Station RF433 transmitter
# Also Digitech XC0348
# https://wiki.trixology.com/index.php?title=Fine_Offset
# https://www.sevenwatt.com/main/wh1080-protocol-v2-fsk/
# https://github.com/merbanan/rtl_433/blob/master/src/devices/fineoffset_wh1080.c
# https://forums.raspberrypi.com/viewtopic.php?f=37&t=14777
# Data is transmitted with On Off Keyed Pulse Width modulation:
# 1 is indicated by ~500uS pulse
# 0 is indicated by ~1500us pulse
# gaps between bits are ~1000us
# Preamble = 6x 1 bits
#
# Byte     0  1  2  3  4  5  6  7  8  9
# Nibble  ab cd ef gh ij kl mn op qr st
# 
# bc: device identifier
# def: temp ( (def-400) / 10) Degrees Celcius 
# gh: humidity %
# ij: wind avg (*0.34) m/s
# kl: wind gust (*0.34) m/s
# mnop: rain (*0.2794) mm running total
# q: battery flag
# r: wind direction (*22.5) Degrees
# st: checksum crc8 with poly 0x31

class FineOffsetWeatherStationManager:
    
    
    def __init__(self):
        self.counter = 0
        self.lastPinValue = 0
        self.byteBuffer = 0
        self.bitCounter = 0
        self.byteCounter = 0
        self.messageBuffer = []
        self.lastLowPulseLength = 0
        self.lastHighPulseLength = 0
        self.lastGoLow = 0
        self.lastGoHigh = 0
        self.newValuesAvailable = False
        
        ds_pin =  Pin(17, Pin.IN, Pin.PULL_UP)	# Internal pullup seems to work with DS18B20
        self.ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
        self.roms = self.ds_sensor.scan()
        print('Found DS devices: ', self.roms)
        self.ds_sensor.convert_temp()
  
        i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9))
        # Print out any addresses found
#         devices = i2c.scan()
#         if devices:
#             for d in devices:
#                 print(hex(d))
                
        self.bme = bme280.BME280(mode=bme280.BME280_OSAMPLE_8, i2c=i2c)
        print(self.bme.values)

  
    #https://gist.github.com/Lauszus/6c787a3bc26fea6e842dfb8296ebd630
    def crc_poly(self, data, n, poly, crc=0):
        g = 1 << n | poly  # Generator polynomial

        # Loop over the data
        for d in data:
            # XOR the top byte in the CRC with the input byte
            crc ^= d << (n - 8)
            
            # Loop over all the bits in the byte
            for _ in range(8):
                # Start by shifting the CRC, so we can check for the top bit
                crc <<= 1

                # XOR the CRC if the top bit is 1
                if crc & (1 << n):
                    crc ^= g

        # Return the CRC value
        return crc
   

    def ResetBuffers(self):
        self.byteBuffer = 0
        self.bitCounter = 0
        self.byteCounter = 0
        self.messageBuffer.clear()
        
    def NewValuesAvailable(self):
        return self.newValuesAvailable
    
    def NewValuesAcknowledged(self):
        self.newValuesAvailable = False
    
    def GetValues(self):
        global roms
        
        messageBuffer = self.messageBuffer
        temp = self.ds_sensor.read_temp(self.roms[0])
        self.ds_sensor.convert_temp()
        bmeValues = self.bme.read_compensated_data(result = None)
        pressure = bmeValues[1]/100
        
        return {
            "sensor_id": (messageBuffer[0] & 0x0F << 4) + (messageBuffer[1] & 0xF0 >> 4),
            "humidity": messageBuffer[3],
            "temperature_outside": ((((messageBuffer[1] & 0x0F) << 8) + messageBuffer[2]) - 400) / 10,
            "temperature_inside": temp,
            "baro": pressure,
            "wind_avg": messageBuffer[4] * 0.34,
            "wind_gust": messageBuffer[5] * 0.34,
            "wind_direction": (messageBuffer[8] & 0x0F) * 22.5,
            "rain": ((messageBuffer[6] << 8) + messageBuffer[7]) * 0.2794,
            "battery_flag": messageBuffer[8] >> 4
            }
       
    def CrcSuccess(self):
        msg = self.messageBuffer[0:9]
        calculatedCrc = self.crc_poly(msg, 8, 0x31)	# CRC8 with poly 0x31
        return self.messageBuffer[9] == calculatedCrc
        
    def PrintValues(self):
        values = str(self.GetValues())
        print(values)
        print(self.bme.values)
        

    def CheckForByte(self):
        if self.byteCounter == 0 and self.byteBuffer == 0x3F:	# Preamble found 00111111
            self.bitCounter = 0
            self.byteCounter = 1
            self.byteBuffer = 0
        if self.bitCounter == 8 and self.byteCounter > 0:
            self.byteCounter += 1
            self.bitCounter = 0
            self.messageBuffer.append(self.byteBuffer)
            self.byteBuffer = 0
            
        if self.byteCounter == 11:		# Packet Received
            #self.PrintValues()
            print("Packet received")
            if self.CrcSuccess():
                self.newValuesAvailable = True


    def CheckForBit(self):
        global calcs

        gap = self.lastLowPulseLength
        pulse = self.lastHighPulseLength

        if gap >= 9 and gap <= 11:	# Valid gap = 1ms
            if pulse >= 4 and pulse <= 6:	# Valid 1 bit = 0.5ms pulse
                self.byteBuffer = self.byteBuffer << 1 | 1
                self.bitCounter += 1
                self.CheckForByte()
            elif pulse >= 14 and pulse <= 16:	# Valid 0 bit = 1.5ms pulse
                self.byteBuffer = self.byteBuffer << 1
                self.bitCounter += 1
                self.CheckForByte()
            else:
                self.ResetBuffers()
        else:
            self.ResetBuffers()

                
    def ProcessRfPulseWord(self, word):
        bits = word
        for bitnumber in range(32):
            self.counter += 1
            newPinValue = 0
            if bits & 1 > 0:
                newPinValue = 1
            bits >>= 1
            if newPinValue != self.lastPinValue:
                if newPinValue == 1:
                    self.lastLowPulseLength = self.counter - self.lastGoLow
                    self.lastGoHigh = self.counter
                if newPinValue == 0:
                    self.lastHighPulseLength = self.counter - self.lastGoHigh
                    self.lastGoLow = self.counter
                    self.CheckForBit()
            self.lastPinValue = newPinValue
        return self.NewValuesAvailable()


# At 10kHz, push rfpin value onto ISR, auto push after 32 bits onto sm0 FIFO
@rp2.asm_pio( in_shiftdir=rp2.PIO.SHIFT_RIGHT,autopush=True, push_thresh=32 )
def PIOStorePinValue():
    wrap_target()
    in_(pins,1)		# Get one bit from pins into ISR
    wrap()

def SetupPIOStateMachine(rfpin):
    sm0 = rp2.StateMachine(0, PIOStorePinValue, freq=10000, in_base=rfpin)
    sm0.active(1)
    return sm0
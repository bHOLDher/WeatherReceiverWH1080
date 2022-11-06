# WeatherReceiverWH1080
This is a receiver that decodes the 433Mhz RF data transmitted by the Fine Offset Electronics WH1080 Weather Station sender module every 95 seconds, translates the data and sends it to an MQTT server. It runs MicroPython on a Pi Pico W.

It also has a air pressure sensor and indoor temperature sensor.

# Install
To get it up and running:
- Wire up the sensors according to circuit.png
- Edit the secrets.py file
- Create MQTT sensors in Home Assistant, see examples in HomeAssistantMqttSensors.yaml
- Install Thonny IDE then use it to install MicroPython on the Pi Pico with a USB cable
- Copy all the .py files in the src folder over to the Pi Pico using Thonny
- Reboot the Pi. It is probably best to watch the output in Thonny to confirm it is running.

# Circuit Diagram
![Circuit Diagram](https://github.com/bHOLDher/WeatherReceiverWH1080/blob/main/circuit.png)

# Components
- Pi Pico W or WH
- Fine Offset Electronics WH1080 Weather Station with RF433 transmitter [Fine Offset Weather Stations](https://wiki.trixology.com/index.php?title=Fine_Offset) or [Maplin N96FY Specifications](http://www.thanetweather.co.uk/weather/n96fy.htm)
- RXB6 433MHz RF Receiver
- 433Mhz helical antenna, or make a [DIY coil loaded antenna](https://www.instructables.com/433-MHz-Coil-loaded-antenna/), or a 165mm long straight wire works well too.
- DS18B20 temperature sensor [DS18B20 Tutorial](https://www.circuitbasics.com/raspberry-pi-ds18b20-temperature-sensor-tutorial/)
- 4.7k Resistor
- GY-BMP280 air pressure sensor [BMP 280 Module information](https://components101.com/sensors/gy-bmp280-module)
- USB charger and Micro USB cable to power the Pi Pico or other options

# Notes
Stay away from the RF receivers with an adjustable inductor (model number XY-MK-5V) and rather find a slightly more expensive superheterodyne receiver with a silver capped module and crystal (model number RXB6). The cheaper receivers might work at close range, but they are super sensitive to things like power supply noise and really don't work well. [Choosing a good 433MHz receiver](https://forum.arduino.cc/t/choosing-a-good-433mhz-receiver/946051/25)
Buy a cheap 433MHz helical antenna, or make one that works almost as well: [433 MHz Coil loaded antenna](https://www.instructables.com/433-MHz-Coil-loaded-antenna/). A 16.5cm straight wire works quite well too.

The RF receiver is sold as a 5V sensor but it appears to run perfectly at 3.3V.

The BMP280 sensor has a temperature sensor, but the whole sensor seems to run a little warm, give or take 2 degrees Celcius above ambient, and I did try to run the sensor in forced mode thinking that it would cool down if it is not constantly sampling data. The sleep mode does not appear to cool it down, so I decided to run a seperate temperature sensor, and only use the air pressure from the BMP280. If I switched off the device for 30 minutes, then switched it back on, I could see the temperature reading slowly climb back up by 2 degrees. I also thought it might be picking up heat from the ESP8266 I was using before. Either way, I trust a DS18B20 reading more.

On the BMP280 I pulled pin SDO high, I think I misunderstood a few years ago, this changes the BMP280 address from default 0x76 to 0x77, so I made a code change for this.

The DS18B20 sensor seemed to work without a pullup resistor at first, using the Pi Pico internal pullup resistor but after a while it stopped working, so I added a 4.7k pull up resistor.

# Technical Information on decoding the Weather Station RF transmission
The data is transmitted with On Off Keyed Pulse Width modulation:
- 1 is indicated by ~500µS pulse
- 0 is indicated by ~1500µs pulse
- gaps between bits are ~1000µs
- Preamble = 6x 1 bits

|Byte     |0  |1  |2  |3  |4  |5  |6  |7  |8  |9|
|---|---|---|---|---|---|---|---|---|---|---|
|Nibble  |ab |cd |ef |gh |ij |kl |mn |op |qr |st|

- bc: device identifier
- def: temp ( (def-400) / 10) Degrees Celcius 
- gh: humidity %
- ij: wind speed avg (*0.34) m/s
- kl: wind speed gust (*0.34) m/s
- mnop: rain (*0.2794) mm running total
- q: battery flag, a non zero value indicates a low battery
- r: wind direction (*22.5) Degrees
- st: checksum crc8 with poly 0x31

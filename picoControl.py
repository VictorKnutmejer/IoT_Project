from machine import Pin
import utime as time
from dht import DHT11, InvalidChecksum
from time import sleep

import time                   # Allows use of time.sleep() for delays
from umqtt.simple import MQTTClient   # For use of MQTT protocol to talk to Adafruit IO
import ubinascii              # Conversions between binary data and various encodings
import machine                # Interfaces with hardware components
import micropython            # Needed to run any MicroPython code
import random                 # Random number generator
from machine import Pin       # Define pin

dhtPIN = 15
dhtSensor = DHT11(Pin(dhtPIN, Pin.OUT, Pin.PULL_DOWN))

green = Pin(13, Pin.OUT)
yellow = Pin(14, Pin.OUT)
red = Pin(27, Pin.OUT)
    
# BEGIN SETTINGS
# These need to be change to suit your environment
RANDOMS_INTERVAL = 20000    # milliseconds
last_random_sent_ticks = 0  # milliseconds

# Wireless network
WIFI_SSID = "YOUR WIFI SSID"
WIFI_PASS = "YOUR WIFI PASSWORD" # No this is not our regular password. :)

# Adafruit IO (AIO) configuration
AIO_SERVER = "io.adafruit.com"
AIO_PORT = 1883
AIO_USER = "YOU ADAFRUIT USERNAME"
AIO_KEY = "YOUR ADAFRUIT ACTIVATION KEY"
AIO_CLIENT_ID = ubinascii.hexlify(machine.unique_id())  # Can be anything

AIO_HUMIDITY_FEED = "Knutmaster/feeds/humidity"
AIO_TEMPERATURE_FEED = "Knutmaster/feeds/temperature"
AIO_UPPER_THRESHOLD_ADJUSTER = "Knutmaster/feeds/upper-threshold-adjuster"
AIO_LOWER_THRESHOLD_ADJUSTER = "Knutmaster/feeds/lower-threshold-adjuster"

upper_threshold = 30
lower_threshold = 10

# END SETTINGS



# FUNCTIONS

# Function to connect Pico to the WiFi
def do_connect():
    import network
    from time import sleep
    import machine
    wlan = network.WLAN(network.STA_IF)         # Put modem on Station mode

    if not wlan.isconnected():                  # Check if already connected
        print('connecting to network...')
        wlan.active(True)                       # Activate network interface
        # set power mode to get WiFi power-saving off (if needed)
        wlan.config(pm = 0xa11140)
        wlan.connect(WIFI_SSID, WIFI_PASS)  # Your WiFi Credential
        print('Waiting for connection...', end='')
        # Check if it is connected otherwise wait
        while not wlan.isconnected() and wlan.status() >= 0:
            print('.', end='')
            sleep(1)
    # Print the IP assigned by router
    ip = wlan.ifconfig()[0]
    print('\nConnected on {}'.format(ip))
    return ip 



# Callback Function to respond to messages from Adafruit IO
def sub_cb(topic, msg):
    global upper_threshold
    global lower_threshold
    
    if topic == b'Knutmaster/feeds/upper-threshold-adjuster':
        print("This is new upper_threshold: ", msg)
        upper_threshold = int(msg)
    elif topic == b'Knutmaster/feeds/lower-threshold-adjuster':
        print("This is new lower_threshold: ",msg)
        lower_threshold = int(msg)               
    else:                        # If any other message is received ...
        print("Unknown message", topic) # ... do nothing but output that it happened.

# Function to generate a random number between 0 and the upper_bound
def random_integer(upper_bound):
    return random.getrandbits(32) % upper_bound


def send_humidity_AND_temperature_value(): #SENDS THE HUMIDITY SENSOR DATA TO THE HUMIDITY FEED
    global last_random_sent_ticks
    global RANDOMS_INTERVAL
    global upper_threshold
    global lower_threshold

    if ((time.ticks_ms() - last_random_sent_ticks) < RANDOMS_INTERVAL):
        return; # Too soon since last one sent.
    
    #Set every light off first.
    red.off() 
    yellow.off()
    green.off()
    
    some_number = random_integer(100)
    
    print("Publishing: {0} to {1} ... ".format(some_number, AIO_HUMIDITY_FEED), end='')
    try:
        client.publish(topic=AIO_HUMIDITY_FEED, msg=str(dhtSensor.humidity/100))
        print("")
        print("humidity OK")
        client.publish(topic=AIO_TEMPERATURE_FEED, msg=str(dhtSensor.temperature))
        print("temperature OK")
        print("Hum: {0:.1%}".format(dhtSensor.humidity/100))
        print("Temp: {}°C".format(dhtSensor.temperature))
        
        if int(dhtSensor.temperature) >= int(upper_threshold):
            red.on()
        elif int(dhtSensor.temperature) < int(lower_threshold):
            green.on()
        else:
            yellow.on()
            
    except Exception as e:
        print("FAILED")
    finally:
        last_random_sent_ticks = time.ticks_ms()

# Try WiFi Connection
try:
    ip = do_connect()
except KeyboardInterrupt:
    print("Keyboard interrupt")

# Use the MQTT protocol to connect to Adafruit IO
client = MQTTClient(AIO_CLIENT_ID, AIO_SERVER, AIO_PORT, AIO_USER, AIO_KEY)

# Subscribed messages will be delivered to this callback
client.set_callback(sub_cb)
client.connect()
client.subscribe(AIO_HUMIDITY_FEED)
client.subscribe(AIO_TEMPERATURE_FEED)
client.subscribe(AIO_UPPER_THRESHOLD_ADJUSTER)
client.subscribe(AIO_LOWER_THRESHOLD_ADJUSTER)


print("Connected to %s, subscribed to %s topic" % (AIO_SERVER, AIO_HUMIDITY_FEED))
print("Connected to %s, subscribed to %s topic" % (AIO_SERVER, AIO_TEMPERATURE_FEED))



try:                      # Code between try: and finally: may cause an error
                          # so ensure the client disconnects the server if
                          # that happens.
    while 1:	# Repeat this loop forever
        client.check_msg()# Action a message if one is received. Non-blocking.
        send_humidity_AND_temperature_value()  # Send a random number to Adafruit IO if it's time.
finally:                  # If an exception is thrown ...
    client.disconnect()   # ... disconnect the client and clean up.
    client = None
    print("Disconnected from Adafruit IO.")    

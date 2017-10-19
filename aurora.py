# These exist in micropython and on PC
import gc
import sys

# This is an optional module to handle user specific external notification (e.g. via slack, email, etc)
try:
    import my_notification  # my_notification module needs to contain a notification(message) function (where message is a string)
except:
    pass

# These are platform dependent
try:  # Try to import these (if we are on ESP8266 board)
    from urequests import get
    from ujson import loads
    from utime import sleep
    from utime import sleep_ms
    from machine import Pin
    from neopixel import NeoPixel
    mp = True # We have imported micropython packages so we are running micropython
    pin = Pin(14, Pin.OUT) # Pin 14 is signal for NeoPixel
    heartbeat = Pin(2, Pin.OUT)  # Pin 2 is connected to the blue LED on Wemos board
    np = NeoPixel(pin, 24)
except: # Looks like we failed to import micropython packages on ESP8266 so assume we are running on PC
    mp = False 
    from requests import get
    from json import loads
    from time import sleep
    import gc

### Add a few constants ###
led_red = (32,0,0)
led_green = (0,32,0)
led_blue = (0,0,32)
led_yellow = (32,32,0)
led_magenta = (64,0,64)
led_off = (0,0,0)

data_poll_interval = 60 # Seconds between polling for new data


############## Here we go then #################

def aurora():
  aurora_data = {"kp": 0, "g": 0, "bz": 0, "bt": 0, "bz_gsm": 0, "speed": 0, "density": 0,\
                 "s_g": 0, "s_bz": 0, "s_bt": 0, "s_speed": 0, "s_density": 0,\
                 "last_s_g": 0, "last_s_bz": 0, "last_s_bt": 0, "last_s_speed": 0, "last_s_density": 0,\
                 "timestamp": "Now"}

  spin_the_ring() # just for fun we will spin the LEDs on the ring to show we're starting

  while True:
    gc.collect()
#    print(gc.mem_free())

    if mp == True:
      heartbeat.off() # turn on LED to show we are retrieving data

    # Read the data from the various web urls
    read_data(aurora_data)

    # Scale the data so it is appropriate for the neopixel display
    scale_data(aurora_data)

    # Print the data out to the terminal (mainly just for debugging etc)
    print_data(aurora_data)

    # Show the values on the neopixel ring
    neopixel_display(aurora_data)

    # Send external notifications if necessary
    notifications(aurora_data)

    if mp == True:
        heartbeat.on() # turn off LED to show we are done retrieving data
        sleep(data_poll_interval / 2)
        heartbeat.off() # show that we are still alive
        sleep_ms(100)
        heartbeat.on()
        sleep(data_poll_interval / 2)
    else:
        sleep(data_poll_interval)

# 
def fetch_json(url):
    response = get(url)
    json_data = response.json()
    response.close() # Get doesn't explicitly close stream itself, so doing this to make sure things are nice and clean
    return json_data

def read_data(aurora_data):
    
    try:
      jdata = fetch_json('http://services.swpc.noaa.gov/products/solar-wind/mag-5-minute.json')
      aurora_data['bz_gsm'] = float(jdata[-1][jdata[0].index('bz_gsm')])
    except:
      print('Error getting bz_gsm')
      aurora_data['bz_gsm'] = 0
    try:
      jdata = fetch_json('http://services.swpc.noaa.gov/products/noaa-scales.json')
      aurora_data['g'] = int(jdata['0']['G']['Scale'])
    except:
      print('Error getting g')
      aurora_data['g'] = 0 
    try:
      jdata = fetch_json('http://services.swpc.noaa.gov/products/summary/solar-wind-mag-field.json')
      aurora_data['bz'] = int(jdata['Bz'])
      aurora_data['bt'] = int(jdata['Bt'])
      aurora_data['timestamp'] = jdata['TimeStamp']
    except:
      print('Error getting Bz/Bt')
      aurora_data['bz'] = 0
      aurora_data['bt'] = 0
      aurora_data['timestamp'] = 'Error'
    try:
      jdata = fetch_json('http://services.swpc.noaa.gov/products/noaa-planetary-k-index.json')
      aurora_data['kp'] = int(jdata[-1][jdata[0].index('Kp')])
    except:
      print('Error getting Kp')
      aurora_data['kp'] = 0
    try:
      jdata = fetch_json('http://services.swpc.noaa.gov/products/solar-wind/plasma-5-minute.json')
      aurora_data['density'] = float(jdata[-1][jdata[0].index('density')])
      aurora_data['speed'] = float(jdata[-1][jdata[0].index('speed')])
    except:
      print('Error getting Density/Speed')
      aurora_data['denisty'] = 0
      aurora_data['speed'] = 0
      
    return aurora_data

def scale_data(aurora_data):
    aurora_data['s_g'] = aurora_data['g'] # Don't bother scaling G for now... it is already 0-5

    aurora_data['s_bt'] = scale_and_clip(aurora_data['bt'],0,20,0,5) # Scale Bt from 0-20 to 0-5

    if aurora_data['bz'] > 0:
        aurora_data['s_bz'] = 0
    else:
        aurora_data['s_bz'] = scale_and_clip(abs(aurora_data['bz']),0,20,0,5) # Scale Bz from 0-20 (actually 0 to -20) to 0-5

    aurora_data['s_density'] = scale_and_clip(aurora_data['density'],0,50,0,5) # Scale density from 0-50 to 0-5

    aurora_data['s_speed'] = scale_and_clip(aurora_data['speed'],0,1000,0,5) # Scale speed from 0-1000 to 0-5

# Scale the values to a range we can use for the neopixels
#   returns an int in range minimum to scale
#   e.g. scale_and_clip(600, 0, 1000, 0, 5) = (600/1000)*5 = 3
#        scale_and_clip(600, 300, 1000, 0, 5) = (600/1000)*5 = 2  (int(rnd(1.5))
def scale_and_clip(value, minimum, maximum, scale_min, scale_max):
    scaled_value = int(round((float(value)/float(maximum)) * float(scale_max)))
    if scaled_value > scale_max:
        scaled_value = scale_max
    elif scaled_value < scale_min: # Note that minimum is the minimum output (not input to this function)
        scaled_value = scale_min
    return scaled_value

    
def print_data(aurora_data):
    var = ('Timestamp {} : kp={} g={} bz={} bz_gsm={} bt={} den={} spd={}')\
        .format(aurora_data['timestamp'], aurora_data['kp'], aurora_data['g'], aurora_data['bz'], aurora_data['bz_gsm'], aurora_data['bt'], aurora_data['density'], aurora_data['speed'])
    print('') 
    print(var)
    
    var = ('Scaled Values : Bt={} G={} Bz={} Density={} Speed={}')\
        .format(aurora_data['s_bt'], aurora_data['s_g'], aurora_data['s_bz'], aurora_data['s_density'], aurora_data['s_speed'])
    print(var)


def spin_the_ring():
  # If we are running on micropython then spin the LED's on the ring
  if mp == True:
    np.fill(led_off)
    np.write()
    for i in range(0,24):
        np[i] = led_blue
        if i > 0: 
            np[i-1] = led_green
        if i > 1: 
            np[i-2] = led_red
        if i > 2: 
            np[i-3] = (0,0,0)
        np.write()
        sleep_ms(50)
    np.fill(led_off)
    np.write()

def neopixel_display(aurora_data):
    if mp == True:
        np.fill(led_off)
        np.write()
        for i in range(0,aurora_data['s_g']): # G can go up to 5 but if it does then bt will overwrite the 5th one
            np[i] = led_yellow  # Make G yellow
        for i in range(4,aurora_data['s_bt']+4):
            np[i] = led_red  # Make Bt red
        for i in range(9,aurora_data['s_bz']+9):
            np[i] = led_green  # Make Bz Green
        for i in range(14,aurora_data['s_density']+14):
            np[i] = led_blue  # Make Density Blue
        for i in range(19,aurora_data['s_speed']+19):
            np[i] = led_magenta  # Make Speed Majenta
        np.write()

def notifications(aurora_data):

    #If we haven't imported our own personalised notification module then say so
    if 'my_notification' not in sys.modules:
        print('my_notification module not loaded')
    else:  # If we have then pass it the data so it can do something with it
        my_notification.notification(aurora_data)



# If we are being imported as a module then do nothing
# If we are being run as a script then run
if __name__ == '__main__':
    aurora()
    

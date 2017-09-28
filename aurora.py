try:
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
except:
    mp = False # Looks like we failed to import micropython packages so we aren't on micropython
    from requests import get
    from json import loads
    from time import sleep

# Later on we can use mp to decide whether to try and talk to neopixels etc or just show values on screen

# Need some dictionaries or something to store the data in
# Need to define some things better such as number of pixels, colours, urls etc
#
# def read_data()
# def scale_data()
# def show_data()
   
def aurora():
  kp, bz, bz_gsm, bt, g, density, speed = 0,0,0,0,0,0,0
  timestamp = 'none'
  print('in aurora function and about to run aurora')
  
  if mp == True:
    np.fill((0,0,0))
    for i in range(0,24):
        np[i] = (0,0,32)
        if i > 0: 
            np[i-1] = (0,32,0)
        if i > 1: 
            np[i-2] = (32,0,0)
        if i > 2: 
            np[i-3] = (0,0,0)
        np.write()
        sleep_ms(50)
    np.fill((0,0,0))

  while True:
    if mp == True:
      heartbeat.off() # turn on LED to show we are retrieving data
      
    try:
      jdata = loads(get('http://services.swpc.noaa.gov/products/solar-wind/mag-5-minute.json').text)
      bz_gsm = float(jdata[-1][jdata[0].index('bz_gsm')])
    except:
      print('Error getting bz_gsm')
    try:
      jdata = loads(get('http://services.swpc.noaa.gov/products/noaa-scales.json').text)
      g = int(jdata['0']['G']['Scale'])
    except:
      print('Error getting g')
    try:
      jdata = loads(get('http://services.swpc.noaa.gov/products/summary/solar-wind-mag-field.json').text)
      bz = int(jdata['Bz'])
      bt = int(jdata['Bt'])
      timestamp = jdata['TimeStamp']
    except:
      print('Error getting Bz/Bt')
    try:
      jdata = loads(get('http://services.swpc.noaa.gov/products/noaa-planetary-k-index.json').text)
      kp = int(jdata[-1][jdata[0].index('Kp')])
    except:
      print('Error getting Kp')
    try:
      jdata = loads(get('http://services.swpc.noaa.gov/products/solar-wind/plasma-5-minute.json').text)
      density = float(jdata[-1][jdata[0].index('density')])
      speed = float(jdata[-1][jdata[0].index('speed')])
    except:
      print('Error getting Density/Speed')

    print('')
    print(timestamp)
    print('kp=',kp, ' g=',g,' bz=',bz, ' bz_gsm=',bz_gsm, ' bt=',bt, ' den=',density, 'spd=',speed)

    s_g = g # Don't bother scaling G for now... it is already 0-5
    print('G ', s_g)

    s_bt = ScaleClip(bt,0,20,5) # Scale Bt from 0-20 to 0-5
    print('Bt ', s_bt)

    if bz > 0:
        s_bz = 0
        print('Bz Positive') # We don't care about +ve Bz so much
    else:
        s_bz = ScaleClip(abs(bz),0,20,5) # Scale Bz from 0-20 (actually 0 to -20) to 0-5
        print('Bz ', s_bz)

    s_density = ScaleClip(density,0,50,5) # Scale density from 0-50 to 0-5
    print('Density ', s_density)

    s_speed = ScaleClip(speed,0,1000,5) # Scale speed from 0-1000 to 0-5
    print('Speed ', s_speed)

    if mp == True:
        np.fill((0,0,0))
        for i in range(0,s_g): # G can go up to 5 but if it does then bt will overwrite the 5th one
            np[i] = (64,64,0)  # Make G yellow
        for i in range(4,s_bt+4):
            np[i] = (64,0,0)  # Make Bt red
        for i in range(9,s_bz+9):
            np[i] = (0,64,0)  # Make Bz Green
        for i in range(14,s_density+14):
            np[i] = (0,0,64)  # Make Density Blue
        for i in range(19,s_speed+19):
            np[i] = (64,0,64)  # Make Speed Majenta
        np.write()

    if mp == True:
        heartbeat.on() # turn off LED to show we are done retrieving data
        sleep(30)
        heartbeat.off() # show that we are still alive
        sleep_ms(100)
        heartbeat.on()
        sleep(30)
    else:
        sleep(60)

# Scale the values in to a range we can use for the neopixels
def ScaleClip(value, minimum, maximum, scale):
    newval = int(round((float(value)/float(maximum)) * float(scale)))
    if newval > maximum:
        newval = maximum
    elif newval < minimum:
        newval = minimum
    return newval
    
if __name__ == '__main__':
    print('in aurora module and about to run aurora... shouldnt see this')
    Aurora()
    
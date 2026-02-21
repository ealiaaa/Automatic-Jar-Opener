import time, sys
from gpiozero import Motor,  LED
from sensor_library import Force_Sensing_Resistor # recommended to import *

TICK_PERIOD:int = 0.1 #controls how often the program iterates. also used outide func tick in func readyStart for the sensor read period
AYYYYYWHAT:int = 50
REQUIRED_HANDLE_FORCE:int = 50 # required sustained grip value to detect grip on handle
SAMPLE_WINDOW_LEN:int = 10  # number of samples per window (~0.1s rn)

MaxAcceptableVariation:int = 1
SlipConfirmThreshold:int = 3     # num of slips that need to happen in a row to confirm that hey its actually slipping

consecutiveSlips:int = 0 # tracks number of slips in a row *across functions*
timeGrabbed:int = 0 # total time rotated for motorTighten, stanrdized to speed 1. collected in func jarGrabbed 
timeTwisted:int = 0 # total time rotated for motorOpen, stanrdized to speed 1. collected in func twist
# both of the above used in func dropProgram to return all motors to initial position
consecutiveGripValuesFailed = 0 # stores number of grip values below REQUIRED_HANDLE_FORCE *across functions*
sensor2Recent:list = [] # buffers to store recent force values to calculate variation and slip
# sensor3Recent = [] # probably unused in final version

# ALERT I've search replaced all rackPosition for 'timeRotate' without a d.
# I've yet to properly rename them tho, ill add that and the variable speeds soon.
# NOTE add graudal torque increase and decreases to ease adjustment and lower wrist injury chance
# add leds

sensorTop = Force_Sensing_Resistor(0)
sensor1 = Force_Sensing_Resistor(1)
sensor2 = Force_Sensing_Resistor(2)
# sensor3 = Force_Sensing_Resistor(3) # probably unused in final version

motorTighten = Motor(forward = 16, backward=20)
motorOpen = Motor(forward=1, backward = 7)

red = LED(26)
green = LED(19)


def rollingAverage():
    pass


def readSensor(sensor):
    return sensor.force_raw()


def forceAverage12():
    return (readSensor(sensor1) + readSensor(sensor2) ) /2 # removed  + readSensor(sensor3) as we probably only have 2 bottom sensors


def readyStart ():
    while True:
        heldCounter = 0
        while readSensor(sensorTop) > REQUIRED_HANDLE_FORCE:
            heldCounter += 1
            time.sleep(TICK_PERIOD)
            if heldCounter >= 5:           # if held down for more than 4 seconds
                print("Starting lid grip sequence")
                return

# merge ready start and letGo

def letGo ():
    global consecutiveGripValuesFailed

    if readSensor(sensorTop) < REQUIRED_HANDLE_FORCE:
        consecutiveGripValuesFailed += 1
        if consecutiveGripValuesFailed >= 5: 
            return True
        else:
            return False
# 5 because 1 would be susceptible to sensor variations, but -> 5 (half a second of sensor time when considering TICK_PERIOD) ->
# is still short enough to allow for quick recognition of handle release
    else:
        consecutiveGripValuesFailed = 0
        return False


def jarGrabbed(grabSpeed:int, gripTo:int):   # 150 and 200!
    global timeGrabbed

    if forceAverage12() < gripTo : # 150 is the initial, slower and weaker jar grip speed
        motorTighten.forward(grabSpeed)
        time.sleep(0.1)
        motorTighten.stop()
        timeRotated += 0.1*grabSpeed
        return False
    return True


def twist(twistSpeed:int):
    global timeTwisted

    motorOpen.forward(twistSpeed)
    time.sleep(0.1)
    motorTighten.stop()
    timeTwisted += 0.1*twistSpeed

    if timeTwisted > 9: # 9 is the currect ESTIMATE of how long itll take t
        print("Lid sucessfully opened: Retracting arms to initial position and dropping lid.")
        return True
    return False


def dropProgram():
    pass
   # motorTighten.turn(-timeRotate)
   # completely open racks back to their initial, retracted timeRotate
    # CONVERT timeRotate to a meaningful amount of revolutions for the down motor to spin to bring the racks back
    # BE CAREFUL. THIS CAN STRIP THE GEARS and that would be annoying


def variation(data):
    total = 0
    average = sum(data) / len(data)

    for reading in data:
        deviation = reading - average
        total += (deviation) ** 2

    averageVariation = total/len(data)

    return averageVariation
'''
**2 makes sure that a positive and a negative deviation don't cancel each other out
abs() could also do that but **2 or **4 or a bigger number also strongly penalizes sudden spikes
so if it slips, the variation is suddenly super massive, making it more obvious
'''


def slipDetect ():
    global consecutiveSlips

    sensor1Recent.append( readSensor(sensor1) )
    sensor2Recent.append( readSensor(sensor2) )
    sensor3Recent.append( readSensor(sensor3) )

    # make sure all the 3 sensors come online and have real values at the same time
    # would be bad if one added nothing or "None" to a list instead of an integer
    # or if list 2 has more entries than list 3 or something

    if len(sensor1Recent) > SAMPLE_WINDOW_LEN:
        sensor1Recent.pop(0)
        sensor2Recent.pop(0)
        sensor3Recent.pop(0)

    if len(sensor1Recent) < SAMPLE_WINDOW_LEN:
        return False


    variation1 = variation(sensor1Recent)
    variation2 = variation(sensor2Recent)
    variation3 = variation(sensor3Recent)
    variationMax = max(variation1, variation2, variation3)

    if variationMax > MaxAcceptableVariation:
        consecutiveSlips += 1
    else:
        consecutiveSlips = 0


    if consecutiveSlips >= SlipConfirmThreshold:
        return True

    return False



def tick():
    if slipDetect():
        if jarGrabbed(1,200):
            if twist(1):
                return True
            else:
                return letGo()
    else:
        if jarGrabbed(0.5,150):
            if twist(0.5):
                return True
            else:
                return letGo()

    return letGo()

def main():
    print("Waiting for user to grip...")
    readyStart()  # waits until it detects user holding handle for more than 0.5s in a row

    opened = False
    while not opened:
        opened = tick()  # returns True for the program to exit
        time.sleep(TICK_DELAY)



try:
    main()

finally:
    dropProgram()
    print("Program done\nRetracting to original position.")
import time, sys
from gpiozero import Motor,  LED
from sensor_library import Force_Sensing_Resistor


'''
Constants
'''
TICK_PERIOD = 0.05 # 20 times per second

#controls how often the program iterates. also used outide func tick in func readyStart for the sensor read period

REQUIRED_HANDLE_FORCE = 100 # required sustained grip value to detect grip on handle
SAMPLE_WINDOW_LEN = 10  # number of samples per window (~0.5s to collect)
MAX_ACCEPTABLE_VARIATION = 1
'''
Variables
'''
# i have realized far too late that a class tracking the states would be better than almost 20 global variables

grabStartTime = None
twistStartTime = None # used in twist and jarGrabbed with time.monotonic() to calculate exaclty how long the motors have been rotating for.

timeGrabbed = 0 # total time rotated for motorGrab, stanrdized to speed 1.
timeTwisted = 0 # total time rotated for motorTwist, stanrdized to speed 1. 
# both of the above used in func dropProgram to return all motors to initial position

triedGrab = 0
triedTwist = 0 # used to communicate to func printStatuses what the motors are doing

redState = "OFF"
greenState = "OFF" # used to communicate to func printStatus whether the LEDs are OFF, ON or Flashing.

grabSpeed = 0.5 # motor speed between 0 and 1
grabTo = 150 # raw force value between 0 and 255
twistSpeed = 0.5 # motor speed between 0 and 1
# assignment of above 3 taken over quickly by slipDetect
rollingAverage = 0
consecutiveGripValuesFailed = 0 # stores number of grip values below REQUIRED_HANDLE_FORCE *across functions*

sensor1RecentVar = []
sensor2RecentVar = [] # buffers to store recent force values to calculate rolling variation and slip
sensor1RecentAvg = []
sensor2RecentAvg = [] # buffers to store recent force values to calculate rolling average
'''
rolling average and rolling variation would be cleaner to break into 2 functions and a helper/collector
function that takes the rolling list, and the other 2 functions do the arithmetic,
but the project specifically requests rolling average to be its own entire function 
'''

'''
Initialize force sensors, motors and LEDs
'''
sensor1 = Force_Sensing_Resistor(1)
sensor2 = Force_Sensing_Resistor(2)
sensor3 = Force_Sensing_Resistor(3)


motorGrab = Motor(forward = 16, backward=20)
motorTwist = Motor(forward=1, backward = 7)

red = LED(26)
green = LED(19)

'''
Sensor-based and helper Functions
'''

def readSensor(sensor): #returns raw sensor value of passed sensor when called
    return sensor.force_raw()


def readyStart (): # waits infinity until topSensor detects hand for more than 0.5 seconds
    while True:
        heldCounter = 0
        while readSensor(sensor1) > REQUIRED_HANDLE_FORCE:
            heldCounter += 1
            time.sleep(TICK_PERIOD)
            if heldCounter >= 10:
                print("Starting lid grip sequence")
                return


def printStatuses():
    print(f"---znTop Force Sensor: {readSensor(sensor1)}\tJar Force Sensor1: {readSensor(sensor2)}\tJar Force Sensor2:  {readSensor(sensor3)}\nRed LED: {redState}\tGreen LED: {greenState}\tGrabbing Motor Speed: {triedGrab}\tTwisting Motor Speed: {triedTwist}")


def dropProgram(motor, duration): # reverses motors back to initial positions
    motor.backward(1)
    time.sleep(duration)
    motor.stop()

def checkSensors(): # checks all the sensors, other functions refer to the values read here.
    global topSensor
    global bottomSensor1
    global bottomSensor2
    topSensor = readSensor(sensor1)
    bottomSensor1 = readSensor(sensor2)
    bottomSensor2 = readSensor(sensor3)
    


def variation(data): # helper function to func slipDetect. returns average of amplified variation of each list item from list average
    total = 0
    average = sum(data) / len(data)

    for reading in data:
        deviation = reading - average
        total += (deviation) ** 2

    averageVariation = total/len(data)

    return averageVariation
'''
**2 makes sure that a positive and a negative deviation don't cancel each other out
abs() could also do that but **2 or **4 or a bigger number also amplifies smaller variations, making them easier to detect
'''

def rollingForceAverage12(): #rolling average of bottom 2 force sensors
    global rollingAverage
    sensor1RecentAvg.append( bottomSensor1 )
    sensor2RecentAvg.append( bottomSensor2 )

    if len(sensor1RecentAvg) > SAMPLE_WINDOW_LEN:
        sensor1RecentAvg.pop(0)
        sensor2RecentAvg.pop(0)

    if len(sensor1RecentAvg) < SAMPLE_WINDOW_LEN:
        return # function returns None if datapoints available is less than n
    avg1 = sum(sensor1RecentAvg) / len(sensor1RecentAvg)
    avg2 = sum(sensor2RecentAvg) / len(sensor2RecentAvg)
    
    rollingAverage = (avg1+avg2)/2 # used in jarGrabbed
'''
I would like to break slipDetect and rollingForceAverage12 into 1 function to collect the rolling window, and 2 functinos to process them
but the rubric specifically wants the rolling Average to be ONE functions only.
'''

def slipDetect (): #calculates rolling **variation** of bottom 2 sensors, determines if excess variation is indicative of slippage
    global grabSpeed
    global grabTo
    global twistSpeed

    sensor1RecentVar.append( bottomSensor1 )
    sensor2RecentVar.append( bottomSensor2 )

    if len(sensor1RecentVar) > SAMPLE_WINDOW_LEN:
        sensor1RecentVar.pop(0)
        sensor2RecentVar.pop(0)

    if len(sensor1RecentVar) < SAMPLE_WINDOW_LEN:
        return # Not enough data, return None
    

    variation1 = variation(sensor1RecentVar)
    variation2 = variation(sensor2RecentVar)
    variationMax = max(variation1, variation2)

    if variationMax > MAX_ACCEPTABLE_VARIATION:
        grabSpeed = 0.4
        grabTo = 200
        twistSpeed = 0.4
##        print("SLIPPING")
    else:
        grabSpeed = 0.1
        grabTo = 150
        twistSpeed = 0.1
##        print("NOT slipping")

def shouldAbort (): # exits straight to finally clause if user lets go of handle for more than 5 times in a row
    global consecutiveGripValuesFailed
    if topSensor < REQUIRED_HANDLE_FORCE:
        consecutiveGripValuesFailed += 1
        if consecutiveGripValuesFailed >= 10:
            raise SystemExit
        else:
            return
# 5 because 1 would be susceptible to sensor variations, but 7 is still short enough to allow for quick recognition of handle release
    else:
        consecutiveGripValuesFailed = 0
        return


def sensorTick():
    checkSensors()

    slipDetect()
    rollingForceAverage12()
    shouldAbort()

'''
Motor-based functions
'''

def jarGrabbed(grabSpeed, grabTo): # tightens grabbing belt until grabTo value, returns if grabTo Value reached yet or not
    global triedGrab
    global grabStartTime
    global rollingAverage

    if rollingAverage < grabTo:
        motorGrab.forward(grabSpeed)
        triedGrab = grabSpeed

        if grabStartTime == None:
            grabStartTime = time.monotonic()
            # initializes time.monotonic to calculate exactly how long the motor has been twisting in case of tick desync     
        return False
    
    else:
        return True


def twist(twistSpeed):
    global triedTwist
    global timeTwisted
    global twistStartTime

    motorTwist.forward(twistSpeed)
    triedTwist = twistSpeed

    if twistStartTime == None:
        twistStartTime = time.monotonic()
        #initializes time.monotonic to calculate exactly how long the motor has been twisting in case of tick desync


    if timeTwisted > 9:
        print("Lid successfully opened")
        return True

    return False


def motorTick():
    global redState
    if not jarGrabbed(grabSpeed, grabTo):
        red.off() # flashes red when only trying to grip the lid
        redState = "Flashing"
        return False
    
    if twist(twistSpeed):
        return True

    red.on()
    redState = "ON"
    return False



def main():
    global triedGrab
    global twistStartTime
    global triedTwist
    global grabStartTime
    global timeGrabbed
    global timeTwisted
    global greenState
    tickCounter = 0

    print("Waiting for user to grip...")
    green.on()
    greenState = "ON"

    readyStart()  # waits until it detects user holding handle for more than 0.5s in a row
    
    greenState = "Flashing"
    
    next_tick = time.monotonic() # sets next_tick to a set large, steadily increasing number that is INDEPENDANT of compute time.
    
    opened = False
    while not opened:
        next_tick += TICK_PERIOD
        tickCounter += 1

        sensorTick()
        
        if tickCounter == 20: # every 20 ticks, will trigger print function ( once every second)
            printStatuses()
            triedGrab = 0
            triedTwist = 0
        if tickCounter % 5 == 0 and tickCounter != 0: # every 5 ticks will trigger motors to update their condition (motors cant on/off faster than 0.1 s)
            motorGrab.stop()
            motorTwist.stop()
            if twistStartTime != None:
                timeTwisted += (time.monotonic() - twistStartTime)*triedTwist
                twistStartTime = None 
            if grabStartTime != None:
                timeGrabbed += (time.monotonic() - grabStartTime)*triedGrab
                grabStartTime = None
            # subtracts now from time motor started twisting, mutiplies by the speed to accumulate time rotating standardized to speed 1 only.

            green.on()
            opened = motorTick()  # will return True for the program to exit (should abort will exit direcctly with exit())

        if tickCounter % 10 == 0 and tickCounter != 0:
            green.off() # flashes green every 0.1 seconds while program running, green turns on in line 258
            red.on() # solid red only when motorTick is trying to twist the lid
        if tickCounter >= 20: # resets tickCounter
            tickCounter = 0
 
        sleep_time = next_tick-time.monotonic() # calculates how long to sleep for to keep tick rates consistent considering compute time
        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            print("tick went over")
            
        
        


try:
    main()
finally:
    green.on()
    red.on()
    greenState = redState = "ON"
    motorGrab.stop()
    motorTwist.stop()

    if twistStartTime != None: #finalizes timeTwisted and timeGrabbed for dropProgram
        timeTwisted += (time.monotonic() - twistStartTime)*triedTwist
        twistStartTime = None
    if grabStartTime != None:
        timeGrabbed += (time.monotonic() - grabStartTime)*triedGrab
        grabStartTime = None

    print("Retracting Twisting motor to original position")
    dropProgram(motorTwist, timeTwisted)
    print("Retracting Grabbing motor to original position")
    dropProgram(motorGrab,timeGrabbed)
    print("Program done")
    green.off()
    red.off()
    greenState = "OFF"
    redState = "OFF"
    printStatuses()
    print(timeGrabbed,timeTwisted)


'''
Ideas for a final product

Consider the Following:
-    NOT having a billion global variables? its kinda hard to keep track of them in my head?

-   a graudal torque increases and decreases to ease adjustment and lower wrist injury chance

-   something like grabSpeed = f(variationMax), making the tighteness directly responsive to slippage, rather than being
just 2 binary 'soft grip' and 'hard grip' states

-   adding hysteresis to slipdetect to prevent rapidly oscillating states
'''


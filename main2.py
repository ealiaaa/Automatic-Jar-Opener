import time, sys
from gpiozero import Motor,  LED
from sensor_library import Force_Sensing_Resistor # recommended to import *

'''
Constants
'''
TICK_PERIOD = 0.01 
'''
controls how often the program iterates. also used outide func tick in func readyStart for the sensor read period

but 0.1 isnt fast enough to calculate real-time slippage at a reasonable rate, and the motors can't turn on and off faster than that
'''
###############SENSOR_FREQUENCY = 10 
'''
to solve this, each tick is subdivided into 10 subticks for the rolling lists for average and average variation ->
to be completed refreshed every tick
'''
REQUIRED_HANDLE_FORCE = 50 # required sustained grip value to detect grip on handle
SAMPLE_WINDOW_LEN = 10  # number of samples per window (~0.1s rn)
MAX_ACCEPTABLE_VARIATION = 1  
# num of slips that need to happen in a row to confirm that it's *actually* slipping and not a sensor fluke

'''
Variables
'''

timeGrabbed = 0 # total time rotated for motorGrab, stanrdized to speed 1. collected in func jarGrabbed 
timeTwisted = 0 # total time rotated for motorTwist, stanrdized to speed 1. collected in func twist
# both of the above used in func dropProgram to return all motors to initial position
triedGrab = 0
triedTwist = 0 # FLAGS used in func tick to communicate to func printStatuses what motors where used
grabSpeed = 0.5 # motor speed between 0 and 1
grabTo = 150 # raw force value between 0 and 255
twistSpeed = 0.5 # motor speed between 0 and 1
# above three only initialized here to not crash, assignment taken over quickly by slipDetect
rollingAverage = 0
consecutiveGripValuesFailed = 0 # stores number of grip values below REQUIRED_HANDLE_FORCE *across functions*
sensor1RecentVar = []
sensor2RecentVar = [] # buffers to store recent force values to calculate rolling variation and slip
sensor1RecentAvg = []
sensor2RecentAvg = [] # buffers to store recent force values to calculate rolling average
'''
rolling average and rolling variation would be cleaner to break into 2 functions and a helper function that takes the rolling list
but the project specifically requests rolling average to be its own entire function 
'''
'''
TODO
PERHAPS 


- check consecutiveSlips necessity with william?
    - i dont think that would even trigger ngl it also depends on the material of the grabby belt, also ->
    - theres just so many variables, its gonna be hard to find a good estimate for that value
        - maybe we can include it and set it to 1 ->
        - so functionally it does nothing but its good for code complexity and its a good idea for a final product
        - to revert back to the old, remove everything between ##########(10#), and uncomment all #####(5#) (replace ##### with blank)


'''

'''
Initialize force sensors, motors and LEDs
'''
sensorTop = Force_Sensing_Resistor(0)
sensor1 = Force_Sensing_Resistor(1)
sensor2 = Force_Sensing_Resistor(2)


motorGrab = Motor(forward = 16, backward=20)
motorTwist = Motor(forward=1, backward = 7)

red = LED(26)
green = LED(19)

'''
Function Definitions 
'''

def readSensor(sensor): #returns raw sensor value of passed sensor when called, delay is implemented in func tick()
    return sensor.force_raw()


def readyStart (): # waits infinity until topSensor detects hand for more than 0.5 seconds
    while True:
        heldCounter = 0
        while readSensor(sensorTop) > REQUIRED_HANDLE_FORCE:
            heldCounter += 1
            time.sleep(TICK_PERIOD)
            if heldCounter >= 5:
                print("Starting lid grip sequence")
                return


def shouldAbort (): # exits straight to finally clause if user lets go of handle for more than 5 times in a row
    global consecutiveGripValuesFailed

    if readSensor(sensorTop) < REQUIRED_HANDLE_FORCE:
        consecutiveGripValuesFailed += 1
        if consecutiveGripValuesFailed >= 7: 
            raise SystemExit
        else:
            return
# 5 because 1 would be susceptible to sensor variations, but 7 is still short enough to allow for quick recognition of handle release
    else:
        consecutiveGripValuesFailed = 0
        return


def jarGrabbed(grabSpeed, grabTo): # tightens grabbing belt until grabTo value, returns if grabTo Value reached yet or not
    global timeGrabbed
    global triedGrab

    if rollingAverage < grabTo:
        motorGrab.forward(grabSpeed)
        timeGrabbed += TICK_PERIOD*grabSpeed
        triedGrab = grabSpeed
        return False
    return True


def twist(twistSpeed): # twists entire jar lid grip mechanism open and returns whether lid is open or not
    global timeTwisted
    global triedTwist

    motorTwist.forward(twistSpeed)
    timeTwisted += TICK_PERIOD*twistSpeed
    triedTwist = twistSpeed

    if timeTwisted > 9: # 9 is the currect ESTIMATE of how long itll take t
        print("Lid sucessfully opened")
        return True
    return False

def printStatuses():
    print("---")
    print(f"Top Force Sensor: {readSensor(sensorTop)}\tJar Force Sensor1: {readSensor(sensor1)}\tJar Force Sensor2:  {readSensor(sensor2)}")
    print(f"Red LED: \nGreen LED: \tGrabbing Motor Speed: {triedGrab}\tTwisting Motor Speed: {triedTwist}")


def dropProgram(motor, duration): # reverses motors back to initial positions exactly
    motor.backward(1)
    time.sleep(duration)
    motor.stop()


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
    global rollingAverage # used to communicate with jarGrabbed to enable motor and sensor call isolation

    sensor1RecentAvg.append( readSensor(sensor1) )
    sensor2RecentAvg.append( readSensor(sensor2) )

    if len(sensor1RecentAvg) > SAMPLE_WINDOW_LEN:
        sensor1RecentAvg.pop(0)
        sensor2RecentAvg.pop(0)

    if len(sensor1RecentAvg) < SAMPLE_WINDOW_LEN:
        return # function returns None if datapoints available is less than n
    avg1 = sum(sensor1RecentAvg) / len(sensor1RecentAvg)
    avg2 = sum(sensor2RecentAvg) / len(sensor2RecentAvg)
    
    rollingAverage = (avg1+avg2)/2
'''
i would love to break slipDetect and rollingForceAverage12 into 1 function to collect the rolling window, and 2 functinos to process them
but the rubric specifically wants the rolling Average to be ONE functions only.
'''

def slipDetect (): #calculates rolling **variation** of bottom 2 sensors, determines if excess variation is indicative of slippage
    global grabSpeed
    global grabTo
    global twistSpeed

    sensor1RecentVar.append( readSensor(sensor1) )
    sensor2RecentVar.append( readSensor(sensor2) )

    if len(sensor1RecentVar) > SAMPLE_WINDOW_LEN:
        sensor1RecentVar.pop(0)
        sensor2RecentVar.pop(0)

    if len(sensor1RecentVar) < SAMPLE_WINDOW_LEN:
        return # Not enough data, return None
    

    variation1 = variation(sensor1RecentVar)
    variation2 = variation(sensor2RecentVar)
    variationMax = max(variation1, variation2)

    if variationMax > MAX_ACCEPTABLE_VARIATION:
        grabSpeed = 0.5
        grabTo = 150
        twistSpeed = 0
    else:
        grabSpeed = 1
        grabTo = 200
        twistSpeed = 1


def sensorTick():
    slipDetect()
    rollingForceAverage12()
    shouldAbort()


def motorTick():
    if not jarGrabbed(grabSpeed, grabTo):
        red.off() # flashes red when only trying to grip the lid
        return False
    
    if twist(twistSpeed):
        return True
    red.on()
    return False


def main():
    global triedGrab
    global triedTwist
    tickCounter = 0

    print("Waiting for user to grip...")
    green.on()
    readyStart()  # waits until it detects user holding handle for more than 0.5s in a row

    next_tick = time.monotonic() # sets next_tick to a set large, steadily increasing number that is INDEPENDANT of compute time.
    opened = False
    while not opened:
        next_tick += TICK_PERIOD
        
        sensorTick()
        
        if tickCounter == 50: # every 50 ticks, will trigger print function ( once every 0.5 seconds)
            printStatuses()
            triedGrab = 0
            triedTwist = 0
            tickCounter = 0
        if tickCounter % 10 == 0 and tickCounter != 0: # every 10 ticks will trigger motors to update their condition (motors cant on/off faster than 0.1 s)
            motorGrab.stop()
            motorTwist.stop()
            green.on()
            opened = motorTick()  # will return True for the program to exit (should abort will exit direcctly with exit())
        if tickCounter % 20 == 0 and tickCounter != 0:
            green.off() # flashes green every 0.1 seconds while program running, green turns on in line 258
            red.on() # solid red only when motorTick is trying to twist the lid
        if tickCounter >= 100: # resets tickCounter every second (100 ticks)
            tickCounter = 0
        
        tickCounter += 1
        
        sleep_time = next_tick-time.monotonic() # calculates how long to sleep for to keep tick rates exactly consistent considering compute time
        if sleep_time > 0:
            time.sleep(sleep_time)

        green.on()
        


try:
    main()
finally:
    green.on()
    red.on()
    print("Retracting Twisting motor to original position")
    dropProgram(motorTwist, timeTwisted)
    print("Retracting Grabbing motor to original position")
    dropProgram(motorGrab,timeGrabbed)
    print("Program done")
    green.off()
    red.off()


'''
Ideas for a final product
Consider the Following:

-   a graudal torque increases and decreases to ease adjustment and lower wrist injury chance

-   something like grabSpeed = f(variationMax), making the tighteness directly responsive to slippage, rather than being
just 2 binary 'soft grip' and 'hard grip' states

-   adding hysteresis to slipdetect to prevent rapidly oscillating states

-   a way to keep motors in continual rather than pulsed actualtion pattern?
        while keeping tick system? the old while: True logic from the first model was more promising for this 
'''


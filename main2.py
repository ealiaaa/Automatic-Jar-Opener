import time, sys
from gpiozero import Motor,  LED
from sensor_library import Force_Sensing_Resistor # recommended to import *

'''
Constants
'''
TICK_PERIOD = 0.1 #controls how often the program iterates. also used outide func tick in func readyStart for the sensor read period
REQUIRED_HANDLE_FORCE = 50 # required sustained grip value to detect grip on handle
SAMPLE_WINDOW_LEN = 10  # number of samples per window (~0.1s rn)
MAX_ACCEPTABLE_VARIATION = 1
SLIP_CONFIRMATION_THRESHOLD = 3     
# num of slips that need to happen in a row to confirm that it's *actually* slipping and not a sensor fluke

'''
Variables
'''
##### consecutiveSlips = 0 # tracks number of slips in a row *across functions*
timeGrabbed = 0 # total time rotated for motorGrab, stanrdized to speed 1. collected in func jarGrabbed 
timeTwisted = 0 # total time rotated for motorTwist, stanrdized to speed 1. collected in func twist
# both of the above used in func dropProgram to return all motors to initial position
triedGrab = 0
triedTwist = 0 # FLAGS used in func tick to communicate to func printCurrent what motors where used
consecutiveGripValuesFailed = 0 # stores number of grip values below REQUIRED_HANDLE_FORCE *across functions*
sensor1RecentVar = []
sensor2RecentVar = [] # buffers to store recent force values to calculate rolling variation and slip
sensor1RecentAvg = []
sensor2RecentAvg = [] # buffers to store recent force values to calculate rolling average
'''
yes rolling average and rolling variation would be cleaner to break into 2 functions and a helper function that takes the rolling list
but the rubric specifically requests rolling average to be its own entire function 
'''
'''
TODO
PERHAPS add graudal torque increase and decreases to ease adjustment and lower wrist injury chance

- add leds
- make sure that we meet all complexity and function requirements from the project module

- check consecutiveSlips necessity with william?
    - i dont think that would even trigger ngl it also depends on the material of the grabby belt, also ->
    - theres just so many variables, its gonna be hard to find a good estimate for that value
        - maybe we can include it and set it to 1 ->
        - so functionally it does nothing but its good for code complexity and its a good idea for a final product
        - to revert back to the old, remove everything between ##########(10#), and uncomment all #####(5#) (replace ##### with blank)
-  check print message timing with william
    - how often should it print? as soon as possible? every 0.5 seconds (5 ticks)?
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


def rollingForceAverage12(): #rolling average of bottom 2 force sensors
    sensor1RecentAvg.append( readSensor(sensor1) )
    sensor2RecentAvg.append( readSensor(sensor2) )

    if len(sensor1RecentVar) > SAMPLE_WINDOW_LEN:
        sensor1RecentAvg.pop(0)
        sensor2RecentAvg.pop(0)

    if len(sensor1RecentAvg) < SAMPLE_WINDOW_LEN:
        return # function returns None if datapoints available is less than n
    avg1 = sum(sensor1RecentAvg) / len(sensor1RecentAvg)
    avg2 = sum(sensor2RecentAvg) / len(sensor2RecentAvg)
    
    return (avg1+avg2)/2


def readyStart (): # waits infinity until topSensor detects hand for more than 0.5 seconds
    while True:
        heldCounter = 0
        while readSensor(sensorTop) > REQUIRED_HANDLE_FORCE:
            heldCounter += 1
            time.sleep(TICK_PERIOD)
            if heldCounter >= 5:
                print("Starting lid grip sequence")
                return


def UsrLetGo (): # returns True if user lets go of handle for more than 0.5 seconds ish
    global consecutiveGripValuesFailed

    if readSensor(sensorTop) < REQUIRED_HANDLE_FORCE:
        consecutiveGripValuesFailed += 1
        if consecutiveGripValuesFailed >= 5: 
            return True
        else:
            return False
# 5 because 1 would be susceptible to sensor variations, but -> 5 (0.5 seconds ish when considering TICK_PERIOD) ->
# is still short enough to allow for quick recognition of handle release
    else:
        consecutiveGripValuesFailed = 0
        return False


def jarGrabbed(grabSpeed, grabTo): # tightens grabbing belt until grabTo value, returns if grabTo Value reached yet or not
    global timeGrabbed
    global triedGrab

    if rollingForceAverage12() < grabTo:
        motorGrab.forward(grabSpeed)
        timeRotated += 0.1*grabSpeed
        triedGrab = grabSpeed
        return False
    return True


def twist(twistSpeed): # twists entire jar lid grip mechanism open and returns whether lid is open or not
    global timeTwisted
    global triedTwist

    motorTwist.forward(twistSpeed)
    timeTwisted += 0.1*twistSpeed
    triedTwist = twistSpeed

    if timeTwisted > 9: # 9 is the currect ESTIMATE of how long itll take t
        print("Lid sucessfully opened")
        return True
    return False

def printCurrent():
    print("---")
    print(f"Top Force Sensor: {readSensor(sensorTop)}\tJar Force Sensor1: {readSensor(sensor1)}\tJar Force Sensor2:  {readSensor(sensor1)}")
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


def slipDetect (): #calculates rolling **variation** of bottom 2 sensors, determines if excess variation is indicative of slippage
    ###### global consecutiveSlips

    sensor1RecentVar.append( readSensor(sensor1) )
    sensor2RecentVar.append( readSensor(sensor2) )


    if len(sensor1RecentVar) > SAMPLE_WINDOW_LEN:
        sensor1RecentVar.pop(0)
        sensor2RecentVar.pop(0)

    if len(sensor1RecentVar) < SAMPLE_WINDOW_LEN:
        return False


    variation1 = variation(sensor1RecentVar)
    variation2 = variation(sensor2RecentVar)
    variationMax = max(variation1, variation2)

##########
    if variationMax > MAX_ACCEPTABLE_VARIATION:
        return True
    else:
        return False
##########


    ##### if variationMax > MAX_ACCEPTABLE_VARIATION:
    #####     consecutiveSlips += 1
    ##### else:
    #####     consecutiveSlips = 0
    
    ##### if consecutiveSlips >= SLIP_CONFIRMATION_THRESHOLD:
    #####     return True

    ##### return False



def tick():
    if slipDetect():
        grabSpeed = 0.5
        grabTo = 150
        twistSpeed = 0.5
    else:
        grabSpeed = 1
        grabTo = 200
        twistSpeed = 1


    if not jarGrabbed(grabSpeed, grabTo):
        red.off()
        return UsrLetGo()
    

    if twist(twistSpeed):
        return True
    
    return UsrLetGo()


def main():
    global triedGrab
    global triedTwist
    tickCounter = 0

    print("Waiting for user to grip...")
    green.on()
    readyStart()  # waits until it detects user holding handle for more than 0.5s in a row

    opened = False
    while not opened:
        green.on()
        red.on()

        opened = tick()  # will return True for the program to exit
        time.sleep(TICK_DELAY)
        
        motorGrab.stop()
        motorTwist.stop()
        green.off()
            
        if tickCounter >= 5: # every 5 ticks, will trigger print function ( once every 0.5 seconds)
            tickCounter = 0
            printCurrent()
            triedGrab = 0
            triedTwist = 0

        else:
            tickCounter += 1





# motor stops cannot be in func tick because then the final successful run of tick would never stop the motors
# and that would make the timeGrabbed timer 0.1 seconds too long while it waits for dropProgram(motorTwist, timeTwisted) to finish


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
every like 5 ticks print motor statuses and the shit they want
'''



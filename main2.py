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
consecutiveGripValuesFailed = 0 # stores number of grip values below REQUIRED_HANDLE_FORCE *across functions*
sensor1Recent = [] # buffers to store recent force values to calculate variation and slip
sensor2Recent = [] # buffers to store recent force values to calculate variation and slip

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
def readSensor(sensor):
    return sensor.force_raw()


def forceAverage12():
    return (readSensor(sensor1) + readSensor(sensor2) ) /2 


def readyStart (): # waits infinity until topSensor detects hand for more than 0.5 seconds
    while True:
        heldCounter = 0
        while readSensor(sensorTop) > REQUIRED_HANDLE_FORCE:
            heldCounter += 1
            time.sleep(TICK_PERIOD)
            if heldCounter >= 5:
                print("Starting lid grip sequence")
                return


def letGo (): # returns True if user lets go of handle for more than 0.5 seconds ish
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

    if forceAverage12() < grabTo : # 150 is the initial, slower and weaker jar grip speed
        motorGrab.forward(grabSpeed)
        time.sleep(0.1)
        motorGrab.stop()
        timeRotated += 0.1*grabSpeed
        return False
    return True


def twist(twistSpeed): # twists entire jar lid grip mechanism open and returns whether lid is open or not
    global timeTwisted

    motorTwist.forward(twistSpeed)
    time.sleep(0.1)
    motorTwist.stop()
    timeTwisted += 0.1*twistSpeed

    if timeTwisted > 9: # 9 is the currect ESTIMATE of how long itll take t
        print("Lid sucessfully opened: Retracting arms to initial position and dropping lid.")
        return True
    return False


def dropProgram(motor, duration): # reverses motors back to initial positions exactly
    motor.backward(1)
    time.sleep(duration)
    motor.stop()



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
    ###### global consecutiveSlips

    sensor1Recent.append( readSensor(sensor1) )
    sensor2Recent.append( readSensor(sensor2) )

    # make sure all the 3 sensors come online and have real values at the same time
    # would be bad if one added nothing or "None" to a list instead of an integer
    # or if list 2 has more entries than list 3 or something

    if len(sensor1Recent) > SAMPLE_WINDOW_LEN:
        sensor1Recent.pop(0)
        sensor2Recent.pop(0)

    if len(sensor1Recent) < SAMPLE_WINDOW_LEN:
        return False


    variation1 = variation(sensor1Recent)
    variation2 = variation(sensor2Recent)
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
        return letGo()
    
    if twist(twistSpeed):
        return True
    
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
    print("Retracting Twisting motor to original position")
    dropProgram(motorTwist, timeTwisted)
    print("Retracting Grabbing motor to original position")
    dropProgram(motorGrab,timeGrabbed)
    print("Program done")
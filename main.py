
import time
from gpiozero import Motor,  LED
from sensor_library.py import Force_Sensing_Resistor # recommended to import *


forceSensorFrequency = 50

gripValue = 1
windowLen = 5
# number of samples per window (~0.1s rn)
#adjust so that you have reasonable windowLen to compare but it'll check slip as frequently as possible

MaxAcceptableVariation = 1
SlipConfirmThreshold = 3     # num of slips that need to happen in a row to confirm that hey its actually slipping

consecutiveSlips = 0 # only initialize to 0 ONCE at the TOP of the program
# needs to be global and untouched between function calls to count consecutive slips

forceSensor1Recent = [] # buffers to store recent force values to calculate variation and slip
forceSensor2Recent = []
forceSensor3Recent = []

consecutiveGripValuesFailed = 0

lidRotationCount = 0

rackPosition = 0

forceSensorTop = Force_Sensing_Resistor(0)
forceSensor1 = Force_Sensing_Resistor(1)
forceSensor2 = Force_Sensing_Resistor(2)
forceSensor3 = Force_Sensing_Resistor(3)


def rollingAverage():




def readForceSensorTop(forceSensorTop):
    return forceSensorTop.force_scaled() # What scale? (5 for 0 to 1 value) #What about raw data? .force_raw()


def readForceSensor1(forceSensor1):
    return forceSensor1.force_scaled() # What scale? (5 for 0 to 1 value) #What about raw data? .force_raw()

def readForceSensor2(forceSensor2):
    return forceSensor2.force_scaled() # What scale? (5 for 0 to 1 value) #What about raw data? .force_raw()

def readForceSensor3(forceSensor3):
    return forceSensor3.force_scaled() # What scale? (5 for 0 to 1 value) #What about raw data? .force_raw()


def forceAverage123(forceSensor1, forceSensor2, forceSensor3):
    return (forceSensor1 + forceSensor2 + forceSensor3) / 3



def readyStart ():
    while True:
        heldCounter = 0

        while readForceSensorTop() > gripValue:
            heldCounter += 1/forceSensorFrequency
            time.sleep(1/forceSensorFrequency)

            if heldCounter >= 4:           # if held down for more than 4 seconds
                print("Starting lid grip sequence")
                return



def stillGrabbing ():
    global consecutiveGripValuesFailed
    if forceSensorTop() < GripValue:
        consecutiveGripValuesFailed += 1

        if len(consecutiveGripValuesFailed) > 25:
            # SET 25 to a reasonable length of grip values to fail to be absolutely sure that they have in fact, let go of the device.
            # take into account how this will work with the frequency and period
            return False

    consecutiveGripValuesFailed = 0
    return True



def grabJar():
    global rackPosition

    if forceAverage123() < 2.1 : # SET to a bit more than the force you expect to need to turn the jar
        DCMotorDown.turn(0.001) # turn FAST but only for a bit
        rackPosition += 0.01 # DISTANCE rack moves based on how much the DC motor moves
        return False
    return True



def grabJarHarder():
    global rackPosition

    if forceAverage123() < 5 : # SET to a a bit under the max amount of stress u think the jar can take
        DCMotorDown.turn(0.1) # turn SLOWLY but only for a bit
        rackPosition += 0.1 # DISTANCE rack moves based on how much the DC motor moves
        return False
    return True



def twist():
    global lidRotationCount

    DCMotorSideways.turn(0.1) # twist jar lid at reasonable speed
    DCMotorDown.turn(0.000001 ) # depends on sideways box gear ratio and DCMotorSideways speed/amount turned
    ## for every revolution the bottom mechanism does, the DCMotorDown will have to complete one as well to maintain jar squeeze levels

    lidRotationCount += 0.05 # amount of complete revolutoins accomplished by once run of this function

    rackPosition += 0.000001 # DISTANCE rack moves based on how much the DCmotorDOWN moves
    #lowkey you might just be able to get rid of this and just spam grabJar instead in main()



def twistSlower():
    global lidRotationCount

    DCMotorSideways.turn(0.01) # Turn jar lid slower b/c it was slipped
    DCMotorDown.turn(0.000000001 ) # depends on sideways box gear ratio and DCMotorSideways speed/amount turned
    ## for every revolution the bottom mechanism does, the DCMotorDown will have to complete one as well to maintain jar squeeze levels

    lidRotationCount += 0.005 # amount of complete revolutoins accomplished by once run of this function

    rackPosition += 0.000000001 # DISTANCE rack moves based on how much the DCmotorDOWN moves
    #lowkey you might just be able to get rid of this and just spam grabJar instead in main()



def dropProgram():
    DCMotorDown.turn(-rackPosition) # completely open racks back to their initial, retracted rackPosition
    # CONVERT rackPosition to a meaningful amount of revolutions for the down motor to spin to bring the racks back
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
# abs() could also do that but **2 or **4 or a bigger number also strongly penalizes sudden spikes
so if it slips, the variation is suddenly super massive, making it more obvious
'''




def slipDetect ():
    global consecutiveSlips

    forceSensor1Recent.append(forceSensor1())
    forceSensor2Recent.append(forceSensor2())
    forceSensor3Recent.append(forceSensor3())

    # make sure all the 3 sensors come online and have real values at the same time
    # would be bad if one added nothing or "None" to a list instead of an integer
    # or if list 2 has more entries than list 3 or something

    if len(forceSensor1Recent) > windowLen:
        forceSensor1Recent.pop(0)
        forceSensor2Recent.pop(0)
        forceSensor3Recent.pop(0)

    if len(forceSensor1Recent) < windowLen:
        return False


    variation1 = variation(forceSensor1Recent)
    variation2 = variation(forceSensor2Recent)
    variation3 = variation(forceSensor3Recent)
    variationMax = max(variation1, variation2, variation3)

    if variationMax > MaxAcceptableVariation:
        consecutiveSlips += 1
    else:
        consecutiveSlips = 0


    if consecutiveSlips >= SlipConfirmThreshold:
        return True

    return False






def main():

    readyStart() # is a while loop that will go forever until you either grab the thing for 4 seconds or keyboard interrupt

    while True:
        if grabJar():
            break

        if not stillGrabbing ():
            print("User has let go of handle: Retracting arms to initial positions and exiting program.")
            dropProgram()
            return


    while True:
        twist()
        grabJar()
        # ik that twist has a bit in it to synchronize the top and bottom mechanisms while twisting to maintain jar lib pressure
        # but its probably easier to have that under-adjust the bottom and then just call grabJar() again, potentially in a loop
        if lidRotationCount > 3:
            print("Lid sucessfully opened: Retracting arms to initial position and dropping lid.")
            dropProgram()
            return
        if not stillGrabbing ():
            print("User has let go of handle: Retracting arms to initial positions and exiting program.")
            dropProgram()
            return

        if slipDetect():
            while True:
                twistSlower()
                grabJarHarder()
                # ik that twistSlower also synchronizes the top and bottom mechanisms while twisting to maintain jar lib pressure
                # but its probably easier to have that under-adjust the bottom and then just call grabJarHarder() again
                if lidRotationCount > 3:
                    print("Lid sucessfully opened: Retracting arms to initial position and dropping lid.")
                    dropProgram()
                    return
                if not stillGrabbing ():
                    print("User has let go of handle: Retracting arms to initial positions and exiting program.")
                    dropProgram()
                    return
                if consecutiveSlips < 50 and not slipDetect(forceSensor1, forceSensor2, forceSensor3):
                    #if arent slipping now and havent for a bit
                    break

#yes i can edit this
try:
    main()

except KeyboardInterrupt:
    print("Program interrupted by KeyboardInterrupt.\nRetracting arms to original position.")
    dropProgram()
finally:
    dropProgram()
    print("Program Terminated for unknown cause\nRetracting arms to original position.")

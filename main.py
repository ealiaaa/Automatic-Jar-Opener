
import time
from gpiozero import Motor,  LED
from sensor_library import Force_Sensing_Resistor # recommended to import *


sensorFrequency = 50

gripValue = 1
windowLen = 5
# number of samples per window (~0.1s rn)
#adjust so that you have reasonable windowLen to compare but it'll check slip as frequently as possible

MaxAcceptableVariation = 1
SlipConfirmThreshold = 3     # num of slips that need to happen in a row to confirm that hey its actually slipping

consecutiveSlips = 0 # only initialize to 0 ONCE at the TOP of the program
# needs to be global and untouched between function calls to count consecutive slips

sensor1Recent = [] # buffers to store recent force values to calculate variation and slip
sensor2Recent = []
sensor3Recent = []



lidRotationCount = 0

timeRotatedFast = 0
timeRotatedSlow = 0
# ALERT I've search replaced all rackPosition for 'timeRotate' without a d. I've yet to properly rename them tho, ill add that and the variable speeds soon.
# NOTE add graudal torque increase and decreases to ease adjustment and lower wrist injury chance


sensorTop = Force_Sensing_Resistor(0)
sensor1 = Force_Sensing_Resistor(1)
sensor2 = Force_Sensing_Resistor(2)
sensor3 = Force_Sensing_Resistor(3)

motorTighten = Motor(forward = 16, backward=20)
motorOpen = Motor(forward=16, backward = 20)




def rollingAverage():
    pass


def readSensor(sensor):
    return sensor.force_scaled()



def forceAverage123(sensor1, sensor2, sensor3):
    return (readSensor(sensor1) + readSensor(sensor2) + readSensor(sensor1)) / 3



def readyStart ():
    while True:
        heldCounter = 0

        while readSensor(sensorTop) > gripValue:
            heldCounter += 1 #/sensorFrequency?
            time.sleep(1/sensorFrequency)

            if heldCounter >= 4:           # if held down for more than 4 seconds
                print("Starting lid grip sequence")
                return

# merge ready start and stillGrabbing

def stillGrabbing ():
    global consecutiveGripValuesFailed
    consecutiveGripValuesFailed = 0

    if readSensor(sensorTop) < GripValue:
        consecutiveGripValuesFailed += 1

        if consecutiveGripValuesFailed > 4:
            # SET 25 to a reasonable length of grip values to fail to be absolutely sure that they have in fact, let go of the device.
            # take into account how this will work with the frequency and period
            return False

    consecutiveGripValuesFailed = 0
    return True



def grabJar():
    global timeRotatedSlow

    if forceAverage123() < 2.1 : # SET to a bit more than the force you expect to need to turn the jar
        motorTighten.forward(1) # turn FAST but only for a bit
        time.sleep(0.2)
        timeRotate += 0.2 # DISTANCE rack moves based on how much the DC motor moves
        return False
    return True



def grabJarHarder():
    global timeRotate

    if forceAverage123() < 5 : # SET to a a bit under the max amount of stress u think the jar can take
        motorTighten.forward(0.2) # turn SLOWLY but only for a bit
        time.sleep(0.4)
        timeRotate += 0.4 # DISTANCE rack moves based on how much the DC motor moves
        return False
    return True



def twist():
    global lidRotationCount

    DCMotorSideways.turn(0.1) # twist jar lid at reasonable speed
    DCMotorDown.turn(0.000001 ) # depends on sideways box gear ratio and DCMotorSideways speed/amount turned
    ## for every revolution the bottom mechanism does, the DCMotorDown will have to complete one as well to maintain jar squeeze levels

    lidRotationCount += 0.05 # amount of complete revolutoins accomplished by once run of this function

    timeRotate += 0.000001 # DISTANCE rack moves based on how much the DCmotorDOWN moves
    #lowkey you might just be able to get rid of this and just spam grabJar instead in main()



def twistSlower():
    global lidRotationCount

    DCMotorSideways.turn(0.01) # Turn jar lid slower b/c it was slipped
    DCMotorDown.turn(0.000000001 ) # depends on sideways box gear ratio and DCMotorSideways speed/amount turned
    ## for every revolution the bottom mechanism does, the DCMotorDown will have to complete one as well to maintain jar squeeze levels

    lidRotationCount += 0.005 # amount of complete revolutoins accomplished by once run of this function

    timeRotate += 0.000000001 # DISTANCE rack moves based on how much the DCmotorDOWN moves
    #lowkey you might just be able to get rid of this and just spam grabJar instead in main()



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
# abs() could also do that but **2 or **4 or a bigger number also strongly penalizes sudden spikes
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

    if len(sensor1Recent) > windowLen:
        sensor1Recent.pop(0)
        sensor2Recent.pop(0)
        sensor3Recent.pop(0)

    if len(sensor1Recent) < windowLen:
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
                if consecutiveSlips < 50 and not slipDetect(sensor1, sensor2, sensor3):
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

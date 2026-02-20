import time
from gpiozero import Motor,  LED
from sensor_library import Force_Sensing_Resistor # recommended to import *

sensorTop = Force_Sensing_Resistor(0)
sensor1 = Force_Sensing_Resistor(1)
sensor2 = Force_Sensing_Resistor(2)
sensor3 = Force_Sensing_Resistor(3)

motorTighten = Motor(forward = 16, backward=20) # (16 and 20 are the GPIO motor input and output pins)
motorOpen = Motor(forward=16, backward = 20)



def sensorTest(t,x,y,z):
	print("Scale 5 data\n")
	print(t.force_scaled())
	print("\t")
	print(x.force_scaled())
	print("\t")
	print(y.force_scaled())
	print("\t")
	print(z.force_scaled())
	print("\n\nForced Raw")
	print(t.force_raw())
	print("\t")

### sensorTest(sensorTop,sensor1,sensor2,sensor3)


def motorTest(motorTighten,motorOpen):
	motorTighten.forward(0.1)
	time.sleep(5)
	motorTighten.backward(0.69)
	time.sleep(5)
	motorOpen.forward(1)
	time.sleep(5)
	motorOpen.backward(1.1) # this should not work
	time.sleep(5)
	motorOpen.stop()   # ALERT it *is* motorOpen.stop() right?




def motorSpeeds():# how to make the motor go slower on the motor
	for i in range(100):
		motorTighten.forward(0.1)
		time.sleep (0.01)
	for i in range (10000):
		motorTighten.forward(.001)
		time.sleep(0.001)


# ?????

def main():
	while True:
		while True:
			sensorTest()
			if input("\nEnter: \n") == 1:
				print("\n-\n-\nMotorTest\n-\n-\n")
				break
	motorTest()




# NOTICE
# how will the wiring work? is it GPIO 16, 20 -> motor driver -> both motors ?


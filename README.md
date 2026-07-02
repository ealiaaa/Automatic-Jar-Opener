## Automatic Jar Opener
#### A First Year Engineering Project

<p>&nbsp;</p>

Using a RaspberryPi and a gripping harness rigged by the CAD team, our code **successfully passed presentations**.

<p>&nbsp;</p>

The finished project successfully **detected the presence of human grip** through an integrated force sensor on a handle and tightens grippers around a jar lid. 
Once the grip force rolling average from the 2 integrated force sensors in the lid grippers are deemed high enough to indicate a solid grip, it begins twisting.

<p>&nbsp;</p>

While it is twisting, it calculates **amplified variation in two rolling averages** of the gripper's two force sensors in an attempt to **detect slippage**.
If slippage is detected, it tightens its grip before continuing to twist.

<p>&nbsp;</p>

Automatically releases grip once jar is open, features a red and green LED, which indicate progression through their state.

/

The **amount of global variables is egregious**, a state class would have been much cleaner. Please look at the diagram for a visual , lightly abstracted walkthrough of the code.

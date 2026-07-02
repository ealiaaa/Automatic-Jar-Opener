## Automatic Jar Opener
### A First Year Engineering Project

Using a RaspberryPi and a gripping harness rigged by the CAD team, our code **successfully passed presentations**.

<!-- -->

The finished project successfully **detects the presence of human grip** through an integrated force sensor on a handle and tightens grippers around a jar lid.

<!-- -->

Once the grip force rolling average (from the 2 integrated force sensors in the lid grippers) are deemed high enough to indicate a solid grip, it begins twisting.

<!-- -->

While it is twisting, it calculates **amplified variation in two rolling averages** of the lid gripper's two force sensors in an attempt to **detect slippage**.
If slippage is detected, it tightens its grip before continuing to twist.

<!-- -->

Automatically releases grip once jar is open and features a red and green LED, which indicate progression through their state (on, off, flashing slow, flashing fast)

<!-- -->
### What I would change
The **amount of global variables is egregious**, a state class would have been cleaner. Please look at the diagram for a **colored**, lightly abstracted walkthrough of the code, unless you want to remember 20 mutating global variables.

Microcontroller Prototyping Tool Guide



About this project

This project is meant to be a tool for DIY-ers and MAKERs who use microcontrollers in their 
projects to interface with external devices. This tool will help users to prototype the 
physical and electrical implementations of their projects. It allows users to test how 
certain devices will behave under certain conditions or when given certain values. This tool 
is meant to help users test these devices without having to write their own test platform 
making the space easier to enter for newcomers or provide convenience for those who do 
not already have their own testing platform. This tool provides a platform for users to 
manipulate digital output and PWM pins, and reading the state of digital input pins all from 
a GUI interface. 


Requirements


There are four main components (Server, GUI, Microcontroller, and MQTT broker) to the 
prototyping system each with its own set of requirements.

Server Requirements:

-	Must be run on a computer or single board computer (SBC) with python installed
-	Must have paho-mqtt python library installed (this can be installed using pip with 
command: pip install paho-mqtt)
-	Computer or SBC must have local network access (if self hosting MQTT broker) or 
internet access (if using remote MQTT broker) (more on this topic later)

GUI Requirements:

-Must be run on a computer or SBC with graphical interface operating system 
(Windows, MacOS, Linux)
-Computer or SBC must have Python installed
-Must have Tkinter (comes standard with python) (this can be installed using pip 
using the following commands: pip install tk )
-Must have paho-mqtt python library installed (this can be installed using pip with 
command: pip install paho-mqtt)
-Computer or SBC must have local network access (if self hosting MQTT broker) or 
internet access (if using remote MQTT broker) (more on this topic later)


Microcontroller Requirements:

Currently this system supports 3 microcontrollers or SBCs (Rapsberry Pi Zero 2w, 
Rapsberry Pi Pico 2w, ESP32-S3)

Raspberry Pi 2 Zero Requirements:

-	Must have a Raspberry Pi Zero 2w running Raspberry Pi OS (we recommend 
bookworm lite which is headless interface) with a Wi-Fi connection to either a local 
network or the internet 
o	To install Raspberry Pi OS using the following link to download the imager, 
and follow the prompts to install the OS, we recommend using the wi-fi 
configuration tool in the installer to set up the initial wi-fi connection, as well 
as enabling SSH: Raspberry Pi software   Raspberry Pi
o	To add additional wi-fi networks after the OS has been set up we recommend 
using cli command: nmtui , This tool will allow you to easily add wi-fi 
connections
-	Must have pigpio installed and running in daemon mode (the link provided here will 
guide you through the setup process: How to Install and Use pigpio for GPIO Control 
on Raspberry Pi   TheLinuxCode) 
-	Must have paho-mqtt python library installed (this can be installed using pip with 
command: pip install paho-mqtt)



ESP32-S3 and Raspberry Pi Pico Requirements:
-	


MQTT Broker Requirements/Configuration:

-	This system uses MQTT messaging for communication, thus a MQTT broker is 
required for the system to work
-	We recommend using the mosquitto broker hosted on the same machine as the 
server, additionally we recommend running mosquitto as a service on that machine
-	This broker should be using no authentication mode with remote access enabled, to 
configure this, add the following lines to the end of the mosquitto.conf file: 
listener (port#)
allow_anonymous true 

where (port#) is replaced with the desired listening port. (This link will guide you on 
raspberry pi: Install Mosquitto Broker Raspberry Pi | Random Nerd Tutorials, and this 
link provides a guide for other operating systems: Quick Guide to The 
Mosquitto.conf File With Examples)
-	You can use a remote MQTT broker hosted by someone else, however this is not 
recommended as the latency will be an issue and affect performance



Running the Software


In this section of the guide, we assume you already have the MQTT broker running as a 
service on your server machine. We also assume you already have a copy of the repository 
on your computers and will transfer the respective files to the respective machines that 
meet the requirements above. You must start the server software first, then you may start 
GUI and microcontroller instance in whatever order you wish to. 

Running the server software:

1.	First navigate to the Server sw folder. In this folder you will see 2 files, classes.py and 
Server.py
2.	Open Server.py in a text editor, so you can configure some of the server options
3.	Modify the following constant values at the top of the file: SERVER_IP, PORT, 
SERVER_KEY, SERVER_TOPIC (note you must provide a value for all of the constant 
variables, they will have default values, but you must modify them to your setup)
SERVER_IP is the IP address or hostname of the MQTT broker you are using
PORT is the port number that the MQTT is listening for traffic on
SERVER_KEY this value that all GUI and microcontroller instances need to have as 
their key value, this provides basic authentication in the form of designated  shared 
key   
SERVER_TOPIC this is the MQTT topic that the server will monitor for incoming 
messages (note this value must be the same in all GUI and microcontroller 
instances)
4.	Save the changes and transfer the Server.py file and classes.py file to the server 
machine that meets the requirements above.
5.	Run the server program by executing the Server.py file with python.

Running the GUI software: 

1.	First navigate to the GUI sw folder. In this folder you will see the file of interest 
GUI.py
2.	Open GUI.py in a text editor, so you can modify the constant values needed by the 
GUI.
3.	Modify the SERVER_TOPIC value at the top of the file to be the SERVER_TOPIC value 
you used for the server software.
4.	Save the changes and transfer the GUI.py file to the machine you plan on running it 
on that meets the requirements above.
5.	Run the GUI program by executing GUI.py with python

Running the microcontroller software for the Raspberry Pi Zero:

1.	First navigate to the Microcontroller sw folder, then navigate to the rpiZero folder. In 
this folder you should see a file named MC.py
2.	Open MC.py in a text editor so you can modify some of the MC connection options.
3.	Modify the following constants at the top of the file: SERVER_IP, PORT, SERVER_KEY, 
MICROCONTROLLER_ID, SERVER_TOPIC, PWMFREQUENCY


SERVER_IP is the IP address or hostname of the MQTT broker you are using

PORT is the port number that the MQTT is listening for traffic on

SERVER_KEY this value should be the same value you entered as the SERVER_KEY 
on the server program

SERVER_TOPIC this is the MQTT topic that the server is monitoring for incoming 
messages (this value should be the same as the SERVER_TOPIC value provided in 
the server program)

MICROCONTROLLER_ID is the string you want the microcontroller ID to be, this 
value should be unique to the microcontroller instance, we recommend the format 
M### where # is an integer

PWMFREQUENCY this is the value that represents the frequency in hertz (Hz) that 
you want the PWM pins to operate at (this value should be a integer) 

4.	Save the changes and transfer the MC.py file to the Raspberry Pi Zero 2w that meets 
the requirements above.
5.	Run the microcontroller program by executing the MC.py file with python.



Using the System


Once the server program is started no additional action is required, it will automatically 
handle communication with the GUI instances and microcontroller instances.

Using the Raspberry Pi Zero 2W Microcontroller software:

	Once the MC.py program is started no additional interaction is needed with the 
software. Since the intent of the microcontroller software is to manipulate GPIO using the 
GUI, hardware configuration is need to utilize the GPIO pins. There are GPIO pins currently 
available for use, 2 Digital Output pins, 2 Digital Input pins, and 2 PWM output pins. You 
can attach devices to these pins and read/control there state from the GUI program. The 
pin out is as follows:
-	Digital Input 1 : GPIO 23
-	Digital Input 2 : GPIO 24
-	Digital Output 1 : GPIO 5
-	Digital Output 2 : GPIO 6
-	PWM 1 : GPIO 12
-	PWM 2 : GPIO 13

Here is a link to the physical pin to GPIO layout for the Raspberry Pi Zero 2W for your 
convenience: RPI Zero 2W Board Layout: GPIO Pinout, Specs, Schematic in detail

Please note that digital input 1 and 2 are set to pull up mode, they will read as HIGH or 1 
until connected to ground.  Additionally, please note that the PWM uses the hardware PWM 
controller as opposed to a software implementation, so when determining a PWM 
frequency to use keep this in mind.

Using the GUI program:

When you first open the GUI program, you will be greeted with a connection page, that will 
allow you to enter the connection details of the server you would like to connect to. Please 
enter the information you provided the server program for each field. After you enter this 
information, click the find microcontrollers button. In the box below the find 
microcontrollers button the box will populate with all of the microcontrollers currently 
connected to the server. You can click this button again to repopulate the box if you 
connect a new microcontroller. After selecting the desired microcontroller to control, press 
connect and you will be brought to that microcontrollers control page. 

From there you can monitor the state of each supported pin on the left hand side of the screen. 
On the right hand side of the screen you can manipulate the supported pin states. For digital output 
pins you can choose to set the state high or low then press set to set the pin state. For the 
PWM pins you can enter an integer value between 0-100 to set the duty cycle of the 
corresponding PWM pin after pressing set. Please note that a value of 0 equates to the 
PWM pin being off, and 100 is the max duty cycle. If at any point the microcontroller 
disconnects and cannot reconnect in the reconnection window, the program will give a 
warning message and then close the program. You can restart the GUI program and 
reconnect to reestablish the connection. 

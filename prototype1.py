import gpiod #https://pypi.org/project/gpiod/  #https://git.kernel.org/pub/scm/libs/libgpiod/libgpiod.git/about/
#With the pi5 there is a new gpio system and previus GPIO libraries are not supported. 
# I heard from some places gpiod is the official but documentation is really hard to find
# I have also heard good things about gpio zero which is supposed to have better documentation

import time

class bcolors: #Terminal colors for easier terminal readability. 
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

EJECTION_SOLENOID_PIN1 = 26 # Define our GPIO PINS
LASER_PIN1 = 17 # first laser
LASER_PIN2 = 27 # second laser
LASER_PIN3 = 22 # third laser

chip = gpiod.Chip('gpiochip4') # Something new required with the pi5 we have to define our chip

ejection_solenoid_switch = chip.get_line(EJECTION_SOLENOID_PIN1) #These will check the state of each GPIO Pin, HIGH or LOW
laser1 = chip.get_line(LASER_PIN1) # This laser will be for checking that items on conveyor line are not too close
laser2 = chip.get_line(LASER_PIN2) # This laser will be for when to take pictures
laser3 = chip.get_line(LASER_PIN3) # This laser will be for when to reject item from the line.

ejection_solenoid_switch.request(consumer="Relay", type=gpiod.LINE_REQ_DIR_OUT)
laser1.request(consumer="Button", type=gpiod.LINE_REQ_DIR_IN)
laser2.request(consumer="Button", type=gpiod.LINE_REQ_DIR_IN)
laser3.request(consumer="Button", type=gpiod.LINE_REQ_DIR_IN)

isinterrupted1 = False # These values will toggle the the if statements for the sensor for a makeshit edge detection
isinterrupted2 = False
isinterrupted3 = False

# Counters for number of items through each sensor
counted1 = 0        # Start of the interrupt of first sensor
lastcounted1 = 0    # End of the interrupt for the first sensor

counted2 = 0 # For second sensor
lastcounted2 = 0

counted3 = 0 # For third sensor
lastcounted3 = 0

# interrupt_list formated as [Initial sensor intrrupt, End sensor 1 intrrupt, Eject Item if True]
interrupt_list = [[0,0,True]]

while True:
    
    ejection_solenoid_switch.set_value(0) # Set the value of our solenoid to LOW / 0
    laser1_state = laser1.get_value() 
    laser2_state = laser2.get_value() # Get the value of our laser sensors, HIGH = 1 / Low = 0
    laser3_state = laser3.get_value()

    if laser1_state == 0 and isinterrupted1 == False: # If the laser returns LOW and it has not been interrupeted yet
        isinterrupted1 = True # Set the interrupt boolean to True
        counted1+=1 # add an interrupt to the counter
        current_time1 = time.time()
        interrupt_list.append([current_time1, 0]) # save the time of the interrupt to the interrupt list. 
        
        print(f"Interrupt #{counted1} start at {current_time1}")
        
        
        # This checks if out interrupt is too close to our last interrupt which could mean items are too close together on the conveyor.
        # If it is add a true value to our interrupt list so we can remove it from the line.
        if counted1 > 1 and interrupt_list[counted1][0]-interrupt_list[counted1-1][1] < 1.5: # our line_proximity value, will determind how close and item can be to the last item.
            print(f"{bcolors.WARNING}LINE ERROR: INTERRUPT #{counted1} TOO CLOSE TO LAST INTERRUPT:{bcolors.FAIL}{interrupt_list[counted1][0]-interrupt_list[counted1-1][1]}{bcolors.ENDC}") 
            interrupt_list[counted1].extend([True])
        
    elif laser1_state == 1 and isinterrupted1 == True: # If the laser returns HIGH and it has been interrupted
        isinterrupted1 = False # set the interrupt boolean to False to allow the a new item to be detected
        lastcounted1+=1
        current_time1 = time.time()
        interrupt_list[counted1][1] = current_time1 # Set the second value in our list to the current interrupt time so we know the end time of the interrupt.
        
        time_interrupted = interrupt_list[counted1][1]-interrupt_list[counted1][0] # Find the amount of time between interrupt and the end of interrupt
        
        print(f"Interrupt #{counted1} end at {current_time1}")
        
        # Check if the interrupt was within an acceptable range
        if 1<time_interrupted<10: # Right now this just checks if the interrupt time was between 1 and 10 seconds for testing
            print(f"Total time interrupted: {bcolors.OKGREEN}{time_interrupted}{bcolors.ENDC} \n")
        else:
            print(f"{bcolors.WARNING}ANOMALY DETECTED: INTERRUPT #{counted1} NOT WITHIN ACCEPTABLE RANGE:{bcolors.FAIL}{time_interrupted}{bcolors.ENDC} \n") 
    
    
    elif laser2_state == 0 and isinterrupted2 == False:
        isinterrupted2 = True
        counted2+=1
        
    elif laser2_state == 1 and isinterrupted2 == True: #This is on the release of the interrupt.
        isinterrupted2 = False
        lastcounted2+=1

        # Take pictures of item.

        print(f"{bcolors.OKCYAN}PICTURE OF ITEM #{counted2} TAKEN{bcolors.ENDC}")

    elif laser3_state == 0 and isinterrupted3 == False:
        isinterrupted3 = True
        counted3+=1

    elif laser3_state == 1 and isinterrupted3 == True: # This is on the release of the interrupt
        isinterrupted3 = False
        lastcounted3+=1

        ejection_solenoid_switch.set_value(1) # Set the electric Solenoid to high. 

        print(f"{bcolors.WARNING}ITEM #{counted3} REMOVED FROM LINE{bcolors.ENDC}")
        time.sleep(.1) # The electic solenoid needs time to fire to it can fully extend, this is something that may need threading or asyncio so it doesnt hold up the other code as it currently does.

# NEED TO DO:
#   * The solenoid fireing currently hold up the rest of the program.
#       * Asycio / threading needed?
#   * Convert program to OOB for better readability and better code
#   * Port program to gpiozero?
#   * Take and send pictures to "server" for processing
import cv2
import numpy as np
import sys
import argparse
import imutils
import time
import gpiozero
import RPi.GPIO as GPIO
from datetime import datetime

servoPIN = 27	#Servo Pin
PHOTOCELL = 17	#Photoresistor pin
RED = 21 #Red LED
YELLOW = 20 #Yellow LED
GREEN = 12 #Green LED

#setup pins
GPIO.setmode(GPIO.BCM)
#Set GPIO pins as outputs
GPIO.setup(24, GPIO.OUT) #Left motor
GPIO.setup(13, GPIO.OUT) #Right motor
GPIO.setup(servoPIN, GPIO.OUT) #Servo
GPIO.setup(GREEN, GPIO.OUT) #Green LED
GPIO.setup(YELLOW, GPIO.OUT) #Yellow LED
GPIO.setup(RED, GPIO.OUT) #Red LED
#Direction(Forward) = [left forward GPIO pin, right forward GPIO pin]
dir1 = [gpiozero.OutputDevice(23), gpiozero.OutputDevice(19)] #Forward
#Direction(Backward) = [left backward GPIO pin, right backward GPIO pin]
dir2 = [gpiozero.OutputDevice(18), gpiozero.OutputDevice(26)] #Backward
#PWM pins = [left pwm pin, right pwm pin]
pwm = [GPIO.PWM(24, 100), GPIO.PWM(13, 100)]  #PWM
servo = GPIO.PWM(servoPIN, 50) # GPIO 17 for PWM with 50Hz


#Initialise pwm at 0
pwm[0].start(0)
pwm[1].start(0)
#Initialise motor at 2.5
servo.start(6.5)
#Multipliers for uneven motor power
m1mult = 1.0 #Left motor multiplier
m2mult = 0.8 #Right motor multiplier


FREQUENCY = 20 #Hz
INTERVAL = 1.0/FREQUENCY
FOCAL_LEN = 3.04 #mm
SENSOR_HEIGHT = 2.76 #mm
SENSOR_WIDTH = 3.68 #mm
OBST_HEIGHT = 150 #mm
ROCK_HEIGHT = 70 #mm
SAMPLE_HEIGHT = 40 #mm
LANDER_HEIGHT = 70 #mm
WALL_HEIGHT = 450 #mm
HEIGHT = 240 #screen height
WIDTH = 320 #screen width
ROT_SCALE = 0.2 #Rotation Scaler
VEL_SCALE = 0.35 #Velocity Scaler
VEL_MIN = 11 #Velocity min value
LASERTHRESH	 = 0 #Initialise threshold at 0
laserArr = []
lasertol = 0.8 #Laser tolerance
currentTime = datetime.now()

#HSV Value arrays
s_min_1 = [int]*3
s_max_1 = [int]*3
s_min_2 = [int]*3
s_max_2 = [int]*3
r_min_ = [int]*3
r_max_ = [int]*3
o_min_ = [int]*3
o_max_ = [int]*3
l_min_ = [int]*3
l_max_ = [int]*3
b_min_ = [int]*3
b_max_ = [int]*3

s_max_arr1 = []
s_min_arr1 = []
s_max_arr2 = []
s_min_arr2 = []
r_max_arr = []
r_min_arr = []
o_max_arr = []
o_min_arr = []
l_max_arr = []
l_min_arr = []
b_max_arr = []
b_min_arr = []

Sample_list = []
Rock_list = []
Obstacle_list = []
Lander_list = []

max_index = 160

captured = 0
flipped = 1

init = False

#Video
#cap = cv2.VideoCapture(sys.argv[1])
#Camera
cap = cv2.VideoCapture(-1)
cap.set(3, 320)									# Set the frame WIDTH
cap.set(4, 240)									# Set the frame HEIGHT
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

class Sample:
	#'Class for Samples'
	sampleCount = 0
	def __init__(self, ID, Dist, Bearing, cX, cY):
		self.Dist = Dist	#Distance from camera to object
		self.Bearing = Bearing		#Angle from centre of POV to object
		self.ID = ID	#ID of object
		self.cX = cX	#x-coord of the centre of the object
		self.cY = cY	#y-coord of the centre of the object
		Sample.sampleCount += 1
	def __del__(self):
		Sample.sampleCount -= 1

class Rock:
	#'Class for Rocks'
	rockCount = 0
	def __init__(self, ID, Dist, Bearing, cX, cY):
		self.Dist = Dist
		self.Bearing = Bearing
		self.ID = ID
		self.cX = cX
		self.cY = cY
		Rock.rockCount += 1
	def __del__(self):
		Rock.rockCount -= 1

class Obstacle:
	#'Class for Obstacles'
	obstacleCount = 0
	def __init__(self, ID, Dist, Bearing, cX, cY):
		self.Dist = Dist
		self.Bearing = Bearing
		self.ID = ID
		self.cX = cX
		self.cY = cY
		Obstacle.obstacleCount += 1
	def __del__(self):
		Obstacle.obstacleCount -= 1

class Lander:
	#'Class for Lander'
	landerCount = 0
	def __init__(self, ID, Dist, Bearing, cX, cY):
		self.Dist = Dist
		self.Bearing = Bearing
		self.ID = ID
		self.cX = cX
		self.cY = cY
		Lander.landerCount += 1
	def __del__(self):
		Lander.landerCount -= 1

def bounds():
	##Gets the HSV values from the .txt files
	#Sample
	f = open("sample.txt","r")
	for i in range(3):
		s_min_1[i] = (int(f.readline()))
		s_max_1[i] = (int(f.readline()))
	f.seek(0)
	for i in range(3):
		s_min_2[i] = (int(f.readline()))
		s_max_2[i] = (int(f.readline()))
	f.close()
	#Rock
	f = open("rock.txt","r")
	for i in range(3):
		r_min_[i] = (int(f.readline()))
		r_max_[i] = (int(f.readline()))
	f.close()
	#Obstacle
	f = open("obstacle.txt","r")
	for i in range(3):
		o_min_[i] = (int(f.readline()))
		o_max_[i] = (int(f.readline()))
	f.close()
	#Lander
	f = open("lander.txt","r")
	for i in range(3):
		l_min_[i] = (int(f.readline()))
		l_max_[i] = (int(f.readline()))
	f.close()
	#Wall
	f = open("wall.txt","r")
	for i in range(3):
		b_min_[i] = (int(f.readline()))
		b_max_[i] = (int(f.readline()))
	f.close()

	global s_min_arr1
	global s_max_arr1
	#min hue mask 1 from 0 to min of txt file
	s_max_1[0] = s_min_1[0]
	s_min_1[0] = 0
	s_min_arr1 = np.array(s_min_1)
	s_max_arr1 = np.array(s_max_1)
	global s_min_arr2
	global s_max_arr2
	#min hue mask 2 from min of txt file to 179
	s_min_2[0] = s_max_2[0]
	s_max_2[0] = 179
	s_min_arr2 = np.array(s_min_2)
	s_max_arr2 = np.array(s_max_2)

	global r_min_arr
	r_min_arr = np.array(r_min_)
	global r_max_arr
	r_max_arr = np.array(r_max_)

	global o_min_arr
	o_min_arr = np.array(o_min_)
	global o_max_arr
	o_max_arr = np.array(o_max_)

	global l_min_arr
	l_min_arr = np.array(l_min_)
	global l_max_arr
	l_max_arr = np.array(l_max_)

	global b_min_arr
	b_min_arr = np.array(b_min_)
	global b_max_arr
	b_max_arr = np.array(b_max_)

def laserSetup():
	while (len(laserArr) < 30):
		laserArr.append(laser())
	global LASERTHRESH
	LASERTHRESH = float(sum(laserArr) / len(laserArr))
	tolerance = lasertol * LASERTHRESH
	LASERTHRESH = LASERTHRESH + tolerance

def offLander():
	drive(-20,0)
	time.sleep(3)

def motor(mot, value):
  	#Drive motor(which motor, PWM intensity)
	if (value > 0):
	#if value is positive: drive forward
		dir1[mot].on()
		dir2[mot].off()
	elif (value < 0):
	#if value is negative: drive backward
		dir1[mot].off()
		dir2[mot].on()
	#set the pwm pin at index mot to "value"
	if (abs(value) > 100):
		value = 100
	pwm[mot].ChangeDutyCycle(abs(value))

def drive(magnitude, rotation):
	motor(0, m1mult * (magnitude - rotation))  #set motor at index 0 (left motor) to (value-rotation)
	motor(1, m2mult * (magnitude + rotation))  #set motor at index 1 (right motor) to (value+rotation)
	#rotation is positive CCW from north

def stop():
	pwm[0].stop() #stop the pwm pin at index 0 (left motor)
	pwm[1].stop() #stop the pwm pin at index 1 (right motor)

def upServo():
	#Put the servo in the up position
	servo.ChangeDutyCycle(3.5)
	time.sleep(0.5)

def pushingServo():
	#Put the servo low enough to push the rock but not the ball
	servo.ChangeDutyCycle(5)
	time.sleep(0.5)

def midServo():
	#Put the servo low enough to capture the ball but not touch the carpet
	servo.ChangeDutyCycle(6.5)
	time.sleep(0.5)

def downServo():
	#Put the servo in the down position
	servo.ChangeDutyCycle(7)
	time.sleep(0.5)

def flipRock():
	downServo()		#Put the servo in the down position
	drive(21, 0)	#Drive forward for 1.7 secs
	time.sleep(1.7)
	drive(0, 0)		#Stop
	time.sleep(2)
	upServo()		#Lift the servo up - flipping rock
	time.sleep(1)
	drive(-15,0)	#Drive backwards for 1 sec
	time.sleep(1)
	drive(0,0)		#Stop
	pushingServo()	#Put the servo low enough to push the rock, and capture the ball
	drive(23, 0)	#Drive forward for 1.5 secs
	time.sleep(1.5)
	drive(0,0)		#Stop
	time.sleep(0.5)
	drive(-10,0)	#Drive backwards slightly so the servo doesn't clip the rock
	time.sleep(0.5)
	drive(0,0)
	midServo()		#Put the servo down but not low enough to scrape the carpet
	drive(-20,0)	#Drive backwards for 2 seconds
	time.sleep(2)
	drive(0,0)		#stop
	global flipped
	flipped = 1		#Set the rock as flipped
	global captured
	captured = 1	#Set the sample as captured

def captureBall():
	upServo()		#Lift the servo up
	time.sleep(1)
	drive(23, -1)	#Drive forward for 3 seconds
	time.sleep(3)
	midServo()		#Lower the servo
	global captured
	captured = 0	#Set the sample as captured
	drive(0, 0)		#Stop
	time.sleep(1)

def returnBall():
	midServo()		#Ensure the gate won't catch on the lander
	drive(55, 0)	#Drive hard for 1.8 seconds
	time.sleep(1.8)
	upServo()		#Lift the gate -releasing the sample
	drive(0,0)		#Stop
	time.sleep(1)
	drive(-20, 0)	#Drive backwards down the lander
	time.sleep(2)
	drive(0, 0)		#Stop
	midServo()		#Put the servo back down

def laser():  
    reading = 0  
    GPIO.setup(PHOTOCELL, GPIO.OUT)  
    GPIO.output(PHOTOCELL, GPIO.LOW)
    time.sleep(0.1)  
    GPIO.setup(PHOTOCELL, GPIO.IN)  
    while (GPIO.input(PHOTOCELL) == GPIO.LOW):  
        reading += 1  
    return reading

def LED(colour):
	if (colour == 1):
		#Green - going to lander
		GPIO.output(GREEN,GPIO.HIGH)
		GPIO.output(YELLOW,GPIO.LOW)
		GPIO.output(RED,GPIO.LOW)
	elif (colour == 2):
		#Yellow - going to target
		GPIO.output(GREEN,GPIO.LOW)
		GPIO.output(YELLOW,GPIO.HIGH)
		GPIO.output(RED,GPIO.LOW)
	elif (colour == 3):
		#Red - looking for target
		GPIO.output(GREEN,GPIO.LOW)
		GPIO.output(YELLOW,GPIO.LOW)
		GPIO.output(RED,GPIO.HIGH)



def thresh(input_frame, type, total_img):
	#input frame, type (sample, rock, obst, etc), output frame
	gray = input_frame[:, :, 2]		#sets to the 3rd channel of input (greyscale)
	thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)[1]		#converts greyscale to binary
	kernel = np.ones((5,5),np.uint8)	#creates a 5x5 matrix of ones for dilation and erotion
	#dilation = cv2.dilate(thresh,kernel,iterations = 2)		#dilates anything larger than the 5x5 matrix, twice
	erosion = cv2.erode(thresh,kernel,iterations = 1)		#erodes anything larger than the 5x5 matrix, 4 times
	opened = cv2.dilate(erosion,kernel,iterations = 1)		#dilates anything larger than the 5x5 matrix, twice
	blurred_thresh = cv2.GaussianBlur(opened, (5, 5), 0)	#applies gausian blur of 5x5
	cv2.namedWindow("Binary", cv2.WINDOW_NORMAL)
	cv2.imshow("Binary", blurred_thresh)
	#ims = blurred_thresh	#somewhat redundant but smaller variable name
	cnts = cv2.findContours(blurred_thresh, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)		#finds the contours and stores them in cnts
	cnts = imutils.grab_contours(cnts)		#grabs contours from cnts
	i = 0	#used for library ID

	# loop over the contours
	for c in cnts:
		# compute the center of the contour
		M = cv2.moments(c)	#Moments
		cX = int(M["m10"] / M["m00"])#Centre x-coord
		cY = int(M["m01"] / M["m00"])#Centre y-coord
		extrleft = tuple(c[c[:,:,0].argmin()][0])#Left most x-coord
		extrright = tuple(c[c[:,:,0].argmax()][0])#Right most x-coord
		extrtop = tuple(c[c[:, :, 1].argmin()][0])#Top most y-coord
		extrbottom = tuple(c[c[:, :, 1].argmax()][0])#Bottom most y-coord
		x1 = extrleft[0]#Left
		x2 = extrright[0]#Right
		y1 = extrtop[1]#Top
		y2 = extrbottom[1]#Bottom
		w = float(x2 - x1)#Width of object (px)
		h = float(y2 - y1)#Height of object (px)

		#When part of the object is at the lower bounds of the screen
		ratio = h / w	#Calculate the ratio of height to width			
		#if the object exceeds the lower bounds of the screen region
		if (type != 3):
			if ((y2 > 235 or y1 < 5 )and ratio < 0.9 and ratio != 0.0):
				#Divide it by the ratio of height to width
				h = h / ratio		
		
		# compute bearing of the contour
		bearing = round(31.1 * ((cX - (WIDTH/2.0))/(WIDTH/2.0)),3)
		# get height/width of contour
		#x,y,h,w = cv2.boundingRect(c)
		#calculate distance
		if (type == 0):
			#dist(cm) = 0.1 x (focal length(mm) x real sample height(mm) x screen height(px))/(pixel height(px) x sensor height(mm))
			dist = round(0.1*(FOCAL_LEN * SAMPLE_HEIGHT * HEIGHT)/(h * SENSOR_HEIGHT),3)
			cv2.drawContours(total_img, [c], -1, (0, 69, 255), 2)	#Draws bounding box on output img around contour #c
		elif (type == 1):
			dist = round(0.1*(FOCAL_LEN*ROCK_HEIGHT*HEIGHT)/(h*SENSOR_HEIGHT),3)
			cv2.drawContours(total_img, [c], -1, (255, 0, 0), 2)
		elif (type == 2):
			dist = round(0.1*(FOCAL_LEN*OBST_HEIGHT*HEIGHT)/(h*SENSOR_HEIGHT),3)
			cv2.drawContours(total_img, [c], -1, (0, 255, 0), 2)
		elif (type == 3):
			dist = round(0.1*(FOCAL_LEN*LANDER_HEIGHT*HEIGHT)/(h*SENSOR_HEIGHT),3)
			cv2.drawContours(total_img, [c], -1, (0, 255, 255), 2)
		# elif (type == 4):
		# 	dist = round(0.1*(FOCAL_LEN*WALL_HEIGHT*HEIGHT)/(h*SENSOR_HEIGHT),3)
		# 	cv2.drawContours(total_img, [c], -1, (255, 255, 255), 2)

		cv2.circle(total_img, (cX, cY), 3, (150, 150, 150), -1)		#draws a circle at the centre of the contour
		# Displays range and bearing on output img
		cv2.putText(total_img, "R: " + str(dist) + "cm", (cX - 15, cY + 20),
			cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
		cv2.putText(total_img, "B: " + str(bearing), (cX - 15, cY + 30),
			cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

		global Sample_list		#Global needs to be called to store into a global variable
		global Rock_list
		global Obstacle_list
		global Lander_list
		if (type == 0):		#if sample
			sample = Sample(i,dist,bearing,cX,cY)
			Sample_list.append(Sample(i,dist,bearing,cX,cY))	#adds this sample to the class of samples
			del sample
			#Displays "sample" in the centre of the contour
			# cv2.putText(total_img, "Sample", (cX - 15, cY - 20),
			# cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
		elif (type == 1):	#if rock
			rock = Rock(i,dist,bearing,cX,cY)
			Rock_list.append(Rock(i,dist,bearing,cX,cY))
			del rock
			# cv2.putText(total_img, "Rock", (cX - 15, cY - 20),
			# cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
		elif (type == 2):	#if obstacle
			obstacle = Obstacle(i,dist,bearing,cX,cY)
			Obstacle_list.append(Obstacle(i,dist,bearing,cX,cY))
			del obstacle
			# cv2.putText(total_img, "Obstacle", (cX - 15, cY - 20),
			# cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
		elif (type == 3):	#if lander
			lander = Lander(i,dist,bearing,cX,cY)
			Lander_list.append(Lander(i,dist,bearing,cX,cY))
			del lander
			# cv2.putText(total_img, "Lander", (cX - 15, cY - 20),
			# cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
		# elif (type == 4):	#if wall
			# cv2.putText(total_img, "Wall", (cX - 15, cY - 20),
			# cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
		i = i + 1	#add 1 to the ID of object class

	# return total_img		#return output image


def capture():
	# Check if camera opened successfully
	if (cap.isOpened()== False): 
	  print("Error opening video stream or file")

	try: 
		while(cap.isOpened()): 
		# Capture frame-by-frame
			ret, frame = cap.read()
			if ret == True:
				cv2.normalize(frame, frame, 0, 255, cv2.NORM_MINMAX)
				process(frame)
				k = cv2.waitKey(1) & 0xFF

				# exit if q or esc are pressed
				if (k == ord('q') or k == 27):
					break

			else:
				break
	# When everything done, release the video capture object
	finally:
		print("clean")
		GPIO.cleanup() # this ensures a clean exit  
		cap.release()
		cleanUp()

def naviagtion():
	global max_index
	global captured
	neg_field = [0] * WIDTH
	M = 0.01
	scal = 0.002
	if (flipped == 0):	#If a rock hasn't been flipped yet
		if len(Rock_list) > 0:
			#Set a known rock location as the target
			peak = Rock_list[0].cX
			targDist = Rock_list[0].Dist
		else:
			#Set the last known location as the target
			peak = max_index
			targDist = 0.0
	else:	#Once a rock has been flipped
		if (captured == 0):		#If it doesn't have a ball
			if len(Sample_list) > 0:
				#Set a known sample location as the target
				peak = Sample_list[0].cX
				targDist = Sample_list[0].Dist
			else:
				#Set the last known location as the target
				peak = max_index
				targDist = 0.0
		else:		#If it has a ball
			if len(Lander_list) > 0:
				#Set a knwon lander location as the target
				peak = Lander_list[0].cX
				targDist = Lander_list[0].Dist
			else:
				#Set the last known location as the target
				peak = max_index
				targDist = 0.0

	neg_field[peak] = 1
	for i in range(peak-1,0,-1):
		neg_field[i] = M * i - peak * M + 1
	for i in range(peak + 1, WIDTH):
		neg_field[i] = ((i - peak) * -1 * M ) + 1
	for i in range(0, WIDTH):
		if (neg_field[i] < 0):
			neg_field[i] = 0
	u = 0.5 * scal * targDist**2
	uball = [0] * WIDTH
	for i in range(0,len(neg_field)-1):
		uball[i] = u * neg_field[i]


	if max(uball) > 0:
		max_index = uball.index(max(uball))
	bearing = 31.1 * ((max_index - (WIDTH/2.0))/(WIDTH/2.0))

	max_val = 0
	rot = 0
	if (targDist == 0):		#if it cant see the target
		#if last seen on the left
		if (max_index < 160):
			#turn left
			rot = 19
		#if last seen on the right
		else:
			#turn right
			rot = -19
	else:		#if it can see the target
		if (targDist < 15):		#if the target is near
			if (abs(bearing) > 5):	#if not centred - centre
				if bearing > 0:	#if target is on the right
					rot = 15	#turn right
				else:	#if the target is on the left
					rot = -15	#turn left
			else:		#if the target is centred
				#what is targ?
				if flipped == 0:	#If Rock is tagret
					flipRock()
					time.sleep(1)
				else:	#Once rock has been flipped
					if (captured == 0):	#If it doesn't have the ball
						captureBall()
						time.sleep(1)
					else:	#If it has the ball
						returnBall()
						captured = 0
		else:	#Drive to target
			max_val = VEL_SCALE * targDist + VEL_MIN
			rot = round(ROT_SCALE*bearing,2)

	obstaclePeak = []
	obstacleDist = []
	start = datetime.now()
	if (flipped == 1):	#If the rock has been flipped
		#Set the rocks as obstacles
		if (len(Rock_list) > 0):
			for i in range(0, len(Rock_list)):	#For all known rocks
				obstaclePeak.append(Rock_list[i].cX)	#Add it's bearing to the obstacle list
				obstacleDist.append(Rock_list[i].Dist)	#Add it's distance to the obstacle list
	#Set the obstacles as obstacles
	if (len(Obstacle_list) > 0):
		for i in range(0, len(Obstacle_list)):	#For all known obstacles
			obstaclePeak.append(Obstacle_list[i].cX)	#Add it's bearing to the obstacle list
			obstacleDist.append(Obstacle_list[i].Dist)	#Add it's distance to the obstacle list
	#Avoid obstacles
	if (len(obstaclePeak) > 0):
		for j in range(0, len(obstaclePeak)):	#For all the known obstacles
			if obstacleDist[j] < 20:	#If they are less than 20cm away
				print("stop")
				#Stop
				max_val = 0
				rot = 0
				currentTime = datetime.now()
				if ((currentTime.second + (currentTime.microsecond / 1000000) - start.second + (start.microsecond / 1000000)) < 2):
					#if it has been less than 2 sec since last avoiding an obstacle
					if obstaclePeak[j] < 160:	#If the obstacle is on the left
						print("turn right")
						max_index = 1	#Set the target's last known location as on the left
						drive(0, -15)	#Turn right
						time.sleep(1)
						drive(0,0)
						time.sleep(1)
						break
					else:		#If obstacle is on the right
						print("turn left")
						drive(15, 0)	#Turn left
						max_index = 319	#Set the target's last known location on the right
						drive(0, -15)
						time.sleep(1)
						drive(0,0)
						time.sleep(1)
						break

			
	if (captured == 0):
		if(targDist != 0):	#Going towards the target
			LED(2)
		else:	#Looking for the target
			LED(3)
	else:	#Going to the lander
		LED(1)

	drive(max_val, -1*rot)




def process(frame):
	now = time.time()	#start process time
	frame = cv2.rotate(frame, cv2.ROTATE_180)		#rotate the frame 180'
	hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)	#convert rgb to hsv

	#sample has 2 mask because hue wraps from 179 around to 0
	s_mask1 = cv2.inRange(hsv, s_min_arr1, s_max_arr1)		#sample mask 1
	s_mask2 = cv2.inRange(hsv, s_min_arr2, s_max_arr2)		#sample mask 2
	s_mask = s_mask1 + s_mask2		#adds sample masks together
	
	r_mask = cv2.inRange(hsv, r_min_arr, r_max_arr)		#rock mask
	o_mask = cv2.inRange(hsv, o_min_arr, o_max_arr)		#obstacle mask
	l_mask = cv2.inRange(hsv, l_min_arr, l_max_arr)		#lander mask
	b_mask = cv2.inRange(hsv, b_min_arr, b_max_arr)		#wall mask

	blurred = cv2.GaussianBlur(frame, (5, 5), 0)		#blur the frame with a 5x5

	# sample_img1 = cv2.bitwise_and(blurred, blurred, mask= s_mask1)
	# sample_img2 = cv2.bitwise_and(blurred, blurred, mask= s_mask2)
	# sample_img = sample_img1 + sample_img2

	#overlay the mask on the blurred image for bitwise and
	sample_img = cv2.bitwise_and(blurred, blurred, mask= s_mask)
	rock_img = cv2.bitwise_and(blurred, blurred, mask= r_mask)
	obstacle_img = cv2.bitwise_and(blurred, blurred, mask= o_mask)
	lander_img = cv2.bitwise_and(blurred, blurred, mask= l_mask)
	#wall_img = cv2.bitwise_and(blurred, blurred, mask= b_mask)

	# total_img = sample_img + rock_img + obstacle_img
	total_img = frame


	#cv2.imshow("Sample",sample_img)
	# cv2.imshow("Rock", rock_img)
	# cv2.imshow("Obstacle", obstacle_img)
	cv2.namedWindow("Raw", cv2.WINDOW_NORMAL)
	cv2.imshow("Raw", total_img)

	global Sample_list		#Global needs to be called to store into a global variable	
	Sample_list = []
	global Rock_list
	Rock_list = []
	global Obstacle_list
	Obstacle_list = []
	global Lander_list
	Lander_list = []

	#object frame = thresh(input img, obj type, output img)
	sample = thresh(sample_img, 0, total_img)
	#rock = thresh(rock_img, 1, total_img)
	#obstacle = thresh(obstacle_img, 2, total_img)
	#lander = thresh(lander_img, 3, total_img)
	#wall = thresh(wall_img, 4,total_img)

	# draw a line down the centre of the screen
	#cv2.line(total_img, ((int(WIDTH/2)),0), ((int(WIDTH/2)),int(HEIGHT)), (255, 255, 255))
	#cv2.line(total_img, ((int(max_index)),0), ((int(max_index)),int(HEIGHT)), (0, 0, 255))
	
	elapsed = time.time() - now			#end process time
	rate = round(1.0/elapsed,0)			#process rate
	if (rate > FREQUENCY):				#only sleep if process rate is faster than desired freq
		time.sleep(INTERVAL - elapsed)
	elapsed2 = time.time() - now
	rate2 = round(1.0/elapsed2,0)
	print("Rate: ", rate2)
	#Display Frequency in top left corner
	# cv2.putText(total_img, "Frequency: " + str(rate2) + "Hz", (15, 20),
	# 		cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
	naviagtion()
	#cv2.imshow("Total", total_img)		#display final output img


def cleanUp():
	# Closes all the frames
	cv2.destroyAllWindows()
	stop()

def main():
	capture()

if __name__ == '__main__':
	if (init == False):
		bounds()
		#laserSetup()
		offLander()
		init = True
	main()

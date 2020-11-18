# -*- coding: utf-8 -*-
'''
Copyright October 2019 Tuyen Nguyen

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

***

Author:      Tuyen Nguyen
Email:       ngtvtuyen@jaist.ac.jp
Affiliation: Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan
Project:     CARESSES (http://caressesrobot.org/en/)

README
This function let the robot moving forward taking into account the surrounding obstacles
Input parameter:  range of obstacles detection (meter), e.g. apar = float(0.6)

## To run the action without running cahrim.py, from current directory:
## python avoidObstacles.py --ip <PEPPER-IP>
'''

import qi
from naoqi import ALProxy
import math
import sys
import almath
import argparse

class ObstacleDetection(object):
    def __init__(self, apar, cpar, session, IP):
        self.laser = ALProxy("ALLaser", IP, 9559)
        self.memory = ALProxy("ALMemory", IP, 9559)
        self.motion = ALProxy("ALMotion", IP, 9559)
        self.motion.setOrthogonalSecurityDistance(0.25)
        self.motion.setTangentialSecurityDistance(0.25)
        self.laser.laserON()
        self.FrontSensor = "Device/SubDeviceList/Platform/LaserSensor/Front/"
        self.LeftSensor = "Device/SubDeviceList/Platform/LaserSensor/Left/"
        self.RightSensor = "Device/SubDeviceList/Platform/LaserSensor/Right/"
        self.rangeOfDetection = apar
        self.rotation_angle = math.pi/6

    def Obstacle_avoidance(self):
        useSensorValues = False
        initRobotPosition = almath.Pose2D(self.motion.getRobotPosition(useSensorValues))
        if (self.Obstacle_front(self.rangeOfDetection)):
            self.Stop_Move()
            if (self.Obstacle_right(0.7) == 0):
                self.Rotate_To(-math.pi/2)
                while (self.Obstacle_front(self.rangeOfDetection)):
                    self.Rotate_To(-self.rotation_angle)
                self.Forward_To(0.1)
                while ((self.Infared_left == 1) or (self.Obstacle_left(0.5) == 1)): 
                    self.Forward(0.1)
                self.Stop_Move()
                endRobotPosition = almath.Pose2D(self.motion.getRobotPosition(useSensorValues))
                print endRobotPosition
                positionDiff = endRobotPosition.diff(initRobotPosition)
                print positionDiff
                self.Rotate_To(positionDiff.theta)
                return 1
            
            elif (self.Obstacle_left(0.7) == 0):
                self.Rotate_To(math.pi/2)
                while (self.Obstacle_front(self.rangeOfDetection)):
                    self.Rotate_To(self.rotation_angle)
                self.Forward_To(0.1)
                while ((self.Infared_right == 1) or (self.Obstacle_right(0.5) == 1)):
                    self.Forward(0.1)
                self.Stop_Move()
                endRobotPosition = almath.Pose2D(self.motion.getRobotPosition(useSensorValues))
                print endRobotPosition
                positionDiff = endRobotPosition.diff(initRobotPosition)
                print positionDiff.theta
                self.Rotate_To(positionDiff.theta)
                return 1
        else:
            return 1

    def Obstacle_front(self,range_detection): 
        for i in range(1,16):
            x = self.memory.getData(self.FrontSensor+"Horizontal/Seg%02d/X/Sensor/Value"%i)
            y = self.memory.getData(self.FrontSensor+"Horizontal/Seg%02d/Y/Sensor/Value"%i)
            dist = math.sqrt(x*x + y*y)
            if((dist < range_detection)):
                return 1
        return 0
            
    def Obstacle_left(self,range_detection):
        for i in range(1,16):
            x = self.memory.getData(self.LeftSensor+"Horizontal/Seg%02d/X/Sensor/Value"%i)
            y = self.memory.getData(self.LeftSensor+"Horizontal/Seg%02d/Y/Sensor/Value"%i)
            dist = math.sqrt(x*x + y*y)
            if((dist < range_detection)):
                return 1
        return 0

    def Obstacle_right(self,range_detection):
        for i in range(1,16):
            x = self.memory.getData(self.RightSensor+"Horizontal/Seg%02d/X/Sensor/Value"%i)
            y = self.memory.getData(self.RightSensor+"Horizontal/Seg%02d/Y/Sensor/Value"%i)
            dist = math.sqrt(x*x + y*y)
            if(dist < range_detection):
                return 1
        return 0

    def Infared_left(self):
        obstacle = self.memory.getData("Device/SubDeviceList/Platform/InfraredSpot/Left/Sensor/Value")
        if (obstacle):
            return 1
        else:	
            return 0
    
    def Infared_right(self):
        obstacle = self.memory.getData("Device/SubDeviceList/Platform/InfraredSpot/Right/Sensor/Value")
        if (obstacle):
            return 1
        else:	
            return 0
    
    def Forward_To(self,speed):
        self.motion.moveTo(speed,0,0)
        pass

    def Forward(self,speed):
        self.motion.move(speed,0,0)
        pass

    def Rotate_To(self,speed):
        self.motion.moveTo(0,0,speed)
        pass

    def Stop_Move(self):
        self.motion.stopMove()
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="150.65.206.126",
                        help="Robot IP address. On robot or Local Naoqi: use '150.65.205.26'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    args = parser.parse_args()
    session = qi.Session()
    try:
        session.connect("tcp://" + args.ip + ":" + str(args.port))
    except RuntimeError:
        print ("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) +".\n"
               "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)

    apar = float(0.6)
    cpar = None
    action = ObstacleDetection(apar,cpar,session,args.ip)

    try:
        while(True):
            action.Obstacle_avoidance()
            action.Forward(0.2)
    except KeyboardInterrupt:
        print "Interrupted"
        action.Stop_Move()
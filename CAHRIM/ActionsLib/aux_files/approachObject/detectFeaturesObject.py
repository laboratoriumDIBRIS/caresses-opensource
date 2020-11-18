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
This function let the robot searching for target and approaching target at appropriate distance 
'''

import qi
from naoqi import ALProxy
import cv2
import math
import argparse
from collections import deque
import numpy as np
import time 

class ObjectTracking(object):
    def __init__(self, apar, cpar, session, IP):
        self.motionProxy = ALProxy('ALMotion', IP, 9559)
        self.videoDevice = ALProxy('ALVideoDevice', IP, 9559)
        self.motionProxy.setAngles(["HeadPitch","HeadYaw"],[0*math.pi/180, 0*math.pi/180],0.3)
        AL_kTopCamera = 0
        AL_kVGA = 2 # 640X480
        AL_khsYColorSpace = 8	
        FRAMERATE = 30
        self.captureDevice = self.videoDevice.subscribeCamera(
            "front camera", AL_kTopCamera, AL_kVGA, AL_khsYColorSpace, FRAMERATE)
        
        ref_image, self.threshold = apar.split(" ")
        self.desired_area, self.speed = cpar.split(" ")
        self.img1 = cv2.imread(str(ref_image),0)      
        self.threshold = int(self.threshold)
        self.desired_area = int(self.desired_area)
        self.speed = float(self.speed)
        self.sift = cv2.xfeatures2d.SIFT_create()
        self.kp1, self.des1 = self.sift.detectAndCompute(self.img1,None)
        self.width = 640 
        self.height = 480 
        self.try_again = 0
        self.flag_object_detected = False

    def ObjTracking(self):
        min_area = 80
        FLANN_INDEX_KDTREE = 0
        index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
        search_params = dict(checks = 50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        image = np.zeros((self.height, self.width), np.uint8)
        try:
            while(True):
                result = self.videoDevice.getImageRemote(self.captureDevice);
                if result == None:
                    print 'cannot capture.'
                elif result[6] == None:
                    print 'no image data string.'
                else:
                    values = map(ord, list(result[6]))
                    i = 0
                    for y in range(0, self.height):
                        for x in range(0, self.width):
                            image.itemset((y, x), values[i])
                            i += 1 
                kp2, des2 = self.sift.detectAndCompute(image,None)
                matches = flann.knnMatch(self.des1,des2,k=2)
                good = []
                self.flag_object_detected = False
                for m,n in matches:
                    if m.distance < 0.7*n.distance:
                        good.append(m)
                if len(good) > self.threshold:
                    src_pts = np.float32([ self.kp1[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
                    dst_pts = np.float32([ kp2[m.trainIdx].pt for m in good ]).reshape(-1,1,2)
                    M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC,5.0)
                    matchesMask = mask.ravel().tolist()
                    h,w = self.img1.shape
                    pts = np.float32([ [0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(-1,1,2)
                    if np.shape(M):
                        dst = cv2.perspectiveTransform(pts,M)
                        # image = cv2.polylines(image,[np.int32(dst)],True,(0,255,0),3, cv2.LINE_AA)
                        self.flag_object_detected = True
                        pos = (dst[0]+dst[1]+dst[2]+dst[3])/4
                        l_12 = math.sqrt((dst[0][0,0]-dst[1][0,0])**2 + (dst[0][0,1]-dst[1][0,1])**2)
                        l_23 = math.sqrt((dst[1][0,0]-dst[2][0,0])**2 + (dst[1][0,1]-dst[2][0,1])**2)
                        l_34 = math.sqrt((dst[2][0,0]-dst[3][0,0])**2 + (dst[2][0,1]-dst[3][0,1])**2)
                        l_41 = math.sqrt((dst[3][0,0]-dst[0][0,0])**2 + (dst[3][0,1]-dst[0][0,1])**2)
                        area = l_12 + l_23 + l_34 + l_41
                        self.try_again = 0
                        if (pos[0,0] < 0):
                            pos[0,0] = 0
                        if (pos[0,1] < 0):
                            pos[0,1] = 0
                        if pos[0,0] < (self.width)/5:
                            self.Rotate(math.pi/20) 
                        elif pos[0,0] > (4*self.width)/5:
                            self.Rotate(-math.pi/20) 
                        else:
                            if (area > min_area) and (area < self.desired_area) and (pos[0,0] >= (self.width)/5 ) and (pos[0,0] <= (4*self.width)/5 ):
                                self.Forward(self.speed)
                                if pos[0,1] < 180:
                                    self.TurningHead(-2*math.pi/180)
                                elif pos[0,1] > 300:
                                    self.TurningHead(2*math.pi/180)
                            else:
                                self.Stop_Move()
                                return 1

                if (not self.flag_object_detected):
                    self.Stop_Move()
                    if (self.try_again < 4):
                        self.try_again = self.try_again + 1
                    elif (self.try_again >= 4):
                        self.RotateTo(math.pi/6)
                        self.try_again = 0           
                # cv2.imshow("pepper-top-camera-640x480", image)
                # key = cv2.waitKey(1) & 0xFF

        except KeyboardInterrupt:
            print "Interrupted by user"
            self.videoDevice.unsubscribe(self.captureDevice);

    def Rotate(self,speed):
        self.motionProxy.move(0,0,speed)
        pass

    def RotateTo(self,speed):
        self.motionProxy.moveTo(0,0,speed)
        pass

    def Forward(self,speed):
        self.motionProxy.move(speed,0,0)
        pass

    def TurningHead(self,angle):
        self.motionProxy.changeAngles("HeadPitch",angle,0.05)
        pass

    def Stop_Move(self):
        self.motionProxy.stopMove()
        pass

    def stop(self):
        self.videoDevice.unsubscribe(self.captureDevice)
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="150.65.205.196",
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

    apar = "RefImage_1.png" + " 8" 
    cpar = "600" + " 0.2"

    action = ObjectTracking(apar,cpar,session,args.ip)
    result = action.ObjTracking()
    print "result: %s" %result
    action.stop()

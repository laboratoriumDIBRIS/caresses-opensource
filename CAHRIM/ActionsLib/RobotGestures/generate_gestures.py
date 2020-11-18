# -*- coding: utf-8 -*-
'''
Copyright December 2019 Tuyen Nguyen

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

Python version: 2.7

README
The action receives the text input and producing the robot's gestures associated with the robot speech.

Dependencies: tensroflow, theano, numpy, scipy, math, pickle, nltk
'''

import tensorflow as tf
import numpy as np
import os
from Utils import ops
import pickle
import time
import skipthoughts
from threading import Thread
import argparse
import qi
import sys
import math
from struct_model import decode_motion_format, filter_data, generator, processing_data
from naoqi import ALProxy

class RobotSpeech(Thread):
    def __init__(self, session, robot_IP, robot_PORT):

        Thread.__init__(self)
        self.alive = True

        # Initialize NAOqi services    
        self.tts_service = session.service("ALTextToSpeech")
        self.tts_service.setLanguage("English")
        self.tts_service.setParameter("speed", 70)
        self.memory = session.service("ALMemory")
        self.subscriber = self.memory.subscriber("PepperSpeech")
        self.subscriber.signal.connect(self.on_Pepper_Speech)

    def on_Pepper_Speech(self,annotation):
        annotation = str(annotation)
        annotation = annotation.strip("[]")
        time.sleep(1)
        self.tts_service.say(annotation)

    def run(self):
        try:
            while self.alive:
                time.sleep(0.2)
        except KeyboardInterrupt:
            print("Interrupted by user, stopping RobotSpeech")
            sys.exit(0)

    def stop(self):
        self.alive = False

class GenerateRobotGesture(object):

    def __init__(self, session, robot_IP, robot_PORT, ref_joints_path, model_path, skipthoughts_path):
        
        self.memory = session.service("ALMemory")
        self.motion = ALProxy("ALMotion", robot_IP, robot_PORT)
        self.robot_joints = ['HeadYaw', 'HeadPitch', 'HipRoll', 'HipPitch', 'KneePitch', 
            'LShoulderPitch', 'LShoulderRoll', 'LElbowYaw', 'LElbowRoll', 'LWristYaw', 'LHand',
            'RShoulderPitch','RShoulderRoll','RElbowYaw','RElbowRoll','RWristYaw','RHand']
        self.fractionMaxSpeed=0.20
        self.time_delay=0.04
        
        # Initialize the pre-trained models
        self.ref_joints_path = ref_joints_path + "ref_joints.pickle"
        self.model_path = model_path + "model.ckpt"

        self.caption_embedding_size = 2400
        self.t_z = tf.placeholder(tf.float32, shape=(None, 100))
        self.t_real_caption = tf.placeholder(tf.float32, shape=(None, self.caption_embedding_size))
        self.G_z = generator(self.t_z, self.t_real_caption)
        self.sess = tf.InteractiveSession()
        saver = tf.train.Saver()
        saver.restore(self.sess, self.model_path)

        self.embedding_model = skipthoughts.load_model(skipthoughts_path)

    def run(self):

        print("Type the input text...")
        print("Type exit to stop the action.")
        sys.stdout.write("> ")
        sys.stdout.flush()
        self.input_text = sys.stdin.readline()

        while self.input_text:
            if (self.input_text.strip() == "exit") :
                break

            description = [self.input_text.strip()]
            encoded_discriptions = skipthoughts.encode(self.embedding_model, description)[:,0:self.caption_embedding_size]
            z_noise = np.random.normal(0, 1, (1, 100))
            generated_gesture = self.sess.run([self.G_z], feed_dict={self.t_z: z_noise, self.t_real_caption: encoded_discriptions})
            self.memory.raiseEvent("PepperSpeech", self.input_text)
            generated_gesture = generated_gesture[0]
            generated_gesture = np.swapaxes(generated_gesture, 1, 2)
            generated_gesture = decode_motion_format(generated_gesture)[0]
            generated_gesture = filter_data(generated_gesture, window_size=7)
            generated_gesture = processing_data(generated_gesture[5:150])
            print(np.shape(generated_gesture))
            self.sendToPepper(generated_gesture, self.fractionMaxSpeed, self.time_delay)
            self.home(fractionMaxSpeed_home=0.1, time_home=0.3)
            print "> ",
            sys.stdout.flush()
            self.input_text = sys.stdin.readline()
                

    def sendToPepper(self, data, fractionMaxSpeed, time_delay):
        for i in range(0,len(data)):
            sent_data =  ([data[i][0], data[i][1], data[i][2], data[i][3], data[i][4], 
                        data[i][5], data[i][6], data[i][7], data[i][8], data[i][9], data[i][10],
                        data[i][11], data[i][12], data[i][13], data[i][14], data[i][15], data[i][16]])
            self.motion.setAngles(self.robot_joints,sent_data,fractionMaxSpeed)
            time.sleep(time_delay)
        return 1

    def home(self, fractionMaxSpeed_home, time_home):
        time.sleep(time_home)
        degree = math.pi/180
        HeadYaw=0*degree
        HeadPitch=0*degree
        HipRoll=-0.3*degree
        HipPitch=-1.8*degree
        LShoulderPitch=89.6*degree
        LShoulderRoll=8.1*degree
        LElbowYaw=-70.9*degree
        LElbowRoll=-29.9*degree
        LWristYaw=0*degree
        LHand = 0.9
        RShoulderPitch=89.6*degree
        RShoulderRoll=-8.6*degree
        RElbowYaw=70.6*degree
        RElbowRoll=29.9*degree
        RWristYaw=0*degree
        RHand = 0.9
        KneePitch = 0*degree

        sent_data =  (HeadYaw, HeadPitch, HipRoll, HipPitch, KneePitch,
                    LShoulderPitch, LShoulderRoll, LElbowYaw, LElbowRoll, LWristYaw, LHand,
                    RShoulderPitch, RShoulderRoll, RElbowYaw, RElbowRoll, RWristYaw, RHand)
        self.motion.setAngles(self.robot_joints,sent_data,fractionMaxSpeed_home)
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default='150.65.205.103',
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    args = parser.parse_args()

    try:
        # Initialize qi framework.
        session = qi.Session()
        session.connect("tcp://" + args.ip + ":" + str(args.port))
        print("\nConnected to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) + ".\n")

    except RuntimeError:
        print ("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) + ".\n"
                                                                                              "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)

    args = parser.parse_args()
    robot_IP = args.ip
    robot_PORT = args.port

    ref_joints_path = "./data/"
    model_path = "./model/"
    skipthoughts_path = "./data/skipthoughts/"

    t = RobotSpeech(session, robot_IP, robot_PORT)
    t.start()

    action = GenerateRobotGesture(session, robot_IP, robot_PORT, ref_joints_path, model_path, skipthoughts_path)
    action.run()

    t.stop()
    print("Sucessfully stop the action")

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

'''

import tensorflow as tf
import numpy as np
from Utils import ops
from scipy import signal
import math
from numpy import linalg as LA


def lrelu(X, leak=0.2):
    f1 = 0.5 * (1 + leak)
    f2 = 0.5 * (1 - leak)
    return f1 * X + f2 * tf.abs(X)

def decode_motion_format(data):
    
    data_x = data[:,:,:,0]
    C7_x = (data_x[:,:,0]+data_x[:,:,4]+data_x[:,:,8]+data_x[:,:,14]+data_x[:,:,20]+data_x[:,:,38]+data_x[:,:,39])/7.0
    RFHD_x = (data_x[:,:,1] + data_x[:,:,3])/2.0 
    RBHD_x = (data_x[:,:,2]) 
    LFHD_x = (data_x[:,:,5] + data_x[:,:,7])/2.0 
    LBHD_x = (data_x[:,:,6]) 
    RSHO_x = (data_x[:,:,9] + data_x[:,:,13])/2.0 
    RELB_x = (data_x[:,:,10] + data_x[:,:,12])/2.0 
    RFIN_x = (data_x[:,:,11]) 
    LSHO_x = (data_x[:,:,15] + data_x[:,:,19])/2.0
    LELB_x = (data_x[:,:,16] + data_x[:,:,18])/2.0 
    LFIN_x = (data_x[:,:,17])
    CLAV_x = (data_x[:,:,21] + data_x[:,:,37])/2.0 
    STRN_x = (data_x[:,:,22] + data_x[:,:,36])/2.0 
    T10_x = (data_x[:,:,23] + data_x[:,:,29] + data_x[:,:,35])/3.0 
    RFWT_x = (data_x[:,:,24] + data_x[:,:,28])/2.0 
    RBWT_x = (data_x[:,:,25] + data_x[:,:,27])/2.0 
    RKNE_x = (data_x[:,:,26]) 
    LFWT_x = (data_x[:,:,30] + data_x[:,:,34])/2.0 
    LBWT_x = (data_x[:,:,31] + data_x[:,:,33])/2.0
    LKNE_x = (data_x[:,:,32])

    data_y = data[:,:,:,1]
    C7_y = (data_y[:,:,0]+data_y[:,:,4]+data_y[:,:,8]+data_y[:,:,14]+data_y[:,:,20]+data_y[:,:,38]+data_y[:,:,39])/7.0 
    RFHD_y = (data_y[:,:,1] + data_y[:,:,3])/2.0
    RBHD_y = (data_y[:,:,2]) 
    LFHD_y = (data_y[:,:,5] + data_y[:,:,7])/2.0
    LBHD_y = (data_y[:,:,6]) 
    RSHO_y = (data_y[:,:,9] + data_y[:,:,13])/2.0 
    RELB_y = (data_y[:,:,10] + data_y[:,:,12])/2.0 
    RFIN_y = (data_y[:,:,11]) 
    LSHO_y = (data_y[:,:,15] + data_y[:,:,19])/2.0 
    LELB_y = (data_y[:,:,16] + data_y[:,:,18])/2.0
    LFIN_y = (data_y[:,:,17]) 
    CLAV_y = (data_y[:,:,21] + data_y[:,:,37])/2.0 
    STRN_y = (data_y[:,:,22] + data_y[:,:,36])/2.0 
    T10_y = (data_y[:,:,23] + data_y[:,:,29] + data_y[:,:,35])/3.0 
    RFWT_y = (data_y[:,:,24] + data_y[:,:,28])/2.0 
    RBWT_y = (data_y[:,:,25] + data_y[:,:,27])/2.0 
    RKNE_y = (data_y[:,:,26])
    LFWT_y = (data_y[:,:,30] + data_y[:,:,34])/2.0
    LBWT_y = (data_y[:,:,31] + data_y[:,:,33])/2.0
    LKNE_y = (data_y[:,:,32]) 

    data_z = data[:,:,:,2]
    C7_z = (data_z[:,:,0]+data_z[:,:,4]+data_z[:,:,8]+data_z[:,:,14]+data_z[:,:,20]+data_z[:,:,38]+data_z[:,:,39])/7.0 
    RFHD_z = (data_z[:,:,1] + data_z[:,:,3])/2.0
    RBHD_z = (data_z[:,:,2]) 
    LFHD_z = (data_z[:,:,5] + data_z[:,:,7])/2.0 
    LBHD_z = (data_z[:,:,6])
    RSHO_z = (data_z[:,:,9] + data_z[:,:,13])/2.0 
    RELB_z = (data_z[:,:,10] + data_z[:,:,12])/2.0 
    RFIN_z = (data_z[:,:,11]) 
    LSHO_z = (data_z[:,:,15] + data_z[:,:,19])/2.0 
    LELB_z = (data_z[:,:,16] + data_z[:,:,18])/2.0 
    LFIN_z = (data_z[:,:,17]) 
    CLAV_z = (data_z[:,:,21] + data_z[:,:,37])/2.0
    STRN_z = (data_z[:,:,22] + data_z[:,:,36])/2.0 
    T10_z = (data_z[:,:,23] + data_z[:,:,29] + data_z[:,:,35])/3.0 
    RFWT_z = (data_z[:,:,24] + data_z[:,:,28])/2.0 
    RBWT_z = (data_z[:,:,25] + data_z[:,:,27])/2.0 
    RKNE_z = (data_z[:,:,26]) 
    LFWT_z = (data_z[:,:,30] + data_z[:,:,34])/2.0 
    LBWT_z = (data_z[:,:,31] + data_z[:,:,33])/2.0
    LKNE_z = (data_z[:,:,32]) 

    C7   = np.stack((C7_x,C7_y,C7_z), axis=2)
    CLAV = np.stack((CLAV_x,CLAV_y,CLAV_z), axis=2)
    T10  = np.stack((T10_x,T10_y,T10_z), axis=2)
    STRN = np.stack((STRN_x,STRN_y,STRN_z), axis=2)
    LSHO = np.stack((LSHO_x,LSHO_y,LSHO_z), axis=2)
    LELB = np.stack((LELB_x,LELB_y,LELB_z), axis=2)
    LFIN = np.stack((LFIN_x,LFIN_y,LFIN_z), axis=2)
    RSHO = np.stack((RSHO_x,RSHO_y,RSHO_z), axis=2)
    RELB = np.stack((RELB_x,RELB_y,RELB_z), axis=2)
    RFIN = np.stack((RFIN_x,RFIN_y,RFIN_z), axis=2)
    LFWT = np.stack((LFWT_x,LFWT_y,LFWT_z), axis=2)
    LBWT = np.stack((LBWT_x,LBWT_y,LBWT_z), axis=2)
    LKNE = np.stack((LKNE_x,LKNE_y,LKNE_z), axis=2)
    RFWT = np.stack((RFWT_x,RFWT_y,RFWT_z), axis=2)
    RBWT = np.stack((RBWT_x,RBWT_y,RBWT_z), axis=2)
    RKNE = np.stack((RKNE_x,RKNE_y,RKNE_z), axis=2)
    LBHD = np.stack((LBHD_x,LBHD_y,LBHD_z), axis=2)
    LFHD = np.stack((LFHD_x,LFHD_y,LFHD_z), axis=2)
    RBHD = np.stack((RBHD_x,RBHD_y,RBHD_z), axis=2)
    RFHD = np.stack((RFHD_x,RFHD_y,RFHD_z), axis=2)

    original_data = np.concatenate((C7, CLAV, T10, STRN, LSHO, LELB, LFIN, RSHO, RELB, RFIN, LFWT, LBWT, LKNE, RFWT, RBWT, RKNE, LBHD, LFHD, RBHD, RFHD), axis=2)

    return original_data 
    
def generator(t_z, t_text_embedding):
    with tf.variable_scope('generator', reuse=False):
        reduce_embedding_size = 256
        reduced_text_embedding = ops.lrelu( ops.linear(t_text_embedding, reduce_embedding_size, 'g_embedding')) 
        z_concat = tf.concat([t_z, reduced_text_embedding], axis=1)
        z_concat = ops.linear(z_concat, 64*8*3*13, 'g_h0_lin')

        w_init = tf.truncated_normal_initializer(mean=0.0, stddev=0.02)
        b_init = tf.constant_initializer(0.0)

        x = tf.reshape(z_concat, [-1, 3, 13, 64*8])
        x = tf.contrib.layers.batch_norm(x)
        x = lrelu(x)

        x= tf.layers.conv2d_transpose(x, filters=256, kernel_size=[3, 6], strides=[1, 2], padding='valid', kernel_initializer=w_init, bias_initializer=b_init)
        x = tf.contrib.layers.batch_norm(x)
        x = lrelu(x)

        x= tf.layers.conv2d_transpose(x, filters=128, kernel_size=[4, 6], strides=[2, 2], padding='same', kernel_initializer=w_init, bias_initializer=b_init)
        x = tf.contrib.layers.batch_norm(x)
        x = lrelu(x)

        x= tf.layers.conv2d_transpose(x, filters=64, kernel_size=[4, 6], strides=[2, 2], padding='same', kernel_initializer=w_init, bias_initializer=b_init)
        x = tf.contrib.layers.batch_norm(x)
        x = lrelu(x)
        
        x= tf.layers.conv2d_transpose(x, filters=3, kernel_size=[4, 6], strides=[2, 2], padding='same', kernel_initializer=w_init, bias_initializer=b_init)
        x = tf.nn.tanh(x)

        return x

def filter_data(motion_data, window_size=8):
    a = 2
    b = (1/window_size)*np.ones((1, window_size))
    for i in range(np.shape(motion_data)[1]):
        motion_data[0:-1,i] = signal.convolve(motion_data[0:-1,i], np.squeeze(np.ones((window_size,1))/window_size), mode='same')
    return motion_data


def RotationZ(theta):
    R_z = np.array([[math.cos(theta),    -math.sin(theta),    0],
            [math.sin(theta),    math.cos(theta),     0],
            [0,                     0,                      1]
            ])
    return np.mat(R_z)

def NormalizeVector(vector):
    norm = LA.norm(vector)
    vector = np.array([vector[0]/norm, vector[1]/norm, vector[2]/norm])
    return vector

def processing_data(data, scale_f = 1000.0):
    data = np.array(data).astype("float")
    data = data*scale_f
    degree = math.pi/180
    HeadYaw=0*degree
    HeadPitch=0*degree
    HipRoll=-0.1*degree
    HipPitch=-2.1*degree
    LShoulderPitch=89.6*degree
    LShoulderRoll=8.1*degree
    LElbowYaw=-70.9*degree
    LElbowRoll=-6.3*degree
    LWristYaw=0*degree
    LHand = 0.9
    RShoulderPitch=100.1*degree
    RShoulderRoll=-5.8*degree
    RElbowYaw=96.5*degree
    RElbowRoll=5.4*degree
    RWristYaw=0*degree
    RHand = 0.9

    Pepper_data = np.array([HeadYaw, HeadPitch, HipRoll, HipPitch, 0,
                            LShoulderPitch, LShoulderRoll, LElbowYaw, LElbowRoll, LWristYaw, LHand,
                            RShoulderPitch, RShoulderRoll, RElbowYaw, RElbowRoll, RWristYaw, RHand])

    for rows in range(np.shape(data)[0]):
        left_hand = data[rows,6*3:6*3+3] 
        left_hand = RotationZ(math.pi/2)*left_hand.reshape((-1,1))
        left_hand = np.array(left_hand).flatten()

        right_hand = data[rows,9*3:9*3+3] 
        right_hand = RotationZ(math.pi/2)*right_hand.reshape((-1,1))
        right_hand = np.array(right_hand).flatten()


        left_shoulder = data[rows,4*3:4*3+3] 
        left_shoulder = RotationZ(math.pi/2)*left_shoulder.reshape((-1,1))
        left_shoulder = np.array(left_shoulder).flatten()


        right_shoulder = data[rows,7*3:7*3+3] 
        right_shoulder = RotationZ(math.pi/2)*right_shoulder.reshape((-1,1))
        right_shoulder = np.array(right_shoulder).flatten()


        left_elbow = data[rows,5*3:5*3+3] 
        left_elbow = RotationZ(math.pi/2)*left_elbow.reshape((-1,1))
        left_elbow = np.array(left_elbow).flatten()


        right_elbow = data[rows,8*3:8*3+3] 
        right_elbow = RotationZ(math.pi/2)*right_elbow.reshape((-1,1))
        right_elbow = np.array(right_elbow).flatten()


        neck = (data[rows,0*3:0*3+3] + data[rows,1*3:1*3+3])/2 
        neck = RotationZ(math.pi/2)*neck.reshape((-1,1))
        neck = np.array(neck).flatten()


        left_hip = (data[rows,10*3:10*3+3] + data[rows,11*3:11*3+3])/2 
        left_hip = RotationZ(math.pi/2)*left_hip.reshape((-1,1))
        left_hip = np.array(left_hip).flatten()


        right_hip = (data[rows,13*3:13*3+3] + data[rows,14*3:14*3+3])/2 
        right_hip = RotationZ(math.pi/2)*right_hip.reshape((-1,1))
        right_hip = np.array(right_hip).flatten()


        torsor = (data[rows,2*3:2*3+3] + data[rows,3*3:3*3+3])/2 
        torsor = RotationZ(math.pi/2)*torsor.reshape((-1,1))
        torsor = np.array(torsor).flatten()


        right_knee = data[rows,15*3:15*3+3]
        right_knee = RotationZ(math.pi/2)*right_knee.reshape((-1,1))
        right_knee = np.array(right_knee).flatten()

        left_right_hip = np.subtract(right_hip,left_hip)
        torsor_right_hip = np.subtract(right_hip,neck) 

        z_ref = np.cross(left_right_hip,torsor_right_hip)
        z_ref = z_ref/np.linalg.norm(z_ref)

        x_ref = left_right_hip/np.linalg.norm(left_right_hip)

        y_ref = np.cross(z_ref,x_ref)

        x_ref = NormalizeVector(x_ref)
        y_ref = NormalizeVector(y_ref)
        z_ref = NormalizeVector(z_ref)

        left_shoulder_elbow = np.subtract(left_elbow,left_shoulder)
        left_shoulder_neck = np.subtract(right_shoulder,left_shoulder)
        left_shoulder_elbow = NormalizeVector(left_shoulder_elbow)
        left_shoulder_neck = NormalizeVector(left_shoulder_neck)
        left_shoulder_angle_roll = 0
        left_shoulder_angle_roll = math.acos(np.dot(left_shoulder_elbow,left_shoulder_neck))
        LShoulderRoll = left_shoulder_angle_roll - math.pi/2

        left_elbow_hand = np.subtract(left_hand,left_elbow)
        left_elbow_shoulder = np.subtract(left_shoulder,left_elbow)
        left_elbow_hand = NormalizeVector(left_elbow_hand)
        left_elbow_shoulder = NormalizeVector(left_elbow_shoulder)
        left_shoulder_angle_pitch =0

        left_shoulder_angle_pitch = math.acos(np.dot(y_ref,left_elbow_shoulder))
        LShoulderPitch = left_shoulder_angle_pitch - math.pi/2 

        left_elbow_angle_roll = 0
        left_elbow_angle_roll = math.acos(np.dot(left_elbow_shoulder,left_elbow_hand))
        left_elbow_angle_roll = left_elbow_angle_roll - math.pi
        LElbowRoll = left_elbow_angle_roll + 0.35

        left_elbow_angle_yaw = 0
        left_elbow_angle_yaw = (left_elbow_hand[2]/ math.sin(left_elbow_angle_roll))*math.pi/2
        # if left_elbow_angle_yaw > 1.5 :
        #     left_elbow_angle_yaw = 1.5
        # if left_elbow_angle_yaw < -1.5 :
        #     left_elbow_angle_yaw = -1.5

        if (left_hand[2] < torsor[2]):
            left_elbow_angle_yaw = 0
        LElbowYaw = left_elbow_angle_yaw

        right_shoulder_elbow = np.subtract(right_elbow,right_shoulder)
        right_shoulder_neck = np.subtract(left_shoulder,right_shoulder)
        right_shoulder_elbow = NormalizeVector(right_shoulder_elbow)
        right_shoulder_neck = NormalizeVector(right_shoulder_neck)
        right_shoulder_angle_roll =0
        right_shoulder_angle_roll = math.acos(np.dot(right_shoulder_elbow,right_shoulder_neck))
        right_shoulder_angle_roll = -(right_shoulder_angle_roll - math.pi/2)
        RShoulderRoll = right_shoulder_angle_roll

        right_elbow_hand = np.subtract(right_hand,right_elbow)
        right_elbow_shoulder = np.subtract(right_shoulder,right_elbow)
        right_elbow_hand = NormalizeVector(right_elbow_hand)
        right_elbow_shoulder = NormalizeVector(right_elbow_shoulder)
        right_shoulder_angle_pitch = 0
        right_shoulder_angle_pitch = math.acos(np.dot(y_ref,right_elbow_shoulder))
        RShoulderPitch = right_shoulder_angle_pitch - math.pi/2 

        right_elbow_angle_roll = 0
        right_elbow_angle_roll = math.acos(np.dot(right_elbow_hand,right_elbow_shoulder))
        right_elbow_angle_roll = -(right_elbow_angle_roll - math.pi)
        RElbowRoll = right_elbow_angle_roll - 0.35

        right_elbow_angle_yaw = 0
        right_elbow_angle_yaw = (right_elbow_hand[2] / math.sin(right_elbow_angle_roll))*math.pi/2
        # if (right_elbow_angle_yaw > 1.5):
        #     right_elbow_angle_yaw = 1.5
        # if (right_elbow_angle_yaw < -1.5):
        #     right_elbow_angle_yaw = -1.5

        if (right_hand[2] < torsor[2]):
            right_elbow_angle_yaw = 0
        RElbowYaw = right_elbow_angle_yaw

        Hip_Roll = math.acos(np.dot(right_shoulder_neck,y_ref)) 
        HipRoll = -(Hip_Roll - math.pi/2)
        if (HipRoll > 5*math.pi/36):
            HipRoll = 5*math.pi/36
        if (HipRoll < -5*math.pi/36):
            HipRoll = -5*math.pi/36

        centralHip_neck = np.subtract(right_hip,right_knee)
        centralHip_neck = NormalizeVector(centralHip_neck)
        Hip_Pitch = math.acos(np.dot(centralHip_neck,z_ref))
        HipPitch = -(Hip_Pitch - math.pi/2)
        if (Hip_Pitch > 5*math.pi/36):
            Hip_Pitch = 5*math.pi/36
        if (Hip_Pitch < -5*math.pi/36):
            Hip_Pitch = -5*math.pi/36

        Pepper_row_data = np.hstack((HeadYaw, HeadPitch, HipRoll, HipPitch, 0,
                    LShoulderPitch, LShoulderRoll, LElbowYaw, LElbowRoll, LWristYaw, LHand,
                    RShoulderPitch, RShoulderRoll, RElbowYaw, RElbowRoll, RWristYaw, RHand))
        Pepper_data = np.vstack((Pepper_data,Pepper_row_data))

    return Pepper_data

# -*- coding: utf-8 -*-
'''
Copyright October 2019 Maxime Busy & Roberto Menicatti & Università degli Studi di Genova

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

Author:      Maxime Busy (1), Roberto Menicatti (2)
Email:       (1) mbusy@softbankrobotics.com (2) roberto.menicatti@dibris.unige.it
Affiliation: (1) SoftBank Robotics, Paris, France (2) Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import threading
import math
import sys
sys.path.append("..")
from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech
from CahrimThreads.sensory_hub import DetectUserDepth, Person
import time

console_outputs = {
    0 : ["Looking for the user...", 0],
    1 : ["User found at: x %f, y %f, z %f. Approaching user...", 0]
}


## Action "Greet".
#
#  Pepper greets the user. This action shouldn't be executed standalone; its child classes should be used instead.
class Greet(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    def __init__(self, apar, cpar, session):
        Action.__init__(self, apar, cpar, session)

        self.ENGLISH_TAG  = "English"
        self.JAPANESE_TAG = "Japanese"
        self.INDIAN_TAG   = "Indian"

        self.WAVE_TAG     = "Wave"
        self.NAMASTE_TAG  = "Namaste"
        self.BOW_TAG      = "Bow"

        self.tts             = session.service("ALTextToSpeech")
        self.postureService  = session.service("ALRobotPosture")
        self.behaviorService = session.service("ALBehaviorManager")
        self.languageTag     = self.ENGLISH_TAG
        self.animationTag    = self.WAVE_TAG
        self.username        = ""
        self.content         = ""
        self.using_face_reco = DetectUserDepth.isUsingFaceRecognition()
        self.try_again = 0
        self.repeatedTimes = 5
        self.lookingUser = False
        self.motion_service = session.service("ALMotion")
        self.is_stopped = False

        self.volume = None
        self.speed = None
        self.pitch = None


    def setRobotLanguage(self):
        """
        Sets the robot language, checks if the desired language is supported
        """

        try:
            assert self.languageTag in self.tts.getSupportedLanguages()
            self.tts.setLanguage(self.languageTag)

        except AssertionError:
            self.logger.warning(self.languageTag + " is not supported by the robot, language set "\
                "to English")

            self.tts.setLanguage(self.ENGLISH_TAG)



    def setVoiceVolume(self, volume):
        """
        Sets the volume of the tts

        Parameters
            volume - The volume, between 0 and 100
        """

        try:
            assert volume >= 0 and volume <= 1.0

        except AssertionError:
            self.logger.warning("Incorrect volume, 0.5 taken into account")
            volume = 0.5

        self.tts.setVolume(volume)



    def setVoiceSpeed(self, speed):
        """
        Set the speed of the robot's voice

        Parameters:
            speed - The speed of the voice, between 50 and 400
        """

        try:
            assert speed >= 50 and speed <= 400

        except AssertionError:
            self.logger.warning("incorrect voice speed, resesting to the default speed")
            speed = 100

        self.tts.setParameter("speed", speed)



    def setVoicePitch(self, pitch):
        """
        Sets the pitch of the robot's voice

        Parameters:
            pitch - The pitch (shift) 1.0 to 4, 0 disables the effect.
        """

        try:
            assert (pitch >= 1.0 and pitch <= 4) or pitch == 0
            self.tts.setParameter("pitchShift", pitch)

        except AssertionError:
            self.logger.warning("Incorrect pitch value, the pitch won't be modified")



    def playGreetingAnimation(self):
        """
        Plays the greeting animation corresponding to the cultural parameters
        (language)
        """

        if self.animationTag == self.WAVE_TAG:
            self.greetWaveHand()

        elif self.animationTag == self.BOW_TAG:
            self.greetBow()

        elif self.animationTag == self.NAMASTE_TAG:
            self.greetNamaste()



    def greetBow(self):
        """
        Plays the lean forward bowing animation
        """

        self.behaviorService.startBehavior("caresses/leanforwardorbowing")



    def greetNamaste(self):
        """
        Plays the namaste animation
        """

        self.behaviorService.startBehavior("caresses/namaste")



    def greetWaveHand(self):
        """
        Plays the lean forward bowing animation
        """

        self.behaviorService.startBehavior("caresses/greetingsuk_silent")

    ## Look for the user.
    def lookForUser(self):
        while not self.is_stopped:

            if self.using_face_reco:
                if Person.isUserPresent():
                    depth, y, z = DetectUserDepth.getUserPosition()
                else:
                    depth, y, z = None, None, None
            else:
                depth, y, z = DetectUserDepth.getUserPosition()

            if (depth):
                self.try_again = 0
                if abs(y) > 0.1:
                    self.refine(y)
                else:
                    self.stopMove()
                    self.is_stopped = True
                    time.sleep(2)
                
            else:
                if (self.try_again < self.repeatedTimes):
                    self.try_again = self.try_again + 1
                    time.sleep(0.5)
                else:
                    if console_outputs[0][1] == 0:
                        self.logger.info(console_outputs[0][0])
                        console_outputs[0][1] = 1
                        console_outputs[1][1] = 0
                    self.rotate(0.2)
                    self.lookingUser = True

    ## Rotate Pepper by the angle specified by the radian parameter.
    #  @param radian Angle in radians.
    def rotate(self, radian):
        self.motion_service.move(0,0,radian)

    ## Stop any Pepper motion.
    def stopMove(self):
        self.motion_service.stopMove()

    ## Adjust Pepper orientation.
    #  @param y User position along the y axis in meters.
    def refine(self, y):

        ky = 0.2
        vel_th = ky * y

        self.motion_service.move(0,0, vel_th)

    ## Method executed when the thread is started.
    def run(self):

        # # If the interaction node is not set, Greet action is called before the ApproachUser. Therefore, it is better to
        # # look for the user and face them before greeting them.
        if caressestools.Settings.interactionNode == "":
            self.lookForUser()

        t = threading.Thread(
            name='greeting_gesture',
            target=self.playGreetingAnimation)

        # print "Greeting gesture"
        t.start()

        self.setVoiceVolume(self.volume)
        self.setVoiceSpeed(self.speed)
        self.setVoicePitch(self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.languageTag.lower())
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))
        self.sp.enableAnimatedSpeech(False)
        self.sp.say(self.content, speech.TAGS[1])
        time.sleep(1)

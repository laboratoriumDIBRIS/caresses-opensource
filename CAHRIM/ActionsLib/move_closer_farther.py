# -*- coding: utf-8 -*-
'''
Copyright October 2019 Bui Ha Duong & Roberto Menicatti & Università degli Studi di Genova

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

Author:      Bui Ha Duong (1), Roberto Menicatti (2)
Email:       (1) bhduong@jaist.ac.jp (2) roberto.menicatti@dibris.unige.it
Affiliation: (1) Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan 
             (2) Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import qi

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech

## Action "MoveCloserFarther".
#
#  Pepper gets closer to or farther from the user according to their expressed preference.
class MoveCloserFarther(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Command: specifies whether to move closer, farther or stay still
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.command = self.apar[0]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        # Initialize NAOqi services
        self.navigation_service = self.session.service("ALNavigation")
        self.sMotion = self.session.service("ALMotion")

        # Set the cultural parameters
        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        # Set up speech.py app to get information
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

        self.distance_move_closer = 0.3
        self.distance_move_farther = 0.1
        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sMotion.setOrthogonalSecurityDistance(0.02)
        self.sMotion.setTangentialSecurityDistance(0.02)

        options = self.sp.script[self.__class__.__name__]["parameters"][self.language]

        if not self.isAvailable(self.command):
            self.command = self.sp.dialog(self.__class__.__name__, options=options, checkValidity=True,
                                     askForConfirmation=False, removeDiscardedOption=False, noisy=self.asr)

        while not self.command == options[2] and not self.is_stopped:

            if self.command == options[0]:
                self.sMotion.moveTo(self.distance_move_closer, 0.0, 0.0, 10)
            elif self.command == options[1]:
                self.sMotion.moveTo(-self.distance_move_farther, 0.0, 0.0)

            self.command = self.sp.dialog(self.__class__.__name__, options=options, checkValidity=True,
                                          askForConfirmation=False, removeDiscardedOption=False, noisy=self.asr)

        self.sMotion.setOrthogonalSecurityDistance(0.4)
        self.sMotion.setTangentialSecurityDistance(0.10)


if __name__ == "__main__":

    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default=caressestools.Settings.robotIP,
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

    caressestools.Settings.robotIP = args.ip

    # Run Action
    apar = '"n/a"'
    cpar = "1.0 100 1.1 english John"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = MoveCloserFarther(apar, cpar, session, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

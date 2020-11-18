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

import qi
import argparse
import sys

from greet  import Greet
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Greet Wave".
#
#  Pepper greets the user with a waving gesture.
class GreetWave(Greet):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    def __init__(self, apar, cpar, session):
        Greet.__init__(self, apar, cpar, session)

        self.animationTag = self.WAVE_TAG

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.languageTag = self.cpar[3].title().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        self.setRobotLanguage()
        self.setVoiceVolume(self.volume)
        self.setVoiceSpeed(self.speed)
        self.setVoicePitch(self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.languageTag.lower())
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

        self.content = self.sp.script["Greet"]["other"]["2"][self.languageTag.lower()].replace("$USERNAME$", self.username)


if __name__ == "__main__":

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
    apar = ""
    cpar = "0.5 100 1.1 english John"

    caressestools.startPepper(session, "normal")
    action = GreetWave(apar, cpar, session)

    action.run()


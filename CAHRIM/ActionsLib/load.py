# -*- coding: utf-8 -*-
'''
Copyright October 2019 Roberto Menicatti & Università degli Studi di Genova

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

Author:      Roberto Menicatti
Email:       roberto.menicatti@dibris.unige.it
Affiliation: Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import math
import time
import functools

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Load".
#
#  Pepper turns around to let the user put an object inside its optional backpack.
class Load(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Object
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    def __init__(self, apar, cpar, session):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.object_id = self.apar[0]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        self.object_params = self.loadParameters("objects.json")

        # Initialize NAOqi services
        self.sMotion  = self.session.service("ALMotion")
        self.sMemory  = self.session.service("ALMemory")
        self.sPosture = self.session.service("ALRobotPosture")

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

        self.is_touched = False

    ## Method executed when the thread is started.
    def run(self):

        self.sp.enableAnimatedSpeech(False)
        self.object_full = self.getAttributeFromID(self.object_params, self.object_id, "full")

        self.sMotion.moveTo(0, 0, math.pi)
        caressestools.setAutonomousAbilities(self.session, False, False, False, False, False)
        self.sPosture.goToPosture("Stand", 0.5)

        parameters = {
            "$USERNAME$": self.username,
            "$OBJECT$": self.object_full
        }

        self.sp.monolog(self.__class__.__name__, "0", param=parameters, tag=speech.TAGS[1])
        time.sleep(2)

        self.sp.monolog(self.__class__.__name__, "1", tag=speech.TAGS[1])

        touch = self.sMemory.subscriber("TouchChanged")
        id_touch = touch.signal.connect(functools.partial(self.onTouched, "TouchChanged"))

        while not self.is_touched and not self.is_stopped:
            pass

        if not self.is_stopped:
            self.sp.monolog(self.__class__.__name__, "2", tag=speech.TAGS[1])

            # # The sleep is required otherwise Pepper will not move after being touched on the head. Summing up the time
            # # required to say the sentence in the previous line and this time.sleep, 2s turns out to be the minimum time
            # # required.
            time.sleep(2)

            self.sMotion.moveTo(0, 0, math.pi)

    ## Callback
    def onTouched(self, msg, value):
        self.is_touched = True


if __name__ == "__main__":

    import argparse
    import qi
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
    caressestools.startPepper(session, caressestools.Settings.interactionNode)

    apar = "glasses"
    cpar = "1.0 100 1.1 english John"

    action = Load(apar, cpar, session)
    action.run()

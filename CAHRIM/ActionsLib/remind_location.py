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

import sys
from random import randint

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Remind Action".
#
# Pepper reminds the user about where an object is located.
class RemindLocation(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Object, location; separated by a white space.
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.object_id = self.apar[0]
        self.location_id = self.apar[1]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        self.object_params = self.loadParameters("objects.json")
        self.location_params = self.loadParameters("locations.json")

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        self.object_full = self.getAttributeFromID(self.object_params, self.object_id, "full")
        self.location_with_object_preposition = self.getAttributeFromID(self.location_params, self.location_id, "prep-object")

        parameters = {
            "$LOCATION$": self.location_with_object_preposition,
            "$OBJECT$": self.object_full
        }

        sentence_index = str(randint(0, len(self.sp.script[self.__class__.__name__][speech.OTHER]) - 1))
        self.sp.monolog(self.__class__.__name__, sentence_index, param=parameters, tag=speech.TAGS[1])

        self.sp.askYesOrNoQuestion(
            self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
        self.sp.monolog(self.__class__.__name__, "1", group="evaluation", tag=speech.TAGS[1])

if __name__ == "__main__":

    import argparse
    import qi

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

    apar = "glasses drawer"
    cpar = "1.0 100 1.1 english John"

    action = RemindLocation(apar, cpar, session, "normal")
    action.run()

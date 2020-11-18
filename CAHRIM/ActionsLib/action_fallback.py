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

from action import Action
from go_to import GoTo
from react_to_sound import ReactToSound
import caressestools.caressestools as caressestools
import caressestools.speech as speech

class KillCAHRIM(Exception):
    pass


## Action "Fallback"
#
#  Pepper goes to the charger node because it cannot continue the interaction. It automatically executed when the battery level is low.
class Fallback(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, output_handler, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')
        self.killcahrim = self.apar[0] == "True"

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        self.output_handler = output_handler
        self.asr = asr

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

    ## Method executed when the thread is started.
    def run(self):

        self.sp.monolog(self.__class__.__name__, "0", tag=speech.TAGS[1])

        params = ["map.json charger", ' '.join(self.cpar) + " charger", self.session, self.output_handler, self.asr]
        self.logger.info("%-17s %3s, %s, [%s], [%s]" % ("Action forced:", str(-2), "GoTo", params[0], params[1]))
        goto = GoTo(*params)
        caressestools.showImg(self.session, caressestools.TABLET_IMG_EXECUTION)
        goto.run()

        if self.killcahrim:
            raise KillCAHRIM
        else:
            params = ['', ' '.join(self.cpar), self.session, self.output_handler]
            self.logger.info("%-17s %3s, %s, [%s], [%s]" % ("Action forced:", str(-2), "ReactToSound", params[0], params[1]))
            reacttosound = ReactToSound(*params)
            caressestools.showImg(self.session, caressestools.TABLET_IMG_REST)
            reacttosound.run()


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

    apar = ""
    cpar = "1.0 100 1.1 english John"

    action = Fallback(apar, cpar, session, "normal")
    action.run()

# -*- coding: utf-8 -*-
'''
Copyright October 2019 Maxime Caniot & Maxime Busy & Roberto Menicatti & Università degli Studi di Genova

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

Author:      Maxime Caniot (1), Maxime Busy (2), Roberto Menicatti (3)
Email:       (1) mcaniot@softbankrobotics.com, (2) mbusy@softbankrobotics.com, (3) roberto.menicatti@dibris.unige.it
Affiliation: (1)(2) SoftBank Robotics, Paris, France, (3) Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

from privacy  import Privacy
import caressestools.caressestools as caressestools


## Action "Privacy Cover Eyes".
#
#  Pepper provides privacy to the user by looking somewhere else and covering its eyes.
class PrivacyCoverEyes(Privacy):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Privacy.__init__(self, apar, cpar, session, asr)

        self.animationTag = self.HIDE_TAG
        self.angle = self.ANGLE_COVER_EYES

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        caressestools.Language.setLanguage(self.language)
        self.setLang(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)


if __name__ == "__main__":

    import qi
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
    apar = ""
    cpar = "1.0 100 1.1 english John"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = PrivacyCoverEyes(apar, cpar, session, "normal")

    action.run()

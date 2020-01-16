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
import time
import threading

from action import Action
import caressestools.multipage_choice_manager as mlt
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Accompany".
#
#  Pepper can be taken by hand to walk around together.
class Accompany(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        # Initialize NAOqi services
        self.sMotion       = self.session.service("ALMotion")
        self.sNavigation   = self.session.service("ALNavigation")
        self.sMemory       = self.session.service("ALMemory")
        self.sBehavior     = self.session.service("ALBehaviorManager")
        self.sPosture      = self.session.service("ALRobotPosture")
        self.sTablet       = self.session.service("ALTabletService")

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

        self.sp.monolog(self.__class__.__name__, "0", tag=speech.TAGS[1])

        caressestools.setAutonomousAbilities(self.session, False, False, False, False, False)
        self.sPosture.goToPosture("Stand", 0.5)

        if not self.sBehavior.isBehaviorRunning("User/follow-me-no-security-avatarion"):
            self.sBehavior.startBehavior("User/follow-me-no-security-avatarion")

        question = self.sp.script[self.__class__.__name__]["other"]["2"][self.language].encode('utf-8')
        options = [self.sp.script[self.__class__.__name__]["user"]["0"][self.language].encode('utf-8')]
        self.choice = mlt.MultiPageChoiceManager(caressestools.Settings.robotIP.encode('utf-8'))
        if self.sp._input==2:
            self.sp.gothread = True
            thr = threading.Thread(name="getinput", target=self.sp.getOptionsFromSmartphone, args=[options])
            thr.start()
        answer = self.choice.giveChoiceMultiPage(question, options, timer=1200, exitOnTouch=False)
        self.sp.gothread=False
        answer = [unicode(answer[0], "utf-8"), answer[1]]
        self.choice.kill()

        self.sp.checkIfKilledDuringMcm(self.choice, answer, self.end)

        self.sp.monolog(self.__class__.__name__, "1", tag=speech.TAGS[1])

        self.end()

        self.sp.askYesOrNoQuestion(self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
        self.sp.monolog(self.__class__.__name__, "1", group="evaluation", tag=speech.TAGS[1])

    ## Method containing all the instructions that should be executing before terminating the action.
    def end(self):

        time.sleep(1)
        self.sBehavior.stopBehavior("User/follow-me-no-security-avatarion")
        self.sPosture.goToPosture("Stand", 0.5)
        ## Always call the following function after executing the "follow-me-no-security-avatarion" app
        self.sMotion.setMoveArmsEnabled(True, True)


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

    apar = ""
    cpar = "1.0 100 1.1 english John"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = Accompany(apar, cpar, session, "normal")
    action.run()

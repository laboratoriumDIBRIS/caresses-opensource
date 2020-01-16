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

import os
import json
from random import randint
import threading

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech
import caressestools.multipage_choice_manager as mcm

## Action "Play Game Memory".
#
#  Pepper lets the user play a memory game on its tablet.
#  This action requires the installation of the NAOqi app CARESSES Game Memory.
class PlayGameMemory(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Topic of the game.
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.topic_id = self.apar[0]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        self.topic_params = self.loadParameters("game_memory_topics.json")
        suggested_topic_IDs = [option.replace('"', '') for option in self.suggestions]
        self.topic_IDs = self.mergeAndSortIDs(self.topic_params, suggested_topic_IDs)
        self.topic_options = self.getAllParametersAttributes(self.topic_params, self.topic_IDs, "full")

        # Initialize NAOqi services
        self.sTablet = self.session.service("ALTabletService")
        self.sMemory = self.session.service("ALMemory")
        self.sBehavior = self.session.service("ALBehaviorManager")

        # Set the cultural parameters
        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(session, self.volume)
        caressestools.setVoiceSpeed(session, self.speed)
        caressestools.setVoicePitch(session, self.pitch)

        # Set up speech.py app to get information
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(session, caressestools.Settings.robotIP.encode('utf-8'))

        self.again = True
        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        if self.sBehavior.isBehaviorRunning("caresses_game_memory/behavior_1"):
            self.sBehavior.stopBehavior("caresses_game_memory/behavior_1")
        self.sBehavior.startBehavior("caresses_game_memory/behavior_1")
        self.sp.monolog(self.__class__.__name__, "0", tag=speech.TAGS[1])

        while self.again and not self.is_stopped:

            if not self.isAvailable(self.topic_id):
                self.topic_full = self.sp.dialog(self.__class__.__name__, self.topic_options, checkValidity=True, askForConfirmation=False, noisy=self.asr)
                self.topic_id = self.getIDFromAttribute(self.topic_params, "full", self.topic_full)
            else:
                self.topic_full = self.getAttributeFromID(self.topic_params, self.topic_id, "full")
                self.sp.monolog(self.__class__.__name__, "with-keyword", param={"$KEYWORD$" : self.topic_full}, group="parameter-answer", tag=speech.TAGS[1])

            self.sMemory.raiseEvent("CARESSES/game_memory/topic", self.topic_id)

            self.sp.monolog(self.__class__.__name__, "1", tag=speech.TAGS[1])
            self.sp.askYesOrNoQuestion(self.sp.script[self.__class__.__name__][speech.OTHER]["2"][self.language].encode('utf-8'), speech.TAGS[4], noisy=self.asr)

            imgs_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "NAOqi_apps", "game_memory_APP", "CARESSES Game Memory", "html", "images", self.topic_id)
            imgs = os.listdir(imgs_folder)

            index = randint(1, len(imgs))
            index = str(index).zfill(2)

            self.sMemory.raiseEvent("CARESSES/game_memory/show", index)

            while self.sBehavior.isBehaviorRunning("caresses_game_memory/behavior_1"):
                pass


            self.mcm = mcm.MultiPageChoiceManager(caressestools.Settings.robotIP)

            memorygames_conf = os.path.join(os.path.dirname(os.path.realpath(__file__)), "aux_files", "memorygames-conf.json")
            with open(memorygames_conf) as f:
                content = json.load(f)

            num_of_questions = len(content["pictures"][self.topic_id][index])

            for q in range(1, num_of_questions + 1):
                question = content["pictures"][self.topic_id][index][str(q)]["question"][self.language].encode('utf-8')
                question_tablet = content["pictures"][self.topic_id][index][str(q)]["question-tablet"][self.language].encode('utf-8')
                options = [o.encode('utf-8') for o in content["pictures"][self.topic_id][index][str(q)]["answers"][self.language]]
                correct_answer = content["pictures"][self.topic_id][index][str(q)]["correct-answer"][self.language]
                options = [o for o in options]

                self.sp.say(question)

                if self.sp._input==2:
                    self.sp.gothread = True
                    thr = threading.Thread(name="getinput", target=self.sp.getOptionsFromSmartphone, args=[options])
                    thr.start()
                answer = self.mcm.giveChoiceMultiPage(question_tablet, options)
                self.sp.gothread=False

                answer = [unicode(answer[0], "utf-8"), answer[1]]
                self.sp.checkIfKilledDuringMcm(self.mcm, answer, self.end)

                while not answer[0].lower() == correct_answer.lower():
                    self.sp.monolog(self.__class__.__name__, "5", tag=speech.TAGS[1])
                    self.sp.say(question, speech.TAGS[4])
                    if self.sp._input==2:
                        self.sp.gothread = True
                        thr = threading.Thread(name="getinput", target=self.sp.getOptionsFromSmartphone, args=[options])
                        thr.start()
                    answer = self.mcm.giveChoiceMultiPage(question_tablet, options)
                    self.sp.gothread=False
                    answer = [unicode(answer[0], "utf-8"), answer[1]]
                    self.sp.checkIfKilledDuringMcm(self.mcm, answer, self.end)

                self.sp.monolog(self.__class__.__name__, "4", tag=speech.TAGS[1])

            caressestools.showImg(self.session, caressestools.TABLET_IMG_EXECUTION)
            self.sBehavior.stopBehavior("caresses_game_memory/behavior_1")
            self.sBehavior.startBehavior("caresses_game_memory/behavior_1")
            question = self.sp.script[self.__class__.__name__][speech.OTHER]["6"][self.language].encode('utf-8')
            self.again = self.sp.askYesOrNoQuestion(question, speech.TAGS[11], noisy=self.asr)
            if self.again:
                self.topic_id = '"n/a"'
            else:
                self.sp.replyAffirmative()

        self.sp.monolog(self.__class__.__name__, "3", tag=speech.TAGS[1])
        self.sp.askYesOrNoQuestion(
            self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
        self.sp.monolog(self.__class__.__name__, "1", group="evaluation", tag=speech.TAGS[1])

        self.end()

    ## Method containing all the instructions that should be executing before terminating the action.
    def end(self):
        self.mcm.kill()
        try:
            self.sBehavior.stopBehavior("caresses_game_memory/behavior_1")
        except:
            pass


if __name__ == "__main__":

    import qi
    import sys
    import argparse

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
    cpar = "1.0 100 1.1 english John britishFestivalsMemoryGame&&britishMonumentsMemoryGame"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = PlayGameMemory(apar, cpar, session, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

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

from random import randint
import time
import functools

from action import Action
from CahrimThreads.sensory_hub import OdomConverter
import caressestools.caressestools as caressestools
import caressestools.speech as speech

MEMORY_CHARGER = "CARESSES_onCharger"


## Action "React To Sound".
#
#  Pepper waits for the user to call or touch it.
class ReactToSound(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param output_handler () Handler of the output socket messages.
    # @param session (qi session) NAOqi session.
    def __init__(self, apar, cpar, session, output_handler):
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
        self.sMotion = self.session.service("ALMotion")
        self.sMemory = self.session.service("ALMemory")
        self.sSoundDet = self.session.service("ALSoundDetection")
        self.sRecharge = self.session.service("ALRecharge")
        self.sSpeechReco = self.session.service("ALSpeechRecognition")
        self.sPosture = self.session.service("ALRobotPosture")
        self.sBattery = self.session.service("ALBattery")

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

        self.sSoundDet.setParameter("Sensitivity", 0.7)
        self.sound_detected = False
        self.word_detected = False
        self.is_touched = False
        self.notify_user = False

        self.output_handler = output_handler

    ## Subscribe to keyword detection event.
    def subscribeToKeywords(self):
        # # Subscribe here to touch and word recognition
        self.sSpeechReco.subscribe("CARESSES/word-detected")
        self.speechRecognized = self.sMemory.subscriber("WordRecognized")
        self.id_speechRecognized = self.speechRecognized.signal.connect(
            functools.partial(self.onSpeechRecognized, "WordRecognized"))
        self.setSpeechRecognition()

    ## Sets parameters for keyword recognition
    def setSpeechRecognition(self):
        self.sSpeechReco.setVisualExpression(False)
        self.sSpeechReco.setAudioExpression(False)
        self.sSpeechReco.pause(True)
        self.sSpeechReco.setLanguage(self.language.title())
        vocabulary = self.sp.script[self.__class__.__name__]["user"]["0"][self.language]
        self.sSpeechReco.setVocabulary(vocabulary, False)
        self.sSpeechReco.pause(False)

    ## Method executed when the thread is started.
    def run(self):

        self.aa = caressestools.getAutonomousAbilities(self.session)
        caressestools.setAutonomousAbilities(self.session, False, False, False, False, False)
        self.sPosture.goToPosture("Stand", 0.5)

        #if self.output_handler is not None:
        #    msg="[approached-user:false]"
        #    self.output_handler.writeSupplyMessage("publish", "D6.1", msg)

        self.subscriber = self.sMemory.subscriber("SoundDetected")
        self.subscriber.signal.connect(self.onSoundDetected)
        self.sSoundDet.subscribe(self.__class__.__name__)

        # Register events
        # 'TouchChanged'
        touch = self.sMemory.subscriber("TouchChanged")
        id_touch = touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))

        # # Use NAOqi keyword detection instead of Google's to avoid too many useless API calls
        self.subscribeToKeywords()

        # # Wait for any user sentence...
        while not self.word_detected and not self.is_touched and not self.is_stopped:

            if self.notify_user:
                self.waitToBeCharged()
                self.notify_user = False

        # # ... and react
        if not self.is_stopped:
            i = 3
            question_index = str(randint(i, len(self.sp.script[self.__class__.__name__][speech.OTHER]) - 1))
            sentence_index = str(randint(0, i - 1))
            question = self.sp.script[self.__class__.__name__]["other"][question_index][self.language]
            sentence = self.sp.script[self.__class__.__name__]["other"][sentence_index][self.language]

            if self.word_detected:
                self.sp.userSaid(self.user_input)
                time.sleep(2)
                full = "%s %s" % (question, sentence)

            else:
                full = sentence

            self.sp.say(full, speech.TAGS[1])

            node = OdomConverter.getCurrentNode()
            try:
                on_charger = self.sMemory.getData(MEMORY_CHARGER)
            except:
                on_charger = True

            if node == "charger" or on_charger == True:

                left = caressestools.leaveChargerNode(self.session)

                if left == False:
                    self.logger.error("ALRecharge getStatus() ERROR #4")
                    return
                else:
                    self.onCharger = False

            if self.output_handler is not None:
                if caressestools.Settings.interactionNode == "":
                    msg = "[(:goal(?G1 (approached-user pepper-1) true)(?G2 move-closer-farther true)(?G3 accept-request true)) (:temporal (before ?G1 ?G2 [1500 inf])(before ?G2 ?G3 [1500 inf]))]"
                else:
                    self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):\"n/a\"]")
                    time.sleep(0.5)
                    msg = "[(:goal(?G1 (robot-at pepper-1) %s))]" % caressestools.Settings.interactionNode

                self.output_handler.writeSupplyMessage("publish", "D5.1", msg)

        caressestools.setAutonomousAbilities(self.session, self.aa[0], self.aa[1], self.aa[2], self.aa[3], self.aa[4])

        self.sSoundDet.unsubscribe(self.__class__.__name__)
        try:
            self.sSpeechReco.unsubscribe("CARESSES/word-detected")
        except:
            pass

    ##
    def waitToBeCharged(self):
        parameters = {
            "$LEVEL$": str(self.sBattery.getBatteryCharge()),
            "$MINIMUM$": str(caressestools.Battery.BATTERY_MINIMUM)
        }
        self.sp.monolog(self.__class__.__name__, "5", tag=speech.TAGS[1], param=parameters)

    ## Callback
    def onTouch(self, msg, value):
        if self.sBattery.getBatteryCharge() < caressestools.Battery.BATTERY_MINIMUM:
            self.notify_user = True
        else:
            self.is_touched = True

    ## Callback
    def onSoundDetected(self, msg):
        self.sound_detected = True

    ## Callback
    def onSpeechRecognized(self, msg, value):
        if value[1] >= 0.45:
            self.user_input = value[0]
            if self.sBattery.getBatteryCharge() < caressestools.Battery.BATTERY_MINIMUM:
                self.waitToBeCharged()
            else:
                self.word_detected = True


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

    apar = ""
    cpar = "1.0 100 1.1 english John"

    action = ReactToSound(apar, cpar, session, None)
    action.run()

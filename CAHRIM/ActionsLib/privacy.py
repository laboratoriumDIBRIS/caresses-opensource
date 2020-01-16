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

from math import pi
import time
import functools

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Privacy".
#
#  Pepper provides privacy to the user by looking somewhere else through three possible different animations. This action shouldn't be executed standalone; its child classes should be used instead.
class Privacy(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        self.HIDE_TAG        = "HideEyes"
        self.HIDE_TURN_TAG   = "HideEyesWithRotation"
        self.HIDE_FLOOR_TURN_TAG = "HideEyesFloorWithRotation"

        self.ANGLE_COVER_EYES = 0
        self.ANGLE_LOOK_DOWN = pi / 4
        self.ANGLE_TURN_AROUND = - pi * 3/4

        # by default
        self.animationTag    = self.HIDE_TAG
        self.behaviorService = self.session.service("ALBehaviorManager")

        self.sMotion = self.session.service("ALMotion")
        self.sMemory = self.session.service("ALMemory")
        self.sAsr    = self.session.service("ASR2")
        self.sSpeechReco = self.session.service("ALSpeechRecognition")
        self.may_turn = False
        self.sleep = False
        self.angle = 0
        self.security_timeout = 90
        self.asr = asr

    ## Set language for dialog.
    #  @param lang Language
    def setLang(self, lang):
        self.language = lang
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

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
        list_1 = [l.encode('utf-8') for l in self.sp.script[speech.KEYWORDS]["gainAttention"][self.language]]
        list_2 = [l.encode('utf-8') for l in self.sp.script[Privacy.__name__][speech.USER]["0"][self.language]]
        vocabulary = list_1 + list_2
        self.sSpeechReco.setVocabulary(vocabulary, False)
        self.sSpeechReco.pause(False)

    ## Callback
    def onSpeechRecognized(self, msg, value):
        if value[1] >= 0.3:
            self.detected_something = True
            self.user_input = value[0]

    ## Method executed when the thread is started.
    def run(self):

        if self.animationTag == self.HIDE_TAG:
            self.hideEyes()

        elif self.animationTag == self.HIDE_TURN_TAG:
            self.hideEyesWithRotation()

        elif self.animationTag == self.HIDE_FLOOR_TURN_TAG:
            self.HideEyesFloorWithRotation()

        caressestools.setAutonomousAbilities(self.session, False, False, False, False, False)

        self.sp.monolog(Privacy.__name__, "2", tag=speech.TAGS[1])

        start = time.time()
        should_rotate = True

        # Register events
        # 'TouchChanged'
        touch = self.sMemory.subscriber("TouchChanged")
        id_touch = touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))

        ## Use NAOqi keyword detection instead of Google's to avoid too many useless API calls
        self.subscribeToKeywords()

        self.user_input = ""
        self.detected_something = False

        while not self.may_turn and not self.is_stopped:

            if time.time() - start >= self.security_timeout:
                should_rotate = False
                break

            if self.detected_something:
                self.sp.userSaid(self.user_input)
                question = self.sp.script[Privacy.__name__][speech.OTHER]["0"][self.language].encode('utf-8')
                self.sSpeechReco.unsubscribe("CARESSES/word-detected")
                turn = self.sp.askYesOrNoQuestion(question, speech.TAGS[4], noisy=self.asr)
                if turn:
                    self.may_turn = True
                else:
                    line = self.sp.script[Privacy.__name__][speech.OTHER]["1"][self.language].encode('utf-8')
                    self.sp.say(line, speech.TAGS[1])
                    self.detected_something = False
                    self.subscribeToKeywords()

        self.sp.replyAffirmative()

        try:
            self.sSpeechReco.unsubscribe("CARESSES/word-detected")
        except:
            pass

        caressestools.setAutonomousAbilities(self.session, False, True, True, True, True)

        if should_rotate:
            if self.sleep:
                time.sleep(7)
            self.sMotion.moveTo(0, 0, self.angle)


    def hideEyesWithRotation(self):
        """
        Plays the hide eyes animation with a 180 turn
        """

        self.behaviorService.startBehavior("caresses/hideeyeswithrotation")


    def hideEyes(self):
        """
        Plays the hide eyes animation
        """

        self.behaviorService.startBehavior("caresses/hideeyes")

    def HideEyesFloorWithRotation(self):
        """
        Plays the hide eyes with a 180 turn and a look at the floor animation
        """

        self.behaviorService.startBehavior("caresses/hideeyesfloorwithrotation")

    ## Callback
    def onTouch(self, msg, value):
        self.sleep = True
        self.may_turn = True

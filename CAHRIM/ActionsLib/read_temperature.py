# -*- coding: utf-8 -*-
'''
Copyright October 2019 Bui Ha Duong

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

Author:      Bui Ha Duong
Email:       bhduong@jaist.ac.jp
Affiliation: Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import qi
import time
import functools
from threading import Timer

from action import Action
import caressestools.caressestools as caressestools

TEMPERATURE_IHOUSE_ROBOT = "caresses-ihouse-temperature"

RESPOND_ERROR = "provided#iHouse#Error"
RESPOND_TTS = "The temperature in iHouse is %s degrees."

ASR_SERVICE = "Caresses_ReadTemperature_ASR"

class ReadTemperature(Action):
    """
    Action Read temperature from iHouse

    Attributes:
        apar : None
        cpar : volume
        session : robot's session
        socket : socket instance connect with uaal_CAHRIM

    README:
        Install App-iHouseTemperature.pml project (inside the folder read_temperature_app/App-iHouseTemperature) on Pepper using Choregraphe.
        Touch Pepper, wait for 30s, or say "stop" to stop the action.
    """
    def __init__(self, apar, cpar, session, output_handler, input_queue, provided_event):
        Action.__init__(self, apar, cpar, session)

        self.tts = session.service("ALTextToSpeech")
        self.asr = session.service("ALSpeechRecognition")
        self.memoryService = session.service("ALMemory")
        self.tabletService = session.service("ALTabletService")

        self.volume = float(cpar)
        self.is_stop = False

        # Output handler for sending messages
        self.output_handler = output_handler
        # Input queue for retrieving temperature
        self.input_queue = input_queue

        self.provided_event = provided_event

        self.setVoiceVolume(self.volume)
        self.setRobotLanguage("English")
        self.setSpeechRecognition()


    def setRobotLanguage(self, language):
        """
        Sets the robot language, checks if the desired language is supported

        Parameters:
            language - The desired language
        """
        try:
            assert language in self.tts.getSupportedLanguages()
            self.tts.setLanguage(language)

        except AssertionError:
            if language.lower() != "japanese":
                print language + " is not supported by the robot, "\
                    "language set to English"

            self.tts.setLanguage("English")


    def setVoiceVolume(self, volume):
        """
        Sets the volume of the tts

        Parameters
            volume - The volume, between 0 and 1
        """
        try:
            assert volume >= 0 and volume <= 1

        except AssertionError:
            print "Incorrect volume, 0.5 taken into account"
            volume = 0.5

        self.tts.setVolume(volume)
    
    def setSpeechRecognition(self):
        self.asr.setLanguage("English")
        vocabulary = ["stop"]
        self.asr.setVocabulary(vocabulary, False)


    def run(self):

        touch = self.memoryService.subscriber("TouchChanged")
        id_touch = touch.signal.connect(functools.partial(self.onTouched, "TouchChanged"))

        speechRecognized = self.memoryService.subscriber("WordRecognized")
        id_speechRecognized = speechRecognized.signal.connect(functools.partial(self.onSpeechRecognized, "WordRecognized"))

        self.tabletService.loadApplication(TEMPERATURE_IHOUSE_ROBOT)
        self.tabletService.showWebview()
        time.sleep(3)

        self.output_handler.writeQueryMessage("request", "iHouse")
        self.provided_event.wait(15)

        data = None
        value = ""

        while not self.input_queue.empty():
            value = self.input_queue.get()
            if value[0] == "provided" and value[1] == "iHouse":
                data = str(int(round(float(value[2]))))
                print "[Action - ReadTemperature] Temperature retrieved correctly with value: %s" % data
                break
            else:
                self.input_queue.put(value)

        if data is not None:

            if RESPOND_ERROR not in value:
                self.memoryService.raiseEvent("pepper/ihouse/temperature", data)
                timer = Timer(30, self.timeout)
                timer.start()

                content = RESPOND_TTS % (data)
                self.tts.say(content)

                self.asr.subscribe(ASR_SERVICE)

                while not self.is_stop:
                    pass

                timer.cancel()
                self.asr.unsubscribe(ASR_SERVICE)

        else:
            print("[Action - ReadTemperature] Failed to retrieve iHouse temperature.")

        self.stop()


    def stop(self):
        self.tabletService.hide()

    def timeout(self):
        self.is_stop = True

    def onTouched(self, msg, value):
        self.is_stop = True

    def onSpeechRecognized(self, msg, value):
        self.is_stop = True

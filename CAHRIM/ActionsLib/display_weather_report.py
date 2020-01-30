# -*- coding: utf-8 -*-
'''
Copyright October 2019 Japan Advanced Institute of Science and Technology & Roberto Menicatti & Università degli Studi di Genova

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

Author:      Bui Ha Duong (1), Roberto Menicatti (2)
Email:       (1) bhduong@jaist.ac.jp (2) roberto.menicatti@dibris.unige.it
Affiliation: (1) Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan 
             (2) Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import time
import os
import json
import functools
from threading import Timer
from google.cloud import translate

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech

WEATHER_REPORT_ROBOT = "caresses-weather-report"
ASR_SERVICE = "Caresses_DisplayWeatherReport_ASR"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="ActionsLib/caressestools/CARESSES-Translate.json"


## Action "Display Weather Report".
#
#  Pepper shows the weather report on its tablet and reads it aloud.
#  This action requires the installation of the NAOqi app DisplayWeatherReport.
class DisplayWeatherReport(Action):
    """
    Action Display Weather Report

    Attributes:
        apar : location
        cpar : volume, speed, pitch, language, username, suggestions
        session : robot's session
    """

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Location.
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.location_id = self.apar[0]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        self.locations_params = self.loadParameters("weather_locations.json")
        suggested_locations_IDs = [option.replace('"', '') for option in self.suggestions]
        self.locations_IDs = self.mergeAndSortIDs(self.locations_params, suggested_locations_IDs)
        self.locations_options = self.getAllParametersAttributes(self.locations_params, self.locations_IDs, "full")

        # Initialize NAOqi services
        self.sTablet = self.session.service("ALTabletService")
        self.sMemory = self.session.service("ALMemory")
        self.sSpeechReco = self.session.service("ALSpeechRecognition")

        # Set the cultural parameters
        caressestools.Language.setLanguage(self.language)
        
        caressestools.setRobotLanguage(session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(session, self.volume)
        caressestools.setVoiceSpeed(session, self.speed)
        caressestools.setVoicePitch(session, self.pitch)

        # Set up speech.py app to get information
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(session, caressestools.Settings.robotIP.encode('utf-8'))

        self.go_on = False
        self.isPageFinished = False
        self.user_input = None
        self.asr = asr

    ## Sets parameters for keyword recognition
    def setSpeechRecognition(self):
        self.sSpeechReco.setVisualExpression(False)
        self.sSpeechReco.setAudioExpression(False)
        self.sSpeechReco.pause(True)
        self.sSpeechReco.setLanguage(self.language.title())
        vocabulary = [w.encode('utf-8') for w in self.sp.script[self.__class__.__name__]["end-action"][self.language]]
        self.sSpeechReco.setVocabulary(vocabulary, False)
        self.sSpeechReco.pause(False)

    ## Method executed when the thread is started.
    def run(self):

        # Instantiates a translation client
        google_credentials = os.path.join(os.path.dirname(os.path.realpath(__file__)), "caressestools", "CARESSES-Translate.json")
        translate_client = translate.Client()
        self.translate_client = translate_client.from_service_account_json(google_credentials)

        onInfo = self.sMemory.subscriber('pepper/weather/info')
        idInfo = onInfo.signal.connect(functools.partial(self.onInfo, 'pepper/weather/info'))

        custom_option = self.sp.script[self.__class__.__name__]["custom-option"][self.language].encode('utf-8')
        self.locations_options.append(custom_option)

        if not self.isAvailable(self.location_id):

            self.location_full = custom_option

            try:
                self.location_full_unicode=unicode(self.location_full,"utf-8")
            except:
                self.location_full_unicode=self.location_full

            while self.location_full_unicode == unicode(custom_option,"utf-8"):

                self.location_full = self.sp.dialog(self.__class__.__name__, self.locations_options, checkValidity=False, askForConfirmation=True, noisy=self.asr)

                try:
                    self.location_full_unicode=unicode(self.location_full,"utf-8")
                except:
                    self.location_full_unicode=self.location_full
        else:
            self.location_full = self.getAttributeFromID(self.locations_params, self.location_id, "full")
            self.sp.monolog(self.__class__.__name__, "with-keyword", param={"$KEYWORD$" : self.location_full}, group="parameter-answer", tag=speech.TAGS[1])
        try:
            self.location_full = self.location_full.decode('utf-8')
        except:
            pass

        self.location_id = self.getIDFromAttribute(self.locations_params, "full", self.location_full)

        if self.location_id is None:
            if not self.language == "english":
                self.location_full_translated = self.translate_client.translate(self.location_full, target_language="en", source_language=self.sp.getLanguageISO_639_1(self.language))['translatedText']
            else:
                self.location_full_translated = self.location_full
            self.city = self.lookForCity(self.location_full_translated)

        else:
            if not self.language == "english":
                self.location_full_eng = self.getAttributeFromID(self.locations_params, self.location_id, "fulleng")
            else:
                self.location_full_eng = self.location_full
        
            self.city = self.location_full_eng
            
        if self.city is not None:

            signalId = self.sTablet.onPageFinished.connect(
                self.onPageFinishedSignal)

            self.sTablet.loadApplication(WEATHER_REPORT_ROBOT)
            self.sTablet.showWebview()

            while not self.isPageFinished:
                time.sleep(0.1)

            self.sTablet.onPageFinished.disconnect(signalId)
            self.isPageFinished = False

            time.sleep(3)
            self.sMemory.raiseEvent("pepper/weather/location", self.city.replace("\"",""))

            self.timer = Timer(60, self.onTimeout)
            self.timer.start()

            time.sleep(5)

            while not self.go_on and not self.is_stopped:
                pass

            if not self.is_stopped:
                if self.user_input is not None:
                    self.sp.userSaid(self.user_input)
                self.sp.askYesOrNoQuestion(
                    self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'), tag=speech.TAGS[3],noisy=self.asr)
                self.sp.monolog(self.__class__.__name__, "1", group="evaluation", tag=speech.TAGS[1])

            self.end()

        else:
            self.sp.monolog(self.__class__.__name__, "2", param={"$CITY$": self.location_full}, tag=speech.TAGS[1])

    ## Method containing all the instructions that should be executing before terminating the action.
    def end(self):
        self.timer.cancel()
        try:
            self.sSpeechReco.unsubscribe(ASR_SERVICE)
        except:
            pass
        self.sTablet.hide()

    ## Callback function.
    def onPageFinishedSignal(self):
        """
        Triggered when the onPageFinished is fired by ALTabletService
        """
        self.isPageFinished = True

    ## Callback function.
    def onInfo(self, msg, value):

        if not self.language == "english":
            self.city = self.translate_client.translate(self.city, target_language=self.sp.getLanguageISO_639_1(self.language), source_language="en")['translatedText']

        if value == "ERROR":
            self.sp.monolog(self.__class__.__name__, "1", param={"$CITY$": self.city}, tag=speech.TAGS[1])
            self.go_on = True
        else:
            status_group = value.split(';')[0].lower()
            status_id = value.split(';')[1]
            temp = value.split(';')[2]

            fpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "aux_files", "weather-conf.json")
            with open(fpath) as f:
                weather = json.load(f)

            try:
                status = weather[status_group][status_id][self.language]
                self.sp.monolog(self.__class__.__name__, "0", param={"$CITY$": self.city, "$STATUS$": status, "$TEMPERATURE$": temp}, tag=speech.TAGS[1])
                ## Subscribe here to touch and word recognition
                self.sSpeechReco.subscribe(ASR_SERVICE)
                self.touch = self.sMemory.subscriber("TouchChanged")
                self.id_touch = self.touch.signal.connect(functools.partial(self.onTouched, "TouchChanged"))

                self.speechRecognized = self.sMemory.subscriber("WordRecognized")
                self.id_speechRecognized = self.speechRecognized.signal.connect(
                    functools.partial(self.onSpeechRecognized, "WordRecognized"))
                self.setSpeechRecognition()

            except:
                self.sp.monolog(self.__class__.__name__, "1", param={"$CITY$": self.city}, tag=speech.TAGS[1])
                self.go_on = True

    ## Callback function.
    def onTouched(self, msg, value):
        self.go_on = True
        self.user_input = None

    ## Callback function.
    def onSpeechRecognized(self, msg, value):
        if value[1] >= 0.4:
            self.user_input = value[0]
            self.go_on = True

    ## Callback function.
    def onTimeout(self):
        self.go_on = True

    ## Returns a city name given the entire user input.
    #  @param input The input from the user.
    def lookForCity(self, input):

        city_list = os.path.join(os.path.dirname(os.path.realpath(__file__)), "aux_files", "city-list.json")
        with open(city_list, 'r') as f:
            content = json.load(f)

        candidates = []

        for city in content:
            if city["name"].lower() in input.lower():
                candidates.append(city["name"])

        try:
            city = max(candidates, key=len).encode('utf-8')
            if city == "":
                city = None
        except:
            city = None

        return city


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
    cpar = "1.0 100 1.1 english John genova&&paris"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = DisplayWeatherReport(apar, cpar, session, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

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
import os
import re
import json
import logging
import string
import time
import functools
import threading
import Queue
import socket
import speech_recognition as sr
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords, wordnet
from nltk.stem import PorterStemmer
from random import randint
from colorama import Fore, init, deinit

import timedateparser
from timedateparser import TimeDateParser
from date_time_selector import DateTimeSelector
from caressestools import Settings, setAutonomousAbilities, getAutonomousAbilities
from custom_number import CustomNumber

# import CahrimThreads.socket_handlers

# # Constants

CAHRIM_KILL_ACTION = "CARESSES_kill_action"
SPEECH_RECO_EVENT = "Audio/RecognizedWords"
SUPPORTED_LANGUAGES = "SUPPORTED-LANGUAGES"
STOP_INTERACTION = "STOP-INTERACTION"

KEYWORDS = "KEYWORDS"
REPEAT = "repeat"
STOP = "stop"
AFFIRMATIVE = "affirmative"
NEGATIVE = "negative"
OPTIONS = "options"
STOP_CALL = "stop-call"
GAIN_ATTENTION = "gainAttention"
THANKS = "thanks"

GETDATE = "get-date"
GETTIME = "get-time"

ADDITIONAL = "ADDITIONAL"
MISSED_ANSWER = "missedAnswer"
FAULT_ADMISSION = "faultAdmission"
SHOW_OPTION = "showingOptions"
FAILURE = "failure"
CSPEM_RESTART = "cspemRestart"
OK = "ok"

ASK_PARAMETERS = "ask-parameters"
PARAMETER_ANSWER = "parameter-answer"
WITH_KEYWORD = "with-keyword"
WITHOUT_KEYWORD = "without-keyword"
ASK_CONFIRMATION = "ask-confirmation"
WRONG_PARAMETER = "wrong-parameter"
OTHER = "other"
USER = "user"

EXIT = "EXIT"

TAGS = {
    0: "AMNo",
    24:"AQNo",
    1: "AMOt",
    2: "AQCo",
    3: "AQEv",
    4: "AQGe",
    5: "AQPa",
    6: "AACo",
    7: "AAEv",
    8: "AAGe",
    9: "AAPa",
    10: "ACFl",
    11: "AQLo",
    12: "CMNo",
    13: "CMOt",
    14: "CMPo",
    15: "CMNe",
    16: "CQCo",
    17: "CQQu",
    18: "CQWa",
    19: "CQQg",
    20: "RMOt",
    21: "RQCo",
    22: "RQPr",
    23: "CQQc"
}

log_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "speechLog.log")
log1 = logging.getLogger('Speech.1')
log2 = logging.getLogger('Speech.2')
ch = logging.StreamHandler()
fh = logging.FileHandler(filename=log_filename, mode='a')
log1.setLevel(logging.DEBUG)
log2.setLevel(logging.INFO)

ch_formatter = logging.Formatter('%(levelname)s: %(message)s')
fh_formatter = logging.Formatter('%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch.setFormatter(ch_formatter)
fh.setFormatter(fh_formatter)
log1.addHandler(fh)
log2.addHandler(ch)

init(autoreset=True)

## Exception raised when the user touches the robot or says one of the exiting keywords.
class StopInteraction(Exception):
    pass

## Exception raised when CAHRIM is killed through terminal.
class KillAction(Exception):
    pass

## Class for retrieving parameters/keywords in dialogs.
class Speech():

    def __init__(self, script, lang, loadconf=True, writedebug=True):
        '''!
        The constructor
        @param script (str or dict) Dictionary containing the dialog or absolute path to the dialog json file (see loadScriptFromFile(), loadScriptFromDict())
        @param lang (str) Language to be used in the dialog
        @param loadconf (bool) Whether to load the configuration file in the init or not
        @param writedebug (bool) Whether or not to print an additional separation line in debug log
        '''

        self.script = None
        self.session = None
        self.ROBOT = "ROBOT"
        self.USER = "USER"

        self.KEYBOARD = "keyboard"
        self.PEPPER = "pepper"
        self.PCMIC = "pc_microphone"


        self._lang = None
        self._supported_languages = []
        self._pepper_is_active = False
        self._mf_weight = 'u'
        self._perfect_match_threshold = 0.5
        self._timeout = 15
        self._ab = []

        self._input = Settings.input_mode
        self._output = Settings.output_mode

        self.gothread=True

        if loadconf:
            if isinstance(script, dict):
                self.loadScriptFromDict(script)
            elif isinstance(script, str):
                self.loadScriptFromFile(script)
            else:
                t = type(script)
                raise TypeError, "Expecting <type 'dict'> or <type 'str'>, got %s instead." % t

            self.setLanguage(lang.lower())

            self.loadKeywords()

        if writedebug:
            log1.debug('-------------------------------------------------------------------------------------')

    def setLanguage(self, language):
        '''!
        Set the language used in the dialog. Raise an exception if the language is not contained in the dialog json file
        (see loadScriptFromFile()).
        @param language (str) Language to use
        '''
        self._lang = language
        assert self._lang in self._supported_languages, "Language '%s' not found in the loaded file." % self._lang

    def getLanguage(self):
        '''!
        Get the currently set language.
        @return (str) The current language
        '''
        return self._lang

    def getLanguageISO_639_1(self, language):
        '''!
        Return the ISO-639-1 code for the given language.
        @param language Language of which the code should be retrieved
        @return (str) The ISO code of the language
        '''
        language = language.lower()

        if language == "english":
            return "en"
        elif language == "italian":
            return "it"
        elif language == "japanese":
            return "ja"

    def getLanguageISO_3166_2(self, language):
        '''!
        Return the ISO-639-1 + ISO-3166-2 code for the given language.
        @param language Language of which the code should be retrieved
        @return (str) The ISO code of the language
        '''
        language = language.lower()

        if language == "english":
            return "en-US"
        elif language == "italian":
            return "it-IT"
        elif language == "japanese":
            return "ja-JP"

    def enablePepperTablet(self, session):
        '''!
        Create a service object linked to ALTabletService
        @param session NAOqi session
        '''
        self.sTablet = self.session.service("ALTabletService")

    def enablePepperInteraction(self, session, ip, initGoogle=True):
        '''!
        Disable user input from keyboard, enable user input through Pepper speech-recognition (Google), enable Pepper
        text-to-speech service.
        @param session (qi session) NAOqi session
        @param ip (str) IP address of the robot
        @param initGoogle (bool) Boolean which starts or not Google recognition
        '''
        self.session = session
        self.ip = ip
        self.sSpeech = self.session.service("ALTextToSpeech")
        self.sAnimSpeech = self.session.service("ALAnimatedSpeech")
        self.sMemory = self.session.service("ALMemory")
        self.sTablet = self.session.service("ALTabletService")
        self.sAsr = self.session.service("ASR2")
        self.sBehavior = self.session.service("ALBehaviorManager")
        self.sPosture = self.session.service("ALRobotPosture")
        self.ROBOT = "PEPPER"

        self.enableAnimatedSpeech(True)

        self._pepper_is_active = True
        # self.setInteractionMode(self.PEPPER)

        if self._input == 3: # Input from Robot mic
            if initGoogle:
                self.initGoogleRecognition()
        else:
            pass


    def enableAnimatedSpeech(self, enabled):
        '''!
        Enable or disable Pepper's arms motion.
        @param enabled (bool) True if animated speech must be enabled, False if must be disabled
        '''
        if self._output == 3 or self._output == 2:
            if enabled:
                self.speech_service = self.sAnimSpeech
            else:
                self.speech_service = self.sSpeech

    def loadKeywords(self):
        '''!
        Load some keywords which are used often within the library.
        '''

        self.KEYWORD_REPEAT = [k.encode('utf-8') for k in self.script[KEYWORDS][REPEAT][self._lang]]
        self.KEYWORD_EXIT = [k.encode('utf-8') for k in self.script[KEYWORDS][STOP][self._lang]]
        self.KEYWORD_AFFIRMATIVE = self.script[KEYWORDS][AFFIRMATIVE][self._lang]
        self.KEYWORD_NEGATIVE = self.script[KEYWORDS][NEGATIVE][self._lang]

    def loadScriptFromFile(self, filename):
        '''!
        Load dialog json file <filename>. If <filename> is an absolute path to an existing file, open it, if it is not
        try looking for it in the same directory of this script. The file must have the following format.
        The fields 'SUPPORTED-LANGUAGES', 'STOP-INTERACTION', 'KEYWORDS' are necessary. Additional languages MUST be
        added in the array of 'SUPPORTED-LANGUAGES', then a sentence/keyword in that language must be added for every
        field. The file should contain the language which is passed to the class constructor. There can be multiple
        numbered sentences for the fields 'ask-parameters' and 'other'.
        {
          "SUPPORTED-LANGUAGES":["language_1"],
          "STOP-INTERACTION":{
            "language_1": <sentence>                     ## sentence said by the bot when asked to stop the interaction
          },
          "KEYWORDS":{
            "repeat":{                                   ## keyword to make the bot repeat the sentence
              "language_1": <keyword>
            },
            "stop":{                                     ## keyword to stop the interaction, this raises an exception
              "language_1": <keyword>
            },
            "affirmative":{                              ## affirmative keywords
              "language_1": [<word1>, <word2>]
            },
            "negative":{                                 ## negative keywords
              "language_1": [<word1>, <word2>]
            }
          },
          "ADDITIONAL":{                                 ## some additional default answers for the bot
            "missedAnswer":{
              "language_1": <sentence>
            },
            "faultAdmission":{
              "language_1": <sentence>
            }
          },
          "topic": {                                     ## conversation topic
            "ask-parameters": {                          ## ONE OR MORE sentences to ask for the required parameters,
              "0": {                                     ### none, one or two placeholders must be present to let the bot make suggestions
                "language_1": <sentence $OPTION1$ $OPTION2$>
              }
            },
            "ask-before-options": {                      ## A SINGLE question to be said before showing the possible options
              "0": {
                "language_1": <sentence>
              }
            },
            "parameter-answer": {                        ## sentences said by the bot when the parameter is retrieved
              "with-keyword": {                          ### A SINGLE sentence for the case in which the parameter is a keyword
                "language_1": <sentence $KEYWORD$>
              },
              "without-keyword": {                       ### A SINGLE sentence for the case in which the parameter is the whole user input
                "language_1": <sentence>
              }
            },
            "ask-confirmation":{                         ## questions made by the bot to ask for confirmation of the parameter
              "with-keyword": {                          ### A SINGLE question for the case in which the parameter is a keyword
                "language_1": <sentence $CONFIRM$>
              },
              "without-keyword":{                        ### A SINGLE question for the case in which the parameter is the whole user input
                "language_1": <sentence $CONFIRM$>
              }
            },
            "wrong-parameter": {                         ## ONE OR MORE sentences said by the bot when the parameter is wrong
              "0": {
                "language_1": <sentence>
              }
            },
            "other": {                                   ## ONE OR MORE bot sentences which do not imply to understand the user reply
              "0": {                                     ### If a variable should be used, put a placeholder in the form specified
                "language_1": <sentence $<PLACEHOLDER>$>
              }
            }
          }
        }

        @param filename (str) Name or absolute path of the json file
        '''
        if os.path.isfile(filename):
            conf = filename
        else:
            conf = os.path.join(os.path.dirname(__file__), filename)
            if not os.path.isfile(conf):
                raise Exception, "File cannot be found: %s" % filename
        with open(conf) as f:
            self.script = json.load(f)
        self._supported_languages = []
        self._supported_languages = [l.encode('utf-8') for l in self.script[SUPPORTED_LANGUAGES]]

    def loadScriptFromDict(self, dict):
        '''!
        Same behavior of loadScriptFromFile() but load the dialogs from a Python dictionary instead of a json file.
        @param dict (dict) Dictionary containing the dialog sentences formatted as explained for loadScriptFromFile()
        '''
        self.script = dict
        self._supported_languages = []
        self._supported_languages = [l.encode('utf-8') for l in self.script[SUPPORTED_LANGUAGES]]

    def setMatchFinderWeight(self, weight):
        '''!
        Set where to put the weight on the sentence to find the match with the user input (see MatchFinder class)
        @param weight (str) A letter indicating which part of the sentence is more relevant to find the match (left 'l',
        center 'c', right 'r', uniform 'u').
        '''
        self._mf_weight = weight

    def getMatchFinderWeight(self):
        '''!
        Returns the current weight of MatchFinder instance
        @return (str) New weight of MatchFinder instance
        '''
        return self._mf_weight

    def setTimer(self, timer):
        '''!
        Set the amount of time that must elapse before the robot asks again the same question when not getting any answer.
        @param timer (int) New timer in seconds
        '''
        self._timeout = timer

    def getTimer(self):
        '''!
        Get the current timer
        @return (int) Current timer
        '''
        return self._timeout


    def setPerfectMatchThreshold(self, threshold):
        '''!
        Set threshold for answer matching (see MatchFinder class).
        @param threshold (float) New threshold for answer matching
        '''
        assert 0.1 <= threshold and threshold <= 1.0, "Threshold must be between 0.1 and 1.0."

        self._threshold = threshold

    def getPerfectMatchThreshold(self):
        '''!
        Get threshold for answer matching (see MatchFinder class).
        @return (float) Current threshold for answer matching
        '''
        return self._threshold

    def getInput(self, blocking=True, noisy="normal"):
        '''!
        Get the input from the user. According to the value of self._input, the input can be taken through different ways
        0 - CONSOLE: the input is typed on the keyboard
        1 - PC: the input is given verbally to the pc microphone
        2 - SMARTPHONE: the input is given verbally to a smartphone microphone
        3 - ROBOT: the input is given verbally to the robot
        @param blocking (bool) Make the function blocking or not. If not, nothing is returned until something is detected
		or the timeout is reached
		@param noisy (str) Environment noise level: either "normal" or "noisy".
        @return (str) User input
        '''
        if self._input == 0:
            if not blocking:
                log1.debug("In KEYBOARD input mode the 'blocking' parameter has no effect. It will be ignored.")
            return self.getInputFromKeyboard()
        elif self._input == 1:
            #TODO handle blocking parameter
            return self.getInputFromMic()
        elif self._input == 2:
            # TODO handle blocking parameter
            return self.getInputFromSmartphone()
        elif self._input == 3:
            self.initGoogleRecognition()
            ifg = self.getInputFromGoogle(blocking=blocking, noisy=noisy)
            return ifg

    def getInputFromKeyboard(self):
        '''!
        Get the user input from the keyboard.
        @return (unicode) User input
        '''
        return raw_input(Fore.CYAN + "USER > ").decode(sys.stdin.encoding)

    def getInputFromMic(self):
        '''!
        Get the user input from the PC mic.
        @return (unicode) User input
        '''

        r = sr.Recognizer()

        # # If outuput is on the shell only, add a sleep, to allow the user to read ROBOT sentence before speaking
        if self._output == 0:
            time.sleep(4)

        with sr.Microphone() as source:
            print("== Now you can speak ==")
            audio = r.listen(source, phrase_time_limit=7)

        # Speech recognition using Google Speech Recognition
        try:
            text = r.recognize_google(audio, language=self.getLanguageISO_3166_2(self._lang))
            # text = r.recognize_google_cloud(audio, language=caressestools.Language.lang_google,
            #                                 credentials_json=GOOGLE_CLOUD_SPEECH_CREDENTIALS)  # , preferred_phrases=settings["google"]["extra-words"][LANGUAGE])
            return text

        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            return ""

    # def getInputFromSmartphone(self):
    #     '''!
    #     Get the user input from a smartphone mic. The smartphone should have the CARESSES app installed in it.
    #     @return (unicode) User input
    #     '''

    #     #connected = False
    #     #while not connected:
    #     #    try:
    #     #        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     #        sock.connect(("127.0.0.1", 12350))
    #     #        connected = True
    #     #    except Exception as e:
    #     #        time.sleep(2)

    #     #output_queue = Queue.Queue(maxsize=0)
    #     #output_handler = CahrimThreads.socket_handlers.OutputMsgHandler(output_queue)
    #     #thread = CahrimThreads.socket_handlers.MsgSender(sock, output_queue)
    #     #thread.start()

    #     #output_handler.writeSupplyMessage("publish", "D11.6", "robotListens")

    #     CahrimThreads.socket_handlers.InputMsgHandler.resetSmartphone()
    #     while (CahrimThreads.socket_handlers.InputMsgHandler.getSmartphone() is None):
    #         pass

    #     toret = CahrimThreads.socket_handlers.InputMsgHandler.getSmartphone()
    #     CahrimThreads.socket_handlers.InputMsgHandler.resetSmartphone()

    #     #sock.close()
    #     #thread.stop()
    #     #time.sleep(1)

    #     return toret

    # def getOptionsFromSmartphone(self, options):

    #     try:
    #         options_str = [a.encode('ascii','ignore') for a in options]
    #     except:
    #         pass


    #     #connected = False
    #     #while not connected:
    #     #    try:
    #     #        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     #        sock.connect(("127.0.0.1", 12350))
    #     #        connected = True
    #     #    except Exception as e:
    #     #        time.sleep(2)

    #     #output_queue = Queue.Queue(maxsize=0)
    #     #output_handler = CahrimThreads.socket_handlers.OutputMsgHandler(output_queue)
    #     #thread = CahrimThreads.socket_handlers.MsgSender(sock, output_queue)
    #     #thread.start()

    #     #output_handler.writeSupplyMessage("publish", "D11.6", "robotListens")
    #     #time.sleep(1)
    #     #sock.close()
    #     #thread.stop()

    #     while(self.gothread):
    #         CahrimThreads.socket_handlers.InputMsgHandler.resetSmartphone()
    #         while (self.gothread and (CahrimThreads.socket_handlers.InputMsgHandler.getSmartphone() is None)):
    #             pass

    #         toret = CahrimThreads.socket_handlers.InputMsgHandler.getSmartphone()
    #         CahrimThreads.socket_handlers.InputMsgHandler.resetSmartphone()
    #         if toret is not None and toret.lower() in map(str.lower,options_str) and toret is not "":
    #             self.sMemory.insertData("WordRecognized", ["<...> "+toret+" <...>", 1])
    #         elif toret is not None:
    #             connected = False
    #             while not connected:
    #                 try:
    #                     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #                     sock.connect(("127.0.0.1", 12350))
    #                     connected = True
    #                 except Exception as e:
    #                     time.sleep(2)

    #             #output_queue = Queue.Queue(maxsize=0)
    #             #output_handler = CahrimThreads.socket_handlers.OutputMsgHandler(output_queue)
    #             #thread = CahrimThreads.socket_handlers.MsgSender(sock, output_queue)
    #             #thread.start()

    #             #output_handler.writeSupplyMessage("publish", "D11.6", "robotListens")
    #             #time.sleep(1)
    #             #sock.close()
    #             #thread.stop()


    def getInputFromGoogle(self, wait=0.1, blocking=True, noisy="normal"):
        '''!
        Get the user input from Pepper's memory, recognized through Google Speech Recognition.
        Clean the memory right before returning, otherwise the same input will be returned every time this function is
        called even if the user did not talk anymore.
        @param wait (float) Waiting time before returning the user input. If a new sentence is detected within the waiting
        time, it is concatenated to the previous detected sentence before being returned
        @param blocking (bool) Make the function blocking or not. If not, nothing is returned until something is detected
		or the timeout is reached
        @return (unicode) User input
        '''

        start_time_no_input = time.time()
        start_time_silence = time.time() + 3600

        user_input = ""
        input = None
        input = self.sMemory.getData(SPEECH_RECO_EVENT)

        #TODO forse questo blocco if si può spostare dentro a enablePepperInteraction()
        if self._pepper_is_active:
            self.signal_tablet_touch = self.sTablet.onTouchUp.connect(self.onTabletTouch)
            self.touched_for_options = False
            if (noisy=="normal"):
                self.touch = self.sMemory.subscriber("TouchChanged")
                self.signal_touch = self.touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))
            else:
                self.touch = self.sMemory.subscriber("LeftBumperPressed")
                self.signal_touch = self.touch.signal.connect(functools.partial(self.onTouch, "LeftBumperPressed"))
            self.is_touched = False

        # # If the function is not blocking, return whatever is in the memory, even if nothing is detected
        if not blocking:
            self.cleanMemory()
            self.sTablet.onTouchUp.disconnect(self.signal_tablet_touch)
            return input
        # # If the function is blocking, return only after detecting something
        else:
            while True:
                while input == None or input == []:
                    killed = self.checkIfKilled()
                    if killed:
                        self.sTablet.onTouchUp.disconnect(self.signal_tablet_touch)
                        self.touch.signal.disconnect(self.signal_touch)
                        raise KillAction
                    if self.is_touched:
                        self.sTablet.onTouchUp.disconnect(self.signal_tablet_touch)
                        self.touch.signal.disconnect(self.signal_touch)
                        self.is_touched = False
                        self.stopInteraction()
                    if self.touched_for_options:
                        self.touch.signal.disconnect(self.signal_touch)
                        return "[[%s]]" % self.script[KEYWORDS][OPTIONS][self._lang]
                    if time.time() - start_time_silence > wait:
                        self.sTablet.onTouchUp.disconnect(self.signal_tablet_touch)
                        self.touch.signal.disconnect(self.signal_touch)
                        return user_input
                    if time.time() - start_time_no_input > self._timeout:
                        self.sTablet.onTouchUp.disconnect(self.signal_tablet_touch)
                        self.touch.signal.disconnect(self.signal_touch)
                        return None

                    input = self.sMemory.getData(SPEECH_RECO_EVENT)

                sep = " " if not user_input == "" else ""
                user_input = user_input + sep + input[0][0].decode('utf-8')
                start_time_silence = time.time()
                start_time_no_input = time.time()
                self.cleanMemory()
                input = self.sMemory.getData(SPEECH_RECO_EVENT)

    ## Callback
    def onTabletTouch(self, x, y):
        try:
            self.sTablet.onTouchUp.disconnect(self.signal_tablet_touch)
        except:
            pass
        self.showOptionsOnTouch()

    ## Callback
    def onTouch(self, msg, value):
        log2.info("The user touched the robot.")
        self.is_touched = True

    def showOptionsOnTouch(self):
        '''!
        Set to True the flag responsible for showing the options on the tablet.
        '''
        self.touched_for_options = True

    def checkIfKilled(self):
        '''!
        Check if the dialog with the robot has been killed externally.
        @return (bool) True if the dialog has been killed, False otherwise
        '''
        try:
            killed = self.sMemory.getData(CAHRIM_KILL_ACTION)
            if killed:
                self.cleanMemory()
                self.sMemory.insertData(CAHRIM_KILL_ACTION, False)
            return killed
        except:
            pass

    def initGoogleRecognition(self):
        '''!
        Subscribe to the microevent SPEECH_RECO_EVENT, which is raised by Softbank Robotics' AbcdkSoundReceiver.py
        inside the _processRemote() function whenever a sentence is recognized by Google services.
        '''
        # # If the action previously ended in a wrong away, clean up the memory
        self.cleanMemory()
        self.sMemory.subscriber(SPEECH_RECO_EVENT)

    def cleanMemory(self):
        '''!
        Clean Pepper's memory from the previously detected words/sentences.
        '''
        try:
            self.sMemory.insertData(SPEECH_RECO_EVENT, [])
        except:
            pass

    def performInteraction(self, line, tag = "    ", extraPhrases=None, noisy="normal"):
        '''!
        Make the bot/robot play its line and get the input by the user. The bot/robot repeats its line if requested by
        the user.
        @param line (str) Sentence that the bot must say
        @param tag (str) Tag identifying the class of <sentence>
        @param extraPhrases (list of str) An optional list of words/phrases which should be given priority in recognition.
        If the list is None, old Google API are used, otherwise new Google Cloud API are used (billing is required)
        @param noisy (str) Environment noise level: either "normal" or "noisy".
        @return (unicode) User input
        '''

        self.say(line, tag)

        if self._input == 3:
            # # Start recognition
            if extraPhrases is not None:
                assert type(extraPhrases) is list
                try:
                    self.sAsr.setGoogleCredentials(Settings.googlekey)
                    self.sAsr.setPreferredPhrases(extraPhrases)
                    use_google_key = True
                except:
                    log1.warning("Google credentials not found. Using old API instead of new one.")
                    extraPhrases = None
            if extraPhrases is None:
                use_google_key = False

            setAutonomousAbilities(self.session,False, True, False, False, False)
            self.sPosture.goToPosture("Stand", 0.5)

            self.sAsr.startReco(self._lang.title(), use_google_key, True)

        must_repeat = True

        while must_repeat:

            user_input = self.getInput(noisy=noisy)

            if user_input is not None:
                if not self._input == 0:
                    self.userSaid(user_input)

                for k in self.KEYWORD_EXIT:
                    if unicode(k.lower(),"utf-8") in user_input.lower():
                        self.stopInteraction()

                must_repeat=False
                for k in self.KEYWORD_REPEAT:
                    if unicode(k.lower(),"utf-8") in user_input.lower():
                        must_repeat=True
                        self.sAsr.stopReco()
                        self.say(line, tag)
                        self.sAsr.startReco(self._lang.title(), use_google_key, True)
                        break

            else:
                must_repeat = False

        if self._input == 3:
            # # Stop recognition
            self.sAsr.stopReco()

        return user_input

    def stopInteraction(self):
        '''!
        Raise a StopInteraction exception. Make the bot an exiting sentence first.
        :raises StopInteraction: if the user verbally stops the interaction through the keyword specified in self.script
        '''
        self.replyAffirmative()
        self.say(self.script[STOP_INTERACTION][self._lang], TAGS[1])

        try:
            self.sAsr.stopReco()
        except:
            pass

        # # Terminate NAOqi running behaviors
        if self._pepper_is_active:
            if self.sBehavior.isBehaviorRunning("caresses_game_memory/behavior_1"):
               self.sBehavior.stopBehavior("caresses_game_memory/behavior_1")

        raise StopInteraction("The user stopped the interaction before expected.")

    def playLine(self, actor, line, tag="    "):
        '''!
        Print the name of the speaker and the line played. If the speaker is the robot Pepper, make it actually pronounce
        the sentence.
        @param actor (str) The speaker
        @param line (str) The sentence
        @param tag (str) Tag identifying the class of <sentence>
        '''

        if actor == self.ROBOT:
            color = Fore.GREEN
        elif actor == self.USER:
            color = Fore.CYAN
        else:
            color = Fore.MAGENTA

        log1.info("[%s] " % tag + actor + " > " + line)
        try:
            print(color + actor + " > " + line.encode("utf-8"))
        except:
            pass

        if actor == self.ROBOT:
            if self._output == 0:
                # # The output is already print on the console, no need to do anything else
                pass
            elif self._output == 1:
                pass
            elif self._output == 2:
                #trasmettere la frase allo smartphone

                #connected = False
                #while not connected:
                #    try:
                #        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                #        sock.connect(("127.0.0.1", 12350))
                #        connected = True
                #    except Exception as e:
                #        time.sleep(2)

                #output_queue = Queue.Queue(maxsize=0)
                #output_handler = CahrimThreads.socket_handlers.OutputMsgHandler(output_queue)
                #thread = CahrimThreads.socket_handlers.MsgSender(sock, output_queue)
                #thread.start()


                #output_handler.writeSupplyMessage("publish", "D11.6", "robotSays:["+line+"]")
                self.speech_service.say(line)
                #sock.close()
                #thread.stop()
                #time.sleep(1)

            elif self._output == 3:
                self.speech_service.say(line)

    def say(self, sentence, tag="    "):
        '''!
        Let the bot say the specified <sentence>.
        @param sentence (str) The sentence to be said
        @param tag (str) Tag identifying the class of <sentence>
        '''
        self.playLine(self.ROBOT, sentence, tag)

    def userSaid(self, sentence, tag="    "):
        '''!
        Call 'playLine' with the USER actor by default.
        @param sentence (str) The sentence said by the user
        @param tag (str) Tag identifying the class of <sentence>
        '''
        self.playLine(self.USER, sentence, tag)

    def monolog(self, topic, sentence, tag="    ", param=None, group=OTHER):
        '''!
        Get a sentence from the loaded json dialog (self.script), as specified by the parameters, and let the bot say it
        without expecting a user reply. By default the sentence is retrieved by the 'other' field of the chosen topic
        and the sentence is expected not to have parameters in it.
        @param topic (str) The topic of the monolog, must be one of the top objects of self.script
        @param sentence (str) Index of the sentence within the selected <group>
        @param tag (str) Tag identifying the class of <sentence>
        @param param "$<PLACEHOLDER>$ (None or dict param: dictionary containing the pairs) <parameter>" which can be passed if the sentence has to be formatted (default None)
        @param group (str) Field of the chosen <topic> from which the sentence should be selected (default 'other')
        '''
        line = self.script[topic][group][str(sentence)][self._lang].encode('utf-8')
        line = unicode(line,"utf-8")

        if param is not None:

            for key in param.keys():
                line = line.replace(key, param[key])

        self.say(line, tag)

    def dialog(self, topic, options, checkValidity, askForConfirmation, sentence=None, useChoiceManagerFromStart=False,
               extraPhrases=None, sayFinalReply=True, removeDiscardedOption=True, excludeSomeSuggestions=None, noisy="normal"):
        '''!
        Dialog with the user to retrieve the desired parameter/keyword. First, get a sentence from the "ask-parameters"
        field of the chosen <topic> of the loaded json dialog (self.script): if <sentence> is not specified, a random one
        is chosen among the ones available according to the number of options passed. The sentence can be structured to
        expect none, one or two parameters (it must have placeholders for the parameters in the form $<PLACEHOLDER>$).
        The parameters will be replaced with the first elements of the <options> list parameter passed to the function
        and used by the bot as suggestions (among the possible input keywords). The function calls self.getResponseByFindingOption()
        to actually retrieve the keyword, check its documentation. Finally reply to the user with a different answer
        depending on the value of the retrieved parameter (if it is one of the possible keywords, the keyword is repeated
        in the answer). If <askForConfirmation> is True, the parameter is returned only if the user confirms, otherwise
        the interaction is repeated. If <useChoiceManagerFromStart> is True, the possible options are immediately displayed
        on the tablet.
        @param topic (str) The topic of the dialog, must be one of the top objects of self.script
        @param options (list of str) Possible options (keywords) to chose from; the first two are used also for suggestions
        @param checkValidity (bool) A boolean to indicate if the parameter to retrieve must be one among <options> or anything
        @param askForConfirmation (bool) A boolean to indicate whether the bot should ask the user if the parameter is correct
        @param sentence (str) Index of the sentence within the "ask-parameters" field of the chosen <topic> (default None)
        @param useChoiceManagerFromStart (bool) A boolean to indicate if the ChoiceManager should be launched immediately (default False)
        @param extraPhrases (list of str) An optional list of words/phrases which should be given priority in recognition.
        If the list is None, old Google API are used, otherwise new Google Cloud API are used (billing is required)
        @param sayFinalReply (bool) Whether or not the last sentence of the robot should be said
        @param removeDiscardedOption (bool) If True then any misunderstood answer will be discarded from the proposed options at the following attempt within the same function call
        @param excludeSomeSuggestions (list of str) Options to be removed. It can be None if no options should be excluded
        @return (unicode) The retrieved parameter
        '''

        try:
            options = [unicode(a, "utf-8") for a in options]
        except:
            pass

        # # If there is a single option and open answer are not accepted, there is no need to ask for the parameter.
        # # Use the only one available.

        if len(options) == 1 and checkValidity is True:
            parameter = options[0]
            finalReply = WITH_KEYWORD
            param = {"$KEYWORD$": parameter}
            if excludeSomeSuggestions is not None:
                if parameter in excludeSomeSuggestions:
                    finalReply = WITHOUT_KEYWORD
                    param = None
        # # Otherwise ask for it...
        else:

            # # Exclude some choices from the suggestions
            options = self.removeSuggestionsFromOptions(options, excludeSomeSuggestions)

            sentences_no_options = []
            sentences_one_option = []
            sentences_two_options = []
            sentences_three_options = []

            need_confirmation = askForConfirmation

            for sent in self.script[topic][ASK_PARAMETERS]:
                s = self.script[topic][ASK_PARAMETERS][sent][self._lang].encode('utf-8')
                if "$OPTION3$" in s:
                    sentences_three_options.append(s)
                elif "$OPTION2$" in s:
                    sentences_two_options.append(s)
                elif "$OPTION1$" in s:
                    sentences_one_option.append(s)
                else:
                    sentences_no_options.append(s)

            correct_parameter = False
            guess = True

            while not correct_parameter:

                # # If possible, suggest at least 2 options
                if len(options) == 1:
                    num_options = 1
                    lines = sentences_one_option
                elif len(options) == 2:
                    num_options = 2
                    lines = sentences_two_options
                elif len(options) > 2:
                    num_options = 3
                    lines = sentences_two_options + sentences_three_options
                else:
                    num_options = 0
                    lines = sentences_no_options

                if sentence == None:
                    sent = randint(0, len(lines) - 1)
                    line = lines[sent]
                else:
                    line = self.script[topic][ASK_PARAMETERS][sent][self._lang].encode('utf-8')

                line = unicode(line,"utf-8")

                if num_options >= 1:
                    o1 = options[0]
                    line = line.replace('$OPTION1$', o1)
                    if num_options > 1:
                        o2 = options[1]
                        line = line.replace('$OPTION2$', o2)
                        if num_options > 2:
                            o3 = options[2]
                            line = line.replace('$OPTION3$', o3)

                # # Include again the removed suggestions
                options = self.addSuggestionsToOptions(options, excludeSomeSuggestions)
                if useChoiceManagerFromStart:
                    if self._pepper_is_active:
                        import multipage_choice_manager as mcm
                        self.mcm = mcm.MultiPageChoiceManager(self.ip)
                    self.say(line, TAGS[5])
                    isKeyword = True
                    parameter = self.selectOption(options)
                    perfect_match = True
                else:
                    user_input = self.performInteraction(line, tag=TAGS[5], extraPhrases=extraPhrases, noisy=noisy)
                    if user_input is None:
                        useChoiceManagerFromStart = True
                        continue
                    isKeyword, parameter, perfect_match = self.getResponseByFindingOption(topic, user_input, options, checkValidity, guess)

                if excludeSomeSuggestions is not None:
                    if parameter in excludeSomeSuggestions:
                        isKeyword = False

                if isKeyword:
                    finalReply = WITH_KEYWORD
                    param = {"$KEYWORD$" : parameter}
                    if not perfect_match:
                        need_confirmation = True
                else:
                    finalReply = WITHOUT_KEYWORD
                    param = None
                if need_confirmation:
                    correct_parameter = self.askIfCorrect(topic, parameter, isKeyword, noisy=noisy)
                    if not correct_parameter:
                        line = self.script[ADDITIONAL][FAULT_ADMISSION][self._lang].encode('utf-8')
                        self.say(line, TAGS[1])
                        if isKeyword:
                            guess = False
                            if removeDiscardedOption:
                                # Remove the option if the user explicitely said it's not the desired one
                                options.remove(parameter)

                                # # If there is a single option left and open answer are not accepted, there is no need to ask for the parameter.
                                # # Use the only one available.

                                if len(options) == 1 and checkValidity is True:
                                    parameter = options[0]
                                    finalReply = WITH_KEYWORD
                                    param = {"$KEYWORD$": parameter}
                                    correct_parameter = True
                                    if excludeSomeSuggestions is not None:
                                        if parameter in excludeSomeSuggestions:
                                            finalReply = WITHOUT_KEYWORD
                                            param = None
                else:
                    correct_parameter = True

                # # Exclude some choices from the suggestions
                options = self.removeSuggestionsFromOptions(options, excludeSomeSuggestions)

        if sayFinalReply:
            self.monolog(topic, finalReply, param = param, group=PARAMETER_ANSWER, tag=TAGS[1])

        return parameter

    def removeSuggestionsFromOptions(self, options, to_remove):
        '''!
        Remove some of the options.
        @param options (list of str) The available options
        @param to_remove (list of str) The options to remove
        @return (list of str) The reduced options
        '''
        if to_remove is not None:
            if isinstance(to_remove, list):
                for o in to_remove:
                    options.remove(o)
            else:
                options.remove(to_remove)

        return options


    def addSuggestionsToOptions(self, options, to_add):
        '''!
        Add some options.
        @param options (list of str) The available options
        @param to_add (list of str) The options to add
        @return (list of str) The incremented options
        '''
        if to_add is not None:
            if isinstance(to_add, list):
                for o in to_add:
                    if o not in options:
                        options.append(o)
            else:
                if to_add not in options:
                    options.append(to_add)

        return options

    def getResponseByFindingOption(self, topic, user_input, options, checkValidity, guess):
        '''!
        If one of the valid keywords (<options>) is found in the user input, the option is returned.
        If not: if <checkValidity> is False (it means that any answer is accepted), the function returns the whole user
        sentence; if True, the bot replies that it didn't get the parameter and force the selection of one of the
        <options> by calling self.selectOption().
        @param topic (str) The topic of the dialog, must be one of the top objects of self.script
        @param user_input (str) What the user said
        @param options (list of str) Possible options (keywords) to choose from
        @param checkValidity (bool) A boolean to indicate if the parameter to retrieve must be one among <options> or anything
        @param guess (bool) A boolean to indicate whether the parameter should be guessed according to meaningful words or not
        @return (bool, str, bool) A boolean indicating if a keyword has been retrieved or not, the keyword or the whole sentence retrieved
                 and a boolean indicating if the keyword detected perfectly matches one among <options>
        '''

        # # Look for exact match of any single keyword in the user input
        sorted_options = reversed(sorted(options, key=len))
        for option in sorted_options:
            if option.lower() in user_input.lower():
                return True, option, True

        if guess:
            # #  Try to guess by analysing only meaningful words
            mf = MatchFinder(self._lang)
            mf.setWeight(self._mf_weight)
            matches = mf.findClosestMatch(user_input, options)
            if matches[0][1] >= self._perfect_match_threshold:
                return True, matches[0][0], False

        # # If none is found, then check if the user asked to explicitly show the possible options
        show_options = self.script[KEYWORDS][OPTIONS][self._lang] in user_input.lower()

        # # If so or if a keyword MUST be found, show the possible options
        if checkValidity or show_options:
            if self._pepper_is_active:
                import multipage_choice_manager as mcm
                self.mcm = mcm.MultiPageChoiceManager(self.ip)
            if show_options:
                self.say(self.script[ADDITIONAL][SHOW_OPTION][self._lang], TAGS[1])
            elif checkValidity:
                self.monolog(topic, str(0), group=WRONG_PARAMETER, tag=TAGS[24])
            option = self.selectOption(options)
            return True, option, True
        else:
            return False, user_input, False

    def selectOption(self, options):
        '''!
        Force the selection of a valid keyword among <options>. If the interaction mode is set to 'pepper', the selection
        is made through the tablet 'ChoiceManager'.
        @param options (list of str) Possible options (keywords) to chose from
        @return (str) The selected option/keyword
        '''
        print options

        if not self._pepper_is_active:

            if self._input == 0: # # CONSOLE, input from keyboard
                option = None
                while not option in options and not option == EXIT:
                    option = raw_input(Fore.CYAN + "USER > ")
                return option

            elif self._input == 1: # # PC, input from PC microphone
                option = self.getInputFromMic()
                while not option in options and not option == EXIT:
                    option = self.getInputFromMic()
                return option

            elif self._input == 2: # # SMARTPHONE, input from smartphone microphone
                pass

            elif self._input == 3: # # ROBOT, input from smartphone microphone
                # # The input is set to Robot mic but Pepper is not active, swith to keyboard input
                option = None
                while not option in options and not option == EXIT:
                    option = raw_input(Fore.CYAN + "USER > ")
                return option

        else:

            question = ""

            if self._input==2:
                self.gothread = True
                t = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[options])
                t.start()

            option = self.mcm.giveChoiceMultiPage(question, options)
            self.gothread = False
            option = [unicode(option[0], "utf-8"), option[1]]

            self.mcm.kill()

            self.checkIfKilledDuringMcm(self.mcm, option)

            return option[0]

    def checkIfKilledDuringMcm(self, mcm, answer, func=None):
        '''!
        Check if the main program was killed when the MultiPageChoiceManager was running. If so, the answer "EXIT" returned
        by the MCM is fake (the answer was inserted in the robot's memory without the user to say it) and, therefore, the
        exception KillAction is raised before the answer is printed or the robot can answer. If not, the answer is displayed.
        If it is "EXIT", then the user wants to stop the interaction and stopInteraction() is called.
        @param mcm MultiPageChoiceManager instance
        @param answer (str) Answer retrieved through the MCM
        @param func Function to call in order to safely stop the program before raising the killing exception
        '''

        killed = self.checkIfKilled()
        if killed:
            if func is not None:
                func()
            raise KillAction
        else:
            self.userSaid(str(answer))

            if answer[0] == mcm.exit_btn:
                if func is not None:
                    func()
                self.stopInteraction()


    def askIfCorrect(self, topic, parameter, isKeywordParameter, noisy="normal"):
        '''!
        Ask the user if the understood parameter is correct or not.
        @param topic (str) The topic of the dialog, must be one of the top objects of self.script
        @param parameter (str) The parameter retrieved during the interaction with the user
        @param isKeywordParameter (bool) A boolean to indicate whether the parameter retrieved is one of the expected
        keywords (True) or the whole user input (False)
        @param noisy (str) Environment noise level: either "normal" or "noisy".
        @return (bool) True if the user has confirmed, False if not
        '''
        keyword_or_not = WITH_KEYWORD if isKeywordParameter else WITHOUT_KEYWORD
        try:
            line = self.script[topic][ASK_CONFIRMATION][keyword_or_not][self._lang].encode('utf-8').replace("$CONFIRM$", parameter)
        except:
            line = self.script[topic][ASK_CONFIRMATION][keyword_or_not][self._lang].replace("$CONFIRM$", parameter)

        return self.askYesOrNoQuestion(line, TAGS[2], noisy=noisy)

    def askYesOrNoQuestion(self, question, tag="    ", noisy="normal"):
        '''!
        Ask a yes-or-no question. Look in the user input for affirmative or negative keywords. If the answer is not clear,
        ask explicitly by calling self.selectOption().
        @param question (str) A yes-or-no type question
        @param tag (str) Tag identifying the class of <question>
        @param noisy (str) Environment noise level: either "normal" or "noisy".
        @return (bool) True if the answer is positive, False if negative
        '''

        found_affermative = False
        found_negative = False

        user_input = self.performInteraction(question, tag, noisy=noisy)

        if user_input is not None:

            for word in self.KEYWORD_AFFIRMATIVE:
                regex = r"(\s|^)(" + word.encode('utf-8') + r")([\,\.]|\s|$)"
                match = re.search(regex, user_input.encode('utf-8'), re.IGNORECASE | re.UNICODE)
                if match is not None:
                    found_affermative = True
                    break

            for word in self.KEYWORD_NEGATIVE:
                regex = r"(\s|^)(" + word.encode('utf-8') + r")([\,\.]|\s|$)"
                match = re.search(regex, user_input, re.IGNORECASE | re.UNICODE)
                if match is not None:
                    found_negative = True
                    break

        found_both = found_affermative and found_negative
        found_none = not (found_affermative or found_negative)

        if user_input is not None:
            # # Check if the user asked to explicitly show the possible options
            show_options = self.script[KEYWORDS][OPTIONS][self._lang] in user_input.lower()

        if found_both or found_none:
            if self._pepper_is_active:
                import multipage_choice_manager as mcm
                self.mcm = mcm.MultiPageChoiceManager(self.ip)
            if user_input is not None and not show_options:
                line = self.script[ADDITIONAL][MISSED_ANSWER][self._lang].encode('utf-8')
                self.say(line, TAGS[0])
            self.say(question, tag)
            #yes = self.KEYWORD_AFFIRMATIVE[0].encode('utf-8')
            yes = self.KEYWORD_AFFIRMATIVE[0]
            #no = self.KEYWORD_NEGATIVE[0].encode('utf-8')
            no = self.KEYWORD_NEGATIVE[0]
            answer = self.selectOption([yes, no])
            answer = True if answer == yes else False
        elif found_affermative:
            answer = True
        elif found_negative:
            answer = False

        return answer

    def replyAffirmative(self):
        '''!
        Let the bot reply with a random affirmative answer among the ones in the configuration file.
        '''
        lines_ok = [l.encode('utf-8') for l in self.script[ADDITIONAL][OK][self._lang]]
        self.say(lines_ok[randint(0, len(lines_ok) - 1)], TAGS[1])


    def customNumber(self):
        '''
        Launch the tablet gui to insert a custom phone number.
        @return (unicode) User input
        '''
        self._ab = getAutonomousAbilities(self.session)
        setAutonomousAbilities(self.session, False, True, False, False, False)
        self.session.service("ALRobotPosture").goToPosture("Stand", 0.5)
        cn = CustomNumber(self.session)
        user_input = cn.selectnumber()
        setAutonomousAbilities(self.session, self._ab[0], self._ab[1], self._ab[2], self._ab[3], self._ab[4])

        return user_input

    def dialogTime(self, askForConfirmation, togetherWithDate=False, noisy="normal"):
        '''!
        Perform dialog to retrieve the time in a sentence by using TimeDateParser class. The dialog will return only the
        the first time retrieved in the sentence. If <askForConfirmation> is True, the parameter is returned only if the user confirms, otherwise
        the interaction is repeated.
        @param askForConfirmation (bool) A boolean to indicate whether the bot should ask the user if the time is correct
        @param togetherWithDate (bool) Whether or not the function was called from within the dialogDate() function
        @param noisy (str) Environment noise level: either "normal" or "noisy".
        @return (str, datetime.time) The time retrieved both as string and as datetime.time object
        '''

        str_time = None
        time = None
        correct_parameter = False

        while not correct_parameter:
            time = None
            while time is None:
                line = self.script[GETTIME][ASK_PARAMETERS]["0"][self._lang].encode('utf-8')

                user_input = self.performInteraction(line, TAGS[5], noisy=noisy)

                # # Check if the user asked to explicitly show the possible options
                if user_input is not None:
                    show_options = self.script[KEYWORDS][OPTIONS][self._lang] in user_input.lower()

                if user_input is None or show_options:
                    self.say(line, TAGS[5])
                    self._ab = getAutonomousAbilities(self.session)
                    setAutonomousAbilities(self.session, False, True, False, False, False)
                    self.session.service("ALRobotPosture").goToPosture("Stand", 0.5)
                    dts = DateTimeSelector(self.session)
                    if self._lang == 'english':
                        user_input = dts.selectTime12()
                        if user_input is None:
                            self.stopInteraction()
                    else:
                        user_input = dts.selectTime24()
                        if user_input is None:
                            self.stopInteraction()
                    setAutonomousAbilities(self.session, self._ab[0], self._ab[1], self._ab[2], self._ab[3],
                                           self._ab[4])
                    self.userSaid(user_input)

                tdp = TimeDateParser(self._lang)

                time_list = tdp.getTime((user_input))

                if time_list is not None:
                    finalReply = WITH_KEYWORD
                    str_time = time_list[0][0]
                    time = time_list[0][1]
                    str_time = tdp.composeStringTime(str_time)
                    if askForConfirmation:
                        correct_parameter = self.askIfCorrect(GETTIME, str_time, False, noisy=noisy)
                    else:
                        correct_parameter = True
                else:
                    self.monolog(GETTIME, str(0), group=WRONG_PARAMETER, tag=TAGS[0])

        if not togetherWithDate:
            self.monolog(GETTIME, "0", param={"$KEYWORD$": str_time}, group=PARAMETER_ANSWER, tag=TAGS[1])

        return str_time, time

    def dialogDateTime(self, required, askForConfirmation, timeRequired=False, noisy="normal"):
        '''!
        Perform a dialog to retrieve the date in a sentence by using TimeDateParser class. The <required> parameters
        specifies which item of the date must be retrieved: this means that the function does not always return a complete
        date but only the information required (e.g. day and month, day and month and year, weekday, etc.).
        If <askForConfirmation> is True, the parameter is returned only if the user confirms that it is correct,
        otherwise the interaction is repeated.
        Valid lists for <required> correspond to commonly used (specific or recurrent) dates (so, month and weekday only are
        not allowed because they don't correspond neither to a recurrent date nor to a specific date) and are:
        YEAR_MONTH_DAY_WEEKDAY: [1, 1, 1, 1]
        YEAR_MONTH_DAY: [1, 1, 1, 0]
        YEAR_MONTH: [1, 1, 0, 0]
        YEAR: [1, 0, 0, 0]
        MONTH_DAY: [0, 1, 1, 0]
        MONTH: [0, 1, 0, 0]
        DAY: [0, 0, 1, 0]
        WEEKDAY: [0, 0, 0, 1]
        @param required (list of bool) List of booleans which specify if a data element must be retrieved or not in this order YYYY, MM, DD, ww
        @param askForConfirmation (bool) A boolean to indicate whether the bot should ask the user if the date is correct
        @param timeRequired (bool) A boolean indicating whether the time should be retrieved too or not (default = False)
        @param noisy (str) Environment noise level: either "normal" or "noisy".
        @return (str, timedateparser.Date, str, datetime.time) A tuple containing the date as a human-like expression, the date as timedateparser.Date object, the time
        as a human-like expression (if required), the time as datetime.time object (if required)
        '''

        allowed_requests = [[1, 1, 1, 1], [1, 1, 1, 0], [1, 1, 0, 0], [1, 0, 0, 0], [0, 1, 1, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
        assert required in allowed_requests, "Not allowed type of date as parameter. Check function documentation."

        correct_parameter = False

        while not correct_parameter:

            got_through_cm = False

            line = self.script[GETDATE][ASK_PARAMETERS]["0"][self._lang].encode('utf-8')

            user_input = self.performInteraction(line, TAGS[5], noisy=noisy)

            # # Check if the user asked to explicitly show the possible options
            if user_input is not None:
                show_options = self.script[KEYWORDS][OPTIONS][self._lang] in user_input.lower()

            if user_input is None or show_options:
                self.say(line, TAGS[5])
                self._ab = getAutonomousAbilities(self.session)
                setAutonomousAbilities(self.session, False, True, False, False, False)
                self.session.service("ALRobotPosture").goToPosture("Stand", 0.5)
                dts = DateTimeSelector(self.session)
                user_input = dts.selectDate()
                setAutonomousAbilities(self.session, self._ab[0], self._ab[1], self._ab[2], self._ab[3], self._ab[4])

                if user_input is None:
                    self.stopInteraction()
                self.userSaid(user_input)
                got_through_cm = True

            tdp = TimeDateParser(self._lang)

            # # If it is required to look for a time indication, look immediately for it. If it is not found, the user will
            # # be asked for it later, after the date.

            str_time, time = None, None

            if timeRequired and not got_through_cm:
                time_list = tdp.getTime((user_input))

                if time_list is not None:
                    str_time = time_list[0][0]
                    time = time_list[0][1]
                    str_time = tdp.composeStringTime(str_time)

            # # Try to look for an entire date first, and try to guess the missing information.
            # # Try at least twice before asking specifically for the individual date elements.
            for attempt in range(2):
                try:
                    say = True
                    date = tdp.getDate((user_input))
                    guessed_date, guessed_weekday = tdp.guessFullDate(date)
                    date_list = date.toList()
                    if guessed_date is not None:
                        date_guess = [guessed_date.year, guessed_date.month, guessed_date.day, guessed_date.isoweekday()]
                except Exception as e:
                    print e
                    self.monolog(GETDATE, 0, tag=TAGS[1])
                    say = False
                    date_list = [None, None, None, None]
                    guessed_date, guessed_weekday = None, None

                if date_list == [None, None, None, None] and not attempt == 1:
                    self.monolog(GETDATE, 0, group=WRONG_PARAMETER, tag=TAGS[0])
                    line = self.script[GETDATE][ASK_PARAMETERS]["0"][self._lang].encode('utf-8')

                    user_input = self.performInteraction(line, TAGS[5],noisy=noisy)

                    if user_input is None:
                        self.say(line, TAGS[5])
                        dts = DateTimeSelector(self.session)
                        user_input = dts.selectDate()
                        if user_input is None:
                            self.stopInteraction()
                        self.userSaid(user_input)
                else:
                    break

            # # Go through the required date elements and if not already retrieved, keep asking the user for them.

            for index, r in enumerate(required):
                if r is True:
                    if date_list[index] is None:
                        if guessed_date is not None:
                            date_list[index] = date_guess[index]
                        else:
                            while date_list[index] is None:
                                try:
                                    sentence = str(randint(0, len(self.script[GETDATE][WRONG_PARAMETER]) - 1))
                                    if say:
                                        self.monolog(GETDATE, sentence, group=WRONG_PARAMETER, tag=TAGS[0])
                                    else:
                                        say = True

                                    # # Retrieve the specific missing element at index <index>
                                    uinput, date_list[index] = self.requireMissingDateElement(index + 1, noisy=noisy)

                                    # # Besides, try again to extract other date info from the user input
                                    date2 = tdp.getDate((uinput))
                                    date_list2 = date2.toList()

                                    for i, date_element in enumerate(date_list):
                                        if date_element is None:
                                            date_list[i] = date_list2[i]

                                    # # Guess the remaining missing information
                                    date = timedateparser.Date.asList(date_list)
                                    guessed_date, guessed_weekday = tdp.guessFullDate(date)

                                    if guessed_date is not None:
                                        date_guess = [guessed_date.year, guessed_date.month, guessed_date.day,
                                                      guessed_date.isoweekday()]
                                except (ValueError, AssertionError):
                                    self.monolog(GETDATE, 0, tag=TAGS[1])
                                    date_list[index] = None
                                    guessed_date, guessed_weekday = None, None

            date = timedateparser.Date.asList(date_list)
            string_date = tdp.composeStringDate(required, date)

            # # If the time is required and was not retrieved in the first user sentence, ask specifically for it.

            if timeRequired:
                if time is None:
                    str_time, time = self.dialogTime(askForConfirmation=False, togetherWithDate=True, noisy=noisy)
                param = "%s %s" % (string_date, str_time)
                param = {"$KEYWORD$": param}
                ret = string_date, date, str_time, time
            else:
                param = {"$KEYWORD$": string_date}
                ret =  string_date, date
            if askForConfirmation:
                correct_parameter = self.askIfCorrect(GETDATE, param["$KEYWORD$"], False, noisy=noisy)
            else:
                correct_parameter = True

        self.monolog(GETDATE, "0", param=param, group=PARAMETER_ANSWER, tag=TAGS[1])

        return ret

    def requireMissingDateElement(self, date_element, noisy="normal"):
        '''!
        Keep trying to retrieve a missing date element.
        @param date_element (int) An integer specifying the missing date element (year=1, month=2, day=3, weekday=4)
        @param noisy (str) Environment noise level: either "normal" or "noisy".
        @return (str, int) The user input and the missing data element
        '''

        x = None
        m = None
        tdp = TimeDateParser(self._lang)

        line = self.script[GETDATE][ASK_PARAMETERS][str(date_element)][self._lang].encode('utf-8')
        while x is None:

            user_input = self.performInteraction(line, TAGS[5], noisy=noisy)

            if user_input is None:
                self.say(line, TAGS[5])
                dts = DateTimeSelector(self.session)
                user_input = dts.selectDate()
                if user_input is None:
                    self.stopInteraction()
                self.userSaid(user_input)

            if date_element == 1:
                x = tdp.getYear((user_input), forceResearch=True)
            elif date_element == 2:
                x = tdp.getDate((user_input)).month #[1]
            elif date_element == 3:
                x = tdp.getDay((user_input), forceResearch=True)
            elif date_element == 4:
                x = tdp.getDate((user_input)).weekday #[3]
            elif date_element == "day-month":
                date2 = tdp.getDate((user_input))
                x = date2.day #[2]
                m = date2.month #[1]
            if x is None:
                self.monolog(GETDATE, str(0), group=WRONG_PARAMETER, tag=TAGS[0])

        return user_input, x


## Class for matching a user input to one among different candidates.
class MatchFinder():

    def __init__(self, language, extraStopWords=None):
        '''!
        The constructor
        @param language (str) The language used in the sentences
        @param lang (list of str) Additional words that should be removed because not relevant for classification
        '''

        self.language = language
        self._weight = 'u'

        if extraStopWords is not None:
            assert type(extraStopWords) == list
            self.extra_stopwords = extraStopWords
        else:
            self.extra_stopwords = []

    def setWeight(self, _weight):
        '''!
        Set which part of the candidate sentence should be given more weight to find the match with the user input.
        @param _weight (str) A letter indicating which part of the sentence is more relevant to find the match (left 'l',
        center 'c', right 'r', uniform 'u').
        '''
        assert _weight in ['l', 'r', 'c', 'u'], "Weight should be one among: 'l', 'r', 'c', 'u'." # left, right, center, uniform
        self._weight = _weight

    def getWeight(self):
        '''!
        Get the current weight.
        @return (str) The current weight
        '''
        return self._weight

    def extractKewyordsFrom(self, sentence, language):
        '''!
        Filter a sentence by removing any 'useless' common word (stopword) according to the nltk library and any additional
        stopword set in the constructor.
        @param sentence (str) Sentence to be filtered
        @param language (str) Language of the sentence and the stopwords
        @return (list of str) The filtered sentence as an array of the only meaningful words
        '''
        try:
            stopWords = set(stopwords.words(language))
        except:
            stopWords = [""]
        ps = PorterStemmer()
        words = word_tokenize(sentence)
        wordsFiltered = []

        for w in words:
            w = w.lower()
            if w not in stopWords and w not in self.extra_stopwords:
                wordsFiltered.append(ps.stem(w).encode('utf-8'))

        return wordsFiltered

    def findClosestMatch(self, input, candidates):
        '''!
        Find the closest match to a given string input among a set of possible candidates.
        @param input (str) The input that should be classified
        @param candidates (list of str) The set of sentences that could match the input
        @return (list of list) An array of arrays, each of which contains the candidate and its match score, ordered from the candidate
        with the highest score to the one with the lowest
        '''

        input_keywords = self.extractKewyordsFrom(input, self.language)
        ordered_candidates = []

        for c in candidates:
            counter = 0
            c_keywords = self.extractKewyordsFrom(c, self.language)
            length = len(c_keywords)
            scores = []

            for index, ck in enumerate(c_keywords):
                if self._weight == 'r':
                    scores.append(float(index + 1))
                elif self._weight == 'l':
                    scores.append(float(length - index))
                elif self._weight == 'c':
                    if index + 1 <= (length / 2):
                        scores.append(float(index + 1))
                    elif index + 1 == round(length / 2):
                        scores.append(float(index + 1))
                    else:
                        scores.append(float((length % (index + 1)) + 1))
                elif self._weight == 'u':
                    scores.append(1.0)

            for index, ck in enumerate(c_keywords):
                if ck in input_keywords:
                    counter += scores[index] / sum(scores)

            ordered_candidates.append([c, counter])

        ordered_candidates.sort(key=lambda x: x[1])
        ordered_candidates.reverse()

        return ordered_candidates


if __name__ == '__main__':

    #===================================================================================================================
    # EXAMPLE OF USAGE
    #===================================================================================================================

    # # Set the language and the topic for the dialog

    lang = "english"
    topic  = "SetReminder"

    # # Set the available options for the parameter that must be retrieved in the dialog (in CARESSES actions, the
    # # options are among the cultural parameters of the action class)

    if lang == "english":
        if topic == "SetReminder":
            options = ["watch Pokémon on TV", "go to the doctor's", "buy some food", "take the medicine", "go to the hairdresser's", "feed the cat", "go to the temple"]
    elif lang == "italian":
        if topic == "SetReminder":
            options = ["prendere le medicine", "andare dal dottore", "dar da mangiare al gatto"]

    options = [unicode(o, "utf-8") for o in options]

    # # Create an instance of the Speech class (from speech import Speech), passing to its constructor the configuration
    # # file (for CARESSES we will use the same "speech_conf.json" for all dialogs) and the language

    speech = Speech("speech_conf.json", lang)
    speech.setMatchFinderWeight('r')

    # # The dialog can be tested either by chatting with the computer through the keyboard or by talking to Pepper

    # # If talking to Pepper, rememeber to start the ASR based on Google developed by SBRE!!!

    # # If talking to Pepper, start a qi session (uncomment the block below)

    # -------------------------------------------------------------------------------------------------------------------
    # import qi, sys
    # 
    # ip = "130.251.13.160"
    # try:
    #     # # Initialize qi framework.
    #     session = qi.Session()
    #     session.connect("tcp://" + ip + ":" + str(9559))
    #     print("\nConnected to Naoqi at ip \"" + ip + "\" on port " + str(9559) + ".\n")
    # 
    #     sMotion = session.service("ALMotion")
    #     # # If "sleeping", wake up Pepper
    #     if not sMotion.robotIsWakeUp():
    #         sMotion.wakeUp()
    # 
    # except RuntimeError:
    #     print ("Can't connect to Naoqi at ip \"" + ip + "\" on port " + str(9559) + ".\n"
    #                                                                                  "Please check your script arguments. Run with -h option for help.")
    #     sys.exit(1)

    # # -------------------------------------------------------------------------------------------------------------------
    #
    # If talking to Pepper, call the following method and, optionally, set voice, speed, pitch
    #
    # speech.enablePepperInteraction(session, ip)
    #
    # import caressestools
    # caressestools.setVoiceSpeed(session, 90)

    # # Call inside a 'try' statement the method dialog() of the class Speech. This method takes as arguments: the topic
    # # of the dialog, the available options, the boolean <checkValidity> to specify whether the parameter to retrieve
    # # through the dialog MUST be one among <options> (True) or can be anything (False), the boolean <askForConfirmation>
    # # to specify whether the robot should ask to the user if the retrieved parameter is correct or not, the boolean
    # # <useChoiceManagerFromStart> to specify wether the ChoiceManager should be launched immediately. The StopInteraction
    # # exception is raised if the user stops the conversation (through the keyword expressed in the configuration file,
    # # currently it is "stop"), before telling the necessary parameter. Check the method documentation to know more.

    try:
        parameter = speech.dialog(topic, options, checkValidity=False, askForConfirmation=True, useChoiceManagerFromStart=False)
        print ("====================================")
        print ("The parameter is: %s" % parameter)

        # # To retrieve a time expression from a dialog, call the method dialogTime().
        # # To retrieve a date expression from a dialog, call dialogDateTime(), by passing as first argument a list of
        # # booleans that indicate which elements of the date are required [year, month, day, weekday]. Only meaningful
        # # combinations of these values are allowed, look at the method documentation.
        # # If you want to retrieve date and time at the same time, call dialogDateTime() by setting the argument
        # # <timeRequired> to True. The argument <askForConfirmation> works as for the above method dialog().

        # parameters = speech.dialogTime(askForConfirmation=True)
        # parameters = speech.dialogDateTime([True, True, True, True], askForConfirmation=True, timeRequired=True)
        #
        # print ("====================================")
        # print ("The parameters are:")
        # for p in parameters:
        #     print p

        deinit()
    except StopInteraction as e:
        print e

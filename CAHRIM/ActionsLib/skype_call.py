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

# README
# As a first thing, install the Android official Skype app on Pepper's tablet, but instead of downloading the latest version
# from the Google Play Store, look on the web for version 7.4.
# Once it is installed, login with a Skype account, you can use your own or create one on purpose.
# Add the desired contacts in /parameters/contacts.json file at the "skype" voice.

import time
import functools
import os
import platform
import webbrowser

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech

## Action "Skype Call".
#
#  Pepper makes a Skype call through the tablet between the user and a person in the contact list.
#  This action requires the installation of the NAOqi app CustomNumber.
class SkypeCall(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Contact ID
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.recipient_id = self.apar[0]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        self.recipient_params = self.loadParameters("contacts.json")
        suggested_recipients_IDs = [option.replace('"', '') for option in self.suggestions]
        self.recipient_IDs = self.mergeAndSortIDs(self.recipient_params, suggested_recipients_IDs)
        self.recipient_options = []
        ## Get only the recipients whose Skype ID or phone number is present
        for id in self.recipient_IDs:
            if not (self.recipient_params["IDs"][id]["skype"].encode('utf-8') == "" and self.recipient_params["IDs"][id]["phone"].encode('utf-8') == ""):
                self.recipient_options.append(self.recipient_params["IDs"][id]["full"].encode('utf-8'))

        self.modes_params = self.loadParameters("call_modes.json")
        self.modes_IDs = self.modes_params["IDs"].keys()
        self.modes_options = self.getAllParametersAttributes(self.modes_params, self.modes_IDs, "full")

        # Initialize NAOqi services
        self.sTablet = self.session.service("ALTabletService")
        self.sMemory = self.session.service("ALMemory")
        self.sSpeechReco = self.session.service("ALSpeechRecognition")

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

        self.is_touched = False
        self.topic_recipient = self.__class__.__name__ + "-Recipient"
        self.topic_mode = self.__class__.__name__ + "-Mode"

        self.exit_keyword = self.sp.script[speech.KEYWORDS][speech.STOP_CALL][self.language]

        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        self.exclude = self.getAttributeFromID(self.recipient_params, "customPerson", "full")

        if not self.isAvailable(self.recipient_id):
            self.recipient_full = self.sp.dialog(self.topic_recipient, self.recipient_options, checkValidity=True, askForConfirmation=True, excludeSomeSuggestions=self.exclude, noisy=self.asr)
            self.recipient_id = self.getIDFromAttribute(self.recipient_params, "full", self.recipient_full)
        else:
            if "custom" in self.recipient_id:
                self.sp.monolog(self.topic_recipient, "with-keyword-custom", group="parameter-answer", tag=speech.TAGS[1])
            else:
                self.recipient_full = self.getAttributeFromID(self.recipient_params, self.recipient_id, "full")
                self.sp.monolog(self.topic_recipient, "with-keyword", param={"$KEYWORD$" : self.recipient_full}, group="parameter-answer", tag=speech.TAGS[1])

        use_skype, use_phone, must_choose = False, False, True

        skype_id = self.getAttributeFromID(self.recipient_params, self.recipient_id, "skype")
        phone_number = self.getAttributeFromID(self.recipient_params, self.recipient_id, "phone")

        use_skype = True if not skype_id == "" else False
        use_phone = True if not phone_number == "" else False
        must_choose = use_skype and use_phone
        no_info = not(use_skype or use_phone)

        if must_choose:
            call_mode = self.sp.dialog(self.topic_mode, self.modes_options, checkValidity=True, askForConfirmation=False, removeDiscardedOption=False, noisy=self.asr)
            if call_mode == self.getAttributeFromID(self.modes_params, "phoneMode", "full"):
                use_skype = False
            elif call_mode == self.getAttributeFromID(self.modes_params, "skypeMode", "full"):
                use_phone = False

        if no_info:
            question = self.sp.script[self.topic_recipient][speech.OTHER]["3"][self.language].encode('utf-8').replace("$RECIPIENT$", self.recipient_full, noisy=self.asr)
            want_to_dial = self.sp.askYesOrNoQuestion(question, speech.TAGS[4], noisy=self.asr)
            if want_to_dial:
                use_phone = True
                self.recipient_id = "custom"
                phone_number = self.getAttributeFromID(self.recipient_params, self.recipient_id, "phone")
            else:
                self.sp.stopInteraction()

        self.sp.monolog(self.topic_recipient, "1", tag=speech.TAGS[1])

        if use_skype:
            self.sTablet.showWebview("http://198.18.0.1/apps/boot-config/preloading_dialog.html")
            time.sleep(1)
            self.sp.monolog(self.topic_recipient, "5", tag=speech.TAGS[1])
            self.sTablet.executeJS("""window.open("skype:%s?call&amp;video=true");""" % skype_id)
        elif use_phone:
            if "custom" in self.recipient_id:
                self.sp.monolog(self.topic_recipient, "2", tag=speech.TAGS[1])
                acq = self.sp.customNumber()
                if acq is not None:
                    phone_number = phone_number[:-3] + acq
                else:
                    line = self.sp.script[speech.STOP_INTERACTION][self.language].encode('utf-8')
                    self.sp.say(line, speech.TAGS[1])
                    self.end()
                    return
            self.sTablet._launchApk("com.skype.raider")
            webbrowser.open('skype:live:laboratorium.dibris;%s' % phone_number)

            self.sp.monolog(self.topic_recipient, "0", tag=speech.TAGS[1])

        else:
            raise Exception, "No Skype id nor phone number provided."

        self.sp.monolog(self.topic_recipient, "6", tag=speech.TAGS[1])

        touch = self.sMemory.subscriber("TouchChanged")
        id_touch = touch.signal.connect(functools.partial(self.onTouched, "TouchChanged"))

        self.subscribeToKeywords()

        self.user_input = ""
        self.detected_something = False

        while not self.is_touched and not self.is_stopped:

            if self.detected_something:
                self.sp.userSaid(self.user_input)
                question = self.sp.script[self.topic_recipient][speech.OTHER]["4"][self.language].encode('utf-8')
                self.sSpeechReco.unsubscribe("CARESSES/word-detected")
                hang_up = self.sp.askYesOrNoQuestion(question, speech.TAGS[4], noisy=self.asr)
                if hang_up:
                    line = self.sp.script[speech.STOP_INTERACTION][self.language].encode('utf-8')
                    self.sp.say(line, speech.TAGS[1])
                    self.is_stopped = True
                else:
                    self.detected_something = False
                    self.subscribeToKeywords()

        self.sTablet._stopApk("com.skype.raider")
        self.sTablet.showWebview("http://198.18.0.1/apps/boot-config/preloading_dialog.html")

        ## Kill Skype on the computer
        if platform.system() == "Windows":
            os.system("taskkill /f /im SkypeApp.exe")
        elif platform.system() == "Linux":
            os.system("killall -9 skypeforlinux")

        if not self.is_stopped:
            self.sp.askYesOrNoQuestion(
                self.sp.script[self.topic_recipient]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
            self.sp.monolog(self.topic_recipient, "1", group="evaluation", tag=speech.TAGS[1])
        self.end()

    ## Method containing all the instructions that should be executing before terminating the action.
    def end(self):
        pass

    ## Callback
    def onTouched(self, msg, value):
        self.is_touched = True

    ## Subscribe to keyword detection event.
    def subscribeToKeywords(self):
        ## Subscribe here to touch and word recognition
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
        vocabulary = [w.encode('utf-8') for w in self.sp.script[self.topic_recipient][speech.USER]["0"][self.language]]
        self.sSpeechReco.setVocabulary(vocabulary, False)
        self.sSpeechReco.pause(False)

    ## Callback
    def onSpeechRecognized(self, msg, value):
        if value[1] >= 0.5:
            self.detected_something = True
            self.user_input = value[0]


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
    apar = '"n/a"'
    cpar = "1.0 100 1.1 english John customPerson"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = SkypeCall(apar, cpar, session, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

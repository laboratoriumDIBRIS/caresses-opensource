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

# README
# You need to put the recipients' Line IDs inside ./parameters/contacts.json
# To get Receiver Line ID :
#  - Receiver adds the CARESSES bot on Line app (by searching on the app or by scanning QR Code : https://qr-official.line.me/M/GQJJzejk_8.png)
#  - Receiver sends a text message to CARESSES bot, the bot will send back the receiver's line id


import requests
import threading

import caressestools.caressestools as caressestools
import caressestools.speech as speech
import caressestools.multipage_choice_manager as mcm


from action import Action

LINE_BOT_URL = '<LINE_BOT_SERVER>'


## Action "Send Line Message"
#
# Pepper sends a message through the Line app to a person in the contact list.
class SendLineMessage(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Message ID, contact ID; separated by a white space.
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.message_id = self.apar[0]
        self.recipient_id = self.apar[1]

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
        ## Get only the recipients whose Line ID is present
        for id in self.recipient_IDs:
            if not self.recipient_params["IDs"][id]["line"].encode('utf-8') == "":
                self.recipient_options.append(self.recipient_params["IDs"][id]["full"].encode('utf-8'))

        self.msg_params = self.loadParameters("messages.json")
        self.msg_IDs = self.msg_params["IDs"].keys()
        self.msg_options_caregiver = []
        self.msg_options_other = []

        for id in self.msg_IDs:
            if self.msg_params["IDs"][id]["compulsory-recipient"].encode('utf-8') == "caregiver":
                self.msg_options_caregiver.append(self.msg_params["IDs"][id]["full"].encode('utf-8'))
            else:
                self.msg_options_other.append(self.msg_params["IDs"][id]["full"].encode('utf-8'))

        # Initialize NAOqi services
        self.sASR = self.session.service("ASR2")

        # Set the cultural parameters
        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(session, self.volume)
        caressestools.setVoiceSpeed(session, self.speed)
        caressestools.setVoicePitch(session, self.pitch)

        # Set up speech.py app to get information
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(session, caressestools.Settings.robotIP.encode('utf-8'))

        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        if len(self.recipient_options) == 0:
            self.sp.monolog(self.__class__.__name__, "4", tag=speech.TAGS[1])
            return

        if not self.isAvailable(self.recipient_id):
            self.recipient_full = self.sp.dialog(self.__class__.__name__, self.recipient_options, checkValidity=True, askForConfirmation=True, useChoiceManagerFromStart=True, noisy=self.asr)
            self.recipient_id = self.getIDFromAttribute(self.recipient_params, "full", self.recipient_full)
        else:
            self.recipient_full = self.getAttributeFromID(self.recipient_params, self.recipient_id, "full")
            self.sp.monolog(self.__class__.__name__, "with-keyword", param={"$KEYWORD$" : self.recipient_full}, group="parameter-answer", tag=speech.TAGS[1])

        if self.recipient_id == "caregiver":
            self.msg_options = self.msg_options_caregiver
        else:
            self.msg_options = self.msg_options_other

        self.mcm = mcm.MultiPageChoiceManager(caressestools.Settings.robotIP.encode('utf-8'))

        if not self.isAvailable(self.message_id):
            self.sp.monolog(self.__class__.__name__, "0", tag=speech.TAGS[1])

            if self.sp._input==2:
                self.sp.gothread = True
                thr = threading.Thread(name="getinput", target=self.sp.getOptionsFromSmartphone, args=[self.msg_options])
                thr.start()
            self.message_full = self.mcm.giveChoiceMultiPage("", self.msg_options)
            self.sp.gothread=False
            
            self.message_full = [unicode(self.message_full[0], "utf-8"), self.message_full[1]]
            self.mcm.kill()
            self.sp.checkIfKilledDuringMcm(self.mcm, self.message_full)

            self.message_id = self.getIDFromAttribute(self.msg_params, "full", self.message_full[0])

        self.recipient_line = self.getAttributeFromID(self.recipient_params, self.recipient_id, "line")
        self.message = self.getAttributeFromID(self.msg_params, self.message_id, "message")

        if self.message_id == "customMessage":
            correct = False
            content = ""
            while not correct:
                self.sASR.startReco(caressestools.Language.lang_naoqi, False, True)
                self.sp.monolog(self.__class__.__name__, "3", tag=speech.TAGS[5])
                content = self.sp.getInput()
                self.sp.userSaid(content)
                self.sASR.stopReco()
                question = self.sp.script[self.__class__.__name__]["ask-confirmation"]["without-keyword"][self.language].replace("$CONFIRM$", content)
                correct = self.sp.askYesOrNoQuestion(question, speech.TAGS[2], noisy=self.asr)
            self.message = self.message.replace("$CONTENT$", content)

        self.sp.replyAffirmative()
        result = self.sendMessage(self.recipient_line, self.message.replace("$USERNAME$", self.username))

        if result == 'OK':
            self.sp.monolog(self.__class__.__name__, "1", param={"$RECIPIENT$" : self.recipient_full}, tag=speech.TAGS[1])

            self.sp.askYesOrNoQuestion(
                self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
            self.sp.monolog(self.__class__.__name__, "1", group="evaluation", tag=speech.TAGS[1])

        else:
            self.sp.monolog(self.__class__.__name__, "2", tag=speech.TAGS[1])

    ## Send the message through the Line bot.
    #  @param receiver_id ID of the contact to whom the message should be sent.
    #  @param message Message content.
    def sendMessage(self, receiver_id, message):
        payload = {'user_id': receiver_id, 'message':message}
        r = requests.post(LINE_BOT_URL, data=payload)
        return r.text


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
    apar = '"n/a" "n/a"'
    cpar = "1.0 100 1.1 english John medicalStaff&&friend"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = SendLineMessage(apar, cpar, session, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

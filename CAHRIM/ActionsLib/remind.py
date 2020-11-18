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
import json
import re

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Remind".
#
#  Pepper reminds the user about something previously specified through the SetReminder action.
class Remind(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Reminder
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    def __init__(self, apar, cpar, session):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.reminder_id = self.apar[0]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        self.reminder_params = self.loadParameters("reminders.json")

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language, loadconf=False)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'), initGoogle=False)

        ## ------------------------------------------------
        ## If Remind action is executed while the ChoiceManager in another action is running, the action running the
        ## ChoiceManager crashes if the function json.load()/json.loads() is called on a very long file/string. Therefore,
        ## here we need to call json.loads() only on the relevant (shorter) part of speech_conf.json.

        conf_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'caressestools', "speech_conf.json")
        with open(conf_file, 'r') as f:
            conf = f.readlines()

        conf_string = ""
        for line in conf:
            conf_string = conf_string + line

        top = re.search(r'\"' + speech.SUPPORTED_LANGUAGES + '\": \[\n(( {4,}.*\n)*) {2}\](,\n {2}\"[A-Z]+-*[A-Z]+\": \{\n(( {4,}.*\n)*) {2}\})+', conf_string)
        rem = re.search(r'\"' + self.__class__.__name__ + '\": \{\n(( {4,}.*\n)*) {2}\}', conf_string)

        if top is not None and rem is not None:
            conf = json.loads("{%s,%s}" % (top.group(), rem.group()))

        self.sp.loadScriptFromDict(conf)
        self.sp.setLanguage(self.language.lower())
        self.sp.loadKeywords()

        ## ------------------------------------------------

        self.gen_rem_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'parameters',
                                             'reminder_generic.json')

    ## Method executed when the thread is started.
    def run(self):
        index = "0" if not self.reminder_id.startswith("GENERIC_") else "1"

        if self.reminder_id.startswith("GENERIC_"):
            with open(self.gen_rem_filename, "r") as f:
                content = json.load(f)
            self.reminder_full = content[self.reminder_id]["full"]
        else:
            self.reminder_full = self.getAttributeFromID(self.reminder_params, self.reminder_id, "full")

        parameters = {
            "$USERNAME$" : self.username,
            "$REMINDER$" : self.reminder_full
        }

        self.sp.monolog(self.__class__.__name__, index, param=parameters, tag=speech.TAGS[1])

        ## It is better not to ask the "evaluation question" in this action as if may activate the ASR2 simultaneously
        ## to some other action.
        # self.sp.askYesOrNoQuestion(
        #     self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'))
        # self.sp.say(self.sp.script[self.__class__.__name__]["evaluation"]["1"][self.language].encode('utf-8'))


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
    caressestools.startPepper(session, caressestools.Settings.interactionNode)

    apar = "receivingDoctorOrNurse"
    cpar = "1.0 100 1.1 english John"

    action = Remind(apar, cpar, session)
    action.run()

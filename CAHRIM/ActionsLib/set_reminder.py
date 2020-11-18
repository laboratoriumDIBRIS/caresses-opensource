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
import datetime
from collections import OrderedDict

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Set Reminder"
#
#  Pepper sets a reminder for the user about something specified by them.
#  This action requires the installation of the NAOqi apps DateSelector, Time12Selector, Time24Selector.
class SetReminder(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Reminder ID.
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param output_handler () Handler of the output socket messages.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, output_handler, asr):
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
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        self.reminder_params = self.loadParameters("reminders.json")
        suggested_reminders_IDs = [option.replace('"', '') for option in self.suggestions]
        self.reminder_IDs = self.mergeAndSortIDs(self.reminder_params, suggested_reminders_IDs)
        self.reminder_options = self.getAllParametersAttributes(self.reminder_params, self.reminder_IDs, "full")

        # Output handler for sending messages
        self.output_handler = output_handler

        self.msg_content = "[(:complex-goal-instance (reminder %s (datetime (y %s) (M %s) (d %s) (h %s) (m %s)) {?Choice}))]"

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))
        self.sp.setMatchFinderWeight('r')


        self.gen_rem_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'parameters',
                                             'reminder_generic.json')
        self.max_slots = 9

        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        custom_option = self.sp.script[self.__class__.__name__]["custom-option"][self.language].encode('utf-8')
        self.reminder_options.append(custom_option)

        if not self.isAvailable(self.reminder_id):
            self.reminder_full = custom_option
            try:
                self.reminder_full_unicode=unicode(self.reminder_full,"utf-8")
            except:
                self.reminder_full_unicode=self.reminder_full
            while self.reminder_full_unicode == unicode(custom_option,"utf-8"):
                self.reminder_full = self.sp.dialog(self.__class__.__name__, self.reminder_options, checkValidity=False, askForConfirmation=True, noisy=self.asr)
                try:
                    self.reminder_full_unicode=unicode(self.reminder_full,"utf-8")
                except:
                    self.reminder_full_unicode=self.reminder_full

        else:
            self.reminder_full = self.getAttributeFromID(self.reminder_params, self.reminder_id, "full")
            self.sp.monolog(self.__class__.__name__, "with-keyword", param={"$KEYWORD$" : self.reminder_full}, group="parameter-answer", tag=speech.TAGS[1])

        self.sp.monolog(self.__class__.__name__, "1", tag=speech.TAGS[1])

        date_time = self.sp.dialogDateTime([True, True, True, True], askForConfirmation=True, timeRequired=True, noisy=self.asr)
        date = date_time[1]
        time = date_time[3]

        date_is_passed = self.isDatePassed(date, time)

        while date_is_passed:
            self.sp.monolog(self.__class__.__name__, "0", tag=speech.TAGS[1])
            date_time = self.sp.dialogDateTime([True, True, True, True], askForConfirmation=True, timeRequired=True, noisy=self.asr)
            date = date_time[1]
            time = date_time[3]

            date_is_passed = self.isDatePassed(date, time)

        msg = self.composeD5_1message(self.reminder_full, date, time)
        self.logger.info("Message for the planner - %s" % msg)
        if self.output_handler is not None:
            self.output_handler.writeSupplyMessage("publish", "D5.1", msg)

        self.sp.setMatchFinderWeight('u')

    ## Check whether the given date and time have already passed or not.
    #  @param date Date
    #  @param time Time
    def isDatePassed(self, date, time):

        reminder_time = datetime.datetime(date.year, date.month, date.day, time.hour, time.minute, time.second)
        now = datetime.datetime.now()
        interval = reminder_time - now
        interval_minutes = int(divmod(interval.total_seconds(), 60)[0])

        return interval_minutes <= 0

    ## Generate the message to send to CSPEM with the goal fdr the Remind action.
    #  @param parameter Content of the reminder
    #  @param date Date
    #  @param time Time
    def composeD5_1message(self, parameter, date, time):

        self.reminder_id = self.getIDFromAttribute(self.reminder_params, "full", parameter)
        if self.reminder_id is None:
            param = self.storeGenericReminder(parameter)
        else:
            param = self.reminder_id

        msg = self.msg_content % (param, str(date.year), str(date.month), str(date.day), str(time.hour), str(time.minute))

        return msg

    ## Save generic reminder in the file parameters/reminder_generic.json.
    def storeGenericReminder(self, reminder):

        index = self.getAvailableIndex()

        with open(self.gen_rem_filename, "r") as f:
            content = json.load(f)

        content[index]["full"] = reminder

        with open(self.gen_rem_filename, "w") as f:
            json.dump(content, f)

        self.freeNextSlot(index)

        return index

    ## Get the index at which to store the generic reminder.
    def getAvailableIndex(self):

        with open(self.gen_rem_filename, "r") as f:
            content = json.load(f)

        content = OrderedDict(sorted(content.items(), key=lambda t: t[0]))

        key = None

        for key in content.keys():
            key = key.encode('utf-8')
            if content[key]["full"] == "":
                break

        return key

    ## Empty the field following the one just used inside the file parameters/reminder_generic.json.
    def freeNextSlot(self, key):

        current_index = int(key.encode('utf-8').split('_')[1])

        if current_index == self.max_slots:
            next_index = 0
        else:
            next_index = current_index + 1

        next_key = "GENERIC_%d" % next_index

        with open(self.gen_rem_filename, "r") as f:
            content = json.load(f)

        content[next_key]["full"] = ""

        with open(self.gen_rem_filename, "w") as f:
            json.dump(content, f)


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

    apar = '"n/a"'
    cpar = "1.0 100 1.1 japanese John walkingInTheGarden&&takingAMedicine"

    action = SetReminder(apar, cpar, session, None, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

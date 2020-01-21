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
# In order to get the apk to control IoT devices, follow the documentation at:
# http://protolab.aldebaran.com/caresses_downloads/doc_bifrost.html
# Ask SoftBank to obtain credentials to enter the page.
# Once the devices are configured, change their names through the official WeMo Android app to "<deviceName>_<room>":
# e.g. "lamp_bedroom".


from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Operate IoT".
#
#  Pepper operates a WeMo smart device in the environment through the Bifrost app.
class OperateIoT(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Device, room, operation; separated by a white space.
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.item_id = self.apar[0]
        self.room = self.apar[1]
        self.operation = self.apar[2]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        self.items_params = self.loadParameters("iot_items.json")
        suggested_items_IDs = [option.replace('"', '') for option in self.suggestions]
        self.items_IDs = self.mergeAndSortIDs(self.items_params, suggested_items_IDs)
        self.items_options = self.getAllParametersAttributes(self.items_params, self.items_IDs, "full")

        # Initialize NAOqi services
        self.sTablet = self.session.service("ALTabletService")
        self.sMemory = self.session.service("ALMemory")

        # Set the cultural parameters
        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(session, self.volume)
        caressestools.setVoiceSpeed(session, self.speed)
        caressestools.setVoicePitch(session, self.pitch)

        # Set up speech.py app to get information
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(session, caressestools.Settings.robotIP.encode('utf-8'))

        self.topic_item = self.__class__.__name__
        self.topic_room = "IoT-iHouse-Room"
        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        if not self.isAvailable(self.item_id):
            self.item_full = self.sp.dialog(self.topic_item, self.items_options, checkValidity=True,
                                            askForConfirmation=False, noisy=self.asr)
            self.item_id = self.getIDFromAttribute(self.items_params, "full", self.item_full)
        else:
            self.item_full = self.getAttributeFromID(self.items_params, self.item_id, "full")
            self.sp.monolog(self.topic_item, speech.WITH_KEYWORD, param={"$KEYWORD$": self.item_full},
                            group="parameter-answer", tag=speech.TAGS[1])

        if not self.isAvailable(self.room):
            room_options = [r.encode('utf-8') for r in self.items_params["IDs"][self.item_id]["locations"]]
            if len(room_options) == 1:
                self.room = room_options[0]
            else:
                self.room = self.sp.dialog(self.topic_room, room_options, checkValidity=True, askForConfirmation=False, noisy=self.asr)

        status = self.getDeviceStatus(self.item_id, self.room)
        status_str = self.items_params["IDs"][self.item_id]["status"][str(status)]

        if not self.isAvailable(self.operation):
            self.operation = str(int(not status))
            operation_str = self.items_params["IDs"][self.item_id]["operations"][self.operation]
            question = self.sp.script[self.topic_item]["other"]["0"][self.language].replace("$DEVICE$", self.item_full).replace("$STATUS$", status_str).replace("$ACTION$", operation_str).replace("$ROOM$", self.room)
            answer = self.sp.askYesOrNoQuestion(question, speech.TAGS[4], noisy=self.asr)
        else:
            if int(self.operation) == status:
                self.sp.monolog(self.topic_item, "1", param={"$DEVICE$": self.item_full, "$STATUS$": status_str}, tag=speech.TAGS[1])
                return
            else:
                operation_str = self.items_params["IDs"][self.item_id]["operations"][self.operation]
                question = self.sp.script[self.topic_item]["other"]["0"][self.language].replace("$DEVICE$",
                                                                                                self.item_full).replace(
                    "$STATUS$", status_str).replace("$ACTION$", operation_str).replace("$ROOM$", self.room)
                answer = self.sp.askYesOrNoQuestion(question, speech.TAGS[4], noisy=self.asr)

        if answer:
            self.setDeviceStatus(self.item_id, self.room, int(self.operation))
            self.sp.monolog(self.topic_item, "2", tag=speech.TAGS[1])

            self.sp.askYesOrNoQuestion(
                self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
            self.sp.monolog(self.__class__.__name__, "1", group="evaluation", tag=speech.TAGS[1])

        else:
            self.sp.replyAffirmative()

    ## Retrieve the status of the desired room's device as specified by the input parameters.
    #  @param device Device of which the status should be retrieved.
    #  @param room Room in which the device is located.
    def getDeviceStatus(self, device, room):
        located_device = "%s_%s" % (device, room)
        status = self.sMemory.getData("Bifrost/Devices/Switch/Status/%s" % located_device)
        return status

    ## Set the status of the desired room's device as specified by the input parameters.
    #  @param device Device of which the status should be altered.
    #  @param room Room in which the device is located.
    #  @param operation Operation to perform on the device.
    def setDeviceStatus(self, device, room, operation):
        located_device = "%s_%s" % (device, room)
        self.sMemory.raiseEvent("Bifrost/Devices/Switch/SetStatus/%s" % located_device, operation)


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
    apar = '"n/a" "n/a" "n/a"'
    cpar = "1.0 100 1.1 english John smartLamp"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = OperateIoT(apar, cpar, session, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

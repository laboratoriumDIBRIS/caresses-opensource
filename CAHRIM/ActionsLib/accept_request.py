# coding: utf8
'''
Copyright October 2019 Carmine Tommaso Recchiuto & Università degli Studi di Genova

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

Author:      Carmine Tommaso Recchiuto
Email:       carmine.recchiuto@dibris.unige.it
Affiliation: Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import qi
import argparse
import caressestools.caressestools as caressestools
from action import Action
from caressestools.input_request_parser import InputRequestParser
from command_manager import CommandManager

## Action "AcceptRequest".
#
#  Pepper suggests activities that can be performed with the user. AFter that, it waits for the user to propose something, or starts chit-chatting about general conversation topics.
class AcceptRequest(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param output_handler () Handler of the output socket messages.
    # @param cultural (string) Interaction's mode, either "experimental" or "control".
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, output_handler, cultural, asr):
        Action.__init__(self, apar, cpar, session)
        self.TAG = self.__class__.__name__

        self.commandManager = None

        self.session = session
        self.output_handler = output_handler  # Output handler for sending messages
        self.cultural = cultural
        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        qi.logDebug(self.TAG, "Create input request parsers")
        inputParser = InputRequestParser("ActionsLib/parameters/chitchat.json")

        qi.logDebug(self.TAG, "Create the command manager")
        self.commandManager = CommandManager(self.apar,
                                             self.cpar,
                                             self.session,
                                             self.output_handler,
                                             self.cultural,
                                             self.asr)

        qi.logDebug(self.TAG, "Parsing the JSON inputs")
        inputDict = inputParser.parseInputs("ActionsLib/parameters/chitchat.json")

        qi.logDebug(self.TAG, "Set the command formatter input dicts")
        self.commandManager.start(inputDict)

    ## Method containing all the instructions that should be executing before terminating the action.
    def stop(self):
        Action.stop(self)
        qi.logDebug(self.TAG, "Disconnecting speech signals")
        self.commandManager.stop()

        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default=caressestools.Settings.robotIP,
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")
    args = parser.parse_args()
    session = qi.Session()
    session.connect("tcp://" + args.ip + ":" + str(args.port))
    print 'Connected to Pepper'
    caressestools.Settings.robotIP = args.ip
    apar = ""
    cpar = "1.0 100 1.0 English Sonali 20 prayingGoal&&showVideoInstructionsGoal_boiledFish&&setReminderGoal_takingMedicine&&audioVideoCallGoal_grandChild"
    action = AcceptRequest(apar, cpar, session, None)  # CURRENTLY CANNOT BE EXECUTED STANDALONE SINCE the output_handler IS REQUIRED AS PARAMETER
    action.run()
    

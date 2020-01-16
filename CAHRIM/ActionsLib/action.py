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

import json
import os
import logging

import caressestools.caressestools as caressestools
import caressestools.speech as speech
from caressestools.speech import CAHRIM_KILL_ACTION


## Default %Action
#
#  Father class of every other action. It is executed only if CAHRIM receives from CSPEM an action which does not exist.
class Action:

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) %Action parameters separated by a white space.
    # @param cpar (string) Cultural parameters separated by a white space.
    # @param session (qi session) NAOqi session.
    def __init__(self, apar, cpar, session):
        self.apar = apar
        self.cpar = cpar
        self.session = session
        name = 'CAHRIM.Executor.' + self.__class__.__name__
        self.logger = logging.getLogger(name)
        self.options_delimiter = "&&"
        self.is_stopped = False
        self.volume_video_increase = 35

    ## Method executed when the thread is started.
    def run(self):
        self.sp = speech.Speech("speech_conf.json", "english")
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))
        self.sp.say("I'm sorry, this action is not ready yet.")

    ## This method is called externally in the Actuation Hub thread to safely kill the action (and should not be called
    #  inside the action).
    #  Any action using a long while or for loop, should make the loop dependent on the variable self.is_stopped.
    #  All the clean-up calls should be done right outside the loop so that they are called either if the action is
    #  forced to stop or if the action is simply over.
    def stop(self):
        self.is_stopped = True
        sMemory = self.session.service("ALMemory")
        sBehavior = self.session.service("ALBehaviorManager")
        sTablet = self.session.service("ALTabletService")

        try:
            sAsr = self.session.service("ASR2")
            sAsr.stopReco()
        except:
            pass

        if sBehavior.isBehaviorRunning("choice-manager/question"):
            sMemory.insertData("WordRecognized", ["<...> EXIT <...>", 1])
        if sBehavior.isBehaviorRunning("caresses_game_memory/behavior_1"):
            sBehavior.stopBehavior("caresses_game_memory/behavior_1")
        sMemory.raiseEvent('CARESSES/DateTimeSelector/exit', True)
        sMemory.insertData(CAHRIM_KILL_ACTION, True)

    ## Load the parameters which can be used by the action from the corresponding parameters file.
    #  @param param_file Name of the parameters file (without path).
    def loadParameters(self, param_file):
        filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'parameters', param_file)
        if os.path.isfile(filename):
            with open(filename, "r") as f:
                content = json.load(f)
            return content
        else:
            return None

    ## Order the parameters by putting the suggestions coming from the CKB in first place.
    #  @param parameters Content of the parameters file.
    #  @param suggestions Array of parameters which have higher likeliness in the CKB.
    def mergeAndSortIDs(self, parameters, suggestions):
        if parameters is not None:
            all_options = [p.encode('utf-8') for p in parameters["IDs"] if not p == "GENERIC"]
            for a in all_options:
                if a not in suggestions:
                    suggestions.append(a)
        return suggestions

    ## Retrieve the values of all the given parameters for the specified key.
    #  @param parameters Content of the parameters file.
    #  @param ordered_IDs Array containing the parameters' IDs already ordered with the suggestions in first place.
    #  @param attribute Key of which the value should be retrieved.
    def getAllParametersAttributes(self, parameters, ordered_IDs, attribute):
        attributes = []
        for id in ordered_IDs:
            attributes.append(parameters["IDs"][id][attribute].encode('utf-8'))
        return attributes

    ## Retrieve the value of the given parameter for the specified key.
    #  @param parameters Content of the parameters file.
    #  @param id ID of the parameter of which the attribute should be retrieved.
    #  @param attributeField Key of which the value should be retrieved.
    def getAttributeFromID(self, parameters, id, attributeField):
        attribute = parameters["IDs"][id][attributeField].encode('utf-8')
        return unicode(attribute, 'utf-8')

    ## Retrieve the ID of the given parameter through the specified key-value pair.
    #  @param parameters Content of the parameters file.
    #  @param attributeField Key of which the value is known.
    #  @param attributeValue Value of the key.
    def getIDFromAttribute(self, parameters, attributeField, attributeValue):
        for p in parameters["IDs"]:
            if parameters["IDs"][p][attributeField] == attributeValue:
                return p

        return None

    ## Set the value of the given parameter for the specified key.
    #  @param parameters Content of the parameters file.
    #  @param id ID of the parameter of which the attribute should be set.
    #  @param attributeField Key of which the value should be set.
    #  @param attributeValue New value for the attribute.
    def setAttribute(self, param_file, id, attributeField, attributeValue):

        parameters = self.loadParameters(param_file)

        parameters["IDs"][id][attributeField] = attributeValue
        filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'parameters', param_file )

        if os.path.isfile(filename):
            with open(filename, "w") as f:
                json.dump(parameters, f)

    ## Return whether or not the action parameter received as 'apar' of the constructor is specified through its ID or
    #  not ("n/a").
    #  @param parameter One of the 'apar' of which the value should be checked.
    def isAvailable(self, parameter):

        return not parameter == '"n/a"'

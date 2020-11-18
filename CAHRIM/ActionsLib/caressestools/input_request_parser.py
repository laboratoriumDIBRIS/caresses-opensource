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
import json
from collections import OrderedDict


## Class "InputRequestParser".
#
#  Class used to format the input data.
class InputRequestParser:

    ## The constructor.
    # @param action (string) Input file
    def __init__(self,action):

        self.TAG = self.__class__.__name__

        try:
            assert action is not None
            self.act  = action

        except AssertionError:
            self.act = 1

    ## Parses the input json file
    # @param jsonFilePath (string) Path to the JSON file
    # @return refinedInputs (dict) The refined input parsed from the json file
    def parseInputs(self, jsonFilePath):

        with open(jsonFilePath, "r") as jsonFile:
            inputs = json.load(jsonFile, object_pairs_hook=OrderedDict)

        refinedInputs = dict()

        for key, value in inputs.items():
            refinedInputs[key] = dict()

            for subkey, subvalue in value.items():
                if isinstance(subvalue, list):
                    refinedInputs[key][subkey] = [element for element in subvalue]

                else:
                    refinedInputs[key][subkey] = subvalue

        # qi.logInfo(self.TAG, "Loaded input dict :\n" + str(refinedInputs))
        return refinedInputs

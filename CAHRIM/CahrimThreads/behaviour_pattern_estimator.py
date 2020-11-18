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

from threading import Thread
import time
import logging

log_bpe = logging.getLogger('CAHRIM.BehaviourPatternEstimator')

class BehaviourPatternEstimator(Thread):

    def __init__(self, output_handler):
        Thread.__init__(self)
        self.id = "Behaviour Pattern Estimator"
        self.alive = True
        self.output_handler = output_handler # Output handler for sending messages

    def run(self):

        while self.alive:
            pass
            # self.output_handler.writeSupplyMessage("publish", "D8.1", new_msg)

        log_bpe.info("%s terminated correctly." % self.id)

    def stop(self):
        self.alive = False
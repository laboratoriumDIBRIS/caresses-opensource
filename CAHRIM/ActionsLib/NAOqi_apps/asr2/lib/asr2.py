#!/usr/bin/env python
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

import qi
from abcdk.AbcdkSoundReceiver.AbcdkSoundReceiver import AbcdkSoundReceiver
from otherlibs.speech_recognition import Recognizer
import sys

sys.path.append("/data/home/nao/.local/share/PackageManager/apps/asr2/lib/otherlibs/")


class ASR2:

    def __init__(self, session):
        self.session = session
        self.module_name = self.__class__.__name__

        self._preVad = 0.3
        self._postVad = 0.7

        self._ab = [False, False, False, False, False]

    ## This function is just for testing purposes
    def echo(self, message):
        return message

    def setGoogleCredentials(self, google_credentials):
        Recognizer.setGoogleCredentials(google_credentials)

    def getGoogleCredentials(self):
        Recognizer.getGoogleCredentials()

    def setPreferredPhrases(self, phrases):
        Recognizer.setPreferredPhrases(phrases)

    def getPreferredPhrases(self):
        Recognizer.getPreferredPhrases()

    def setVads(self, vads):
        self._preVad = vads[0]
        self._postVad = vads[1]

    def getVads(self):
        return [self._preVad, self._postVad]

    def startReco(self, language, useGoogleKey, blockHead):

        self.abcdk_id = register_as_service(AbcdkSoundReceiver)
        self.asr = self.session.service("AbcdkSoundReceiver")

        self.session.service("ALAudioDevice").enableEnergyComputation()
        self.asr.start(language, useGoogleKey, self._preVad, self._postVad, self.session.service("ALAudioDevice").getFrontMicEnergy())
        self.asr.subscribeAudio()
        self.session.service("ALMemory").insertData("Audio/RecognizedWords", [])


        self._ab = self._getAutonomousAbilities()

        if blockHead:
            ## Stop head motion
            self._setAutonomousAbilities(False, True, False, False, False)
            self.session.service("ALRobotPosture").goToPosture("Stand", 0.5)

    def stopReco(self):
        self.session.service("ALLeds").reset("AllLeds")
        self.asr.stop()
        self.session.service("ALMemory").removeData("Audio/RecognizedWords")
        self.session.unregisterService(self.abcdk_id)

        self._setAutonomousAbilities(self._ab[0], self._ab[1], self._ab[2], self._ab[3], self._ab[4])

    def _setAutonomousAbilities(self, blinking, background, awareness, listening, speaking):
        '''
        Enable some of the autonomous abilities.

        :param session:    qi session
        :param blinking:   boolean for AutonomousBlinking
        :param background: boolean for BackgroundMovement
        :param awareness:  boolean for BasicAwareness
        :param listening:  boolean for ListeningMovement
        :param speaking:   boolean for SpeakingMovement
        :return: ---
        '''

        sLife = self.session.service("ALAutonomousLife")

        sLife.setAutonomousAbilityEnabled("AutonomousBlinking", blinking)
        sLife.setAutonomousAbilityEnabled("BackgroundMovement", background)
        sLife.setAutonomousAbilityEnabled("BasicAwareness", awareness)
        sLife.setAutonomousAbilityEnabled("ListeningMovement", listening)
        sLife.setAutonomousAbilityEnabled("SpeakingMovement", speaking)

    def _getAutonomousAbilities(self):
        sLife = self.session.service("ALAutonomousLife")

        blinking   = sLife.getAutonomousAbilityEnabled("AutonomousBlinking")
        background = sLife.getAutonomousAbilityEnabled("BackgroundMovement")
        awareness  = sLife.getAutonomousAbilityEnabled("BasicAwareness")
        listening  = sLife.getAutonomousAbilityEnabled("ListeningMovement")
        speaking   = sLife.getAutonomousAbilityEnabled("SpeakingMovement")

        return [blinking, background, awareness, listening, speaking]

def register_as_service(service_class, robot_ip="127.0.1"):
    """
    Registers a service in NAOqi
    """
    session = qi.Session()
    session.connect("tcp://%s:9559" % robot_ip)
    service_name = service_class.__name__
    instance = service_class(session)
    try:
        service_id = session.registerService(service_name, instance)
        print 'Successfully registered service: {}'.format(service_name)
    except RuntimeError:
        print '{} already registered, attempt re-register'.format(service_name)
        for info in session.services():
            try:
                if info['name'] == service_name:
                    session.unregisterService(info['serviceId'])
                    print "Unregistered {} as {}".format(service_name,
                                                         info['serviceId'])
                    break
            except (KeyError, IndexError):
                pass
        service_id = session.registerService(service_name, instance)
        print 'Successfully registered service: {}'.format(service_name)

    return service_id


if __name__ == "__main__":
    """
    Registers ASR2 as a NAOqi service.
    """
    register_as_service(ASR2)
    app = qi.Application()
    app.run()

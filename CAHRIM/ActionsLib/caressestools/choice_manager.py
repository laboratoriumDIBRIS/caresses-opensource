#!/usr/bin/env python
# coding: utf8

# Copyright 2017 SoftBank Robotics

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# 	http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Project     : Caresses
# Author      : Maxime Busy
# Departement : Innovation Software

from naoqi import ALProxy
import argparse
import time
import qi


class ChoiceManager:

    def __init__(self, ip):
        """
        Constructor

        Parameters:
            ip - The ip address of the robot (string)
        """
        try:
            assert ip is not None
            assert ip != ""
            assert ip != "127.0.0.1"
            refinedIp  = ip

        except AssertionError:
            refinedIp = "198.18.0.1"

        self.TAG           = self.__class__.__name__
        self.EXTRACTOR     = "choice_extractor"
        self.HTML_EVENT    = "HTMLQuestion"

        self.session = qi.Session()
        self.session.connect("tcp://" + str(ip) + ":9559")

        self.speechReco    = self.session.service("ALSpeechRecognition")
        self.behaviours    = self.session.service("ALBehaviorManager")
        self.tabletService = self.session.service("ALTabletService")
        self.tts           = self.session.service("ALTextToSpeech")
        self.memory        = self.session.service("ALMemory")
        self.logger        = self.session.service("ALLogger")

        self.bPageLoaded = False
        self.bRepeatAnswer = False
        self.bBehaviourStarted = False

        self.signalId = None

        self.kill(hideWebview=False)
        self.launchBehavior()

        try:
            assert self.isBehaviourRunning()
            qi.logInfo(self.TAG, "Choice Manager started on " + refinedIp)

        except AssertionError:
            qi.logError(self.TAG, "Choice Manager could not be started on "\
                + refinedIp)


    def giveChoice(self, question, answerList, confidence=0.5, bSayQuestion=True):
        """
        The question is said and displayed, the answers are displayed and the
        robot tries to verbally catch them

        Parameters:
            question - The question (string)
            answerList - The list containing the answers
            confidence - The confidence for the answer in percents (if the
            answer A is recognized with a confidence superior to the specified
            confidence, the answer will be returned. otherwise, the program
            continues to wait)
            bSayQuestion - Boolean, the robot will tell orally the question if True
        """
        answer = ""

        try:
            assert self.isBehaviourRunning()

        except AssertionError:
            return answer


        self.memory.insertData("WordRecognized", [])
        self.memory.insertData("tabletResponse", "")
        self.speechReco.setVisualExpression(True)
        self.speechReco.setAudioExpression(False)

        self.speechReco.pause(True)
        self.speechReco.setVocabulary(answerList, True)

        self.showHTMLQuestion(question, answerList)

        if(bSayQuestion):
            self.tts.say(question)

        self.speechReco.pause(False)
        self.speechReco.subscribe(self.EXTRACTOR);

        while True:

            vocalData  = self.memory.getData("WordRecognized")
            tabletData = self.memory.getData("tabletResponse")

            if len(vocalData) > 0:
                if vocalData[1] > confidence:
                    answer    = vocalData
                    answer[0] = answer[0][6:]    # filter the <...> <...> of the
                    answer[0] = answer[0][:-6]  # answer
                    break

            if tabletData != "":
                answer = [tabletData, 1]
                break

            time.sleep(0.1)

        self.speechReco.unsubscribe(self.EXTRACTOR)
        self._sendCommandToHTML(["erase_all","",""])

        if self.bRepeatAnswer:
            self.tts.say(answer[0])

        return answer



    def setRepeatAnswer(self, bRepeatAnswer):
        """
        Choose wether if the robot repeats the answer or not.

        Parameters:
            bRepeatAnswer - Boolean, the robot will repeat the answer if True,
            and won't otherwise
        """

        self.bRepeatAnswer = bRepeatAnswer



    def showHTMLQuestion(self, question, answerList):
        """
        Send the question and the answers to the javascript part

        Parameters:
            question - The question
            answerList - The list of answers
        """

        try:
            assert question is not None
            assert answerList is not None

        except AssertionError:
            print "Bad use of the method"
            return

        self.memory.insertData( "isLoaded", "" )

        self._sendQuestionToHTML(question,answerList)



    def _sendQuestionToHTML(self, question, answerList):
        """
        Translates the question to be set into a command, and sends it to the
        web page

        Parameters:
            question - The question to be sent
            answerList - The list of answers to be sent
        """

        try:
            assert not isinstance(answerList, list)

        except AssertionError:
            answerList = ";".join(answerList)

        try:
            assert self.memory.getData("isLoaded") == ""

        except:
            return

        self._sendCommandToHTML([question, answerList])



    def _sendCommandToHTML(self, command):
        """
        Sends a command to the HTML page

        Parameters:
            command - The command to be sent
        """

        time.sleep(0.2)
        self.memory.raiseEvent(self.HTML_EVENT,command)


    def isBehaviourRunning(self):
        return self.bBehaviourStarted

    def onPageFinishedSignal(self):
        self.bPageLoaded = True

    def launchBehavior(self):
        try:
            self.signalId = self.tabletService.onPageFinished.connect(
                self.onPageFinishedSignal)

            self.behaviours.startBehavior("choice-manager/question")
            self.bBehaviourStarted = True

            while not self.bPageLoaded:
                time.sleep(0.1)

            self.bPageLoaded = False
            self.tabletService.onPageFinished.disconnect(self.signalId)

            time.sleep(1)

        except RuntimeError:
            self.bBehaviourStarted = False
            qi.logError(self.TAG, "Runtime error occured while trying to "\
                + "launch the choice manager")


    def kill(self, hideWebview=True):
        try:
            self.behaviours.stopBehavior("choice-manager/question")
            self.bBehaviourStarted = False
            if hideWebview:
                self.tabletService.hideWebview()

        except RuntimeError:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--ip",
                        type=str,
                        default="10.0.207.72",
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")

    args = parser.parse_args()

    choice = ChoiceManager(args.ip)
    choice.setRepeatAnswer(True)

    print choice.giveChoice("Are you ok ?", ["yes", "no"], confidence=0.45)
    print choice.giveChoice("Am I a robot ?", ["yes", "no"], confidence=0.45)
    # print choice.giveChoice("Hey, ça va ?", ["oui", "non"], confidence=0.45)
    # print choice.giveChoice("Quelle est ta couleur préférée ?", ["orange", "bleu", "rouge", "jaune"], confidence=0.45)
    # print choice.giveChoice("私はロボットですか?", ["はい", "いいえ"], confidence=0.45)
    # print choice.giveChoice("あなたの好きな色は何ですか?", ["青色", "赤色", "黄色"], confidence=0.45)

    choice.kill()

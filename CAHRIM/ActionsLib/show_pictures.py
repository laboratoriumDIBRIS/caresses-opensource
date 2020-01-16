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

import time
import functools

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Show Pictures"
#
#  Pepper shows on its tablet the pictures previously taken through the action Take And Send Picture or previously stored in Pepper's memory.
#  This action requires the installation of the NAOqi app Pictures
class ShowPictures(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space. <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        # Initialize NAOqi services
        self.sTablet = self.session.service("ALTabletService")
        self.sMemory = self.session.service("ALMemory")
        self.sSpeechReco = self.session.service("ALSpeechRecognition")
        self.sBehavior = self.session.service("ALBehaviorManager")

        # Set the cultural parameters
        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(session, self.volume)
        caressestools.setVoiceSpeed(session, self.speed)
        caressestools.setVoicePitch(session, self.pitch)

        # Set up speech.py app to get information
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(session, caressestools.Settings.robotIP.encode('utf-8'))

        self.extension = "jpg"
        self.path_take = "/data/home/nao/.local/share/PackageManager/apps/%s/html/images/"
        self.path_show = "http://%s/apps/%s/images/%s"

        self.must_stop = False
        self.pic_list_received = False
        self.pics = []
        self.is_touched = False

        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        listReceived = self.sMemory.subscriber("CARESSES/pictures/list")
        id_listReceived = listReceived.signal.connect(
            functools.partial(self.onListReceived, "CARESSES/pictures/list"))

        line_show = self.sp.script[self.__class__.__name__][speech.OTHER]["0"][self.language].encode('utf-8')
        line_end = self.sp.script[self.__class__.__name__][speech.OTHER]["1"][self.language].encode('utf-8')
        line_like = self.sp.script[self.__class__.__name__][speech.OTHER]["2"][self.language].encode('utf-8')
        line_nopics = self.sp.script[self.__class__.__name__][speech.OTHER]["3"][self.language].encode('utf-8')
        voc = [k.encode('utf-8') for k in self.sp.script[self.__class__.__name__][speech.USER]["0"][self.language]]
        stop_keyword = voc[0]

        self.sBehavior.startBehavior("pictures/list-pictures")

        while not self.pic_list_received:
            pass

        for pic in self.all_pics:
            if not "Logo_CARESSES_tablet" in pic:
                self.pics.append(pic)

        self.setSpeechRecognition(voc)

        if not len(self.pics) == 0:
            for pic in self.pics:
                self.sTablet.preLoadImage(self.path_show % (caressestools.Settings.robotIP, caressestools.DEF_IMG_APP, pic))

            self.sp.say(line_show.replace("$STOPKEYWORD$", stop_keyword), speech.TAGS[1])

            self.sSpeechReco.setVisualExpression(False)
            self.sSpeechReco.setAudioExpression(False)

            self.sSpeechReco.subscribe("WordRecognized")
            speechRecognized = self.sMemory.subscriber("WordRecognized")
            id_speechRecognized = speechRecognized.signal.connect(functools.partial(self.onSpeechRecognized, "WordRecognized"))

            self.touch = self.sMemory.subscriber("TouchChanged")
            self.signal_touch = self.touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))

            for pic in self.pics:
                if self.is_stopped or self.is_touched:
                    break
                self.sTablet.showImage(
                    self.path_show % (caressestools.Settings.robotIP, caressestools.DEF_IMG_APP, pic))
                time.sleep(5)
                if self.must_stop == True:
                    self.sp.userSaid(self.user_input)
                    self.sp.replyAffirmative()
                    break

            if pic == self.pics[-1]:
                self.sp.say(line_end.replace("$USERNAME$", self.username), speech.TAGS[1])

            if not self.is_stopped and not self.is_touched:
                self.sp.askYesOrNoQuestion(
                    self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
                self.sp.monolog(self.__class__.__name__, "1", group="evaluation", tag=speech.TAGS[1])

        else:
            self.sp.say(line_nopics, speech.TAGS[1])

        self.end()

    ## Callback
    def onListReceived(self, msg, value):
        self.all_pics = value
        self.pic_list_received = True

    ## Sets parameters for keyword recognition
    def setSpeechRecognition(self, vocabulary):
        self.sSpeechReco.pause(True)
        self.sSpeechReco.setLanguage(caressestools.Language.lang_naoqi)
        self.sSpeechReco.setVocabulary(vocabulary, True)
        self.sSpeechReco.pause(False)

    ## Callback
    def onSpeechRecognized(self, msg, value):
        if value[1] > 0.4:
            self.user_input = value[0][6:-6]
            self.must_stop = True

    ## Callback
    def onTouch(self, msg, value):
        self.touch.signal.disconnect(self.signal_touch)
        self.logger.info("The user touched the robot.")
        self.is_touched = True
        self.sp.replyAffirmative()
        self.sp.say(self.sp.script[speech.STOP_INTERACTION][self.language], speech.TAGS[1])

    ## Method containing all the instructions that should be executing before terminating the action.
    def end(self):
        try:
            self.sSpeechReco.unsubscribe("WordRecognized")
        except:
            pass


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
    apar = ''
    cpar = "1.0 100 1.1 english John"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = ShowPictures(apar, cpar, session, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

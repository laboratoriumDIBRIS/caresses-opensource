# -*- coding: utf-8 -*-
'''
Copyright October 2019 Bui Ha Duong & Roberto Menicatti & Università degli Studi di Genova

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

Author:      Bui Ha Duong (1), Roberto Menicatti (2)
Email:       (1) bhduong@jaist.ac.jp (2) roberto.menicatti@dibris.unige.it
Affiliation: (1) Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan 
             (2) Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import functools
import time
from threading import Timer
from random import shuffle

from aux_files.youtube_helper.youtube_helper import YoutubeHelper, YOUTUBE_EMBED_LINK
from aux_files.youtube_helper.db_helper import DatabaseHelper

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech

ASR_SERVICE = "Caresses_PlayMusic_ASR"
PLAY_YOUTUBE_ROBOT = "caresses-play-youtube"


## Action "You Tube Tv".
#
#  Pepper plays a video from YouTube. This action shouldn't be executed standalone; its child classes should be used instead.
#  This action requires the installation of the NAOqi app PlayYouTube.
class YouTubeTv(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) ID of the video, as stored in the CKB.
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.video_id = self.apar[0]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        # Initialize NAOqi services
        self.memory_service = session.service("ALMemory")
        self.tablet_service = session.service("ALTabletService")
        self.sAudio = self.session.service("ALAudioDevice")

        self.yt = YoutubeHelper()
        self.db = DatabaseHelper()

        # Flag to keep action running
        self.is_running = True
        # Flag to keep track the ending of the music video
        self.is_ended = False

        self.is_site_loaded = False

        # Set the cultural parameters
        caressestools.Language.setLanguage(self.language)
        caressestools.setRobotLanguage(session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(session, self.volume)
        caressestools.setVoiceSpeed(session, self.speed)
        caressestools.setVoicePitch(session, self.pitch)
        caressestools.setTabletVolume(session, 15)

        # Set up speech.py app to get information
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(session, caressestools.Settings.robotIP.encode('utf-8'))

        self.subaction = None
        self.params = None
        self.search_keyword = ""
        self.max_results = 8
        self.again = True
        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        suggested_IDs = [option.replace('"', '') for option in self.suggestions]
        self.IDs = self.mergeAndSortIDs(self.params, suggested_IDs)
        self.options = self.getAllParametersAttributes(self.params, self.IDs, "full")

        custom_option = self.sp.script[self.__class__.__name__]["custom-option"][self.language].encode('utf-8')
        self.options.append(custom_option)

        signalID = self.tablet_service.onPageFinished.connect(self.onPageFinished)

        while self.again and not self.is_stopped:

            if not self.isAvailable(self.video_id):
                self.video_full = custom_option
                try:
                    self.video_full_unicode=unicode(self.video_full,"utf-8")
                except:
                    self.video_full_unicode=self.video_full

                while self.video_full_unicode == unicode(custom_option,"utf-8"):
                    ## Set the weight of parameter guessing to be higher in the first part of the sentence (l=left)
                    self.sp._mf_weight = 'l'
                    self.video_full = self.sp.dialog(self.__class__.__name__, self.options,
                                                 checkValidity=False, askForConfirmation=True, noisy=self.asr)
                    try:
                        self.video_full_unicode=unicode(self.video_full,"utf-8")
                    except:
                        self.video_full_unicode=self.video_full

                self.video_id = self.getIDFromAttribute(self.params, "full", self.video_full)
            else:
                self.video_full = self.getAttributeFromID(self.params, self.video_id, "full")
                self.sp.monolog(self.__class__.__name__, speech.WITH_KEYWORD, param={"$KEYWORD$": self.video_full},
                                group="parameter-answer", tag=speech.TAGS[1])

            self.sp.monolog(self.__class__.__name__, "1", param={"$USERNAME$": self.username}, tag=speech.TAGS[1])
            self.sp.monolog(self.__class__.__name__, "2", tag=speech.TAGS[1])

            # Get video id
            id_list = self.yt.search_video_id(self.video_full + self.search_keyword)
            id_list_top = id_list[0:4]
            id_list_bottom = id_list[4:len(id_list)]
            shuffle(id_list_top)
            id_list = id_list_top + id_list_bottom

            if self.video_id is not None:
                url = self.getAttributeFromID(self.params, self.video_id, "url")
                id = self.yt.get_video_id(url)
                embeddable = self.yt.checkIfEmbeddable(id)

                if embeddable:
                    playable = self.yt.checkIfPlayable(id)
                    if playable:
                        id_list = [id] + id_list_top + id_list_bottom


            for id in id_list:
                try:
                    video_duration = self.yt.get_video_duration(id)
                    break
                except:
                    # If the video is unavailable then talk with user
                    self.sp.monolog(self.__class__.__name__, "video-unavailable", tag=speech.TAGS[1])
                    self.logger.info("Video no more available.")

            # Start the application on tablet
            self.tablet_service.cleanWebview()
            self.tablet_service.loadUrl(YOUTUBE_EMBED_LINK % id)
            # self.tablet_service.loadUrl('https://www.youtube.com/tv#/watch/video/control?v=' + id)
            self.tablet_service.showWebview()
            self.old_volume = self.sAudio.getOutputVolume()
            self.new_volume = self.old_volume + self.volume_video_increase if self.old_volume + self.volume_video_increase <= 100 else 100
            self.sAudio.setOutputVolume(self.new_volume)

            while not self.is_site_loaded:
                pass

            time.sleep(5)

            timer = Timer(int(video_duration), self.timeout)
            timer.start()

            # Register events
            # 'TouchChanged'
            touch = self.memory_service.subscriber("TouchChanged")
            id_touch = touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))

            while self.is_running and not self.is_stopped:
                pass

            self.sAudio.setOutputVolume(self.old_volume)

            timer.cancel()

            caressestools.showImg(self.session, caressestools.TABLET_IMG_EXECUTION)

            if not self.is_stopped:
                question = self.sp.script[self.__class__.__name__][speech.OTHER]["3"][self.language].encode('utf-8')
                self.again = self.sp.askYesOrNoQuestion(question, speech.TAGS[11], noisy=self.asr)
                if self.again:
                    self.video_id = '"n/a"'
                    self.is_running = True
                else:
                    self.sp.replyAffirmative()
                    self.sp.askYesOrNoQuestion(
                        self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
                    self.sp.monolog(self.__class__.__name__, "1", group="evaluation", tag=speech.TAGS[1])

        self.tablet_service.hide()
        self.db.close()

    ## Callback
    def timeout(self):
        self.is_running = False

    ## Callback
    def onTouch(self, msg, value):
        self.is_running = False

    ## Callback
    def onPageFinished(self):
        self.is_site_loaded = True

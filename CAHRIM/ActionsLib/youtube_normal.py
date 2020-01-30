# -*- coding: utf-8 -*-
'''
Copyright October 2019 Japan Advanced Institute of Science and Technology & Roberto Menicatti & Università degli Studi di Genova

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
from aux_files.youtube_helper.youtube_helper import YoutubeHelper
from aux_files.youtube_helper.db_helper import DatabaseHelper

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech

ASR_SERVICE = "Caresses_PlayMusic_ASR"
PLAY_YOUTUBE_ROBOT = "caresses-play-youtube"


## Action "You Tube Normal".
#
#  Pepper plays a video from YouTube. This action shouldn't be executed standalone; its child classes should be used instead.
#  This action requires the installation of the NAOqi app PlayYouTube.
class YouTubeNormal(Action):

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
        self.must_continue = self.apar[1].lower() == "true"

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
        # Flag to keep the status of the video
        self.is_video_unavailable = False

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

        self.params = None
        self.again = True
        self.asr =asr

    ## Method executed when the thread is started.
    def run(self):

        suggested_IDs = [option.replace('"', '') for option in self.suggestions]
        self.IDs = self.mergeAndSortIDs(self.params, suggested_IDs)
        self.options = self.getAllParametersAttributes(self.params, self.IDs, "full")

        custom_option = self.sp.script[self.__class__.__name__]["custom-option"][self.language].encode('utf-8')
        self.options.append(custom_option)

        # 'pepper/music/ended'
        onEnded = self.memory_service.subscriber('pepper/music/ended')
        idEnded = onEnded.signal.connect(functools.partial(self.onEnded, 'pepper/music/ended'))

        # 'pepper/music/paused'
        onPaused = self.memory_service.subscriber('pepper/music/paused')
        idPaused = onPaused.signal.connect(functools.partial(self.onPaused, 'pepper/music/paused'))

        # 'pepper/music/unavailable'
        onUnavailable = self.memory_service.subscriber('pepper/music/unavailable')
        idUnavailable = onUnavailable.signal.connect(functools.partial(self.onUnavailable, 'pepper/music/unavailable'))

        while self.again and not self.is_stopped:
            if not self.isAvailable(self.video_id):
                self.video_full = custom_option
                try:
                    self.video_full_unicode=unicode(self.video_full,"utf-8")
                except:
                    self.video_full_unicode=self.video_full
                while self.video_full_unicode == unicode(custom_option,"utf-8"):
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

            # Get video id
            if self.video_id is not None:
                url = self.getAttributeFromID(self.params, self.video_id, "url")
                id = self.yt.get_video_id(url)
                id_list = self.yt.search_video_id(self.video_full)
                index = 0
            else:
                id_list = self.yt.search_video_id(self.video_full)
                id = id_list[0]
                index = 1

            # Start the application on tablet
            self.tablet_service.cleanWebview()
            self.tablet_service.loadApplication(PLAY_YOUTUBE_ROBOT)
            self.sp.monolog(self.__class__.__name__, "1", param={"$USERNAME$": self.username}, tag=speech.TAGS[1])
            self.tablet_service.showWebview()
            time.sleep(3)
            self.sp.monolog(self.__class__.__name__, "2", tag=speech.TAGS[1])

            self.play(id, 0)

            # Register events
            # 'TouchChanged'
            touch = self.memory_service.subscriber("TouchChanged")
            id_touch = touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))

            # Play music
            try:
                while self.is_running and not self.is_stopped:
                    if self.is_ended:
                        # If ended the video then reset the rows in database
                        self.db.update_stop_seconds(id, 0.0)
                        # Stop the action also
                        self.is_running = False

                    if self.is_video_unavailable:
                        self.sAudio.setOutputVolume(self.old_volume)
                        # If the video is unavailable then talk with user
                        self.sp.monolog(self.__class__.__name__, "video-unavailable", tag=speech.TAGS[1])
                        id = id_list[index]
                        index += 1
                        self.is_video_unavailable = False
                        self.play(id, 1)

            finally:
                self.sAudio.setOutputVolume(self.old_volume)
                self.memory_service.raiseEvent("pepper/music/pause", "pause")
                time.sleep(5)

                if not self.is_video_unavailable and not self.is_ended:
                    # Get the stop seconds
                    stop_seconds = self.memory_service.getData('pepper/music/stop_seconds')
                    # Update the stop second in database
                    self.db.update_stop_seconds(id, stop_seconds)

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

        # Stop the action
        self.db.close()
        self.tablet_service.hide()

    ## Play the video.
    #  @param id YouTube ID of the video
    #  @param reload
    def play(self, id, reload):
        # reload = 0 -> play the first time
        # reload = 1 -> reload new id because the video is unavailable

        # Search in database to get the stop time if the video is played before
        start_seconds = self.db.get_start_seconds(id)

        if start_seconds > 0.0:
            is_continue = self.must_continue
            # Ask if user want to continue from the previous stop second.
            if not self.must_continue:
                question = self.sp.script[self.__class__.__name__][speech.OTHER]["0"][self.language].encode("utf-8")
                is_continue = self.sp.askYesOrNoQuestion(question, speech.TAGS[4], noisy=self.asr)

            if not is_continue:
                start_seconds = 0.0

        self.old_volume = self.sAudio.getOutputVolume()
        self.new_volume = self.old_volume + self.volume_video_increase if self.old_volume + self.volume_video_increase <= 100 else 100
        self.sAudio.setOutputVolume(self.new_volume)

        # Send data to robot's tablet
        data = '{ "id":"%s", "startSeconds":"%s"}' % (id, start_seconds)
        if reload:
            self.memory_service.raiseEvent("pepper/music/reload", data)
        else:
            self.memory_service.raiseEvent("pepper/music/play", data)

    ## Callback
    def onTouch(self, msg, value):
        self.is_running = False

    ## Callback
    def onEnded(self, msg, value):
        self.is_ended = True

    ## Callback
    def onPaused(self, msg, value):
        pass

    ## Callback
    def onUnavailable(self, msg, value):
        self.is_video_unavailable = True

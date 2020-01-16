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

from youtube_tv import YouTubeTv
import caressestools.caressestools as caressestools
import caressestools.speech as speech

ASR_SERVICE = "Caresses_PlayMusic_ASR"
PLAY_YOUTUBE_ROBOT = "caresses-play-youtube"


## Action "Play Karaoke".
#
#  Pepper shows a karaoke video from YouTube on its tablet.
#  This action requires the installation of the NAOqi app PlayYouTube.
class PlayKaraoke(YouTubeTv):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) ID of the video, as stored in the CKB.
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        YouTubeTv.__init__(self, apar, cpar, session, asr)

        self.subaction = "KARAOKE"
        self.params = self.loadParameters("karaoke.json")
        self.search_keyword = " karaoke"


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
    apar = '"n/a" "n/a"'
    cpar = "1.0 100 1.1 english John timeAfterTime"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = PlayKaraoke(apar, cpar, session, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

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

from ActionsLib.caressestools import caressestools
from ActionsLib.caressestools import speech

def main(session, language, session_number, robot):

    language = language
    volume = 0.7
    speed  = 80
    pitch  = 1

    caressestools.Language.setLanguage(language)

    caressestools.setRobotLanguage(session, caressestools.Language.lang_naoqi)
    caressestools.setVoiceVolume(session, volume)
    caressestools.setVoiceSpeed(session, speed)
    caressestools.setVoicePitch(session, pitch)

    sp = speech.Speech("speech_conf.json", language)
    sp.enablePepperInteraction(session, caressestools.Settings.robotIP.encode('utf-8'))

    with open("end_session_conf.json", 'r') as f:
        sentences = json.load(f)

    try:
        line = sentences[str(session_number)][robot][language].encode('utf-8')
    except Exception as e:
        print e
        print "Cannot retrieve any sentence."
        sys.exit()

    if not line == "":
        sp.say(line, speech.TAGS[1])
    else:
        print "ERROR: No sentence for the '%s' robot at the end of session %d in the %s language!" % (robot, session_number, language)


if __name__ == "__main__":

    import argparse
    import qi
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--language", "-l", required=True, type=str, help="Language supported in CARESSES [english, japanese]")
    parser.add_argument("--group", "-g", required=True, type=str, help="CARESSES experiments group [experimental, control]")
    parser.add_argument("--session", "-s", required=True, type=int, help="Session number [1, 2, 3, 4, 5, 6]")
    parser.add_argument("--ip", type=str, default=caressestools.Settings.robotIP, help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559, help="Naoqi port number")

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

    assert args.group in ["experimental", "control"], "'group' parameter can either be 'experimental' or 'control'"
    assert args.session in [1, 2, 3, 4, 5, 6], "'session' parameter can only be: 1, 2, 3, 4, 5, 6."

    main(session, args.language, args.session, args.group)
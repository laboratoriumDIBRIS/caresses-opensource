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
import sys
import argparse

def main(session):

    sSpeech = session.service("ALTextToSpeech")
    sRecharge = session.service("ALRecharge")
    sMemory = session.service("ALMemory")

    sSpeech.setVolume(0.7)
    sSpeech.setParameter("speed", 90.0)
    sSpeech.setParameter("pitchShift", 1.0)

    sSpeech.say("I'm sorry, I need to rest for a while now. Let's talk again later! Bye bye!")

    sRecharge.goToStation()
    while not sRecharge.getStatus() in [0, 4]:  # idle, error
        pass
    if sRecharge.getStatus() == 4:
        print ("ERROR")
    elif sRecharge.getStatus() == 0:
        onCharger = True
        sMemory.insertData("CARESSES_onCharger", onCharger)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, required=True,
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

    main(session)

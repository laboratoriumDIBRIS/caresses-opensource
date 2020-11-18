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

import sys
import time
import threading

from action import Action
import caressestools.multipage_choice_manager as mlt
from aux_files.go_to.graphnavigation import *
import caressestools.caressestools as caressestools
import caressestools.speech as speech


## Action "Set Node"
#
#  Pepper asks to be taken by hand to a node of the map in order to reset its localization.
class SetNode(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Name of graph file.
    # @param cpar (string) Volume, speed, pitch, language, username; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    def __init__(self, apar, cpar, session):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.map = self.apar[0]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')

        # Initialize NAOqi services
        self.sMotion       = self.session.service("ALMotion")
        self.sNavigation   = self.session.service("ALNavigation")
        self.sMemory       = self.session.service("ALMemory")
        self.sBehavior     = self.session.service("ALBehaviorManager")
        self.sPosture      = self.session.service("ALRobotPosture")
        self.sTablet       = self.session.service("ALTabletService")

        graph_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "aux_files", "go_to", self.map)
        self.file = GraphFile()
        self.file.loadFile(graph_file, draw = False)

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))


    ## Method executed when the thread is started.
    def run(self):

        self.sp.monolog(self.__class__.__name__, "0", tag=speech.TAGS[1])

        caressestools.setAutonomousAbilities(self.session, False, False, False, False, False)
        self.sPosture.goToPosture("Stand", 0.5)

        if not self.sBehavior.isBehaviorRunning("User/follow-me-no-security-avatarion"):
            self.sBehavior.startBehavior("User/follow-me-no-security-avatarion")

        question = ""
        nodes = Graph.nodes
        options = [x.getLabel() for x in Graph.nodes if not x.getLabel().startswith("node")]
        self.choice = mlt.MultiPageChoiceManager(caressestools.Settings.robotIP.encode('utf-8'))

        if self.sp._input==2:
            self.sp.gothread = True
            thr = threading.Thread(name="getinput", target=self.sp.getOptionsFromSmartphone, args=[options])
            thr.start()
        answer = self.choice.giveChoiceMultiPage(question, options, timer=1200, exitOnTouch=False)
        self.sp.gothread=False
            

        
        answer = [unicode(answer[0], "utf-8"), answer[1]]
        self.choice.kill()

        self.sp.checkIfKilledDuringMcm(self.choice, answer, self.end)

        node = findNodeFromLabel(answer[0])

        position = self.sMotion.getRobotPosition(True)
        self.sMemory.insertData("CARESSES_fixedPose", [node.x * self.file.k, node.y * self.file.k, math.radians(node.th)])
        self.logger.info("Storing the following pose as node '%s': (%g, %g, %g) ==> (%g, %g, 0)" % (answer, position[0], position[1], position[2], node.x, node.y))

        self.sp.monolog(self.__class__.__name__, "1", tag=speech.TAGS[1])

        self.end()

    ## Method containing all the instructions that should be executing before terminating the action.
    def end(self):

        time.sleep(1)
        self.sBehavior.stopBehavior("User/follow-me-no-security-avatarion")
        self.sPosture.goToPosture("Stand", 0.5)
        ## Always call the following function after executing the "follow-me-no-security-avatarion" app
        self.sMotion.setMoveArmsEnabled(True, True)

        self.file.unloadCurrentWork(draw=False)


if __name__ == "__main__":

    import argparse
    import qi

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

    apar = "map.json"
    cpar = "1.0 100 1.1 english John"

    action = SetNode(apar, cpar, session)
    action.run()

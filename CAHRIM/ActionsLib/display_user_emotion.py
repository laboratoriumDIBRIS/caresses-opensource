# -*- coding: utf-8 -*-
'''
Copyright October 2019 Tuyen Nguyen

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

Author:      Tuyen Nguyen
Email:       ngtvtuyen@jaist.ac.jp
Affiliation: Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan
Project:     CARESSES (http://caressesrobot.org/en/)

README
This action gets information about user's emotion (user_id,estimated_emotion,confident_value) from thread EstimateUserEmotion 
and display the estimated emotion on the robot's tablet

Input parameter:  The confident value for accepting the estimated emotion

## To run the action without running cahrim.py:
## - comment the import of caressestools
## - replace the default value of the "ip" script argument with a string
## - run the action from the CAHRIM directory through the command:
## python -m ActionsLib.display_user_emotion --ip <PEPPER-IP>
'''
import time
import sys
sys.path.append("..")
import caressestools.caressestools as caressestools
from CahrimThreads.sensory_hub import EstimateUserEmotion
from action import Action
import numpy as np
import functools

FACIAL_EXPRESSION_ROBOT = "caresses-facial-expression"

class UserEmotion(Action):
    """
    Action display_user_emotion

    Attributes:
        apar : ---
        cpar : confident value for accepting the estimated emotion
        session : robot's session
    """

    def __init__(self, apar, cpar, session):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')
        self.confident_value = float(self.cpar[0])
        
        # Initialize NAOqi services
        self.memory = session.service("ALMemory")
        self.sTablet = session.service("ALTabletService")
        self.sTablet.loadApplication(FACIAL_EXPRESSION_ROBOT)
        self.sTablet.showWebview()

        # Subcribe the NAOqi touch events
        self.touch = self.memory.subscriber("TouchChanged")
        self.id_touch = self.touch.signal.connect(functools.partial(self.onTouched, "TouchChanged"))


    def run(self):
        timer_start = time.time()
        action_start_time = time.time()

        while not self.is_stopped:
            user_id, emotion_label, confident_value = EstimateUserEmotion.getUserEmotion()
            if confident_value >= self.confident_value:
                emotion_label = np.array([emotion_label])
                self.memory.raiseEvent('/face/emotion',emotion_label.tolist())    
            time.sleep(1.5)
    
        self.end()

    def end(self):
        self.sTablet.hide()    

    def onTouched(self, msg, value):
        self.is_stopped = True

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
    apar = ""
    cpar = "0.5"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    
    t = EstimateUserEmotion(session,None)
    t.start()
    
    action = UserEmotion(apar, cpar, session)
    action.run()

    t.stop()
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
import sys


class DateTimeSelector():

    def __init__(self, session):

        self.session = session
        self.isPageFinished = False
        self.received = False
        self.exit = False
        self.app = None
        self.event = None

        self.sTablet = self.session.service("ALTabletService")
        self.sMemory = self.session.service("ALMemory")

        self.sTablet.hideWebview()

    def selectTime12(self):

        self.app = 'time12selector'
        self.event = 'CARESSES/DateTimeSelector/time12'
        return self.run()

    def selectTime24(self):

        self.app = 'time24selector'
        self.event = 'CARESSES/DateTimeSelector/time24'
        return self.run()
    
    def selectDate(self):
        
        self.app = 'dateselector'
        self.event = 'CARESSES/DateTimeSelector/date'
        return self.run()

    def run(self):

        self.date_time = None

        signalId = self.sTablet.onPageFinished.connect(self.onPageFinishedSignal)

        self.sTablet.loadApplication(self.app)
        self.sTablet.showWebview()

        while not self.isPageFinished:
            time.sleep(0.1)

        self.sTablet.onPageFinished.disconnect(signalId)
        self.isPageFinished = False

        onInfo = self.sMemory.subscriber(self.event)
        idInfo = onInfo.signal.connect(functools.partial(self.onInfoReceived, self.event))

        onExit = self.sMemory.subscriber('CARESSES/DateTimeSelector/exit')
        idExit = onExit.signal.connect(functools.partial(self.onExitReceived, 'CARESSES/DateTimeSelector/exit'))

        ## Subscribe to touch event to quit the MultiPageChoiceManager if Pepper is touched
        touch = self.sMemory.subscriber("TouchChanged")
        idTouch = touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))

        while not self.received and not self.exit:
            pass

        self.kill()

        onInfo.signal.disconnect(idInfo)
        onExit.signal.disconnect(idExit)
        touch.signal.disconnect(idTouch)

        return self.date_time

    def onInfoReceived(self, msg, value):
        self.date_time = value
        self.received = True

    def onExitReceived(self, msg, value):
        self.date_time = None
        self.exit = True

    def onPageFinishedSignal(self):
        """
        Triggered when the onPageFinished is fired by ALTabletService
        """
        self.isPageFinished = True

    def onTouch(self, msg, value):
        self.sMemory.raiseEvent("CARESSES/DateTimeSelector/exit", True)

    def kill(self):
        self.received = False
        self.exit = False
        self.sTablet.hideWebview()


if __name__ == "__main__":

    import argparse
    import qi

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1",
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

    dts = DateTimeSelector(session)
    try:
        print dts.selectTime12()
        time.sleep(2)
        print dts.selectTime24()
        time.sleep(2)
        print dts.selectDate()
        time.sleep(2)
    except KeyboardInterrupt:
        sys.exit(1)

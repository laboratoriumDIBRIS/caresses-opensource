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

import Queue
import socket
import argparse
import os
import time
import logging
import sys
import qi.logging
from threading import Event
from colorama import init, deinit

from ActionsLib.caressestools.caressestools import Settings, connectToPepper, startPepper, showImg, unloadImg, stopPepper, loadMap, TABLET_IMG_DEFAULT
from CahrimThreads.socket_handlers import MsgReceiver, MsgSender, InputMsgHandler, OutputMsgHandler
from CahrimThreads.actuation_hub import StateObserver
from CahrimThreads.behaviour_pattern_estimator import BehaviourPatternEstimator
from CahrimThreads.sensory_hub import DBObserver, OdomConverter, DetectUserDepth, EstimateUserEmotion
from CahrimThreads.user_behaviour_analysis import ActivityAndLocationRecognition

output_queue = Queue.Queue(maxsize=0)
input_queue  = Queue.Queue(maxsize=0)

log_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cahrimLog.log")
logger = logging.getLogger('CAHRIM')
ch = logging.StreamHandler()
fh = logging.FileHandler(filename=log_filename, mode='a')
ch_formatter = logging.Formatter('[%(name)-40s] - %(levelname)8s: %(message)s')
fh_formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(name)-40s] - %(levelname)8s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
ch.setFormatter(ch_formatter)
fh.setFormatter(fh_formatter)
logger.setLevel(logging.DEBUG)

loglevels = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "notset": logging.NOTSET
}

def main(startingNode, group, asr, loglevel, useFaceReco):

    experimental = group.lower() == "experimental"
    mode = "Experimental" if experimental else "Control"

    temp = asr.lower() == "noisy"
    asr = "noisy" if temp else "normal"

    fh.setLevel(logging.DEBUG)
    ch.setLevel(loglevels[loglevel])
    logger.addHandler(ch)
    logger.addHandler(fh)
    # qi.logging.setLevel(qi.logging.VERBOSE)

    print("-----------------------------------------------")
    logger.info("Starting CAHRIM in %s mode" % mode)
    print("-----------------------------------------------\n")

    ## Load IPs and Ports
    robotIP    = Settings.robotIP
    robotPort  = Settings.robotPort
    cahrimIP   = Settings.cahrimIP
    cahrimPort = int(Settings.cahrimPort)

    ## Connect to Pepper
    session = connectToPepper(robotIP, robotPort)

    ## Wake Pepper up and start autonomous abilities
    startPepper(session, startingNode)

    ## Start socket communication with uAAL-CAHRIM
    connected = False
    while not connected:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((cahrimIP, cahrimPort))
            connected = True
            logger.info("Socket communication with uAAL-CAHRIM started.")
        except Exception as e:
            logger.warning(e)
            logger.info("Trying to reconnect...")
            time.sleep(2)

    provided_event = Event()

    output_handler = OutputMsgHandler(output_queue)
    input_handler = InputMsgHandler(session, output_handler, input_queue, provided_event, experimental, asr)

    ## Create threads' instances
    threads = []

    threads.append(MsgReceiver(sock, input_handler))
    threads.append(MsgSender(sock, output_queue))

    threads.append(StateObserver(session, output_handler, asr))
    # threads.append(BehaviourPatternEstimator(output_handler))
    # threads.append(DBObserver(output_handler))
    threads.append(OdomConverter(session, startingNode))
    threads.append(DetectUserDepth(session, output_handler, useFaceReco))
    # threads.append(ActivityAndLocationRecognition(output_handler))
    threads.append(EstimateUserEmotion(session, output_handler)) 

    ## Start all threads
    for t in threads:
        t.start()
        t_name = t.id if hasattr(t, "id") else t.__class__.__name__
        logger.info("%s started." % t_name)

    print("-----------------------------------------------\n"
          " ===> All threads started.\n"
          "-----------------------------------------------\n")

    showImg(session, TABLET_IMG_DEFAULT)

    StateObserver.starting_node = startingNode

    try:
        while True:
            if StateObserver.killed_cahrim:
                logger.info("CAHRIM interrupted through fallback solution.")
                break

    except KeyboardInterrupt:

        logger.info("CAHRIM interrupted by user. Shutting down all running threads... Please wait a few seconds.")

    ## Stop all threads

    for t in reversed(threads):
        t.stop()
        time.sleep(1)

    unloadImg(session)
    stopPepper(session)

    sock.close()



if __name__ == '__main__':

    init(autoreset=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("node", type=str, help="Set the starting position node of the robot")
    parser.add_argument("--group", "-g", required=True, type=str, help="CARESSES experiments group [experimental, control]")
    parser.add_argument("--loglevel", "-l", type=str, default="info",
                        help="Set the logging level to one of these values: notset, debug, info [default], warning, error, critical")
    parser.add_argument("--useFaceReco", "-u", action='store_true',
                        help="Use face recognition instead of 'ALPeoplePerception' for detecting the presence of the user")
    parser.add_argument("--asr", "-a", required=True, type=str, help="Noise level [noisy, normal]")
    args = parser.parse_args()

    successful = loadMap()
    if not successful:
        sys.exit()

    assert args.group in ["experimental", "control"], "'group' parameter can either be 'experimental' or 'control'"

    assert args.asr in ["noisy", "normal"], "'asr' parameter can either be 'noisy' or 'normal'"

    main(args.node, args.group, args.asr, args.loglevel, args.useFaceReco)

    deinit()

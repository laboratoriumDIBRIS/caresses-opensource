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
from random import randint

from action import Action
from set_node import SetNode
from aux_files.go_to.graphnavigation import *
from CahrimThreads.sensory_hub import OdomConverter
import caressestools.caressestools as caressestools
import caressestools.speech as speech
from caressestools.caressestools import MEMORY_CHARGER, MEMORY_FIXED_POSE

# MAX_NODES_DISTANCE = 2.9
CHARGER = "charger"

DRAW = False

ERROR = [
    "No information about the goal! Exiting...",
    "Invalid goal name! Exiting...",
    "Something went wrong!"
]
WARNING = [
    "No last pose has been stored! Launching setNode.py..."
]

## Action "Go To No Goal".
#
#  Pepper goes to a specified node of the map. The goal for the Accept Request or React To Sound actions is not sent.
class GoToNoGoal(Action):


    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Name of graph file, goal; separated by a white space.
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param output_handler () Handler of the output socket messages.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, output_handler, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.graph = self.apar[0]
        self.goal_id = self.apar[1]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        self.location_params = self.loadParameters("locations.json")
        suggested_location_IDs = [option.replace('"', '') for option in self.suggestions]
        self.location_IDs = self.mergeAndSortIDs(self.location_params, suggested_location_IDs)
        self.location_options = self.getAllParametersAttributes(self.location_params, self.location_IDs, "full")

        # Initialize NAOqi services
        self.sMemory       = session.service("ALMemory")
        self.sMotion       = session.service("ALMotion")
        self.sNavigation   = session.service("ALNavigation")
        self.sLocalization = session.service("ALLocalization")
        self.sPosture      = session.service("ALRobotPosture")
        self.sRecharge     = session.service("ALRecharge")

        self.running = True
        self.r0_wf = None
        self.r0_mf = None

        self.enough_attempts = 4
        self.closest_reached_threshold = 0.4
        self.node_reached_threshold = 0.4
        self.goal_reached_threshold = 0.2

        try:
            self.onCharger = self.sMemory.getData(MEMORY_CHARGER)
        except:
            self.onCharger = False

        self.graph_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "aux_files", "go_to", self.graph)
        self.loadGraph(self.graph_file)

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

        self.sMotion.setOrthogonalSecurityDistance(0.02)
        self.sMotion.setTangentialSecurityDistance(0.02)

        self.output_handler = output_handler
        self.asr = asr

    ## Loads the graph file passed as parameter.
    #  @param graph_file Path to the graph file.
    def loadGraph(self, graph_file):

        self.file = GraphFile()
        self.file.loadFile(graph_file, draw=DRAW)
        self.k = self.file.k

        self.plot_elements = {
            "start": {
                "point": None,
                "direction": None
            },
            "current-goal": {
                "point": None
            },
            "pose-estimated": {
                "point": None,
                "direction": None,
                "label": None
            },
            "pose-detected": {
                "point": None,
                "direction": None,
                "label": None
            },
            "nodes": {}
        }

    ## Method executed when the thread is started.
    def run(self):

        # # Get destination node through dialogue

        if not self.isAvailable(self.goal_id):
            self.goal_full = self.sp.dialog(self.__class__.__name__, self.location_options, sentence="0", checkValidity=True, askForConfirmation=True, sayFinalReply=False, noisy=self.asr)
            self.goal_id = self.getIDFromAttribute(self.location_params, "full", self.goal_full)

            if self.goal_id == "charger":
                bye_sentences = [s.encode('utf-8') for s in self.sp.script["Chitchat"]["goodbye"][self.language]]
                self.sp.say(bye_sentences[randint(0, len(bye_sentences) - 1)], speech.TAGS[1])
            else:
                self.sp.monolog(self.__class__.__name__, "with-keyword", param={"$KEYWORD$": self.goal_full},
                                group="parameter-answer", tag=speech.TAGS[1])
        else:
            self.goal_full = self.getAttributeFromID(self.location_params, self.goal_id, "full")

            if self.goal_id == "charger":
                bye_sentences = [s.encode('utf-8') for s in self.sp.script["Chitchat"]["goodbye"][self.language]]
                self.sp.say(bye_sentences[randint(0, len(bye_sentences) - 1)], speech.TAGS[1])

        self.final_goal = findNodeFromLabel(self.goal_full)

        if self.final_goal is None:
            self.logger.error(ERROR[1])
            self.sp.monolog(self.__class__.__name__, "2", tag=speech.TAGS[1])
            raise Exception, "Invalid goal"

        # # Initialize motion

        caressestools.setAutonomousAbilities(self.session, False, False, False, False, False)

        self.sRecharge.stopAll()
        self.sPosture.goToPosture("Stand", 0.5)
        self.sMotion.moveInit()

        self.pose = OdomConverter.getRobotInMap()
        self.pose = Pose(self.pose[0] / self.k, self.pose[1] / self.k, self.pose[2])

        # # Leave the docking station if on top of it

        if self.onCharger:

            off = caressestools.getOffTheDockingStation(self.session)

            if off == False:
                self.logger.error(ERROR[2])
                self.end()
                return
            else:
                self.onCharger = False
                self.pose = OdomConverter.getRobotInMap()
                self.pose = Pose(self.pose[0] / self.k, self.pose[1] / self.k, self.pose[2])

        self.logger.info("Detected pose: (%g, %g, %g)" % (round(self.pose.x, 3), round(self.pose.y, 3), round(math.degrees(self.pose.th), 3)))

        goal_reached = False
        closest = 0
        attempts = 0

        while not goal_reached and not self.is_stopped:

            ## First reach the closest node if too far

            reachable_nodes = Graph.nodes[:]
            try:
                reachable_nodes.remove(findNodeFromLabel(CHARGER))
            except:
                pass
            closest_nodes = sortNodesFromClosestToFurthest(self.pose, reachable_nodes)

            g_mf = Pose(closest_nodes[closest].x, closest_nodes[closest].y, closest_nodes[closest].th)
            dist = numpy.linalg.norm(self.pose.toVector()[0:2] - g_mf.toVector()[0:2]) * self.k

            if dist > self.closest_reached_threshold:

                self.logger.info("Heading towards closest node in the graph: " + closest_nodes[closest].getLabel())
                goal_reached, dist= self.navigateToNode(closest_nodes[closest], self.closest_reached_threshold)

                if not goal_reached:
                    self.logger.info("Node not reached.")
                    closest += 1 if closest < len(closest_nodes) - 1 else len(closest_nodes) -1
                    continue

            if closest_nodes[0].getLabel() == self.final_goal.getLabel():
                goal_reached = True

            ## Then navigate using A* algorithm

            path = self.computePath(closest_nodes[closest], self.final_goal)

            for index, path_node in enumerate(path[1:]):

                if self.is_stopped:
                    break

                self.logger.info("Heading towards next node in the path: " + path_node.getLabel())

                if path_node.getLabel() == CHARGER and caressestools.Settings.docking_station == True:

                    docked = caressestools.goToDockingStation(self.session)

                    if not docked:
                        self.logger.info("Lost!")
                        self.askToBeHelped()
                        break
                    else:
                        goal_reached = True
                        self.sMemory.insertData(MEMORY_FIXED_POSE, [path_node.x * self.k, path_node.y * self.k,
                                                                    math.radians(path_node.th)])

                else:
                    if index == len(path) - 1:
                        goal_reached, dist = self.navigateToNode(path_node, self.goal_reached_threshold)
                    else:
                        goal_reached, dist = self.navigateToNode(path_node, self.node_reached_threshold)

                if not goal_reached:
                    attempts += 1
                    self.logger.info("Node not reached.")
                    if attempts == self.enough_attempts:
                        self.sp.monolog(self.__class__.__name__, "0", tag=speech.TAGS[1])
                        self.askToBeHelped()
                        attempts = 0
                    break

                self.logger.info("Node reached.")

            closest = 0

        if not self.final_goal.getLabel() == CHARGER:
            self.assumeNodeOrientation(self.final_goal.th)

        self.end()

    ## Returns the path to follow as array of nodes.
    #  @param start Initial node.
    #  @param end Final node.
    def computePath(self, start, end):

        came_from, cost_so_far = a_star_search(start, end)
        path_to_final_goal = reconstruct_path(came_from, start, end)

        path_as_string = ""
        for index, x in enumerate(path_to_final_goal):
            path_as_string += x.getLabel()
            if not index == len(path_to_final_goal) - 1:
                path_as_string += " - "

        self.logger.info("Path to final goal: %s" % path_as_string)

        return path_to_final_goal

    ## Move Pepper to the given node.
    #  @param node Destination node.
    #  @param threshold Threshold in meters to determine whether the node was reached or not.
    def navigateToNode(self, node, threshold):

        g_mf = Pose(node.x, node.y, node.th)
        g_rf = g_mf.inFrame(self.pose)

        arrived = self.sNavigation.navigateTo(g_rf.x * self.k, g_rf.y * self.k)

        self.pose = OdomConverter.getRobotInMap()
        self.pose = Pose(self.pose[0] / self.k, self.pose[1] / self.k, self.pose[2])

        dist = numpy.linalg.norm(self.pose.toVector()[0:2] - g_mf.toVector()[0:2]) * self.k
        arrived = True if dist < threshold else False

        start = time.time()
        while not arrived and not self.is_stopped:
            g_rf = g_mf.inFrame(self.pose)
            angle = math.atan2(g_rf.y * self.k, g_rf.x * self.k) #radians
            x_dist = g_rf.x * self.k / math.cos(angle)
            self.sMotion.moveTo(0.0, 0.0, angle)
            arrived = self.sMotion.moveTo(x_dist, 0.0, 0.0, 15)
            self.pose = OdomConverter.getRobotInMap()
            self.pose = Pose(self.pose[0] / self.k, self.pose[1] / self.k, self.pose[2])
            dist = numpy.linalg.norm(self.pose.toVector()[0:2] - g_mf.toVector()[0:2]) * self.k
            arrived = True if dist < threshold else False
            if time.time() - start > 15:
                if arrived is False:
                    break

        return arrived, dist

    ## Rotate Pepper to assume the orientation of a node.
    #  @param node_theta Orientation of the node in degrees.
    def assumeNodeOrientation(self, node_theta):
        robot_theta = OdomConverter.getRobotInMap()[2]
        if robot_theta < 0.0:
            robot_theta = 2 * math.pi + robot_theta
        if node_theta < 0.0:
            node_theta = 360.0 + node_theta
        node_theta = math.radians(node_theta)
        angle = float(node_theta - robot_theta)

        if abs(angle) > math.pi:
            angle = float(angle - 2 * math.pi * math.copysign(1.0, angle))

        self.sMotion.moveTo(0.0, 0.0, angle)

    ## Pepper asks for help to the user and launches the action "Set Node".
    def askToBeHelped(self):

        self.file.unloadCurrentWork(draw=DRAW)

        setnode_apar = self.graph
        setnode_cpar = "%s %s %s %s %s" % (str(self.volume), str(self.speed), str(self.pitch), self.language, self.username)

        sn = SetNode(setnode_apar, setnode_cpar, self.session)
        sn.run()

        self.loadGraph(self.graph_file)
        self.final_goal = findNodeFromLabel(self.final_goal.getLabel())

        self.pose = OdomConverter.getRobotInMap()
        self.pose = Pose(self.pose[0] / self.k, self.pose[1] / self.k, self.pose[2])

    ## Method containing all the instructions that should be executing before terminating the action.
    def end(self):
        self.sRecharge.stopAll()
        self.sMotion.stopMove()
        caressestools.setAutonomousAbilities(self.session, False, True, True, True, True)
        self.sMotion.setOrthogonalSecurityDistance(0.4)
        self.sMotion.setTangentialSecurityDistance(0.10)
        self.file.unloadCurrentWork(draw=DRAW)
        if not self.is_stopped:
            self.logger.info("Final goal reached!")


if __name__ == "__main__":

    import argparse
    import qi
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default=caressestools.Settings.robotIP,
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    parser.add_argument("--goal", type=str,
                        default="n/a",
                        help="Goal node in the graph")

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
    caressestools.startPepper(session, caressestools.Settings.interactionNode)

    apar = 'map.json "n/a"'
    cpar = "1.0 100 1.1 english John wardrobe&&drawer&&window"

    n = GoToNoGoal(apar, cpar, session, None, "normal")

    try:
        n.run()
    except speech.StopInteraction as e:
        print e
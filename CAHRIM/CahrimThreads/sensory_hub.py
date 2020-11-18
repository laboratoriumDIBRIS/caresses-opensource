# -*- coding: utf-8 -*-
'''
Copyright October 2019 Roberto Menicatti & Università degli Studi di Genova & Bui Ha Duong

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

Author:      Roberto Menicatti (1), Bui Ha Duong (2)
Email:       (1) roberto.menicatti@dibris.unige.it (2) bhduong@jaist.ac.jp
Affiliation: (1) Laboratorium, DIBRIS, University of Genova, Italy
             (2) Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan
Project:     CARESSES (http://caressesrobot.org/en/)
'''

from threading import Thread
# from OpenVokaturi.VocalEmotionEstimatorEngine import VocalEmotionEstimatorEngine
import time
import numpy
import math
import os
import json
import logging
import cv2

from ActionsLib.aux_files.go_to.graphnavigation import *
import ActionsLib.caressestools.caressestools as caressestools


log_dbo = logging.getLogger('CAHRIM.SensoryHub.DBObserver')
log_oc = logging.getLogger('CAHRIM.SensoryHub.OdomConverter')
log_es = logging.getLogger('CAHRIM.SensoryHub.ESModule')
log_dud = logging.getLogger('CAHRIM.SensoryHub.DetectUserDepth')
log_eue = logging.getLogger('CAHRIM.SensoryHub.EstimateUserEmotion')

class DBObserver(Thread):

    def __init__(self, output_handler):
        Thread.__init__(self)
        self.id = "Sensory Hub - DB Observer"
        self.alive = True
        self.output_handler = output_handler # Output handler for sending messages

    def run(self):
        while self.alive:
            pass
            # TODO do something
            # self.output_handler.writeSupplyMessage("publish", "D6.2", msg_content)

        log_dbo.info("%s terminated correctly." % self.id)

    def stop(self):
        self.alive = False


## Convert Pepper odometry coordinates to map coordinates
class OdomConverter(Thread):

    radius = 0.7

    DATA = "CARESSES_fixedPose"
    POSE = "CARESSES_pose"

    r0_wf = None
    r0_mf = None
    current_node = "n/a"

    graph =None

    def __init__(self, session, startingNode):
        Thread.__init__(self)
        self.id = "Sensory Hub - Odom Converter"
        self.alive = True

        self.sMotion = session.service("ALMotion")
        self.sMemory = session.service("ALMemory")

        folder = "ActionsLib"
        subfolder = "aux_files"
        subsubfolder = "go_to"
        map = "map.json"
        graph_file = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), folder, subfolder, subsubfolder, map)
        with open(graph_file) as f:
            OdomConverter.graph = json.load(f)

        OdomConverter.r0_wf = self.sMotion.getRobotPosition(True)  # robot in Pepper's world-frame (frame in which it wakes up)

        ## Load map.json as graph and set starting node
        f = GraphFile()
        f.loadFile(graph_file, draw=False)
        scale_factor = float(OdomConverter.graph["scale-factor"])
        starting_node = findNodeFromLabel(startingNode)
        if starting_node is None:
            log_oc.error("Starting node '%s' does not exist in the map." % startingNode)
            f.unloadCurrentWork(draw=False)
            raise Exception, "Invalid starting node."
        else:
            OdomConverter.r0_mf = [starting_node.x * scale_factor, starting_node.y * scale_factor, math.radians(starting_node.th)] # robot in map-frame
            log_oc.info("Starting pose at node: %s" % startingNode)
            f.unloadCurrentWork(draw=False)

    def run(self):

        while self.alive:
            time.sleep(0.5)
            try:
                OdomConverter.r_wf = self.sMotion.getRobotPosition(False)

                OdomConverter.r_r0f = OdomConverter.toFrame(OdomConverter.r_wf, OdomConverter.r0_wf)
                OdomConverter.m_r0f = OdomConverter.toFrame([0, 0, 0], OdomConverter.r0_mf)
                OdomConverter.r_mf = OdomConverter.toFrame(OdomConverter.r_r0f, OdomConverter.m_r0f)

                OdomConverter.r0_wf = OdomConverter.r_wf
                try:
                    OdomConverter.r0_mf = self.sMemory.getData(OdomConverter.DATA)
                    self.sMemory.removeData(OdomConverter.DATA)
                except:
                    OdomConverter.r0_mf = OdomConverter.r_mf
                    pose = [float(x) for x in OdomConverter.r0_mf]
                    self.sMemory.insertData(OdomConverter.POSE, pose)

                    OdomConverter.current_node = OdomConverter.getClosebyNode(pose[0], pose[1])
            except:
                pass

        log_oc.info("%s terminated correctly." % self.id)

    @staticmethod
    def getRobotInMap():
        return OdomConverter.r0_mf

    @staticmethod
    def getCurrentNode():
        return OdomConverter.current_node

    @staticmethod
    def toFrame(pose, frame):
        pose = numpy.array([pose[0], pose[1], pose[2]])
        frame = numpy.array([frame[0], frame[1], frame[2]])

        rot_matrix = numpy.array([(math.cos(frame[2]), math.sin(frame[2]), 0),
                                  (-math.sin(frame[2]), math.cos(frame[2]), 0),
                                  (0, 0, 1)])

        transposed_vector = rot_matrix.dot(pose - frame)

        return [transposed_vector[0], transposed_vector[1], transposed_vector[2]]

    @staticmethod
    def getClosebyNode(x, y):

        closest = []

        for n in OdomConverter.graph["nodes"]:
            x0 = OdomConverter.graph["nodes"][n.encode('utf-8')]["coordinates"][0] * OdomConverter.graph["scale-factor"]
            y0 = OdomConverter.graph["nodes"][n.encode('utf-8')]["coordinates"][1] * OdomConverter.graph["scale-factor"]
            if OdomConverter.isInCircle(x, y, x0, y0, OdomConverter.radius):
                dist = numpy.linalg.norm(numpy.array([x, y]) - numpy.array([x0, y0]))
                label = OdomConverter.graph["nodes"][n.encode('utf-8')]["label"].encode('utf-8')
                closest.append([label, dist])

        if len(closest) is not 0:
            ordered_nodes = sorted(closest, key=lambda x: x[1])
            return ordered_nodes[0][0]
        else:
            return "n/a"

    @staticmethod
    def isInCircle(x, y, x0, y0, radius):
        return ((x - x0) ** 2 + (y - y0) ** 2) < radius ** 2

    def stop(self):
        self.alive = False


class ESModule():

    @staticmethod
    def handle(msg):
        pass


## Compute distance between Pepper and the user
class DetectUserDepth(Thread):

    user_position = [0, 0, 0]
    user_id = None
    timeout = 20

    useFaceReco = False
    userApproached=False

    def __init__(self, session, output_handler, useFaceReco):
        Thread.__init__(self)

        self.id = "Sensory Hub - User Detection Depth"
        self.alive = True

        self.output_handler = output_handler
        self.useFaceReco = useFaceReco
        DetectUserDepth.useFaceReco = useFaceReco

        self.people_perception = session.service("ALPeoplePerception")
        self.sFaceDet = session.service("ALFaceDetection")
        self.sMemory = session.service("ALMemory")
        self.sSpeech = session.service("ALTextToSpeech")

        self.people_perception.setMaximumDetectionRange(3.5)
        self.people_perception.setTimeBeforePersonDisappears(DetectUserDepth.timeout)
        self.people_perception.setTimeBeforeVisiblePersonDisappears(DetectUserDepth.timeout)
        self.people_perception.setFastModeEnabled(False)

        self.subscriber = self.sMemory.subscriber("PeoplePerception/PeopleDetected")
        self.subscriber_a = self.sMemory.subscriber("PeoplePerception/JustArrived")
        self.subscriber_l = self.sMemory.subscriber("PeoplePerception/JustLeft")
        self.subscriber_list = self.sMemory.subscriber("PeoplePerception/PeopleList")

        self.perceived_people_list = []

        # self.subscriber.signal.connect(self.on_human_detected)
        self.subscriber_a.signal.connect(self.on_human_arrived)
        self.subscriber_l.signal.connect(self.on_human_left)
        self.subscriber_list.signal.connect(self.on_people_list_updated)

        if self.useFaceReco:
            self.subscriber_f = self.sMemory.subscriber("FaceDetected")
            self.subscriber_f.signal.connect(self.on_face_detected)
            self.sFaceDet.subscribe("DetectUserDepth")
            self.sFaceDet.setRecognitionConfidenceThreshold(0.7)

            self.perceived_people_list = []
            self.detected_faces = []

            self._loadKnownPeopleList()

    # def on_human_detected(self, value):
    #     userID = value[1][0][0]
    #     try:
    #         DetectUserDepth.user_position = self.sMemory.getData("PeoplePerception/Person/"+str(userID)+"/PositionInTorsoFrame")
    #     except Exception as e:
    #         time.sleep(1)

    def on_human_arrived(self, value):
        if not self.useFaceReco:
            self.notifyIfUserIsFar(False)

    def on_human_left(self, value):
        if not self.useFaceReco:
            self.notifyIfUserIsFar(True)

    def on_people_list_updated(self, people_list):
        self.perceived_people_list = people_list

    def on_face_detected(self, value):
        if (len(value) > 0):
            if len(value[1]) > 0:
                self.detected_faces = value[1][:-1]
                for person in Person.list:
                    for index, face in enumerate(value[1][:-1]):
                        face_label = value[1][index][1][2]
                        if face_label == person.naoqi_face_label:
                            person.face_recognized = True
                            person.not_visible_since = time.time()
                            if not person.is_present:
                                person.is_present = True
                                if person.is_user:
                                    self.notifyIfUserIsFar(False)
                            break
                        else:
                            person.face_recognized = False
        else:
            self.detected_faces = []
            for person in Person.list:
                person.face_recognized = False

    def run(self):
        while(self.alive):
            time.sleep(0.5)
            if len(self.perceived_people_list) >= 1:
                if not self.perceived_people_list[0] == DetectUserDepth.user_id:
                    DetectUserDepth.user_id = self.perceived_people_list[0] ## We assume that the first person detected is the user. If someone else joins the user, he's added to the list, so he's not at index 0.
            if not len(self.sMemory.getDataList(str(DetectUserDepth.user_id))) == 0:
                try:
                    DetectUserDepth.user_position = self.sMemory.getData("PeoplePerception/Person/" + str(DetectUserDepth.user_id) + "/PositionInTorsoFrame")
                except:
                    DetectUserDepth.user_position = [None, None, None]
            else:
                DetectUserDepth.user_position = [None, None, None]

            if self.useFaceReco:
                for p in Person.list:
                    ## Uncomment the following line for debug
                    # print p
                    if p.is_present:
                        if time.time() - p.not_visible_since > DetectUserDepth.timeout:
                            p.is_present = False
                            if p.is_user:
                                self.notifyIfUserIsFar(True)
                ## Uncomment the following three lines for debug
                # self.printPersonSituation()
                # print "======================================"
                # time.sleep(1)

        log_dud.info("%s terminated correctly." % self.id)

    def printPersonSituation(self):
        print("----------------------------")
        print "People detected: " + str(len(self.perceived_people_list))
        print "Faces detected: " + str(len(self.detected_faces))
        known_present_names = []
        for p in Person.getPresentKnownPersons():
            known_present_names.append(p.name)
        print "Known people: " + str(len(Person.getPresentKnownPersons()))
        print known_present_names
        if len(self.perceived_people_list) >= len(Person.getPresentKnownPersons()):
            unknown = len(self.perceived_people_list) - len(Person.getPresentKnownPersons())
        else:
            unknown = 0
        print "Unknown people: " + str(unknown)

    @staticmethod
    def isUserApproached():
        if caressestools.Settings.interactionNode == "":
            #return DetectUserDepth.userApproached
            return True
        else:
            return True

    def notifyIfUserIsFar(self, is_user_far):
        DetectUserDepth.userApproached=not is_user_far
        approached = str(not is_user_far).lower()
        message_D6_1 = "[approached-user:%s]" % approached
        #self.output_handler.writeSupplyMessage("publish", "D6.1", message_D6_1)
        log_dud.debug("Sending to CSPEM the state: %s" % message_D6_1)


    def _loadKnownPeopleList(self):
        directory = os.path.dirname(os.path.dirname(__file__))
        file_path = os.path.join(directory, "knownPeopleList.json")
        try:
            with open(file_path) as known_people_file:
                known_people_dict = json.load(known_people_file)
            for p_id in known_people_dict.keys():
                p = known_people_dict[p_id]
                Person(p["name"].encode('utf-8'), p["family-name"].encode('utf-8'), p_id, p["naoqi-face-label"].encode('utf-8'))
        except Exception as e:
            print e
            log_dud.error("File 'knownPeopleList.json' not found at %s" % file_path + ". Ignoring face recognition.")

    @staticmethod
    def getUserPosition():
        user_pos = DetectUserDepth.user_position
        DetectUserDepth.user_position = [0, 0, 0]
        return user_pos

    @staticmethod
    def isUsingFaceRecognition():
        return DetectUserDepth.useFaceReco

    def stop(self):
        if self.useFaceReco:
            self.sFaceDet.unsubscribe("DetectUserDepth")
        self.alive = False


## Define a Person object to keep track of recognized face in the environment
class Person():

    list = []

    def __str__(self):
        pars = self.name, str(self.face_recognized) + ",", str(self.is_present) + ",", str(time.time() - self.not_visible_since)
        p_str = '{0:{width0}} - Face recognized: {1:{width1_2}} Present: {2:{width1_2}} Not seen for {3:{width3}} s.'.format(*pars, width0=10, width1_2=6, width3=15)
        return p_str

    def __init__(self, name, family_name, id, face_label):
        self.name = name
        self.family_name = family_name
        self.id = id
        self.naoqi_face_label = face_label
        self.people_perception_id = None
        self.face_recognized = False
        self.not_visible_since = time.time()

        self.is_present = False
        self.is_user = self.naoqi_face_label == "user"

        Person.list.append(self)

    @staticmethod
    def getPresentKnownPersons():
        present_known_list = []
        for p in Person.list:
            if p.is_present == True:
                present_known_list.append(p)

        return present_known_list

    @staticmethod
    def isUserPresent():
        known_people_present = Person.getPresentKnownPersons()
        for p in known_people_present:
            if p.is_user:
                return True
        return False

# class VocalEmotionEstimator(Thread):
#
#     engine = VocalEmotionEstimatorEngine()
#
#     def __init__(self, session):
#         Thread.__init__(self)
#         self.session = session
#         self.alive = True
#
#     def run(self):
#         self.service_id = self.session.registerService("VocalEmotionEstimator", self.engine)
#         self.audio_device = self.session.service('ALAudioDevice')
#         # ALL_Channels: 0
#         # AL::LEFTCHANNEL: 1
#         # AL::RIGHTCHANNEL: 2
#         # AL::FRONTCHANNEL: 3
#         # AL::REARCHANNEL: 4.
#         self.audio_device.setClientPreferences('VocalEmotionEstimator', VocalEmotionEstimatorEngine.RATE, 3, 0)
#         self.audio_device.subscribe('VocalEmotionEstimator')
#         while self.alive:
#             pass
#
#     @staticmethod
#     def getVoiceEmotion():
#         return VocalEmotionEstimator.engine.emotion
#
#     def stop(self):
#         self.audio_device.unsubscribe('VocalEmotionEstimator')
#         self.session.unregisterService(self.service_id)
#         self.alive = False

class EstimateUserEmotion(Thread):
    def __init__(self, session, output_handler):
        Thread.__init__(self)

        self.id = "Sensory Hub - Estimate User Emotion"
        self.output_handler = output_handler
        self.alive = True
        self.got_face = False
        self.faceC = session.service("ALFaceCharacteristics")
        self.emotion_labels = numpy.array(['neutral', 'happy', 'surprised', 'angry', 'sad'])
        self.sMemory = session.service("ALMemory")
        self.subscriber_f = self.sMemory.subscriber("FaceDetected")
        self.subscriber_f.signal.connect(self.on_face_detected)
        self.sFaceDet = session.service("ALFaceDetection")
        self.sFaceDet.subscribe("HumanGreeter")
        self.kepp_runing = True
        EstimateUserEmotion.user_emotion = [None, None, None]

    def on_face_detected(self, value):
        """
        Callback for event FaceDetected.
        """
        if  (value) and (not self.got_face):  
            self.got_face = True 
            self.getExpression()
            self.got_face = False

    def run(self):
        """
        Loop on, wait for events until manual interruption.
        """
        while self.alive:
            time.sleep(0.5)
        log_eue.info("%s terminated correctly." % self.id)

    def getExpression(self):
        ids_info = []
        ids = self.sMemory.getData("PeoplePerception/VisiblePeopleList")
        if ids:
            if (ids > 1):
                id = ids[0] # If more than one user available, using the infomation of the first user
            else:
                id = ids
            self.faceC.analyzeFaceCharacteristics(id)
            time.sleep(0.5)
            try:
                expression = self.sMemory.getData("PeoplePerception/Person/"+str(id)+"/ExpressionProperties")
                if (len(expression)>0):
                    emotion_data = numpy.array([expression[0], expression[1], expression[2], expression[3], expression[4]])
                    estimated_emotion = self.emotion_labels[numpy.argmax(emotion_data)]
                    confident_value =  numpy.max(emotion_data)
                    EstimateUserEmotion.user_emotion = [id, estimated_emotion, confident_value]
            except:
                EstimateUserEmotion.user_emotion = [None, None, None]

    def stop(self):
        self.sFaceDet.unsubscribe("HumanGreeter")
        self.alive = False

    @staticmethod
    def getUserEmotion():
        user_emo = EstimateUserEmotion.user_emotion
        return user_emo
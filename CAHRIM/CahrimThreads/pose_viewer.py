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

import os
import turtle
import json
import math

# import ActionsLib.caressestools.caressestools as caressestools

## Plot Pepper position
class MovementViewer():

    POSE = "CARESSES_pose"

    def __init__(self, K, session):

        self.K = K
        self.sMemory = session.service("ALMemory")

        folder = "ActionsLib"
        subfolder = "aux_files"
        subsubfolder = "go_to"
        map = "map.json"
        file = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), folder, subfolder, subsubfolder, map)
        with open(file) as f:
            graph = json.load(f)

        self.sc = turtle.Screen()  # creates a graphics window

        x_min, x_max, y_min, y_max = self.computeMapExtremes(graph)
        self.width, self.height = self.computeWindowSize(x_min, x_max, y_min, y_max)

        self.sc.setup(int(self.width), int(self.height), 0, 0)
        self.robot = turtle.Turtle()
        self.robot.up()

        self.drawMap(graph)

        self.robot.color('green')
        self.robot.shape('classic')

        try:
            self.pose = self.sMemory.getData(MovementViewer.POSE)
        except:
            sys.exit()


        self.robot.goto(self.K * self.pose[0], self.K * self.pose[1])
        # self.robot.down()

    # def move(self, x, y, theta):
    #     self.robot.settiltangle(math.degrees(theta))
    #     self.robot.goto(self.K * x, self.K * y)

    def run(self):
        try:
            self.pose = self.sMemory.getData(MovementViewer.POSE)
        except:
            pass
        self.robot.settiltangle(math.degrees(self.pose[2]))
        self.robot.goto(self.K * self.pose[0], self.K * self.pose[1])

    def computeMapExtremes(self, graph):
        scale_factor = graph["scale-factor"]
        all_x = []
        all_y = []
        for n in graph["nodes"]:
            all_x.append(graph["nodes"][n.encode('utf-8')]["coordinates"][0])
            all_y.append(graph["nodes"][n.encode('utf-8')]["coordinates"][1])

        return min(all_x) * scale_factor, max(all_x) * scale_factor, min(all_y) * scale_factor, max(all_y) * scale_factor

    def computeWindowSize(self, min_x, max_x, min_y, max_y):
        width = max(abs(min_x), abs(max_x)) * 2
        height = max(abs(min_y), abs(max_y)) * 2
        width = (width * 1.2 ) * self.K
        height = (height * 1.2) * self.K
        return width, height

    def drawMap(self, graph):

        r = 10
        scale_factor = graph["scale-factor"]

        self.robot.hideturtle()
        for n in graph["nodes"]:
            x = graph["nodes"][n.encode('utf-8')]["coordinates"][0]
            y = graph["nodes"][n.encode('utf-8')]["coordinates"][1]
            label = graph["nodes"][n.encode('utf-8')]["label"].encode('utf-8')
            x = self.K * x * scale_factor
            y = self.K * y * scale_factor
            self.robot.goto(x, y)
            self.robot.dot(r)
            self.robot.write(label, move=False, align="center", font=("Helvetica", 10, "normal"))
        self.robot.showturtle()

    def kill(self):
        self.sc.bye()

if __name__ == '__main__':

    import argparse
    import qi
    import sys

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


    mv = MovementViewer(150, session)
    try:
        while True:
            mv.run()
    except KeyboardInterrupt:
        mv.kill()
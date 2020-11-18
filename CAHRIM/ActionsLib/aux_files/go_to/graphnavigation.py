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

import heapq
import math
import numpy
import os
import json
import tkFileDialog, tkMessageBox

from threading import Thread
from matplotlib.patches import Rectangle


FONTSIZE = 10
MAX_NODES = 4 ## ==> 10^(MAX_NODES) nodes
MAX_EDGES = 2 * MAX_NODES
MAX_OBST = MAX_NODES


########################################################################################################################
# GRAPH CLASSES AND FUNCTIONS
########################################################################################################################


class Element():

    def __init__(self):
        ## Element properties
        self.type = None
        self._id = None
        self._label = None
        ## Matplotlib properties
        self.matplotlib_element = None
        self.matplotlib_subelement = None
        self.matplotlib_label = None
        self.axes = None
        self.canvas = None

        self.setID()

    def setLabel(self, label, addGraphLabel=False):
        self._label = label

    def setID(self, ID=None):
        pass

    def getID(self):
        return self._id

    def getLabel(self):
        return self._label


class Node(Element):

    def __str__(self):
        pars = self.type, self.x, self.y, self._id, self._label
        fmt = "%s at (%g, %g), ID: %s, Label: %s"
        return fmt % pars

    def __init__(self, x, y):
        Element.__init__(self)

        self.type = "Node"
        self.x = float(x if not Mode.snap_to_grid else round(x))
        self.y = float(y if not Mode.snap_to_grid else round(y))
        self.th = 0.0 # degrees
        self.neighbors = []

        Graph.nodes.append(self)

    def setID(self, ID=None):
        if ID == None:
            ## The ID of the node simply is its index in the nodes array
            self._id = "node_" + str(getHighestIndex(Graph.nodes) + 1).zfill(MAX_NODES)
        else:
            self._id = ID
        ## The label is initially assigned equal to the ID
        self.setLabel(self._id)

    def setLabel(self, label, drawNow=False, addGraphLabel=False):
        self._label = label

        if addGraphLabel:
            if self.matplotlib_label == None:
                self.matplotlib_label = self.axes.text(self.x, self.y + 0.5, label,
                                                       color='black', fontsize=FONTSIZE,
                                                       bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': 0.9,
                                                             'pad': 0.2},
                                                       zorder=2)
            else:
                self.matplotlib_label.set_text(label)

            if drawNow: self.canvas.draw()

    def addDrawing(self, axes, canvas, drawNow=False):
        self.axes = axes
        self.canvas = canvas
        self.matplotlib_element = \
        self.axes.plot(self.x, self.y, color='black', marker='o', markersize=8, zorder=2, picker=5)[0]
        self.matplotlib_subelement= self.axes.arrow(self.x, self.y,
                                        math.cos(math.radians(self.th)),
                                        math.sin(math.radians(self.th)),
                                        color="red",
                                        length_includes_head=True,
                                        head_width=0.2,
                                        head_length=0.2,
                                        zorder=4)
        if drawNow: self.canvas.draw()

    def delete(self, now=True):
        ## Delete graphic elements
        # - Label
        if not self.matplotlib_label == None:
            self.matplotlib_label.remove()
        # - Node
        if not self.matplotlib_element == None:
            self.matplotlib_element.remove()
        # - Orientation arrow
        if not self.matplotlib_subelement == None:
            self.matplotlib_subelement.remove()
        # - Edges
        to_delete = []
        for index, edge in enumerate(Graph.edges):
            if self._label in edge.getLabel().split("-"):
                if not edge.matplotlib_element == None:
                    edge.matplotlib_element.remove()
                to_delete.append(index)
        # Finally update the canvas
        if now: self.canvas.draw()

        ## Remove array elements
        # - Node
        Graph.nodes.remove(self)
        # - Node from neighbors
        for node in Graph.nodes:
            if self in node.neighbors:
                node.neighbors.remove(self)
        # - Edges
        Graph.edges[:] = [x for i, x in enumerate(Graph.edges) if not i in to_delete]


class Edge(Element):

    def __str__(self):
        pars = self.type, self.node_0.getLabel(), self.node_0.x, self.node_0.y, self.node_1.getLabel(), self.node_1.x, self.node_1.y, self._id, self.getLabel()
        fmt = "%s connecting node '%s' at (%g, %g) and node '%s' at (%g, %g), ID: %s, Label: %s"
        return fmt % pars

    def __init__(self, node_0, node_1):
        Element.__init__(self)

        self.type = "Edge"
        self.node_0 = node_0
        self.node_1 = node_1
        self.x_0 = self.node_0.x
        self.y_0 = self.node_0.y
        self.x_1 = self.node_1.x
        self.y_1 = self.node_1.y
        self.weight = 3

        self.node_0.neighbors.append(self.node_1)
        self.node_1.neighbors.append(self.node_0)

        ## The label is set equal to the couple of the connected nodes
        self.setLabel("%s-%s" % (self.node_0.getID(), self.node_1.getID()))

        Graph.edges.append(self)

    def setID(self, ID=None):
        if ID == None:
            ## The ID of the edge simply is its index in the edges array
            self._id = "edge_" + str(getHighestIndex(Graph.edges) + 1).zfill(MAX_EDGES)
        else:
            self._id = ID

    def getLabel(self):
        return "%s-%s" % (self.node_0.getLabel(), self.node_1.getLabel())

    def getOppositeDirectedEdge(self):
        return "%s-%s" % (self.getLabel().split("-")[1], self.getLabel().split("-")[0])

    def addDrawing(self, axes, canvas, drawNow=False):
        self.axes = axes
        self.canvas = canvas
        self.matplotlib_element = \
        self.axes.plot([self.x_0, self.x_1], [self.y_0, self.y_1], color='k', linestyle='-', linewidth=1, zorder=2)[0]
        if drawNow: self.canvas.draw()

    def delete(self, now=True):
        ## Delete graphic element
        if not self.matplotlib_element == None:
            self.matplotlib_element.remove()

        ## Update the canvas
        if now: self.canvas.draw()

        ## Remove neighborhood link
        self.node_0.neighbors.remove(self.node_1)
        self.node_1.neighbors.remove(self.node_0)

        ## Remove array elements
        Graph.edges.remove(self)


class Obstacle(Element):

    def __str__(self):
        pars = self.type, self.x_0, self.y_0, abs(self.x_1 - self.x_0), abs(self.y_1 - self.x_1), self._id, self._label
        fmt = "%s at (%g, %g) with width %g and height %g, ID: %s, Label: %s"
        return fmt % pars

    def __init__(self, x0, y0):
        Element.__init__(self)

        self.type = "Obstacle"
        self.x_0 = float(x0 if not Mode.snap_to_grid else round(x0))
        self.y_0 = float(y0 if not Mode.snap_to_grid else round(y0))
        self.x_1 = None
        self.y_1 = None

        self.drawing_started = False
        self.finalized = False

        self.rect = Rectangle((0, 0), 1, 1, zorder=2, picker=5)
        Graph.obstacles.append(self)

    def setID(self, ID=None):
        if ID == None:
            ## The ID of the obstacle simply is its index in the obstacles array
            self._id = "obst_" + str(getHighestIndex(Graph.obstacles) + 1).zfill(MAX_OBST)
        else:
            self._id = ID
        ## The label is initially assigned equal to the ID
        self.setLabel(self._id)

    def setLabel(self, label, drawNow=False, addGraphLabel=False):
        self._label = label

        if addGraphLabel:
            if self.matplotlib_label == None:
                x = self.x_0 + self.matplotlib_element.get_width() / 2
                y = self.y_0 + self.matplotlib_element.get_height() / 2
                self.matplotlib_label = self.axes.text(x, y, label,
                                                       color='black', fontsize=FONTSIZE,
                                                       bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': 0.9,
                                                             'pad': 0.2},
                                                       horizontalalignment='center',
                                                       verticalalignment='center',
                                                       zorder=2)
            else:
                self.matplotlib_label.set_text(label)

            if drawNow: self.canvas.draw()

    def addDrawing(self, axes, canvas, x1, y1, drawNow=False):
        self.axes = axes
        self.canvas = canvas
        if not self.drawing_started:
            self.axes.add_patch(self.rect)
            self.drawing_started = True
        if not self.finalized:
            x_1 = float(x1 if not Mode.snap_to_grid else round(x1))
            y_1 = float(y1 if not Mode.snap_to_grid else round(y1))
            self.rect.set_width(x_1 - self.x_0)
            self.rect.set_height(y_1 - self.y_0)
            self.rect.set_xy((self.x_0, self.y_0))
            if drawNow: self.canvas.draw()

    def finalizeDrawing(self, x1, y1):
        self.x_1 = self.rect.get_width() + self.x_0
        self.y_1 = self.rect.get_height() + self.y_0

        self.matplotlib_element = self.rect

    def delete(self, now=True):
        ## Delete graphic elements
        # - Label
        if not self.matplotlib_label == None:
            self.matplotlib_label.remove()
        # - Obstacle
        if not self.matplotlib_element == None:
            self.matplotlib_element.remove()
        # Finally update the canvas
        if now: self.canvas.draw()

        ## Remove array elements
        Graph.obstacles.remove(self)


class Graph():
    nodes = []
    edges = []
    obstacles = []


class MouseState(object):
    isPressed = False
    isReleased = False


class Temp():
    node_0 = None
    node_1 = None

    obstacle = None

    @staticmethod
    def reset():
        Temp.node_0 = None
        Temp.node_1 = None

        Temp.obstacle = None


def findEdgeFromLabel(label):
    for edge in Graph.edges:
        if edge.getLabel() == label:
            return edge
    return None


def findEdgeFromNodes(node0, node1):
    l0 = node0.getLabel()
    l1 = node1.getLabel()

    for edge in Graph.edges:
        if l0 in edge.getLabel():
            if l1 in edge.getLabel():
                return edge
    return None


def findNodeFromLabel(label):
    for node in Graph.nodes:
        if node.getLabel() == label:
            return node
    return None


def findNodeFromMatPoint(matplotlib_point):
    for node in Graph.nodes:
        if node.matplotlib_element == matplotlib_point:
            return node
    return None


def findObstFromLabel(label):
    for obst in Graph.obstacles:
        if obst.getLabel() == label:
            return obst
    return None


def findObstFromMatRect(matplotlib_rect):
    for obst in Graph.obstacles:
        if obst.matplotlib_element == matplotlib_rect:
            return obst
    return None


########################################################################################################################
# GRAPH-FILE and GUI CLASSES AND FUNCTIONS
########################################################################################################################


class Mode(Thread):

    alive = True
    snap_to_grid = True
    NODE = 0
    EDGE = 10
    OBST = 20
    PAN  = 30
    ZOOM = 40

    def __init__(self, toolbar, status):
        Thread.__init__(self)

        self.toolbar = toolbar
        self.status  = status
        self._mode = None

        self.statusbar_label = {
            0: "NODE MODE - Left-Click on the graph to draw a node, Right-Click to add label and orientation to a node, Center-Click to delete a node.",
            10: "EDGE MODE enabled - Click on the first node of the edge.",
            11: "EDGE MODE enabled - Click on the second node of the edge.",
            20: "OBST MODE enabled - Left-Click, move and release to draw an obstacle. Right-Click on an obstacle to label it. Center-Click on an obstacle to delete it.",
            30: "PAN MODE enabled",
            40: "ZOOM MODE enabled - Select the area with the Left button to zoom in and with the Right button to zoom out.",
            100: ""
        }

    def run(self):
        self.setMode(Mode.NODE)
        self.prevMode = self.toolbar._active

        while Mode.alive == True:

            if not self.toolbar._active == self.prevMode:
                self.prevMode = self.toolbar._active

                if self.toolbar._active == "PAN":
                    self.setMode(Mode.PAN)

                elif self.toolbar._active == "ZOOM":
                    self.setMode(Mode.ZOOM)

    def setMode(self, mode):
        self._mode = mode
        self.setStatusbarLabel(mode)

        if mode not in [Mode.PAN, Mode.ZOOM]:
            if self.toolbar._active == "PAN":
                self.toolbar.pan()

            elif self.toolbar._active == "ZOOM":
                self.toolbar.zoom()

        ## Forget coordinates of the first node of an edge, or of an obstacle initial coordinates
        ## if meanwhile the mode has changed
        Temp.reset()

    def getMode(self):
        return self._mode

    def setStatusbarLabel(self, mode):
        self.status.set(self.statusbar_label[mode])


class GraphFile():

    def __init__(self):

        self.scale_factor_var = None
        self.k = None
        self.filename = ""
        self.saved = True

    def setUpGraphics(self, axes, canvas):
        self.axes = axes
        self.canvas = canvas

    def saveAs(self):

        initialdir = os.path.dirname(os.path.realpath(__file__))

        self.filename = tkFileDialog.asksaveasfilename(initialdir=initialdir, title="Choose directory and file name", defaultextension=".json")

        if self.filename:
            with open(self.filename, "w") as f:
                json.dump(self.collectFileData(), f)
            self.saved = True

    def save(self):
        if self.filename == "":
            self.saveAs()
        else:
            with open(self.filename, "w") as f:
                json.dump(self.collectFileData(), f)
            self.saved = True

    def open(self):

        initialdir = os.path.dirname(os.path.realpath(__file__))

        if not self.saved:
            save_before_open = tkMessageBox.askyesno("Current work will be lost!", "Do you want to save your work before opening a new file?")

            if save_before_open:
                self.save()

        self.filename = tkFileDialog.askopenfilename(initialdir=initialdir, title="Open file", defaultextension=".json")

        if self.filename:
            self.unloadCurrentWork(draw=True)
            self.loadFile(self.filename, draw=True)
            self.scale_factor_var.set(str(self.k))


    def loadFile(self, filename, draw):
        ## Disable snap to grid while loading the file, otherwise float coordinates are converted to int
        Mode.snap_to_grid = False

        with open(filename, "r") as f:
            content = json.load(f)
        ## Retrieve scale factor
        self.k = float(content["scale-factor"])
        ## Draw nodes
        for node_ID in content["nodes"]:
            node = content["nodes"][node_ID]
            n = Node(node["coordinates"][0], node["coordinates"][1])
            n.th = float(node["coordinates"][2])
            n.setID(node_ID.encode('utf-8'))
            if draw: n.addDrawing(self.axes, self.canvas)
            if node_ID != node["label"]:
                n.setLabel(node["label"].encode('utf-8'), addGraphLabel=draw)
        ## Draw edges
        for edge_ID in content["edges"]:
            edge = content["edges"][edge_ID]
            e = Edge(findNodeFromLabel(edge["node-0"]), findNodeFromLabel(edge["node-1"]))
            e.setID(edge_ID.encode('utf-8'))
            if draw: e.addDrawing(self.axes, self.canvas)
        ## Draw obstacles
        for obstacle_ID in content["obstacles"]:
            obstacle = content["obstacles"][obstacle_ID]
            o = Obstacle(obstacle["start-point"][0], obstacle["start-point"][1])
            o.setID(obstacle_ID.encode('utf-8'))
            if draw:
                o.addDrawing(self.axes, self.canvas, obstacle["end-point"][0], obstacle["end-point"][1])
                o.finalizeDrawing(obstacle["end-point"][0], obstacle["end-point"][1])
            if obstacle_ID != obstacle["label"]:
                o.setLabel(obstacle["label"].encode('utf-8'), addGraphLabel=draw)

        if draw:
            self.canvas.draw()
            Mode.snap_to_grid = True
        self.saved = True


    def collectFileData(self):
        new_file = {"scale-factor": float(self.scale_factor_var.get()),
                    "nodes":{},
                    "edges":{},
                    "obstacles":{}}
        ## Collect nodes
        for node in Graph.nodes:
            new_file["nodes"][node.getID()] = {
                "label": node.getLabel(),
                "coordinates": [node.x, node.y, node.th],
                "neighbors": [n.getLabel() for n in node.neighbors]
            }
        ## Collect edges
        for edge in Graph.edges:
            new_file["edges"][edge.getID()] = {
                "label": edge.getLabel(),
                "node-0": edge.node_0.getLabel(),
                "node-1": edge.node_1.getLabel()
            }
        ## Collect obstacles
        for obstacle in Graph.obstacles:
            new_file["obstacles"][obstacle.getID()] = {
                "label": obstacle.getLabel(),
                "start-point": [obstacle.x_0, obstacle.y_0],
                "end-point": [obstacle.x_1, obstacle.y_1]
            }

        return new_file


    def unloadCurrentWork(self, draw):

        nodeList = Graph.nodes[:]
        for node in nodeList:
            node.delete(now=False)

        obstList = Graph.obstacles[:]
        for obstacle in obstList:
            obstacle.delete(now=False)

        if draw: self.canvas.draw()


    def close(self):

        if not self.saved:
            exit_without_saving = tkMessageBox.askyesno("Current work will be lost!",
                                                     "Are you sure you want to exit without saving your work?")
            if not exit_without_saving:
                self.save()


########################################################################################################################
# ........... CLASSES AND FUNCTIONS
########################################################################################################################


class Point():

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def __str__(self):
        pars = self.x, self.y
        fmt = "[%g %g]"
        return fmt % pars

    def toVector(self):
        return numpy.array([self.x, self.y])

    def inFrame(self, frame):

        fr = frame.toVector()

        rot_matrix = numpy.array([(math.cos(fr[2]), math.sin(fr[2])),
                                  (-math.sin(fr[2]), math.cos(fr[2]))])
        transposed_vector = rot_matrix.dot(self.toVector() - fr[0:2])

        return Point(transposed_vector[0], transposed_vector[1])


class Pose(Point):

    def __init__(self, x, y, th):
        Point.__init__(self, x, y)
        self.th = float(th) # radians

    def __str__(self):
        pars = self.x, self.y, self.th
        fmt = "[%g %g %g]"
        return fmt % pars

    def toVector(self):
        return numpy.array([self.x, self.y, self.th])

    def inFrame(self, frame):
        fr = frame.toVector()

        rot_matrix = numpy.array([(math.cos(fr[2]), math.sin(fr[2]), 0),
                                  (-math.sin(fr[2]), math.cos(fr[2]), 0),
                                  (0, 0, 1)])
        transposed_vector = rot_matrix.dot(self.toVector() - fr)

        return Pose(transposed_vector[0], transposed_vector[1], transposed_vector[2])


########################################################################################################################
# PATHFINDING CLASSES AND FUNCTIONS
########################################################################################################################

class PriorityQueue:
    def __init__(self):
        self.elements = []

    def empty(self):
        return len(self.elements) == 0

    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def get(self):
        return heapq.heappop(self.elements)[1]


def heuristic(a, b):
    return abs(a.x - b.x) + abs(a.y - b.y)


def a_star_search(start, goal):
    frontier = PriorityQueue()
    frontier.put(start, 0)
    came_from = {}
    cost_so_far = {}
    came_from[start] = None
    cost_so_far[start] = 0

    while not frontier.empty():
        current = frontier.get()

        if current == goal:
            break

        for next in current.neighbors:
            new_cost = cost_so_far[current] + findEdgeFromNodes(current, next).weight
            if next not in cost_so_far or new_cost < cost_so_far[next]:
                cost_so_far[next] = new_cost
                priority = new_cost + heuristic(goal, next)
                frontier.put(next, priority)
                came_from[next] = current

    return came_from, cost_so_far


def reconstruct_path(came_from, start, goal):
    current = goal
    path = []
    while current != start:
        path.append(current)
        current = came_from[current]
    path.append(start) # optional
    path.reverse() # optional
    return path


def sortNodesFromClosestToFurthest(current_pose, node_list):

    distances = []
    sorted_distances = []
    closest_nodes = []

    for node in node_list:
        n = numpy.array([node.x, node.y])
        dist = numpy.linalg.norm(current_pose.toVector()[0:2] - n)
        distances.append([node, dist])

    sorted_distances = sorted(distances, key=lambda x:x[1])

    for dist in sorted_distances:
        closest_nodes.append(dist[0])

    return closest_nodes


########################################################################################################################
# PLOT CLASSES AND FUNCTIONS
########################################################################################################################


def setFigure(axes, width):
    axes.set_xticks(range(-100, 100, 1))
    axes.set_yticks(range(-100, 100, 1))

    xlim = int(round((width / 30) / 2))

    axes.set_xlim(-xlim, xlim)
    axes.set_ylim(-10, 10)
    axes.grid(zorder=1)
    axes.set_aspect('equal')


def drawPathToGoal(axes, drawn_nodes, path):

    for node in path:
        if node.getLabel() in drawn_nodes:
            drawn_nodes[node.getLabel()].remove()
        drawn_nodes[node.getLabel()], = axes.plot(node.x, node.y, color='#ef8f0a', marker='o', markersize=8, zorder=2)

    return drawn_nodes


def drawDetectedPose(figure, axes, drawn_plot, pose, label=''):

    for key in drawn_plot["pose-detected"]:
        if drawn_plot["pose-detected"][key] is not None:
            drawn_plot["pose-detected"][key].set_alpha(0.5)

    drawn_plot["pose-detected"]["point"] = axes.plot(pose.x, pose.y,
                                                     color='blue',
                                                     marker='o',
                                                     markersize=7,
                                                     zorder=4)[0]
    drawn_plot["pose-detected"]["direction"] = axes.arrow(pose.x, pose.y,
                                                          math.cos(pose.th),
                                                          math.sin(pose.th),
                                                          fc='#0000ff',
                                                          ec='#0000ff',
                                                          length_includes_head=True,
                                                          head_width=0.2,
                                                          head_length=0.2,
                                                          zorder=4)
    if not label == '':
        drawn_plot["pose-detected"]["label"] = axes.text(pose.x + 1.4 * math.cos(pose.th),
                                                            pose.y + 1.4 * math.sin(pose.th),
                                                            label,
                                                            color='blue',
                                                            fontsize=8,
                                                            bbox={'facecolor': 'white', 'edgecolor': 'none',
                                                                  'alpha': 0.9, 'pad': 0.2},
                                                            zorder=4)

    figure.canvas.draw()


def drawFixedPose(figure, axes, drawn_plot, pose, label=''):

    for key in drawn_plot["pose-detected"]:
        if drawn_plot["pose-detected"][key] is not None:
            drawn_plot["pose-detected"][key].set_alpha(0.5)

    drawn_plot["pose-detected"]["point"] = axes.plot(pose.x, pose.y,
                                                     color='#29c90c',
                                                     marker='o',
                                                     markersize=7,
                                                     zorder=4)[0]
    drawn_plot["pose-detected"]["direction"] = axes.arrow(pose.x, pose.y,
                                                          math.cos(pose.th),
                                                          math.sin(pose.th),
                                                          fc='#29c90c',
                                                          ec='#29c90c',
                                                          length_includes_head=True,
                                                          head_width=0.2,
                                                          head_length=0.2,
                                                          zorder=4)
    if not label == '':
        drawn_plot["pose-detected"]["label"] = axes.text(pose.x + 1.4 * math.cos(pose.th),
                                                            pose.y + 1.4 * math.sin(pose.th),
                                                            label,
                                                            color='#29c90c',
                                                            fontsize=8,
                                                            bbox={'facecolor': 'white', 'edgecolor': 'none',
                                                                  'alpha': 0.9, 'pad': 0.2},
                                                            zorder=4)

    figure.canvas.draw()

def drawGoal(figure, axes, drawn_plot, goal):

    if drawn_plot["current-goal"]["point"] is not None:
        drawn_plot["current-goal"]["point"].remove()

    drawn_plot["current-goal"]["point"] = axes.plot(goal.x, goal.y,
                                                        color='red',
                                                        marker='x',
                                                        markersize=10, zorder=3)[0]
    figure.canvas.draw()


def drawNode(figure, axes, drawn_plot, node, reached):

    color = 'green' if reached == True else 'red'

    if drawn_plot["nodes"]:
        drawn_plot["nodes"][node.getLabel()].remove()
    drawn_plot["nodes"][node.getLabel()] = axes.plot(node.x, node.y, color=color, marker='o', markersize=8, zorder=2)[0]

    figure.canvas.draw()


########################################################################################################################
# OTHER CLASSES AND FUNCTIONS
########################################################################################################################


def printGoalInfo(goal, robot_goal):

    print("Goal in world frame (u):")
    print(goal.x, goal.y)
    print("Goal in robot frame (u):")
    print(robot_goal.x, robot_goal.y)
    # print("Goal in world frame (m):")
    # print(goal.toMeters().x, goal.toMeters().y)
    # print("Goal in robot frame (m):")
    # print(robot_goal.toMeters().x, robot_goal.toMeters().y)


def getHighestIndex(list):

    int_list = []

    for l in list:
        l_id = int(l.getID().split("_")[1])
        int_list.append(l_id)

    highest = max(int_list) if int_list else 0

    return highest

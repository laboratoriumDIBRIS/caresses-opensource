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

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.lines
import matplotlib.patches as patches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure

import time

import tkSimpleDialog
from Tkinter import *
from ttk import Frame, Button, Label, Checkbutton, Entry

from graphnavigation import *

DEBUG = False


class GraphDrawer(Frame):

    def __init__(self):
        Frame.__init__(self)

        self.initUI()

    def initUI(self):
        self.master.title("Graph Drawer")
        self.pack(fill=BOTH, expand=True)
        self.centerWindow()

        menubar = Menu(self.master)
        self.master.config(menu=menubar)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(8, weight=1)
        self.rowconfigure(9, pad=7)

        nbtn = Button(self, text="Node Mode", command=self.drawNode)
        nbtn.grid(row=1, column=3, pady=4)

        ebtn = Button(self, text="Edge Mode", command=self.drawEdge)
        ebtn.grid(row=2, column=3, pady=4)

        rbtn = Button(self, text="Obst Mode", command=self.drawRect)
        rbtn.grid(row=3, column=3, pady=4)

        cbtn = Button(self, text="Clear", command=self.clear)
        cbtn.grid(row=4, column=3, pady=4)

        self.node_list = Listbox(self, selectmode=EXTENDED)
        self.node_list.grid(row=5, column=3, padx=5, pady=5)
        n_scrollbar = Scrollbar(self, orient=VERTICAL)
        n_scrollbar.grid(row=5, column=4, padx=5, sticky='nsw')
        self.node_list.config(yscrollcommand=n_scrollbar.set)
        n_scrollbar.config(command=self.node_list.yview)
        self.node_list.bind('<FocusOut>', lambda e: self.node_list.selection_clear(0, END))
        self.node_list.bind('<Double-Button>', self.highlightNode)

        self.edge_list = Listbox(self, selectmode=EXTENDED)
        self.edge_list.grid(row=6, column=3, padx=5, pady=5)
        e_scrollbar = Scrollbar(self, orient=VERTICAL)
        e_scrollbar.grid(row=6, column=4, padx=5, sticky='nsw')
        self.edge_list.config(yscrollcommand=e_scrollbar.set)
        e_scrollbar.config(command=self.edge_list.yview)
        self.edge_list.bind('<FocusOut>', lambda e: self.edge_list.selection_clear(0, END))
        self.edge_list.bind('<Double-Button>', self.highlightEdge)

        self.obst_list = Listbox(self, selectmode=EXTENDED)
        self.obst_list.grid(row=7, column=3, padx=5, pady=5)
        o_scrollbar = Scrollbar(self, orient=VERTICAL)
        o_scrollbar.grid(row=7, column=4, padx=5, sticky='nsw')
        self.obst_list.config(yscrollcommand=o_scrollbar.set)
        o_scrollbar.config(command=self.obst_list.yview)
        self.obst_list.bind('<FocusOut>', lambda e: self.obst_list.selection_clear(0, END))
        self.obst_list.bind('<Double-Button>', self.highlightObst)

        self.status = StringVar()
        lbl = Label(self, textvariable=self.status)
        lbl.grid(row=9, column=0, sticky=W, pady=4, padx=5)

        fig = Figure(figsize=(9, 9), dpi=100)
        self.axes = fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(fig, self)
        self.canvas.get_tk_widget().grid(row=1, column=0, columnspan=2, rowspan=8,
                                    padx=5, sticky=E + W + S + N)

        self.canvas.get_tk_widget().update()
        canvas_width = self.canvas.get_tk_widget().winfo_width()

        setFigure(self.axes, canvas_width)

        self.canvas.mpl_connect('button_press_event',   self.on_click)
        self.canvas.mpl_connect('pick_event',            self.on_pick)
        self.canvas.mpl_connect('button_press_event',   self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('motion_notify_event',  self.on_motion)

        self.canvas.show()

        self.snap = BooleanVar()
        self.snap.set(Mode.snap_to_grid)
        cb = Checkbutton(self, text="Snap to grid", variable=self.snap, command=self.on_snap)
        cb.grid(row = 0, column =3)

        txt = Label(self, text="(units) 1 = (meters) ")
        txt.grid(row=0, column=1, sticky=E, padx=(2, 70))
        self.k = StringVar()
        self.k.set("1.00")
        spb = Spinbox(self, from_=0.1, to=100, increment=.1, format='%5.2f', width=6, textvariable=self.k)
        spb.grid(row=0, column=1, sticky=E, padx=(2, 20))

        self.frame = Frame(self)
        self.frame.grid(row=0, column=0, sticky=W, pady=4, padx=5)

        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.frame)
        self.toolbar.update()
        self.toolbar.pack()

        self.mode = Mode(self.toolbar, self.status)
        self.mode.start()

        self.file = GraphFile()
        self.file.setUpGraphics(self.axes, self.canvas)
        self.file.scale_factor_var = self.k

        fileMenu = Menu(menubar)
        fileMenu.add_command(label="Open", command=self.openFile)
        fileMenu.add_command(label="Save", command=self.file.save)
        fileMenu.add_command(label="Save As", command=self.file.saveAs)
        menubar.add_cascade(label="File", menu=fileMenu)

        self.axes.plot(0, 0, color='red', marker='+', markersize=8, zorder=1)

    def highlightNode(self, event):
        index = self.node_list.curselection()[0]
        item_label = self.node_list.get(index)
        node = findNodeFromLabel(item_label)
        node.matplotlib_element.set_color("lime")
        node.canvas.draw()
        time.sleep(0.2)
        node.matplotlib_element.set_color("black")
        node.canvas.draw()

    def highlightEdge(self, event):
        index = self.edge_list.curselection()[0]
        item_label = self.edge_list.get(index)
        edge = findEdgeFromLabel(item_label)
        edge.matplotlib_element.set_color("lime")
        edge.canvas.draw()
        time.sleep(0.2)
        edge.matplotlib_element.set_color("black")
        edge.canvas.draw()

    def highlightObst(self, event):
        index = self.obst_list.curselection()[0]
        item_label = self.obst_list.get(index)
        obst = findObstFromLabel(item_label)
        obst.matplotlib_element.set_color("lime")
        obst.canvas.draw()
        time.sleep(0.2)
        obst.matplotlib_element.set_color("#1F77B4")
        obst.canvas.draw()

    def openFile(self):
        self.file.open()
        self.refreshLists()

    def centerWindow(self):

        sw = self.master.winfo_screenwidth()
        sh = self.master.winfo_screenheight()

        w = sw * 2 / 3
        h = sh * 2 / 3 + 10

        x = (sw - w) / 2
        y = (sh - h) / 2
        self.master.geometry('%dx%d+%d+%d' % (w, h, x, y))


    ## BUTTONS ACTIONS

    def drawNode(self):
        self.mode.setMode(Mode.NODE)

    def drawEdge(self):
        self.mode.setMode(Mode.EDGE)

    def drawRect(self):
        self.mode.setMode(Mode.OBST)

    def clear(self):
        self.file.saved = False
        self.file.unloadCurrentWork(draw=True)
        self.clearLists()

    ## LIST FUNCTIONS

    def clearLists(self):
        self.node_list.delete(0, END)
        self.edge_list.delete(0, END)
        self.obst_list.delete(0, END)
    
    def refreshLists(self):
        ## Clear list
        self.clearLists()

        ## Update lists

        for item in Graph.nodes:
            self.node_list.insert(END, item.getLabel())
        for item in Graph.edges:
            self.edge_list.insert(END, item.getLabel())
        for item in Graph.obstacles:
            self.obst_list.insert(END, item.getLabel())

    def deleteElementsFromList(self, mylist, indexes):

        list_copy = mylist.get(0, END)
        mylist.delete(0, END)
        for i, n in enumerate(list_copy):
            if i not in indexes:
                mylist.insert(END, list_copy[i])
        self.refreshLists()

    ## MOUSE EVENTS CALLBACKS

    def on_click(self, event):

        if self.mode.getMode() == Mode.NODE:
            ## Draw node on left-click
            if event.button == 1:
                if event.xdata and event.ydata:
                    n = Node(event.xdata, event.ydata)
                    n.addDrawing(event.inaxes, event.canvas, drawNow=True)
                    ## A new node implies unsaved changes
                    self.file.saved = False
                    if DEBUG: print n

        elif self.mode.getMode() == Mode.EDGE:
            pass

        elif self.mode.getMode() == Mode.OBST:
            pass

        self.refreshLists()


    def on_pick(self, event):

        ## Start drawing an edge on left-click
        if event.mouseevent.button == 1:

            if self.mode.getMode() == Mode.EDGE:
                if Temp.node_0 == None:
                    Temp.node_0 = findNodeFromMatPoint(event.artist)
                    self.mode.setStatusbarLabel(11)
                else:
                    Temp.node_1 = findNodeFromMatPoint(event.artist)
                    e = Edge(Temp.node_0, Temp.node_1)
                    e.addDrawing(event.artist.axes, event.canvas, drawNow=True)
                    Temp.reset()
                    self.mode.setStatusbarLabel(10)
                    if DEBUG: print e

        ## Delete selected node on wheel-click
        elif event.mouseevent.button == 2:

            if self.mode.getMode() == Mode.NODE:
                findNodeFromMatPoint(event.artist).delete()
            elif self.mode.getMode() == Mode.EDGE:
                pass
            elif self.mode.getMode() == Mode.OBST:
                findObstFromMatRect(event.artist).delete()

        ## Label selected node on right-click
        elif event.mouseevent.button == 3:

            new_label, new_theta = None, None

            if isinstance(event.artist, matplotlib.lines.Line2D):
                is_node = True
                is_obst = False
                element = findNodeFromMatPoint(event.artist)
            elif isinstance(event.artist, matplotlib.patches.Rectangle):
                is_node = False
                is_obst = True
                element = findObstFromMatRect(event.artist)
            else:
                return              

            ## If a node is picked, ask for label and orientation
            if is_node:
                self.insertNodeLabelAndAngle(element)
            ## Else if an obstacle is picked, just ask for the label
            elif is_obst:
                self.insertObstacleLabel(element)

        self.file.saved = False
        self.refreshLists()


    def on_press(self, event):
        MouseState.isPressed = True
        MouseState.isReleased = False

        if event.button == 1:

            if self.mode.getMode() == Mode.NODE:
                pass
            elif self.mode.getMode() == Mode.EDGE:
                pass
            elif self.mode.getMode() == Mode.OBST:
                o = Obstacle(event.xdata, event.ydata)
                Temp.obstacle = o


    def on_release(self, event):
        MouseState.isPressed = False
        MouseState.isReleased = True

        if event.button == 1:

            if self.mode.getMode() == Mode.NODE:
                pass
            elif self.mode.getMode() == Mode.EDGE:
                pass
            elif self.mode.getMode() == Mode.OBST:
                Temp.obstacle.finalizeDrawing(event.xdata, event.ydata)
                if DEBUG: print Temp.obstacle
                Temp.reset()
                ## A new obstacle implies unsaved changes
                self.file.saved = False
        
        self.refreshLists()


    def on_motion(self, event):

        if event.button == 1:

            if self.mode.getMode() == Mode.NODE:
                pass
            elif self.mode.getMode() == Mode.EDGE:
                pass
            elif self.mode.getMode() == Mode.OBST:
                if MouseState.isPressed:
                    Temp.obstacle.addDrawing(event.inaxes, event.canvas, event.xdata, event.ydata, drawNow=True)


    def on_snap(self):

        Mode.snap_to_grid = True if self.snap.get() == True else False


    def on_delete(self):
        self.file.close()
        self.master.destroy()

    ## POP UP WINDOWS

    def insertNodeLabelAndAngle(self, element):
        
        label = element.getLabel()
        id = element.getID()
        label_field = label if not label == id else ""
        theta = element.th
        NodeInfoDialog.setLabelField(label_field)
        NodeInfoDialog.setThetaField(str(theta))
        node_dbox = NodeInfoDialog(self, title="Assign node info")

        if node_dbox.result is not None:
            new_label, new_theta = node_dbox.result

            if new_theta is not None:
                ## Consider empty field as theta = 0.0
                if new_theta == '':
                    new_theta = 0.0
                new_theta = float(new_theta)
                element.th = new_theta
                ## Update orientation arrow
                element.matplotlib_subelement.remove()
                element.matplotlib_subelement = element.axes.arrow(element.x, element.y,
                            math.cos(math.radians(element.th)),
                            math.sin(math.radians(element.th)),
                            color="red",
                            length_includes_head=True,
                            head_width=0.2,
                            head_length=0.2,
                            zorder=4)
                element.canvas.draw()

            self.updateLabel(element, new_label)
        

    def insertObstacleLabel(self, element):
        
        label = element.getLabel()
        id = element.getID()
        label_field = label if not label == id else ""
        new_label = tkSimpleDialog.askstring("Assign Label", "Enter the label", initialvalue=label_field)

        self.updateLabel(element, new_label)

    
    def updateLabel(self, element, new_label):

        if new_label is not None:
            new_label = new_label.replace("-", "_").replace(" ", "_")
            element.setLabel(new_label, drawNow=True, addGraphLabel=True)
            ## If label is removed, set again the label equal to the ID but do not show it
            if new_label == '':
                element.setLabel(id, drawNow=False, addGraphLabel=True)


    ## KEYBOARD CALLBACKS

    def key(self, event):

        if event.keysym == "Delete":
            ## Get selected line index for Node list
            indexes = self.node_list.curselection()
            if not len(indexes) == 0:
                for index in indexes:
                    item_label = self.node_list.get(index)
                    findNodeFromLabel(item_label).delete()
                self.deleteElementsFromList(self.node_list, indexes)
            ## Get selected line index for Edge list
            indexes = self.edge_list.curselection()
            if not len(indexes) == 0:
                for index in indexes:
                    item_label = self.edge_list.get(index)
                    findEdgeFromLabel(item_label).delete()
                self.deleteElementsFromList(self.edge_list, indexes)
            ## Get selected line index for Obstacle list
            indexes = self.obst_list.curselection()
            if not len(indexes) == 0:
                for index in indexes:
                    item_label = self.obst_list.get(index)
                    findObstFromLabel(item_label).delete()
                self.deleteElementsFromList(self.obst_list, indexes)
            
            self.file.saved = False

        if event.keysym == "Return":
            ## Get selected line index for Node list
            indexes = self.node_list.curselection()
            if len(indexes) == 1:
                item_label = self.node_list.get(indexes[0])
                element = findNodeFromLabel(item_label)
                self.insertNodeLabelAndAngle(element)
                self.refreshLists()
            ## Get selected line index for Obstacle list
            indexes = self.obst_list.curselection()
            if len(indexes) == 1:
                item_label = self.obst_list.get(indexes[0])
                element = findObstFromLabel(item_label)
                self.insertObstacleLabel(element)
                self.refreshLists()

            self.file.saved = False


class NodeInfoDialog(tkSimpleDialog.Dialog):

    _label_var = None
    _theta_var = None

    def body(self, master):

        Label(master, text="Label:").grid(row=0, sticky=W)
        Label(master, text="Theta (deg):").grid(row=1, sticky=W)

        self._label_var = StringVar(master, value=NodeInfoDialog._label_var)
        self._theta_var = StringVar(master, value=NodeInfoDialog._theta_var)

        self.e1 = Entry(master, textvariable=self._label_var)
        self.e2 = Entry(master, textvariable=self._theta_var)

        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        return self.e1 # initial focus

    def validate(self):
        if not self.e2.get() == "":
            theta = float(self.e2.get())
            if theta < -360.0 or theta > 360.0:
                tkMessageBox.showerror("Invalid Theta value", "Insert a value between -360° and 360°")
                self.e2.delete(0, 'end')
                return 0
            else:
                return 1
        else:
            return 1

    def apply(self):
        label = self.e1.get()
        theta = self.e2.get()

        self.result =  label, theta

    @staticmethod
    def setLabelField(label):
        NodeInfoDialog._label_var = str(label)

    @staticmethod
    def setThetaField(theta):
        NodeInfoDialog._theta_var = str(theta)

def main():
    root = Tk()
    app = GraphDrawer()
    root.protocol("WM_DELETE_WINDOW", app.on_delete)
    # icon = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'CARESSES_ico.ico')
    # root.wm_iconbitmap(icon)
    root.bind_all('<Key>', app.key)
    root.mainloop()

    ## Stop Mode thread when the app window is closed
    Mode.alive = False


if __name__ == '__main__':
    main()
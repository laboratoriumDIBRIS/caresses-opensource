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

import argparse
import time
import functools
from threading import Thread

from choice_manager import ChoiceManager
from naoqi import ALProxy

class Timer(Thread):

    ## This thread starts a timer which, if initialized inside the function giveChoiceMultipage(), terminates the
    # MultipageChoiceManager once the predefined time elapses by faking the user input "EXIT". This is to avoid the
    # blocking call to the MultiPageChoiceManager to keep Pepper stuck forever if the user doesn't give any answer.

    def __init__(self, ip, timeout):
        Thread.__init__(self)
        self.start_time = time.time()
        self.pMemory = ALProxy("ALMemory", str(ip), 9559)
        self.timeout = timeout #seconds
        self.stopped = False

    def run(self):

        while not self.stopped and time.time() - self.start_time < self.timeout:
            pass

        if not self.stopped:
            self.pMemory.insertData("WordRecognized", ["<...> EXIT <...>", 1])

    def killTimer(self):
        self.stopped = True


class MultiPageChoiceManager(ChoiceManager):

    def __init__(self, ip):
        ChoiceManager.__init__(self, ip)
        self.back_btn = "BACK"
        self.next_btn = "NEXT"
        self.exit_btn = "EXIT"

        self.ip = ip

        ## Use these values if using balloon-shaped answers
        # self._limits = [0, 5, 13, 21, 29]
        ## Use these values if using CARESSES layout
        self._limits = [10, 17, 24, 30, 38]

        self._clear()

    def _clear(self):
        self.options = None
        self.page_index = -1
        self.row_index = 0
        self.max_rows = 2
        self.pages = []
        self.max_buttons_per_page = 10

    def _newPage(self):
        self.pages.append([])
        self.page_index += 1
        self.row_index = 0
        for r in range(0, self.max_rows):
            self.pages[self.page_index].append([])

    def _newRow(self):
        if self.row_index == self.max_rows - 1:
            self._newPage()
        else:
            self.row_index += 1

    def _getRow(self):
        return self.pages[self.page_index][self.row_index]

    def _getPage(self):
        return self.pages[self.page_index]

    def _getTotalRowLength(self, row):
        tot_len = 0
        for o in row:
            tot_len += len(o)
        return tot_len

    def _getCurrentPageNumberOfOptions(self):

        options_num = 0

        for row in self.pages[self.page_index]:
            options_num = options_num + len(row)

        return options_num

    def _fillPages(self):

        self._newPage()

        for o in self.options:

            added = False

            while not added:

                row = self._getRow()

                # is_back_button_present =
                # is_next_button_present =

                if self.row_index == self.max_rows - 1:
                    ## Add navigation buttons to the number of options
                    tot_options = self._getCurrentPageNumberOfOptions() + 3

                    if tot_options == self.max_buttons_per_page:
                        self._newRow()
                        continue

                if len(row) == 5:
                    self._newRow()
                elif len(row) == 4:
                    if self._getTotalRowLength(row) + len(o) <= self._limits[0]:
                        row.append(o)
                        added = True
                    else:
                        self._newRow()
                elif len(row) == 3:
                    if self._getTotalRowLength(row) + len(o) <= self._limits[1]:
                        row.append(o)
                        added = True
                    else:
                        self._newRow()
                elif len(row) == 2:
                    if self._getTotalRowLength(row) + len(o) <= self._limits[2]:
                        row.append(o)
                        added = True
                    else:
                        self._newRow()
                elif len(row) == 1:
                    if self._getTotalRowLength(row) + len(o) <= self._limits[3]:
                        row.append(o)
                        added = True
                    else:
                        self._newRow()
                elif len(row) == 0:
                    if self._getTotalRowLength(row) + len(o) <= self._limits[4] or self.row_index == 0:
                        row.append(o)
                        added = True
                    else:
                        self._newRow()

    def _groupPageOptions(self):
        options_per_page = []
        for page in self.pages:
            page_options = []
            for row in page:
                for option in row:
                    page_options.append(option)
            options_per_page.append(page_options)

        return options_per_page

    def giveChoiceMultiPage(self, question, answerList, confidence=0.5, bSayQuestion=False, timer=80, exitOnTouch=True):

        if question == "":
            self.max_rows += 1
        self.options = answerList
        self._fillPages()
        sub_options = self._groupPageOptions()

        index = 0
        sayQuestion = bSayQuestion

        while index is not None:
            chunk = sub_options[index][:]
            if not index == 0:
                chunk.append(self.back_btn)
            if not index == len(sub_options) - 1:
                chunk.append(self.next_btn)
            chunk.append(self.exit_btn)

            ## Eventually start a timer to quit the MultiPageChoiceManager if no answer is given
            if timer is not None:
                t = Timer(self.ip, timer)
                t.start()

            if exitOnTouch:
                ## Subscribe to touch event to quit the MultiPageChoiceManager if Pepper is touched
                self.touch = self.memory.subscriber("TouchChanged")
                self.signal_touch = self.touch.signal.connect(functools.partial(self.onTouched, "TouchChanged"))

            self.answer = self.giveChoice(question, chunk, confidence, sayQuestion)
            if timer is not None:
                t.killTimer()
            sayQuestion = False
            if self.answer[0] == self.next_btn:
                index += 1
            elif self.answer[0] == self.back_btn:
                index -= 1
            else:
                index = None

        self._clear()

        if exitOnTouch:
            self.touch.signal.disconnect(self.signal_touch)

        return self.answer

    def onTouched(self, msg, value):

        self.memory.insertData("WordRecognized", ["<...> EXIT <...>", 1])

    # def kill(self):
    #     self.behaviours.stopBehavior("choice-manager/question")
    #     self.tabletService.hide()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument("--ip",
                        type=str,
                        default="10.0.207.72",
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")

    args = parser.parse_args()
    
    ## Uncomment the block below and comment the other options array to see how "words" of random 
    ## different lengths are divided across pages. Otherwise test it with the animal options.
    #  
    # from random import randint
    # options = []
    # for i in range(0, 15):
    #     length = randint(1, 29)
    #     o = "A" * length
    #     options.append(o)

    # Multi choice manager with a Japanese version.
    # THE ROBOT'S LANGUAGE MUST BE ENGLISH
    question = "Select one"
    # options = ["dog", "cat", "elephant", "mouse", "rhinoceros", "bird", "puffer fish", "lion", "giraffe", "eagle", "wolf"]
    options = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]
    # Multi choice manager with a Japanese version.
    # THE ROBOT'S LANGUAGE MUST BE JAPANESE
    # Blue, red, green, yellow, orange, pink, purple, white, black, brown, grey
    # question = "色を選んでください"
    # options = ["青", "赤", "緑", "黄", "オレンジ", "ピンク", "紫の", "白", "黒", "褐色", "灰色"]

    multipagechoice = MultiPageChoiceManager(args.ip)

    time.sleep(3)

    print multipagechoice.giveChoiceMultiPage(question, options)

    multipagechoice.kill()

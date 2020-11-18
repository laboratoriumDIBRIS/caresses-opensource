# coding: utf8
'''
Copyright October 2019 Carmine Tommaso Recchiuto & Università degli Studi di Genova

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

Author:      Carmine Tommaso Recchiuto
Email:       carmine.recchiuto@dibris.unige.it
Affiliation: Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import qi
import argparse
import sys
from action import Action
import os
import json
import caressestools.caressestools as caressestools
import string
import glob
import time
from naoqi import ALProxy
import thread
import csv
import re
import signal
import sys
import random
import functools
from caressestools.multipage_choice_manager import MultiPageChoiceManager
from caressestools.input_request_parser import InputRequestParser
import requests
import urllib2
import cookielib
import qi
import time
import threading
import caressestools.speech as speech
from CahrimThreads.sensory_hub import DetectUserDepth
import CahrimThreads.socket_handlers

JSON_FILEPATH= "ActionsLib/caressestools/speech_conf.json"
action_json= "ActionsLib/parameters/accept_request.json"


## Action "Chitchat".
#
#  Pepper talks with the user aboutgeneral conversation topics. The action works only within the whole CAHRIM system, and with the CKB running, since all sentences are chosen by the CKB module.
class ChitChat(Action):
    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english).
    # @param session (qi session) NAOqi session.
    # @param output_handler () Handler of the output socket messages.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, output_handler, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = apar.split(' ')
        # Parse the cultural parameters
        self.cpar = cpar.split(' ')
        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].title().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.ctopicb = self.apar[0].replace('_', ' ')
        self.loops = int(self.apar[1])
        with open(JSON_FILEPATH) as f:
            self.inputs = json.load(f)
        self.sMemory           = self.session.service("ALMemory")
        self.tts               = self.session.service("ALAnimatedSpeech")
        self.tts2              = self.session.service("ALTextToSpeech")
        self.sDialog           = self.session.service("ALDialog")
        self.asr               = self.session.service("ALSpeechRecognition")
        self.asr.pause(True)
        self.asr.pause(True)
        self.asr.setLanguage(self.language)
        vocabulary = [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]]
        self.asr.setVocabulary(vocabulary,True)
        self.asr.pause(False)
        self.tablet            = self.session.service("ALTabletService")
        self.sASR              = self.session.service("ASR2")
        self.posture       = self.session.service("ALRobotPosture")
        self.tts2.setLanguage(self.language)
        self.tts2.setParameter("speed", self.speed)
        self.tts2.setParameter("pitchShift", self.pitch)
        self.tts2.setVolume(self.volume)
        self.asr.setAudioExpression(False)
        self.user_input = None
        self.soundService = "google"
        self.initSoundService(self.soundService)
        self.speechReco()
        self.sMemory.subscriber("ALTextToSpeech/TextDone")
        self.choice=None
        self.classe="none"
        self.output_handler=output_handler
        self.myflag=0
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))
        self.sentences=[]
        self.classes=[]
        self.types=[]
        self.tag=[]
        self.pointer=0
        self.going=1
        with open(action_json) as f:
            self.CMoptions = json.load(f)
        self.firsttimer=90
        self.noisy=asr

    ## Callback function used to detect keywords (yes/no)
    # @param value Keyword recognized
    def onSpeechRecognized(self, value):
        if value[1] > 0.55:
            self.key = value[0].split(' ')[1]

    ## Method to initialize the dictionary (yes/no)
    def speechReco(selsf):
        #self.asr.pause(True)
        #self.asr.setVocabulary(vocabulary,True)
        #self.asr.pause(False)
        pass

    ## The robot's tablet may be used to show images related to the conversation topics (the images' urls are saved in an additional file). The current method display the images on the tablet.
    def showingimages(self):
        self.closethread=1
        data=[]
        url_a=[]
        url_b=[]
        url_c=[]
        url_d=[]
        url_e=[]

        images_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "aux_files", "images.csv")

        with open(images_path,'rb') as f:
            reader= csv.reader(f)
            count=0
            for row in reader:
                data.append(row[0])
                url_a.append(row[1])
                if(row[2]!=""):
                    url_b.append(row[2])
                else:
                    url_b.append(row[1])
                if(row[3]!=""):
                    url_c.append(row[3])
                else:
                    url_c.append(row[1])
                if(row[4]!=""):
                    url_d.append(row[4])
                else:
                    url_d.append(row[1])
                if(row[5]!=""):
                    url_e.append(row[5])
                else:
                    url_e.append(row[1])

        url = [["" for x in range(5)] for y in range(len(data))]
        for x in range(0,len(data)):
            url[x]=[url_a[x],url_b[x],url_c[x],url_d[x],url_e[x]]

        while(self.closethread):
            if(self.classe=="choicemanager"):
                pass
            elif(self.classe=="none"):
                caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                self.synchro=1
            else:
                myflag=False
                self.synchro=0
                for x in range(0,len(data)):
                    if data[x]==self.classe:
                        myurl=random.choice(url[x])
                        myflag=True

                if myflag==True:
                    self.tablet.loadUrl(myurl)
                    self.tablet.showWebview()
                    time.sleep(8)
                else:
                    self.classe="none"

    ## The flag set by this method means that the action has been started by the AcceptRequest action. This may be useful to understand if the action should send a goal before exiting.
    def calledbyar(self):
        self.myflag=1

    ## Timer used to stop the ChoiceManager
    def goodbyetimer(self):
        start=time.time()
        self.timeout=0
        while(self.timing):
            if(time.time()-start>self.gt):
                 self.timeout=1
                 self.sMemory.insertData("WordRecognized", ["<...> " + "EXIT" + " <...>",1.0])
                 break
            else:
                time.sleep(1)

    ## Method for setting TAGS in the log file
    # @param type (string) type of sentence pronounced by the robot
    def typesToTag(self, type):
        if type=="wait":
            self.tag.append(speech.TAGS[18])
        elif type=="question":
            self.tag.append(speech.TAGS[17])
        elif type=="goal":
            self.tag.append(speech.TAGS[19])
        elif type=="contextual":
            self.tag.append(speech.TAGS[23])
        elif type=="positive":
            self.tag.append(speech.TAGS[14])
        elif type=="negative":
            self.tag.append(speech.TAGS[15])
        elif type=="notunderstood":
            self.tag.append(speech.TAGS[12])
        else:
            self.tag.append(speech.TAGS[13])

    ## Method that handles sentences received by the CKB. When a new sentence is received, all relevant information are stored (content of the sentence, type of the sentence, tag, class of the instance)
    def handleinputmessages(self):
        while(self.going):
            l = CahrimThreads.socket_handlers.InputMsgHandler.robotsaysCheck()
            if( l is not None):
                #l = l.decode("utf-8")
                CahrimThreads.socket_handlers.InputMsgHandler.robotsaysDone()
                if "_" in l:
                    sentence_temp=l.split('_')[0]
                    self.types.append(l.split('_')[1])
                    self.typesToTag(l.split('_')[1])
                    if "&" in sentence_temp:
                        self.sentences.append(sentence_temp.split('&')[0])
                        self.classes.append(sentence_temp.split('&')[1].lower())
                    else:
                        self.sentences.append(sentence_temp)
                        self.classes.append("none")
                    self.sentences[self.pointer]=self.sentences[self.pointer].rstrip()
                    self.types[self.pointer]=self.types[self.pointer].rstrip()
                    self.classes[self.pointer]=self.classes[self.pointer].rstrip()
                    self.tag[self.pointer]=self.tag[self.pointer].rstrip()
                else:
                    sentence_temp=l
                    if "&" in sentence_temp:
                        self.sentences.append(sentence_temp.split('&')[0])
                        self.classes.append(sentence_temp.split('&')[1].lower())
                    else:
                        self.sentences.append(sentence_temp)
                        self.classes.append("none")
                    self.sentences[self.pointer]=self.sentences[self.pointer].rstrip()
                    self.types.append("")
                    self.tag.append(speech.TAGS[13])
                    self.classes[self.pointer]=self.classes[self.pointer].rstrip()

                count=0
                for i in self.sentences[self.pointer]:
                    if i.isalpha():
                        break
                    else:
                        count=count+1

                
                self.sentences[self.pointer]=self.sentences[self.pointer][count:]
                self.pointer=self.pointer+1

    ## Method executed when the thread is started
    def run(self):
        inputParser = InputRequestParser("ActionsLib/parameters/chitchat.json")
        self.inputDict = inputParser.parseInputs("ActionsLib/parameters/chitchat.json")
        self.may_stop=False
        self.choice=None
        self.tts2.setLanguage(self.language)
        self.tts2.setParameter("speed", self.speed)
        self.tts2.setParameter("pitchShift", self.pitch)
        self.tts2.setVolume(self.volume)
        self.asr.setAudioExpression(False)
        self.user_input = None
        self.soundService = "google"
        self.initSoundService(self.soundService)
        with open(JSON_FILEPATH) as f:
            self.inputs = json.load(f)
        #self.speechReco()
        self.sMemory.subscriber("ALTextToSpeech/TextDone")
        self.classe="none"
        self.classe="none"
        self.synchro=1
        time.sleep(0.2)
        t=""
        connected = False
        self.pepper=self.inputs["Chitchat"]["over_and_out"][self.language.lower()]
        self.initSoundService(self.soundService)
        self.user_input=""
        sentence_b2=""
        sentence_b=""
        sentence_b3=""
        self.exiting=0
        self.timeout=0

        speechRecognized = self.sMemory.subscriber("WordRecognized")
        id_speechRecognized = speechRecognized.signal.connect(functools.partial(self.onSpeechRecognized, "WordRecognized"))
        self.asr.subscribe("Test_ASR")

        self.output_handler.writeSupplyMessage("publish", "D5.2", "chitchat:started")

        if ("doesntmatter" not in self.ctopicb):
            time.sleep(0.1)
            self.ctopic = self.ctopicb
            self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+self.ctopic+"]")
        else:
            self.ctopic = ""

        count1=0
        self.freeze=0
        self.stype=""
    
        #t1 = threading.Thread(name="Hello1", target=self.showingimages)
        #t1.start()
        t2 = threading.Thread(name="handlemessages", target=self.handleinputmessages)
        t2.start()
        pointer=0
        flagCM=0
        self.exitingfromfreeze=0
        self.intent="talk"
        first=True
        self.state_rec=0

        while (self.going):
            self.goal=0
            self.key=None
            self.exitingfromfreeze=0

            if self.choice is not None:
                self.choice.kill()
                caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                del self.choice
                self.choice=None


            if self.state_rec==1:
                self.sASR.stopReco()
                caressestools.setAutonomousAbilities(self.session,False, True, True, True, True)
                self.state_rec=0
            elif self.state_rec==2:
                self.sASR.stopReco()
                self.state_rec=0


            
            if self.freeze==1:
                self.initSoundService(self.soundService)
                self.sASR.startReco(caressestools.Language.lang_naoqi, False, False)
                self.state_rec=2
                try:
                    self.user_input=unicode(self.user_input,"utf-8")
                except:
                    pass
                
                if self.user_input=="EXIT":
                    self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+self.user_input+"]")
                    self.freeze=0
                    continue
                if self.user_input=="yes_EXXIT":
                    caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                    self.freeze=0
                    message=self.inputs["Chitchat"]["repeat"][self.language.lower()]
                    self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+message+"]")
                    continue
                if not self.user_input == None and not self.user_input == "":
                    if self.inputs["KEYWORDS"]["continue"][self.language.lower()][0] in self.user_input:
                        if(self.choice is None):
                            self.classe="none"
                            while(self.synchro==0):
                                pass
                            self.classe="choicemanager"
                            self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                        self.sent=random.choice(self.inputs["AcceptRequest"]["continue"][self.language.lower()])
                        self.sp.say(self.sent, speech.TAGS[16])
                        if self.sp._input==2:
                            self.gothread = True
                            opts = [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]]
                            thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
                            thr.start()
                        result=self.choice.giveChoiceMultiPage(self.inputs["AcceptRequest"]["continue_cm"][self.language.lower()], [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                        self.gothread = False
                        result = [unicode(result[0], "utf-8"), result[1]]
                        self.sp.userSaid(str(result))
                        if(result[0]=="EXIT"):
                            self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:[EXIT]")
                            self.freeze=0
                            self.user_input=""
                            self.exitingfromfreeze=1
                            continue
                        elif(result[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                            self.freeze=0
                            message=self.inputs["Chitchat"]["repeat"][self.language.lower()]
                            self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+message+"]")
                            continue

            if (pointer<self.pointer):
            	first=True
                if "chitchat:finished" in self.sentences[pointer]:
                    if(self.myflag!=1):
                        if DetectUserDepth.isUserApproached():
                            self.output_handler.writeSupplyMessage("publish","D5.1","[(:goal(?G1 accept-request true))]")
                        else:
                            msg="(:goal(?G1 accept-request true))"
                            msg="(:goal(?G1 (approached-user pepper-1) true)(?G2"+msg.split("?G1")[1].split("))")[0]+"))(:temporal(before ?G1 ?G2 [1500 inf]))"
                            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                        break
                    break

                elif "goal(?G1" in self.sentences[pointer] or "no pddl associated" in self.sentences[pointer]:
                    if "goal(?G1" in self.sentences[pointer]:
                        msg=self.sentences[pointer].replace("\n","").replace("\r","")
                        if DetectUserDepth.isUserApproached() or "robot-at" in msg or "object-at-na" in msg:
                            if "?G1" in msg and "?G2" in msg:
                                msg="(:goal(?G1"+msg.split("?G1")[1].split("?G2")[0]+"?G2"+msg.split("?G2")[1]+"?G2 [1500 inf]))"
                            else:
                                msg="(:"+msg

                            if "robot-at" in msg or "object-at-na" in msg:
                                self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):precharger]")
                                time.sleep(0.5)

                            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                        elif "?G1" in msg and "?G2" in msg:
                            #messs="approached-user:false"
                            #self.output_handler.writeSupplyMessage("publish", "D6.1", "["+messs+"]")
                            #time.sleep(0.2)
                            msg="(:goal(?G1 (approached-user pepper-1) true)(?G2"+msg.split("?G1")[1].split("?G2")[0]+"?G3"+msg.split("?G2")[1].split("inf])")[0]+"?G2 [1500 inf])(before ?G2 ?G3 [1500 inf]))"
                            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                        elif  "?G1" in msg:
                            #messs="approached-user:false"
                            #self.output_handler.writeSupplyMessage("publish", "D6.1", "["+messs+"]")
                            #time.sleep(0.2)
                            msg="(:goal(?G1 (approached-user pepper-1) true)(?G2"+msg.split("?G1")[1].split("))")[0]+"))(:temporal(before ?G1 ?G2 [1500 inf]))"
                            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                    self.goal=1
                    break
                
                else:
                    sentence_b3=sentence_b2
                    sentence_b2=sentence_b
                    sentence_b=self.sentences[pointer]
                    self.stype=self.types[pointer]
                    self.classe=self.classes[pointer]
                    self.questionsaid=self.sentences[pointer]
                    self.stag=self.tag[pointer]

                    if(sentence_b3[-15:]==sentence_b[-15:] and (self.stype=="question" or self.stype=="goal" or self.stype=="contextual")):
                        flagCM=1
                        caressestools.setAutonomousAbilities(self.session,False, True, True, True, True)

                    if(flagCM==0):
                        if (self.stype=="wait" or self.stype=="question" or self.stype=="goal" or self.stype=="contextual"):
                            caressestools.setAutonomousAbilities(self.session,False, True, False, False, False)
                            self.posture.goToPosture("Stand", 0.5)
                        self.sp.say(self.sentences[pointer], self.stag)
                        # a= self.sMemory.getData("ALTextToSpeech/TextDone")
                        # while(a!=1):
                        #     a= self.sMemory.getData("ALTextToSpeech/TextDone")
                    else:
                        if(self.choice is None):
                            self.classe="none"
                            while(self.synchro==0):
                                pass
                            self.classe="choicemanager"
                            self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                        self.sp.say(self.sentences[pointer], self.tag[pointer])
                        if self.sp._input==2:
                            self.gothread = True
                            opts = [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]]
                            thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
                            thr.start()
                        a=self.choice.giveChoiceMultiPage("", [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                        self.gothread = False
                        a = [unicode(a[0], "utf-8"), a[1]]
                        self.sp.userSaid(str(a))
                        self.ctopic=a[0]
                        if(a[0] is not "EXIT"):
                            self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+self.ctopic+"]")
                            flagCM=0
                            pointer=pointer+1
                            continue
                        else:
                            self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:[EXIT]")
                            flagCM=0
                            pointer=pointer+1
                            continue


                    if(self.stype!="" and self.stype!="negative" and self.stype!="positive" and self.stype!="notunderstood" and flagCM==0):
                        self.initSoundService(self.soundService)
                        self.sASR.startReco(caressestools.Language.lang_naoqi, False, True)
                        self.getInput(self.soundService)
                        self.state_rec=1
                        try:
                            self.user_input=unicode(self.user_input,"utf-8")
                        except:
                            pass

                        if not self.sp._input in [0, 3]:
                            self.sp.userSaid(self.user_input)


                        for i in range(0, len(self.inputs["KEYWORDS"]["goodbye"][self.language.lower()])):
                            if self.inputs["KEYWORDS"]["goodbye"][self.language.lower()][i] in self.user_input:
                                if not self.confirmed:
                                    if(self.choice is None):
                                        self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                                    self.sp.say(self.inputs["Chitchat"]["I_am_going"][self.language.lower()], speech.TAGS[16])
                                    if self.sp._input==2:
                                        self.gothread = True
                                        opts = [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]]
                                        thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
                                        thr.start()
                                    rr= self.choice.giveChoiceMultiPage(self.inputs["Chitchat"]["goodbye_confirm"][self.language.lower()], [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                                    self.gothread = False
                                    rr = [unicode(rr[0], "utf-8"), rr[1]]
                                    self.sp.userSaid(str(rr))
                                    if(rr[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                                        self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:[EXIT]")
                                        self.intent="goodbye"
                                        break
                                    elif (rr[0].lower()==self.inputs["AcceptRequest"]["no"][self.language.lower()]):
                                        message="repeat"
                                        self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+message+"]")
                                        self.user_input=""
                                        self.exitingfromfreeze=1
                                        continue
                                    elif(rr[0]=="EXIT"):
                                        self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:[EXIT]")
                                        self.user_input=""
                                        self.exitingfromfreeze=1
                                        break
                                else:
                                    self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:[EXIT]")
                                    self.intent="goodbye"
                                    break

                        if self.intent=="goodbye":
                            break

                        self.checkActions()
                        if self.intent=="action":
                            if(self.choice is None):
                                self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                            self.sp.say(self.confirm, speech.TAGS[16])
                            if self.sp._input==2:
                                self.gothread = True
                                opts = [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]]
                                thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
                                thr.start()
                            rt= self.choice.giveChoiceMultiPage(self.inputs["Chitchat"]["action_confirm"][self.language.lower()], [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                            self.gothread = False
                            rt = [unicode(rt[0], "utf-8"), rt[1]]
                            self.sp.userSaid(str(rt))
                            
                            if(rt[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                                self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:[EXIT]")
                                break
                            elif(rt[0].lower()==self.inputs["AcceptRequest"]["no"][self.language.lower()]):
                                self.intent="talk"
                                #message="repeat\n"
                                #self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+message+"]")
                                #self.user_input=""
                                #self.exitingfromfreeze=1
                            else:
                                self.intent=""
                                self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:[EXIT]")
                                self.user_input=""
                                #self.exitingfromfreeze=1

                        if not self.user_input == None and not self.user_input == "" and self.freeze!=1 and self.intent=="talk":
                            for i in range(0, len(self.inputs["KEYWORDS"]["freeze"][self.language.lower()])):
                                if self.inputs["KEYWORDS"]["freeze"][self.language.lower()][i] in self.user_input:
                                    if(self.choice is None):
                                        self.classe="none"
                                        while(self.synchro==0):
                                            pass
                                        self.classe="choicemanager"
                                        self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                                    self.sent=random.choice(self.inputs["AcceptRequest"]["freeze"][self.language.lower()])
                                    self.sp.say(self.sent, speech.TAGS[16])
                                    if self.sp._input==2:
                                        self.gothread = True
                                        opts = [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]]
                                        thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
                                        thr.start()
                                    result=self.choice.giveChoiceMultiPage(self.inputs["AcceptRequest"]["freeze_cm"][self.language.lower()], [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                                    self.gothread = False
                                    result = [unicode(result[0], "utf-8"), result[1]]
                                    self.sp.userSaid(str(result))
                                    if(result[0]=="EXIT"):
                                        self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:[EXIT]")
                                        self.user_input=""
                                        self.exitingfromfreeze=1
                                        continue
                                    elif(result[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                                        self.sent=random.choice(self.inputs["AcceptRequest"]["freezed"][self.language.lower()])
                                        self.sp.say(self.sent, speech.TAGS[13])
                                        self.freeze=1
                                        self.user_input=""
                                        continue
                                    else:
                                        message=self.inputs["Chitchat"]["repeat"][self.language.lower()]
                                        self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+message+"]")
                                        self.user_input=""
                                        self.exitingfromfreeze=1
                                        continue
                    
                        if (self.user_input==None or self.user_input=="") and self.freeze!=1 and self.stype!="wait" and self.exitingfromfreeze==0 and self.intent=="talk":
                            if(self.choice is None):
                                self.classe="none"
                                while(self.synchro==0):
                                    pass
                                self.classe="choicemanager"
                                self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                            if self.loops==1:
                                self.gt=self.firsttimer
                            elif self.loops==2:
                                self.gt=self.firsttimer+120
                            else:
                                self.gt=self.firsttimer+360
                            self.sent=random.choice(self.inputs["Chitchat"]["canrepeat2"][self.language.lower()])
                            self.sp.say(self.sent, speech.TAGS[12])
                            self.sp.say(self.sentences[pointer], self.tag[pointer])
                            self.timing=1
                            t1 = threading.Thread(name="timer", target=self.goodbyetimer)
                            t1.start()
                            if self.sp._input==2:
                                self.gothread = True
                                opts = [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]]
                                thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
                                thr.start()
                            a=self.choice.giveChoiceMultiPage("", [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False, timer=self.gt+60)
                            self.gothread = False
                            a = [unicode(a[0], "utf-8"), a[1]]
                            self.timing=0
                            self.sp.userSaid(str(a))
                            self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+a[0]+"]")
                            self.ctopic=a[0]

                        elif not self.user_input == None and not self.user_input == "" and self.freeze!=1 and self.intent=="talk":
                            self.ctopic=self.user_input
                            self.user_input=""

                            if self.stype=="wait" and self.myflag==0 and "EXIT" not in self.ctopic:
                                self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:[xxxxxxx]")
                            else:
                                self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+self.ctopic+"]")
                   
                            self.ctopic=""

                pointer=pointer+1


            else:
            	if(first==True):
            		timecheck=time.time()
            		first=False
            	else:
            		if (time.time()-timecheck>30):
            			self.output_handler.writeSupplyMessage("publish", "D5.2", "chitchat:started")
            			time.sleep(0.1)
            			self.ctopic = self.ctopicb
            			self.output_handler.writeSupplyMessage("publish", "D5.2", "userSays:["+self.ctopic+"]")
            			first=True



        if (self.intent=="goodbye"):
            self.goal=1
            self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):\"n/a\"]")
            time.sleep(0.5)
            msg="(:goal(?G1 (robot-at pepper-1) charger))"
            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")

        elif (self.intent=="action"):
            self.performAction()

        
        self.end()
        return [self.goal,self.timeout]

    ## Method containing all the instructions that should be executing before terminating the action.
    def end(self):

        if self.choice is not None:
            self.choice.kill()
            caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
            del self.choice
            self.choice=None

        if self.state_rec==1:
            self.sASR.stopReco()
            caressestools.setAutonomousAbilities(self.session,False, True, True, True, True)
            self.state_rec=0
        elif self.state_rec==2:
            self.sASR.stopReco()
            self.state_rec=0


            
    	try:
        	self.asr.unsubscribe("Test_ASR")
        except:
        	pass
        self.cleanMemory()
        self.going=0
        self.closethread=0
        self.going=0

        for topic in self.sDialog.getAllLoadedTopics():
            self.sDialog.deactivateTopic(topic)
            self.sDialog.unloadTopic(topic)

        caressestools.setAutonomousAbilities(self.session, False, True, True, True, True)

    ##  Get the input from the user. According to the value of self.sp._input, the input can be taken through different ways: 0 - CONSOLE: the input is typed on the keyboard, 1 - PC: the input is given verbally to the pc microphone, 2 - SMARTPHONE: the input is given verbally to a smartphone microphone, 3 - ROBOT: the input is given verbally to the robot
    # @param sound_service (string) Google or Nuance.
    def getInput(self, sound_service):

        self.touched_for_options = False
        self.touched_bumper = False

        if self.sp._input == 0:
            self.user_input = self.sp.getInputFromKeyboard()
        elif self.sp._input == 1:
            self.user_input = self.sp.getInputFromMic()
        elif self.sp._input == 2:
            self.user_input = self.sp.getInputFromSmartphone()
        elif self.sp._input == 3:
            self.getInputFromGoogle()

    ##  Method used to get the user's feedback if the smartphone is used as an external microphone.
    # @param options (string) Possible user answers.
    def getOptionsFromSmartphone(self, options):

        self.confirmed=False
        
        try:
            options_str = [a.encode('ascii','ignore') for a in options]
        except:
            pass

        while(self.gothread):
            CahrimThreads.socket_handlers.InputMsgHandler.resetSmartphone()
            while (self.gothread and (CahrimThreads.socket_handlers.InputMsgHandler.getSmartphone() is None)):
                pass

            toret = CahrimThreads.socket_handlers.InputMsgHandler.getSmartphone() 
            CahrimThreads.socket_handlers.InputMsgHandler.resetSmartphone()
            if toret is not None and toret.lower() in map(str.lower,options_str) and toret is not "":
                self.sMemory.insertData("WordRecognized", ["<...> "+toret+" <...>", 1])

    ## Google Services may be used to retrieve the user's sentences
    def getInputFromGoogle(self):

        input=None
        input = self.sMemory.getData("Audio/RecognizedWords")
        start=time.time()
        mem=""
        exit=False
        self.signalID = self.tablet.onTouchUp.connect(self.onTabletTouch)
        self.touched_for_options = False
        interruptwait=False
        touched_during_yn=False
        self.confirmed=False
        result=["EXIT","1"]


        if self.freeze==1:
            while input == None or input == []:
                 input = self.sMemory.getData("Audio/RecognizedWords")
                 if not input == None and not input == []:
                    self.user_input = input[0][0].decode('utf-8')
                    self.touched_for_options=False
                    break
                 elif self.touched_for_options:
                    self.sp.userSaid("[TABLET TOUCHED]")
                    self.tablet.onTouchUp.disconnect(self.signalID)
                    if(self.choice is None):
                        self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                    if self.sp._input==2:
                        self.gothread = True

                        thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
                        thr.start()
                    result= self.choice.giveChoiceMultiPage(self.inputs["AcceptRequest"]["continue_cm"][self.language.lower()], [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                    self.gothread = False
                    result = [unicode(result[0], "utf-8"), result[1]]
                    self.user_input=str(result)
                    break

        elif self.stype=="wait":
            touch = self.sMemory.subscriber("TouchChanged")
            id_touch = touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))
            while(True):
                input = self.sMemory.getData("Audio/RecognizedWords")
                a=time.time()-start
                if not input == None and not input == [] and not input[0][0].decode('utf-8')==mem: 
                    start=time.time()
                    mem=input[0][0].decode('utf-8')
                    try:
                        mem=unicode(mem,"utf-8")
                    except:
                        pass

                    try:
                        print("INTERMEDIATE > " +mem)
                    except:
                        print("INFO: the user is talking")

                    for i in range(0, len(self.inputs["KEYWORDS"]["goodbye"][self.language.lower()])):
                        if self.inputs["KEYWORDS"]["goodbye"][self.language.lower()][i] in mem:
                            self.tablet.onTouchUp.disconnect(self.signalID)
                            if(self.choice is None):
                                self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                            self.sp.say(self.inputs["Chitchat"]["I_am_going"][self.language.lower()], speech.TAGS[16])
                            if self.sp._input==2:
                                self.gothread = True
                                thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone)
                                thr.start()
                            rr= self.choice.giveChoiceMultiPage(self.inputs["Chitchat"]["goodbye_confirm"][self.language.lower()], [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                            self.gothread = False
                            rr = [unicode(rr[0], "utf-8"), rr[1]]
                            self.sp.userSaid(str(rr))
                            if(rr[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                                interruptwait=True
                                exit=True
                                self.confirmed=True
                                mem = self.inputs["KEYWORDS"]["goodbye"][self.language.lower()][i]
                                self.touched_for_options=False
                                self.user_input=self.user_input+" " +mem
                                break
                            elif (rr[0].lower()==self.inputs["AcceptRequest"]["no"][self.language.lower()]):
                                self.confirmed=True
                                self.sp.say(random.choice(self.inputs["ADDITIONAL"]["ok"][self.language.lower()]), speech.TAGS[13])
                                self.signalID = self.tablet.onTouchUp.connect(self.onTabletTouch)
                                self.touched_for_options=False
                                mem=""
                                try:
                                    self.sMemory.removeData("Audio/RecognizedWords")
                                    self.initSoundService(self.soundService)
                                except:
                                    pass
                                continue
                            else:
                                self.touched_for_options==True
                                result=["EXIT","1"]
                                break 

                    if self.inputs["Chitchat"]["repeat"][self.language.lower()] in mem or self.inputs["KEYWORDS"]["revise"][self.language.lower()][0] in mem or self.inputs["KEYWORDS"]["freeze"][self.language.lower()][0] in mem or self.inputs["Chitchat"]["say_again"][self.language.lower()] in mem:
                        if self.inputs["Chitchat"]["repeat"][self.language.lower()] in mem or self.inputs["Chitchat"]["say_again"][self.language.lower()] in mem:
                            self.tablet.onTouchUp.disconnect(self.signalID)
                            if(self.choice is None):
                                self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                            self.sp.say(self.inputs["Chitchat"]["repeat_confirm"][self.language.lower()], speech.TAGS[16])
                            if self.sp._input==2:
                                self.gothread = True
                                thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone)
                                thr.start()
                            rr= self.choice.giveChoiceMultiPage(self.inputs["Chitchat"]["repeat_tablet"][self.language.lower()], [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                            self.gothread = False
                            rr = [unicode(rr[0], "utf-8"), rr[1]]
                            self.sp.userSaid(str(rr))
                            if(rr[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                                interruptwait=True
                                exit=True
                                mem = self.inputs["Chitchat"]["repeat"][self.language.lower()]
                                self.touched_for_options=False
                                self.user_input=self.user_input+" " +mem
                                break
                            elif (rr[0].lower()==self.inputs["AcceptRequest"]["no"][self.language.lower()]):
                                self.sp.say(random.choice(self.inputs["ADDITIONAL"]["ok"][self.language.lower()]), speech.TAGS[13])
                                self.signalID = self.tablet.onTouchUp.connect(self.onTabletTouch)
                                self.touched_for_options=False
                                mem=""
                                try:
                                    self.sMemory.removeData("Audio/RecognizedWords")
                                    self.initSoundService(self.soundService)
                                except:
                                    pass
                                continue
                            else:
                                self.touched_for_options==True
                                result=["EXIT","1"]
                                break
                        if self.inputs["KEYWORDS"]["revise"][self.language.lower()][0] in mem:
                            self.tablet.onTouchUp.disconnect(self.signalID)
                            if(self.choice is None):
                                self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                            self.sp.say(self.inputs["AcceptRequest"]["revise"][self.language.lower()][0], speech.TAGS[16])
                            if self.sp._input==2:
                                self.gothread = True
                                thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone)
                                thr.start()

                            rr= self.choice.giveChoiceMultiPage(self.inputs["AcceptRequest"]["revise_cm"][self.language.lower()], [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                            self.gothread = False
                            rr = [unicode(rr[0], "utf-8"), rr[1]]
                            self.sp.userSaid(str(rr))
                            if(rr[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                                interruptwait=True
                                exit=True
                                self.touched_for_options=False
                                self.user_input=self.user_input+" " +mem
                                break
                            elif (rr[0].lower()==self.inputs["AcceptRequest"]["no"][self.language.lower()]):
                                self.sp.say(random.choice(self.inputs["ADDITIONAL"]["ok"][self.language.lower()]), speech.TAGS[13])
                                self.signalID = self.tablet.onTouchUp.connect(self.onTabletTouch)
                                self.touched_for_options=False
                                mem=""
                                try:
                                    self.sMemory.removeData("Audio/RecognizedWords")
                                    self.initSoundService(self.soundService)
                                except:
                                    pass
                                continue
                            else:
                                self.touched_for_options==True
                                result=["EXIT","1"]
                                break
                        else:
                            interruptwait=True
                            exit=True

                    self.user_input=self.user_input+" " +mem
                    result=[self.user_input,"1.0"]
                    
                    for words in self.pepper:
                        if words in self.user_input:
                            exit=True

                elif self.touched_for_options:
                    self.sp.userSaid("[TABLET TOUCHED]")
                    self.tablet.onTouchUp.disconnect(self.signalID)
                    if(self.choice is None):
                        self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                    if self.sp._input==2:
                        self.gothread = True
                        thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone)
                        thr.start()    
                    result= self.choice.giveChoiceMultiPage("", [self.inputs["Chitchat"]["over_and_out_only"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                    self.gothread = False
                    result = [unicode(result[0], "utf-8"), result[1]]
                    exit=True
                if exit==True:
                    break
                if self.may_stop==True:
                    self.may_stop=False
                    start=time.time()-58.0
                if(time.time()-start>60.0):
                    self.user_input=self.user_input + " "+self.inputs["Chitchat"]["over_and_out_only"][self.language.lower()]
                    self.touched_for_options=False
                    break

        else:
            if(self.noisy=="noisy"):
                touch = self.sMemory.subscriber("LeftBumperPressed")
                id_touch = touch.signal.connect(functools.partial(self.onTouch, "LeftBumperPressed"))
            else:
                touch = self.sMemory.subscriber("TouchChanged")
                id_touch = touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))
            while input == None or input == []:
                input = self.sMemory.getData("Audio/RecognizedWords")
                if(time.time()-start>30.0):
                    self.touched_for_options=False
                    self.may_stop=False
                    break
                if not self.key == None:
                    self.user_input = self.key
                    self.touched_for_options=False
                    self.may_stop=False
                    break
                if self.may_stop==True:
                    touched_during_yn=True
                    self.may_stop=False
                    break
                if self.touched_for_options:
                    self.sp.userSaid("[TABLET TOUCHED]")
                    self.tablet.onTouchUp.disconnect(self.signalID)
                    self.sp.say(self.questionsaid, self.stag)
                    if(self.choice is None):
                        self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                    if self.sp._input==2:
                        self.gothread = True
                        thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone)
                        thr.start()
                    result= self.choice.giveChoiceMultiPage("", [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                    self.gothread = False
                    result = [unicode(result[0], "utf-8"), result[1]]
                    self.user_input=str(result)
                    break

                    

            if touched_during_yn==True:
                self.user_input="EXIT"

            elif not input == None and not input == []:
                self.user_input=input[0][0].decode('utf-8')
        try:
            self.user_input=unicode(self.user_input,"utf-8")
        except:
            pass

        self.sp.userSaid(self.user_input)

        if(self.touched_for_options and self.freeze==1):
            if (result[0]=="EXIT"):
                self.user_input=result[0]
            elif (result[0]==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                self.user_input="yes_EXXIT"
        elif(self.touched_for_options and self.stype=="wait"):
            if result[0]=="EXIT":
                self.user_input=result[0]
            else:
                self.user_input=self.user_input+" "+self.inputs["Chitchat"]["over_and_out_only"][self.language.lower()]
            try:
                result = [unicode(result[0], "utf-8"), result[1]]
            except:
                pass
            self.sp.userSaid(str(result))
        elif(interruptwait):
            self.user_input=mem
        elif (self.touched_for_options):
            self.user_input=result[0]

    ## Callback function
    def onTabletTouch(self, x, y):
        self.touched_for_options = True

    ## Nuance Services may be used to retrieve the user's sentences
    def getInputFromNuance(self):

        self.user_input = self.sMemory.getData("caresses/user_input")

    ## Clean the memory and subscribe again otherwise you keep getting the same user_input lots of times
    def cleanMemory(self):

        try:
            self.sMemory.removeData("Audio/RecognizedWords")
            self.sMemory.removeData("WordRecognized")
        except:
            pass
        try:
            self.sMemory.removeData("caresses/user_input")
            self.sDialog.unsubscribe("free_speech_dialog")
            self.sMemory.unsubscribe("WordRecognized")
        except:
            pass

    # The method checks if the user had the intention of performing an action
    def checkActions(self):
        for entry in self.inputDict.keys():
            if "action" in entry:
                for req_par_1 in self.inputDict[entry]["request_parameters_1"]:
                    if req_par_1.lower() in " " + self.user_input.lower()+" *":
                        for req_par_2 in self.inputDict[entry]["request_parameters_2"]:
                            if req_par_2.lower() in " " + self.user_input.lower()+" *":
                                self.intent="action"
                                self.action = self.inputDict[entry]["id_request"]
                                self.confirm = self.inputDict[entry]["confirmation"]

    # The method handles the user's request of performing an action
    def performAction(self):
        self.sentence=random.choice(self.inputs["AcceptRequest"]["achievegoal"][self.language.lower()])
        self.sp.say(self.sentence, speech.TAGS[13])
        self.goal=1
        if ("n/a" in self.action):
            if ("robot-at" in self.action):
                msg="(:goal(?G1 ("+self.action+"))"
                self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):precharger]")
                time.sleep(0.5)

            elif ("object-at-na" in self.action):
                msg="(:goal(?G1 "+self.action+" true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"


                if(self.choice is None):
                    self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                self.getInputFromChoiceManagerObjects(self.inputs["Chitchat"]["move_object_t"][self.language.lower()])
                if self.tobese is not "EXIT":
                    msg=msg.replace("\"n/a\"", self.tobese)
                else:
                    msg = "EXIT"
                    self.goal=0

                self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):precharger]")
                time.sleep(0.5)
            elif ("remind-object-position" in self.action):
                msg="(:goal(?G1 "+self.action+" true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"
                if(self.choice is None):
                    self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                self.getInputFromChoiceManagerObjects(self.inputs["Chitchat"]["remind_object_t"][self.language.lower()])
                if self.tobese is not "EXIT":
                    msg=msg.replace("\"n/a\"", self.tobese)
                else:
                    msg = "EXIT"
                    self.goal=0
            elif ("help-with-meal" in self.action):
                msg="(:goal(?G1 "+ self.action+" true))"
                msg=msg.replace("\"n/a\"", self.inputs["Chitchat"]["meal_keyword"][self.language.lower()])
            else:
                msg="(:goal(?G1 "+self.action+" true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"
                #msg=msg.replace("\"n/a\"", "meal")
        else:
            if "help-with-ritual" in self.action or "help-with-dressing" in self.action or "help-with-exercise" in self.action:
                msg="(:goal(?G1 "+self.action+" true))"
            elif ("provide-privacy" in self.action):
                msg="(:goal(?G1 "+self.action+" true)(?G2 react-sound true))(:temporal(before ?G1 ?G2 [1500 inf]))"
            else:
                msg="(:goal(?G1 "+self.action+" true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"

        if msg is not "EXIT" and (DetectUserDepth.isUserApproached() or "robot-at" in msg or "object-at-na" in msg):
            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
        elif "?G1" in msg and "?G2" in msg:
            msg="(:goal(?G1 (approached-user pepper-1) true)(?G2"+msg.split("?G1")[1].split("?G2")[0]+"?G3"+msg.split("?G2")[1]+"?G2 [1500 inf])(before ?G2 ?G3 [1500 inf]))"
            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
        elif  "?G1" in msg:
            msg="(:goal(?G1 (approached-user pepper-1) true)(?G2"+msg.split("?G1")[1].split("))")[0]+"))(:temporal(before ?G1 ?G2 [1500 inf]))"
            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
        elif msg == "EXIT":
            if(self.myflag!=1):
                if DetectUserDepth.isUserApproached():
                    self.output_handler.writeSupplyMessage("publish","D5.1","[(:goal(?G1 accept-request true))]")
                else:
                    msg2="(:goal(?G1 accept-request true))"
                    msg2="(:goal(?G1 (approached-user pepper-1) true)(?G2"+msg2.split("?G1")[1].split("))")[0]+"))(:temporal(before ?G1 ?G2 [1500 inf]))"
                    self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg2+"]")

    ## Method used to obtain additional information from the user, in a specific context, i.e. when the user requests to execute the MoveObject Action or the RemindObject action.
    # @param tabletview (string) The goal requested by the user.
    def getInputFromChoiceManagerObjects(self, tabletview):
        display=[]
        for i in range(0, len(self.CMoptions["IDs"])):
            if (self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["tablet-view"])==tabletview:
                a=i
                for j in range (0, len(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[a]]["options"]["full"])):
                    display.append(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[a]]["options"]["full"][j])

        if self.sp._input==2:
            self.gothread = True
            thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone)
            thr.start()
        self.result2= self.choice.giveChoiceMultiPage(self.inputs["AcceptRequest"]["cm_q2"][self.language.lower()], display, confidence=0.50, bSayQuestion=False)
        self.gothread = False
        self.result2 = [unicode(self.result2[0], "utf-8"), self.result2[1]]
        self.sp.userSaid(str(self.result2))
        for i in range (0, len(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[a]]["options"]["IDs"])):
            if(self.result2[0]==self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[a]]["options"]["full"][i]):
                self.tobese=self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[a]]["options"]["IDs"][i]
                break
            else:
                self.tobese="EXIT"

    ## Method to initialize the Speech Recognition
    # @param sound_service Either Google or Nuance
    def initSoundService(self, sound_service):

        if sound_service.lower() == "google":
            self.initGoogleRecognition()
        elif sound_service.lower() == "nuance":
            self.initNuanceRecognition()

    ## Method to initialize the Google Speech Recognition
    def initGoogleRecognition(self):

        # If the action previously ended in a wrong away, clean up the memory
        try:
            self.sMemory.removeData("Audio/RecognizedWords")
        except:
            pass

        # Subscribe to the microevent "Audio/RecognizedWords", raised by AbcdkSoundReceiver.py inside the _processRemote()
        # function whenever a sentence is recognized by Google services
        self.sMemory.subscriber("Audio/RecognizedWords")

    ## Method to initialize the Nuance Speech Recognition
    def initNuanceRecognition(self):

        topic_name = "mytopic"

        # If the action previously ended in a wrong away, clean up the memory
        try:
            self.sDialog.deactivateTopic(topic_name)
            self.sDialog.unloadTopicContent(topic_name)
            self.sMemory.removeData("caresses/user_input")
            self.sDialog.unsubscribe("free_speech_dialog")
        except:
            pass

        topicContent = ("topic: ~%s()\n"
                        "language: %s\n"
                        "#Catch everything\n"
                        "u:(_*) $caresses/user_input=$1\n" % (topic_name, caressestools.Language.lang_qichat))

        self.sDialog.loadTopicContent(topicContent)
        self.sDialog.activateTopic(topic_name)
        self.sDialog.subscribe("free_speech_dialog")
        self.sMemory.subscriber("caresses/user_input")

    ## Event handlers
    def onTouch(self, msg, value):
        self.may_stop = True


if __name__ == "__main__":
    import argparse
    import qi
    print("\nBe sure to have the CKB and the Pepper ASR running before launching the Chitchat action\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default=caressestools.Settings.robotIP,
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559, help="Naoqi port number")

    args = parser.parse_args()
    session = qi.Session()
    session.connect("tcp://" + args.ip + ":" + str(args.port))

    caressestools.Settings.robotIP = args.ip

    print("\nConnected to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) + ".\n")
    cpar = "1.0 100 1.0 English Sonali"
    apar = "The_Diwali_Festival 1"
    action = ChitChat(apar, cpar, session, None)
    action.run()

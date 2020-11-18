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
import time
import functools
import caressestools.caressestools as caressestools
import socket
import time
import os
import random
import string
import action
import json
from caressestools.multipage_choice_manager import MultiPageChoiceManager
from caressestools.speech import CAHRIM_KILL_ACTION, KillAction
from chitchat import ChitChat
from collections import OrderedDict
import csv
import threading
import caressestools.speech as speech
import sys
from CahrimThreads.sensory_hub import DetectUserDepth
import CahrimThreads.socket_handlers

JSON_FILEPATH= "ActionsLib/caressestools/speech_conf.json"
action_json="ActionsLib/parameters/accept_request.json"
triggering_keywords= "../CKB/triggering_keyword.json"
resume_file="../CKB/resume.csv"


## Class "CommandManager".
#
#  Class used by the AcceptRequest Action, that allows the robot to interact with the users, proposing activities, accepting their requests and launching the Chitchat Action.
class CommandManager(object):

    ## The constructor.
    # @param self The object pointer.
    # @param apar ---
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param output_handler () Handler of the output socket messages.
    # @param cultural (string) Interaction's mode, either "experimental" or "control".
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, output_handler, cultural, asr):

        self.session           = session
        self.apar = apar.split(' ')
        self.cpar = cpar.split(' ')
        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].title().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.back_max_waiting_time = float(self.cpar[5])
        self.max_waiting_time = self.back_max_waiting_time
        self.allsugg = self.cpar[6].replace('"', '').split('&&')
        self.sugg=["" for x in range(len(self.allsugg))]
        self.options=["" for x in range(len(self.allsugg))]

        for index in range(0,len(self.allsugg)):
            if (len(self.allsugg[index].split('_'))>1):
                self.sugg[index]=self.allsugg[index].split('_')[0]
                self.options[index]=self.allsugg[index].split('_')[1]
            else:
                self.sugg[index]=self.allsugg[index].split('_')[0]
                self.options[index]="None"

        self.output_handler    = output_handler
        self.tts               = self.session.service("ALAnimatedSpeech")
        self.tts2              = session.service("ALTextToSpeech")
        self.sMemory           = self.session.service("ALMemory")
        self.sDialog	       = self.session.service("ALDialog")
        self.tablet            = self.session.service("ALTabletService")
        self.beep              = self.session.service("ALSpeechRecognition")
        self.sASR              = self.session.service("ASR2")
        self.tts2.setParameter("speed", self.speed)
        self.tts2.setParameter("pitchShift", self.pitch)
        self.tts2.setVolume(self.volume)
        self.tts2.setLanguage(self.language)
        self.sDialog.setLanguage(self.language)
        self.beep.setAudioExpression(False)
        self.user_input = None
        self.soundService = "google"
        self.initSoundService(self.soundService)
        with open(JSON_FILEPATH) as f:
            self.inputs = json.load(f)
        with open(action_json) as f:
            self.CMoptions = json.load(f)
        self.choice=None
        self.count=0
        self.letssay=""
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))
        self.triggertest=0
        self.tagsaved=""

        if cultural:
            self.firsttimer=100
        else:
            self.firsttimer=580

        self.firsttopic=6
        self.asr = asr

    ## Timer used to stop the ChoiceManager
    def goodbyetimer(self):
        self.start=time.time()
        self.timeout=0
        while(self.waiting):
            if(time.time()-self.start>self.gt):
                 self.timeout=1
                 self.sMemory.insertData("WordRecognized", ["<...> " + self.inputs["AcceptRequest"]["no"][self.language.lower()] + " <...>",1.0])
                 break
            else:
                time.sleep(1)

    ## Method for starting the interaction
    # @param inputDict The input refined by the request_parser.
    def start(self, inputDict):

        self.inputDict = inputDict
        self.request()

    ## The robot suggests activities to the user
    def saysugg(self):
        self.rr=self.rr+1
        if self.rr==2:
            self.rr=0

        if self.iteration==1:
            self.gt=self.firsttimer
        elif self.iteration==2:
            self.gt=self.firsttimer+120
        elif self.iteration==3:
            self.gt=self.firsttimer+360
        
        if self.iteration==4:
            pass
        else:
            if self.rr==1:
                display_temp=[]
                display=[]
                keywords=[]
                indice=0
                time.sleep(1)
                with open(resume_file,'rb') as f:
                    reader=csv.reader(f)
                    for row in reader:
                        if row[1]==row[2] and indice!=0 and row[3]!="0.0":
                            display_temp.append(row[0])
                        indice=indice+1

                for i in range(self.firsttopic, len(display_temp)):
                    if display_temp[i]=="BELIEFANDVALUE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][0])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][0])
                    if display_temp[i]=="HISTORICFACTORPERIOD":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][1])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][1])
                    if display_temp[i]=="HOBBY":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][2])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][2])
                    if display_temp[i]=="DAILYROUTINE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][3])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][3])
                    if display_temp[i]=="CELEBRATINGEVENTS":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][4])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][4])
                    if display_temp[i]=="HEALTH":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][5])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][5])
                    if display_temp[i]=="USERPREFERENCE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][6])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][6])
                    if display_temp[i]=="LIFE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][7])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][7])
                    if display_temp[i]=="PHYSICALENVIRONMENT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][8])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][8])
                    if display_temp[i]=="ROBOT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][9])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][9])
                    if display_temp[i]=="SOCIALENVIRONMENT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][10])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][10])

                for i in range(0, self.firsttopic):
                    if display_temp[i]=="BELIEFANDVALUE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][0])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][0])
                    if display_temp[i]=="HISTORICFACTORPERIOD":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][1])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][1])
                    if display_temp[i]=="HOBBY":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][2])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][2])
                    if display_temp[i]=="DAILYROUTINE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][3])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][3])
                    if display_temp[i]=="CELEBRATINGEVENTS":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][4])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][4])
                    if display_temp[i]=="HEALTH":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][5])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][5])
                    if display_temp[i]=="USERPREFERENCE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][6])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][6])
                    if display_temp[i]=="LIFE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][7])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][7])
                    if display_temp[i]=="PHYSICALENVIRONMENT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][8])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][8])
                    if display_temp[i]=="ROBOT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][9])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][9])
                    if display_temp[i]=="SOCIALENVIRONMENT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][10])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][10])

                self.randomtopic=self.randomtopic+1
                CahrimThreads.socket_handlers.InputMsgHandler.increaseCounter2()
                if(self.randomtopic==len(display)):
                    self.randomtopic=0
                    CahrimThreads.socket_handlers.InputMsgHandler.zeroCounter2()
                randtop=keywords[self.randomtopic]
                self.chat_cpar = str(self.volume)+" "+str(self.speed)+" "+str(self.pitch)+" "+self.language+" "+self.username
                self.chat_apar = randtop+" "+str(self.iteration)
                
                caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                newAction = ChitChat(self.chat_apar, self.chat_cpar, self.session, self.output_handler, self.asr)
                newAction.calledbyar()
                ret=newAction.run()
                self.goaltest= ret[0]
                if(ret[1]==1):
                    self.iteration=self.iteration+1
                else:
                    self.iteration=1
                self.start = time.time()

                if(self.goaltest==0):
                    caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                    self.rr=1
                    self.start=time.time()
                    self.initSoundService(self.soundService)
                    self.saysugg()

            else:
                self.tosugg=self.tosugg+1
                CahrimThreads.socket_handlers.InputMsgHandler.increaseCounter()
                if self.tosugg==len(self.sugg):
                    self.tosugg=0
                    CahrimThreads.socket_handlers.InputMsgHandler.zeroCounter()
                self.sentence=random.choice(self.inputs["AcceptRequest"]["waitrequest"][self.language.lower()])
                self.sp.say(self.sentence, speech.TAGS[20])
                self.tagsaved=speech.TAGS[20]
                tosugg=self.tosugg
                self.sentence=self.inputs["AcceptRequest"]["backup_sentence"][self.language.lower()]
                try:
                    if((self.options[tosugg])=="None"):
                        self.sentence=random.choice(self.inputs["AcceptRequest"]["suggestion"][self.language.lower()])+" "+ self.CMoptions["IDs"][self.sugg[tosugg]]["full"]
                    else:
                        for x in range(0,len(self.CMoptions["IDs"][self.sugg[tosugg]]["options"]["IDs"])):
                            if((self.CMoptions["IDs"][self.sugg[tosugg]]["options"]["IDs"][x])==self.options[tosugg]):
                                if self.language.lower() == "japanese":
                                    self.sentence=random.choice(self.inputs["AcceptRequest"]["suggestion"][self.language.lower()])+ " "+ self.CMoptions["IDs"][self.sugg[tosugg]]["options"]["full"][x] + " "+ self.CMoptions["IDs"][self.sugg[tosugg]]["full"]
                                else:
                                    self.sentence=random.choice(self.inputs["AcceptRequest"]["suggestion"][self.language.lower()])+ " "+ self.CMoptions["IDs"][self.sugg[tosugg]]["full"] + " "+ self.CMoptions["IDs"][self.sugg[tosugg]]["options"]["full"][x]
                except:
                    pass

                for i in xrange(0,len(self.inputs["AcceptRequest"]["replacement"][self.language.lower()]),2):
                    replaced=self.sentence.replace(self.inputs["AcceptRequest"]["replacement"][self.language.lower()][i],self.inputs["AcceptRequest"]["replacement"][self.language.lower()][i+1])



                self.sp.say(replaced, speech.TAGS[22])
                self.tagsaved=speech.TAGS[22]
                self.user_input= ""
                self.initSoundService(self.soundService)


                for entry in self.inputDict.keys():
                    if "action" in entry:
                        if self.inputDict[entry]["id_request"].split(" ")[0] in self.CMoptions["IDs"][self.sugg[tosugg]]["pddl"]:
                            self.letssay= self.inputDict[entry]["request_parameters_1"][0] + " " + self.inputDict[entry]["request_parameters_2"][0]

    ## Method that handles the interaction with the user
    def request(self):

        self.tts2.setLanguage(self.language)
        self.tts2.setParameter("speed", self.speed)
        self.tts2.setParameter("pitchShift", self.pitch)
        self.tts2.setVolume(self.volume)
        self.beep.setAudioExpression(False)
        self.choice=None
        self.initSoundService(self.soundService)
        self.going=1
        self.timeout=0
        self.letssay=""
        self.iteration=1
        self.rr=random.choice(range(0,2))
        self.tosugg=CahrimThreads.socket_handlers.InputMsgHandler.getCounter()
        self.randomtopic=CahrimThreads.socket_handlers.InputMsgHandler.getCounter2()
        self.isproposal=True
        data=[]
        self.goaltest=0
        self.intent=""

        if (CahrimThreads.socket_handlers.InputMsgHandler.triggerCheck()):
            self.triggertest=1
            CahrimThreads.socket_handlers.InputMsgHandler.triggerDone()

        if(self.triggertest==0):
            stringtosay = random.choice(self.inputs["AcceptRequest"]["hello"][self.language.lower()])
            self.sp.say(stringtosay, speech.TAGS[20])
            self.tagsaved=speech.TAGS[20]
            self.saysugg()

        self.par1=""
        self.par2=""
        self.start = time.time()
        self.freeze=0

        while (self.going):
            if self.iteration==1:
                self.gt=self.firsttimer
            elif self.iteration==2:
                self.gt=self.firsttimer+120
            elif self.iteration==3:
                self.gt=self.firsttimer+360
            else:
                self.sentence=random.choice(self.inputs["ADDITIONAL"]["ok"][self.language.lower()])
                self.sp.say(self.sentence, speech.TAGS[20])
                self.tagsaved=speech.TAGS[20]
                msg="(:goal(?G1 (robot-at pepper-1) charger))"

                self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):precharger]")
                time.sleep(0.5)


                self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                break

            if self.goaltest==1:
                break
            ''' check if dialogue is triggered'''
            if (CahrimThreads.socket_handlers.InputMsgHandler.triggerCheck()):
                self.triggertest=1
                CahrimThreads.socket_handlers.InputMsgHandler.triggerDone()
            '''check if the robot is freezed and it should be unblocked'''
            if self.freeze==1:
                self.initSoundService(self.soundService)
                self.sASR.startReco(caressestools.Language.lang_naoqi, False, False)
                self.getInput(self.soundService)
                self.sASR.stopReco()

                if not self.sp._input in [0, 3]:
                    self.sp.userSaid(self.user_input)

                if self.max_waiting_time==0:
                    self.max_waiting_time=self.back_max_waiting_time
                    self.user_input=self.inputs["KEYWORDS"]["continue"][self.language.lower()][0]
                if not self.user_input == None and not self.user_input == "":
                    if self.inputs["KEYWORDS"]["continue"][self.language.lower()][0] in self.user_input:
                        if(self.choice is None):
                            self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                        self.sentence=random.choice(self.inputs["AcceptRequest"]["continue"][self.language.lower()])
                        self.sp.say(self.sentence, speech.TAGS[21])
                        self.tagsaved=speech.TAGS[21]
                        result=self.checkConfirmation(self.inputs["AcceptRequest"]["continue_cm"][self.language.lower()])
                        if(result[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()] or result[0]=="EXIT"):
                            self.freeze=0
                            self.start=time.time()
                            self.saysugg()
                            continue

            elif time.time() - self.start >= float(self.max_waiting_time):
                self.max_waiting_time=self.back_max_waiting_time
                if (self.touched_for_options):
                    result=[self.inputs["AcceptRequest"]["yes"][self.language.lower()],""]
                    self.iteration=1
                else:
                    if(self.choice is None):
                        self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                    self.sentence=random.choice(self.inputs["AcceptRequest"]["waitingtime"][self.language.lower()])
                    if(self.isproposal):
                        self.sp.say(self.sentence, speech.TAGS[22])
                        self.tagsaved=speech.TAGS[22]
                    else:
                        self.sp.say(self.sentence, speech.TAGS[21])
                        self.tagsaved=speech.TAGS[21]
                        self.isproposal=True
                    self.waiting=1
                    t1 = threading.Thread(name="timer", target=self.goodbyetimer)
                    t1.start()
                    result=self.checkConfirmation(self.inputs["AcceptRequest"]["options_cm"][self.language.lower()])

                if(result[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                    self.iteration=1
                    self.waiting=0
                    if(self.choice is None):
                        self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                    self.getInputFromChoiceManager()
                    if(self.result[0]==self.inputs["AcceptRequest"]["Chitchat"][self.language.lower()] and self.result2[0]!="EXIT"):
                        self.chat_cpar = str(self.volume)+" "+str(self.speed)+" "+str(self.pitch)+" "+self.language+" "+self.username
                        self.chat_apar = self.tobese+" "+str(self.iteration)
                        if (self.choice!=None):
                            self.choice.kill()
                            caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                            del self.choice
                            self.choice=None
                        caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                        newAction = ChitChat(self.chat_apar, self.chat_cpar, self.session, self.output_handler, self.asr)
                        newAction.calledbyar()
                        ret=newAction.run()
                        self.goaltest= ret[0]
                        if(ret[1]==1):
                            self.iteration=self.iteration+1
                        else:
                            self.iteration=1
                        if self.goaltest==1:
                            break
                        self.rr=1
                        caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                        self.start=time.time()
                        self.initSoundService(self.soundService)
                        self.saysugg()
                        continue

                    elif(self.result[0]!="EXIT" and self.result2[0]!="EXIT" and self.result[0]!=self.inputs["AcceptRequest"]["no"][self.language.lower()]):
                        #vedere input choice manager per azione
                        self.sentence=random.choice(self.inputs["AcceptRequest"]["achievegoal"][self.language.lower()])
                        self.sp.say(self.sentence, speech.TAGS[20])
                        self.tagsaved=speech.TAGS[20]
                        chunks = self.msg.split('?')
                        if(self.result2[0]==self.inputs["AcceptRequest"]["other"][self.language.lower()]):
                            self.result2[0]=""

                        if ("object-at" in self.msg):
                            self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):precharger]")
                            time.sleep(0.5)

                        if ("robot-at" in self.msg):
                            self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):precharger]")
                            time.sleep(0.5)

                            if(self.result2[0]!=""):
                                mess=chunks[0]+"?"+chunks[1] + self.tobese+"))"
                            else:
                                mess=chunks[0]+"?"+chunks[1] + "\"n/a\"))"
                        else:
                            if((len(chunks)==3) and self.result2[0]!=""):
                                mess=chunks[0]+"?"+chunks[1]+self.tobese+") true))"
                            elif ((len(chunks)==3) and "help-with-meal" in self.msg):
                                mess=chunks[0]+"?"+chunks[1]+"meal) true))"
                            elif ((len(chunks)==3)):
                                mess=chunks[0]+"?"+chunks[1]+"\"n/a\") true))"
                            elif ((len(chunks)<=5)):
                                mess=self.msg
                            elif ((len(chunks)==6) and self.result2[0]!=""):
                                mess=chunks[0]+"?"+chunks[1]+self.tobese+") true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"
                            elif ((len(chunks)==6)):
                                mess=chunks[0]+"?"+chunks[1]+"\"n/a\") true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"
                            elif ((len(chunks)==7) and self.result2[0]!=""):
                                mess=chunks[0]+"?"+chunks[1]+self.tobese+" \"n/a\") true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"
                            elif ((len(chunks)==7)):
                                mess=chunks[0]+"?"+chunks[1]+"\"n/a\" \"n/a\") true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"
                            elif ((len(chunks)==8) and self.result2[0]!=""):
                                mess=chunks[0]+"?"+chunks[1]+self.tobese+"\"n/a\" \"n/a\") true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"
                            elif ((len(chunks)==8)):
                                mess=chunks[0]+"?"+chunks[1]+"\"n/a\" \"n/a\" \"n/a\") true)(?G2 accept-request true))(:temporal(before ?G1 ?G2 [1500 inf]))"
                        if DetectUserDepth.isUserApproached() or "robot-at" in mess or "object-at-na" in mess:
                            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+mess+"]")
                        elif "?G1" in mess and "?G2" in mess:
                                #messs="approached-user:false"
                                #self.output_handler.writeSupplyMessage("publish", "D6.1", "["+messs+"]")
                                #time.sleep(0.2)
                                mess="(:goal(?G1 (approached-user pepper-1) true)(?G2"+mess.split("?G1")[1].split("?G2")[0]+"?G3"+mess.split("?G2")[1].split("inf])")[0]+"?G2 [1500 inf])(before ?G2 ?G3 [1500 inf]))"
                                self.output_handler.writeSupplyMessage("publish", "D5.1", "["+mess+"]")
                        elif  "?G1" in mess:
                                #messs="approached-user:false"
                                #self.output_handler.writeSupplyMessage("publish", "D6.1", "["+messs+"]")
                                #time.sleep(0.2)
                                mess="(:goal(?G1 (approached-user pepper-1) true)(?G2"+mess.split("?G1")[1].split("))")[0]+"))(:temporal(before ?G1 ?G2 [1500 inf]))"
                                self.output_handler.writeSupplyMessage("publish", "D5.1", "["+mess+"]")

                        break

                    else:
                        self.saysugg()
                        self.start = time.time()
                else:
                    if(self.timeout!=1):
                        self.iteration=1
                        self.waiting=0
                        self.saysugg()
                    self.start = time.time()


            else:
                if(self.timeout==1):
                    self.timeout=0
                    self.iteration=self.iteration+1
                    if self.iteration==1:
                        self.gt=self.firsttimer
                    elif self.iteration==2:
                        self.gt=self.firsttimer+120
                    elif self.iteration==3:
                        self.gt=self.firsttimer+360

                    if self.iteration==4:
                        self.sentence=random.choice(self.inputs["ADDITIONAL"]["ok"][self.language.lower()])
                        self.sp.say(self.sentence, speech.TAGS[20])
                        self.tagsaved=speech.TAGS[20]
                        msg="(:goal(?G1 (robot-at pepper-1) charger))"
                        self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):\"n/a\"]")
                        time.sleep(0.5)
                        self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                        break
                    else:
                        self.saysugg()
                        self.start = time.time()

                if(self.triggertest==1):
                    self.triggertest=0
                    self.chat_cpar = str(self.volume)+" "+str(self.speed)+" "+str(self.pitch)+" "+self.language+" "+self.username
                    self.chat_apar = "doesntmatter 1"
                    if (self.choice!=None):
                        self.choice.kill()
                        caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                        del self.choice
                        self.choice=None
                    caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                    newAction = ChitChat(self.chat_apar, self.chat_cpar, self.session, self.output_handler, self.asr)
                    newAction.calledbyar()
                    ret=newAction.run()
                    self.goaltest= ret[0]
                    if(ret[1]==1):
                        self.iteration=self.iteration+1
                    else:
                        self.iteration=1
                    if self.goaltest==1:
                        break
                    self.rr=1
                    caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                    time.sleep(1)
                    if (CahrimThreads.socket_handlers.InputMsgHandler.triggerCheck()):
                        self.triggertest=1
                        CahrimThreads.socket_handlers.InputMsgHandler.triggerDone()
                    if(self.triggertest==0):
                        self.start=time.time()
                        self.saysugg()
                        self.initSoundService(self.soundService)
                    else:
                        self.start=time.time()
                        self.initSoundService(self.soundService)
                    continue

                if (self.iteration<4):
                    self.intent=""
                    self.start=time.time()
                    self.initSoundService(self.soundService)
                    self.sASR.startReco(caressestools.Language.lang_naoqi, False, False)
                    self.getInput(self.soundService)
                    self.sASR.stopReco()

                    if not self.sp._input in [0, 3]:
                        self.sp.userSaid(self.user_input)

                else:
                    self.sentence=random.choice(self.inputs["ADDITIONAL"]["ok"][self.language.lower()])
                    self.sp.say(self.sentence, speech.TAGS[20])
                    self.tagsaved=speech.TAGS[20]
                    msg="(:goal(?G1 (robot-at pepper-1) charger))"
                    self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):\"n/a\"]")
                    time.sleep(0.5)
                    self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                    break

                if not self.user_input == None and not self.user_input == "":
                    self.iteration=1

                    for i in range(0, len(self.inputs["KEYWORDS"]["yestosuggestion"][self.language.lower()])):
                        testsugg= " "+self.user_input+" "
                        if self.inputs["KEYWORDS"]["yestosuggestion"][self.language.lower()][i] in testsugg.lower():
                            self.user_input = self.letssay
                            self.letssay=""

                    self.tobesent=self.user_input
                    self.checkInputDict()

                    for i in range(0, len(self.inputs["KEYWORDS"]["revise"][self.language.lower()])):
                        if self.inputs["KEYWORDS"]["revise"][self.language.lower()][i] in self.user_input:
                            self.intent="revise"

                    for i in range(0, len(self.inputs["KEYWORDS"]["repeat_chitchat"][self.language.lower()])):
                        if self.inputs["KEYWORDS"]["repeat_chitchat"][self.language.lower()][i] in self.user_input:
                            self.intent="repeat"

                    for i in range(0, len(self.inputs["KEYWORDS"]["options2"][self.language.lower()])):
                        if self.inputs["KEYWORDS"]["options2"][self.language.lower()][i] in self.user_input:
                            self.intent="options"

                    for i in range(0, len(self.inputs["KEYWORDS"]["freeze"][self.language.lower()])):
                        if self.inputs["KEYWORDS"]["freeze"][self.language.lower()][i] in self.user_input:
                            self.intent="freeze"

                    for i in range(0, len(self.inputs["KEYWORDS"]["goodbye"][self.language.lower()])):
                        if self.inputs["KEYWORDS"]["goodbye"][self.language.lower()][i] in self.user_input:
                            self.intent="goodbye"

                    for i in range(0, len(self.inputs["KEYWORDS"]["stopaction"][self.language.lower()])):
                        if self.inputs["KEYWORDS"]["stopaction"][self.language.lower()][i] in self.user_input:
                            self.intent="goodbye2"

                    if self.inputs["KEYWORDS"]["switchculture"][self.language.lower()] in self.user_input:
                        self.intent="switch"

                    self.user_input= ""


                    if self.intent=="switch":
                        if(self.choice is None):
                            self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                        display=[]
                        self.sentence=self.inputs["AcceptRequest"]["switch1"][self.language.lower()]
                        self.sp.say(self.sentence,speech.TAGS[22])
                        self.tagsaved=speech.TAGS[22]
                        question= self.inputs["AcceptRequest"]["switch1tab"][self.language.lower()]
                        if self.sp._input==2:
                            self.gothread = True
                            opts=[self.inputs["AcceptRequest"]["england"][self.language.lower()], self.inputs["AcceptRequest"]["india"][self.language.lower()],self.inputs["AcceptRequest"]["japan"][self.language.lower()]]
                            thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
                            thr.start()
                        a=self.choice.giveChoiceMultiPage(question, [self.inputs["AcceptRequest"]["england"][self.language.lower()], self.inputs["AcceptRequest"]["india"][self.language.lower()],self.inputs["AcceptRequest"]["japan"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                        self.gothread = False
                        a = [unicode(a[0], "utf-8"), a[1]]
                        self.sp.userSaid(str(a))
                        if a[0]==self.inputs["AcceptRequest"]["india"][self.language.lower()]:
                            st1="indian"
                        elif a[0]==self.inputs["AcceptRequest"]["japan"][self.language.lower()]:
                            st1="japanese"
                        else:
                            st1="english"

                        display=[]
                        self.sentence=self.inputs["AcceptRequest"]["switch2"][self.language.lower()]
                        self.sp.say(self.sentence,speech.TAGS[22])
                        self.tagsaved=speech.TAGS[22]
                        question= self.inputs["AcceptRequest"]["switch2tab"][self.language.lower()]
                        if self.sp._input==2:
                            self.gothread = True
                            opts=[self.inputs["AcceptRequest"]["english"][self.language.lower()], self.inputs["AcceptRequest"]["italian"][self.language.lower()],self.inputs["AcceptRequest"]["japanese"][self.language.lower()]]
                            thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
                            thr.start()
                        a=self.choice.giveChoiceMultiPage(question, [self.inputs["AcceptRequest"]["english"][self.language.lower()], self.inputs["AcceptRequest"]["italian"][self.language.lower()],self.inputs["AcceptRequest"]["japanese"][self.language.lower()]], confidence=0.50, bSayQuestion=False)
                        self.gothread = False
                        a = [unicode(a[0], "utf-8"), a[1]]
                        self.sp.userSaid(str(a))
                        if a[0]==self.inputs["AcceptRequest"]["italian"][self.language.lower()]:
                            st2="it"
                        elif a[0]==self.inputs["AcceptRequest"]["japanese"][self.language.lower()]:
                            st2="ja"
                        else:
                            st2="en"

                        stringtt="userSays[abracadabra_"+st1+"_"+st2+"]"
                        self.output_handler.writeSupplyMessage("publish", "D5.2", stringtt)
                        self.choice.kill()
                        caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                        del self.choice
                        self.choice=None
                        self.sentence=self.inputs["AcceptRequest"]["waitforswitch"][self.language.lower()]
                        self.sp.say(self.sentence,speech.TAGS[20])
                        break

                    if self.intent=="freeze":
                        if(self.choice is None):
                            self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                        self.sentence=random.choice(self.inputs["AcceptRequest"]["freeze"][self.language.lower()])
                        self.sp.say(self.sentence, speech.TAGS[21])
                        self.tagsaved=speech.TAGS[21]
                        result=self.checkConfirmation(self.inputs["AcceptRequest"]["freeze_cm"][self.language.lower()])
                        if(result[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                            self.sentence=random.choice(self.inputs["AcceptRequest"]["freezed"][self.language.lower()])
                            self.sp.say(self.sentence, speech.TAGS[20])
                            self.tagsaved=speech.TAGS[20]
                            self.freeze=1
                        else:
                            self.sentence=random.choice(self.inputs["AcceptRequest"]["noproblem"][self.language.lower()])
                            self.sp.say(self.sentence, speech.TAGS[20])
                            self.tagsaved=speech.TAGS[20]
                            self.saysugg()
                            self.start=time.time()
                            continue
                    elif self.intent=="revise":
                        if(self.choice is None):
                            self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                        self.sentence=random.choice(self.inputs["AcceptRequest"]["revise"][self.language.lower()])
                        self.sp.say(self.sentence, speech.TAGS[21])
                        self.tagsaved=speech.TAGS[21]
                        result=self.checkConfirmation(self.inputs["AcceptRequest"]["revise_cm"][self.language.lower()])
                        if(result[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):

                            self.chat_cpar = str(self.volume)+" "+str(self.speed)+" "+str(self.pitch)+" "+self.language+" "+self.username
                            self.chat_apar = self.tobesent.replace(' ', '_')+" "+str(self.iteration)
                            if (self.choice!=None):
                                self.choice.kill()
                                caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                                del self.choice
                                self.choice=None
                            caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                            newAction = ChitChat(self.chat_apar, self.chat_cpar, self.session, self.output_handler, self.asr)
                            newAction.calledbyar()
                            ret=newAction.run()
                            self.goaltest= ret[0]
                            if(ret[1]==1):
                                self.iteration=self.iteration+1
                            else:
                                self.iteration=1
                            if self.goaltest==1:
                                break
                            self.rr=1
                            caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                            self.start=time.time()
                            self.initSoundService(self.soundService)
                            self.saysugg()
                            continue
                        else:
                            self.sentence=random.choice(self.inputs["AcceptRequest"]["noproblem"][self.language.lower()])
                            self.sp.say(self.sentence, speech.TAGS[20])
                            self.tagsaved=speech.TAGS[20]
                            self.saysugg()
                            self.start=time.time()
                            continue

                    elif self.intent=="repeat":
                        justsaying=random.choice(self.inputs["AcceptRequest"]["repeat"][self.language.lower()])
                        self.sp.say(justsaying, speech.TAGS[20])
                        self.sp.say(self.sentence, self.tagsaved)
                        self.start=time.time()
                        continue
                    elif self.intent=="goodbye":
                        if(self.choice is None):
                            self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                        self.sentence=random.choice(self.inputs["AcceptRequest"]["goodbye"][self.language.lower()])
                        self.sp.say(self.sentence, speech.TAGS[21])
                        self.tagsaved=speech.TAGS[21]
                        result=self.checkConfirmation(self.inputs["AcceptRequest"]["goodbye_cm"][self.language.lower()])
                        if(result[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                            self.sentence=random.choice(self.inputs["ADDITIONAL"]["ok"][self.language.lower()])
                            self.sp.say(self.sentence, speech.TAGS[20])
                            self.tagsaved=speech.TAGS[20]
                            msg="(:goal(?G1 (robot-at pepper-1) charger))"
                            self.output_handler.writeSupplyMessage("publish", "D6.2", "[(robot-at pepper-1):\"n/a\"]")
                            time.sleep(0.5)
                            self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                            break
                        else:
                            self.sentence=random.choice(self.inputs["AcceptRequest"]["goodbye_no"][self.language.lower()])
                            self.sp.say(self.sentence, speech.TAGS[20])
                            self.tagsaved=speech.TAGS[20]
                            self.saysugg()
                            self.start=time.time()
                            continue

                    elif self.intent=="options":
                        self.start=-float(self.max_waiting_time)
                        self.isproposal=False
                        continue

                    elif self.intent=="goodbye2":
                        if(self.choice is None):
                            self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))
                        self.sentence=random.choice(self.inputs["AcceptRequest"]["goodbye"][self.language.lower()])
                        self.sp.say(self.sentence, speech.TAGS[21])
                        self.tagsaved=speech.TAGS[21]
                        result=self.checkConfirmation(self.inputs["AcceptRequest"]["goodbye_cm"][self.language.lower()])
                        if(result[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                            self.sentence=random.choice(self.inputs["ADDITIONAL"]["ok"][self.language.lower()])
                            self.sp.say(self.sentence, speech.TAGS[20])
                            self.tagsaved=speech.TAGS[20]
                            break
                        else:
                            self.sentence=random.choice(self.inputs["AcceptRequest"]["goodbye_no"][self.language.lower()])
                            self.sp.say(self.sentence, speech.TAGS[20])
                            self.tagsaved=speech.TAGS[20]
                            self.saysugg()
                            self.start=time.time()
                            continue

                    elif self.intent == "action":
                        if(self.choice is None):
                            self.choice = MultiPageChoiceManager(str(caressestools.Settings.robotIP))

                            #self.tts.say(random.choice(self.inputs["AcceptRequest"]["action_check"][self.language.lower()]) + str(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["confirmation"]) +"?")
                        self.sentence=self.confirm
                        self.sp.say(self.sentence, speech.TAGS[21])
                        self.tagsaved=speech.TAGS[21]

                        result=self.checkConfirmation(self.inputs["Chitchat"]["action_confirm"][self.language.lower()])
                        if(result[0].lower()==self.inputs["AcceptRequest"]["yes"][self.language.lower()]):
                            self.sentence=random.choice(self.inputs["AcceptRequest"]["achievegoal"][self.language.lower()])
                            self.sp.say(self.sentence, speech.TAGS[20])
                            self.tagsaved=speech.TAGS[20]
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

                            if DetectUserDepth.isUserApproached() or "robot-at" in msg or "object-at-na" in msg:
                                self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                            elif "?G1" in msg and "?G2" in msg:
                                #messs="approached-user:false"
                                #self.output_handler.writeSupplyMessage("publish", "D6.1", "["+messs+"]")
                                #time.sleep(0.2)
                                msg="(:goal(?G1 (approached-user pepper-1) true)(?G2"+msg.split("?G1")[1].split("?G2")[0]+"?G3"+msg.split("?G2")[1]+"?G2 [1500 inf])(before ?G2 ?G3 [1500 inf]))"
                                self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                            elif  "?G1" in msg:
                                #messs="approached-user:false"
                                #self.output_handler.writeSupplyMessage("publish", "D6.1", "["+messs+"]")
                                #time.sleep(0.2)
                                msg="(:goal(?G1 (approached-user pepper-1) true)(?G2"+msg.split("?G1")[1].split("))")[0]+"))(:temporal(before ?G1 ?G2 [1500 inf]))"
                                self.output_handler.writeSupplyMessage("publish", "D5.1", "["+msg+"]")
                            if msg == "EXIT":
                                self.sentence=random.choice(self.inputs["AcceptRequest"]["noproblem"][self.language.lower()])
                                self.sp.say(self.sentence, speech.TAGS[20])
                                self.tagsaved=speech.TAGS[20]
                                self.user_input= ""
                                self.initSoundService(self.soundService)
                                self.saysugg()
                                self.start=time.time()
                                continue   
                            break
                        elif (result[0]=="EXIT"):
                            self.sentence=random.choice(self.inputs["AcceptRequest"]["noproblem"][self.language.lower()])
                            self.sp.say(self.sentence, speech.TAGS[20])
                            self.tagsaved=speech.TAGS[20]
                            self.user_input= ""
                            self.initSoundService(self.soundService)
                            self.saysugg()
                            self.start=time.time()
                            continue   
                        else:
                            if(self.talk=="ok"):
                                self.sentence=random.choice(self.inputs["AcceptRequest"]["letstalk"][self.language.lower()])
                                #self.sp.say(self.sentence)
                                self.chat_cpar = str(self.volume)+" "+str(self.speed)+" "+str(self.pitch)+" "+self.language+" "+self.username
                                self.chat_apar = self.tobesent.replace(' ', '_')+" "+str(self.iteration)
                                if (self.choice!=None):
                                    self.choice.kill()
                                    caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                                    del self.choice
                                    self.choice=None
                                if self.choice!=None:
                                    self.choice.kill()
                                    caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                                    del self.choice
                                    self.choice=None
                                caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                                newAction = ChitChat(self.chat_apar, self.chat_cpar, self.session, self.output_handler, self.asr)
                                newAction.calledbyar()
                                ret=newAction.run()
                                self.goaltest= ret[0]
                                if(ret[1]==1):
                                    self.iteration=self.iteration+1
                                else:
                                    self.iteration=1
                                if self.goaltest==1:
                                    break
                                self.rr=1
                                caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                                self.start=time.time()
                                self.initSoundService(self.soundService)
                                self.saysugg()
                                continue
                            else:
                                self.sentence=random.choice(self.inputs["AcceptRequest"]["noproblem"][self.language.lower()])
                                self.sp.say(self.sentence, speech.TAGS[20])
                                self.tagsaved=speech.TAGS[20]
                                self.user_input= ""
                                self.initSoundService(self.soundService)
                                self.saysugg()
                                self.start=time.time()
                                continue

                    elif self.intent=="talk":
                        if(self.talk=="ok"):
                            self.sentence=random.choice(self.inputs["AcceptRequest"]["letstalk"][self.language.lower()])
                            #self.sp.say(self.sentence)
                            self.chat_cpar = str(self.volume)+" "+str(self.speed)+" "+str(self.pitch)+" "+self.language+" "+self.username
                            self.chat_apar = self.tobesent.replace(' ', '_')+" "+str(self.iteration)
                            if (self.choice!=None):
                                self.choice.kill()
                                caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                                del self.choice
                                self.choice=None
                            caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                            newAction = ChitChat(self.chat_apar, self.chat_cpar, self.session, self.output_handler, self.asr)
                            newAction.calledbyar()
                            ret=newAction.run()
                            self.goaltest= ret[0]
                            if(ret[1]==1):
                                self.iteration=self.iteration+1
                            else:
                                self.iteration=1
                            if self.goaltest==1:
                                break
                            self.rr=1
                            caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                            self.start=time.time()
                            self.initSoundService(self.soundService)
                            self.saysugg()
                            continue
                        else:
                            if(random.randint(1,5)==1):
                                self.chat_cpar = str(self.volume)+" "+str(self.speed)+" "+str(self.pitch)+" "+self.language+" "+self.username
                                self.chat_apar = self.tobesent.replace(' ', '_')+" "+str(self.iteration)
                                if (self.choice!=None):
                                    self.choice.kill()
                                    caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                                    del self.choice
                                    self.choice=None
                                caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                                newAction = ChitChat(self.chat_apar, self.chat_cpar, self.session, self.output_handler, self.asr)
                                newAction.calledbyar()
                                ret=newAction.run()
                                self.goaltest= ret[0]
                                if(ret[1]==1):
                                    self.iteration=self.iteration+1
                                else:
                                    self.iteration=1
                                if self.goaltest==1:
                                    break
                                self.rr=1
                                caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
                                self.start=time.time()
                                self.initSoundService(self.soundService)
                                self.saysugg()
                                continue
        self.stop()

    ## Method used to get a confirmation from the user in relation to a robot's question. The ChoiceManager is used to this aim.
    # @param question (string) The question posed by the robot.
    def checkConfirmation(self, question):
        if self.sp._input==2:
            self.gothread = True
            opts=[self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]]
            thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[opts])
            thr.start()
        a=self.choice.giveChoiceMultiPage(question, [self.inputs["AcceptRequest"]["yes"][self.language.lower()], self.inputs["AcceptRequest"]["no"][self.language.lower()]], confidence=0.50, bSayQuestion=False, timer=self.gt+60)
        self.gothread = False
        a = [unicode(a[0], "utf-8"), a[1]]
        if (self.timeout!=1):
            self.sp.userSaid(str(a))
        self.choice.kill()
        caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
        del self.choice
        self.choice=None
        return a

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
            thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[display])
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

        self.choice.kill()
        caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
        del self.choice
        self.choice=None

    ## The method is used when the robot should show all options on its tablet, and thus retrieve the user's feedback.
    def getInputFromChoiceManager(self):

        self.tobese="\"n/a\""

        display=[]
        self.sentence=random.choice(self.inputs["AcceptRequest"]["cm_question"][self.language.lower()])
        self.sp.say(self.sentence, speech.TAGS[22])
        self.tagsaved=speech.TAGS[22]

        for i in range(0, len(self.CMoptions["IDs"])):
            if self.CMoptions["IDs"].keys()[i] in self.sugg:
                display.append(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["tablet-view"])

        display.append(self.inputs["AcceptRequest"]["Chitchat"][self.language.lower()])

        for i in range(0, len(self.CMoptions["IDs"])):
            if self.CMoptions["IDs"].keys()[i] not in self.sugg:
                display.append(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["tablet-view"])

        if self.sp._input==2:
            self.gothread = True
            thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[display])
            thr.start()
        self.result= self.choice.giveChoiceMultiPage(self.inputs["AcceptRequest"]["cm_q1"][self.language.lower()], display, confidence=0.50, bSayQuestion=False)
        self.gothread = False
        self.result = [unicode(self.result[0], "utf-8"), self.result[1]]
        self.sp.userSaid(str(self.result))
        display=[]
        display_temp=[]
        keywords=[]
        self.result2=["",""];
        a=0;
        self.sMemory.removeData("WordRecognized")
        self.sMemory.removeData("tabletResponse")
        time.sleep(1)
        
        if (self.result[0]==self.inputs["AcceptRequest"]["Chitchat"][self.language.lower()]):
            indice=0
            with open(resume_file,'rb') as f:
                reader=csv.reader(f)
                for row in reader:
                    if row[1]==row[2] and indice!=0 and row[3]!="0.0":
                        display_temp.append(row[0])
                    indice=indice+1

            for i in range(self.firsttopic, len(display_temp)):
                    if display_temp[i]=="BELIEFANDVALUE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][0])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][0])
                    if display_temp[i]=="HISTORICFACTORPERIOD":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][1])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][1])
                    if display_temp[i]=="HOBBY":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][2])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][2])
                    if display_temp[i]=="DAILYROUTINE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][3])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][3])
                    if display_temp[i]=="CELEBRATINGEVENTS":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][4])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][4])
                    if display_temp[i]=="HEALTH":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][5])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][5])
                    if display_temp[i]=="USERPREFERENCE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][6])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][6])
                    if display_temp[i]=="LIFE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][7])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][7])
                    if display_temp[i]=="PHYSICALENVIRONMENT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][8])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][8])
                    if display_temp[i]=="ROBOT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][9])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][9])
                    if display_temp[i]=="SOCIALENVIRONMENT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][10])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][10])

            for i in range(0, self.firsttopic):
                    if display_temp[i]=="BELIEFANDVALUE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][0])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][0])
                    if display_temp[i]=="HISTORICFACTORPERIOD":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][1])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][1])
                    if display_temp[i]=="HOBBY":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][2])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][2])
                    if display_temp[i]=="DAILYROUTINE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][3])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][3])
                    if display_temp[i]=="CELEBRATINGEVENTS":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][4])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][4])
                    if display_temp[i]=="HEALTH":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][5])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][5])
                    if display_temp[i]=="USERPREFERENCE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][6])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][6])
                    if display_temp[i]=="LIFE":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][7])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][7])
                    if display_temp[i]=="PHYSICALENVIRONMENT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][8])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][8])
                    if display_temp[i]=="ROBOT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][9])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][9])
                    if display_temp[i]=="SOCIALENVIRONMENT":
                        display.append(self.inputs["AcceptRequest"]["display_to_be_appended"][self.language.lower()][10])
                        keywords.append(self.inputs["AcceptRequest"]["keywords_to_be_appended"][self.language.lower()][10])

        for i in range(0, len(self.CMoptions["IDs"])):
            if self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["tablet-view"]==self.result[0]:
                a=i
                if ("options" in self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]):
                    for j in range (0, len(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["options"]["full"])):
                       if self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["options"]["IDs"][j] in self.options:
                            display.append(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["options"]["full"][j])
                    for j in range (0, len(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["options"]["full"])):
                       if self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["options"]["IDs"][j] not in self.options:
                            display.append(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["options"]["full"][j])
                self.msg=self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[i]]["pddl"]
            

        if (self.result[0]==self.inputs["AcceptRequest"]["Chitchat"][self.language.lower()]):
            if self.sp._input==2:
                self.gothread = True
                thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[display])
                thr.start()
            self.result2= self.choice.giveChoiceMultiPage(self.inputs["AcceptRequest"]["cm_q2"][self.language.lower()], display, confidence=0.50, bSayQuestion=False)
            self.gothread = False
            self.result2 = [unicode(self.result2[0], "utf-8"), self.result2[1]]
            for i in range(0, len(keywords)):
                if (self.result2[0]==display[i]):
                    self.tobese=keywords[i]


        elif (len(display))>0:
            if self.sp._input==2:
                self.gothread = True
                thr = threading.Thread(name="getinput", target=self.getOptionsFromSmartphone, args=[display])
                thr.start()
            self.result2= self.choice.giveChoiceMultiPage(self.inputs["AcceptRequest"]["cm_q2"][self.language.lower()], display, confidence=0.50, bSayQuestion=False)
            self.gothread = False
            self.result2 = [unicode(self.result2[0], "utf-8"), self.result2[1]]
            for i in range (0, len(self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[a]]["options"]["IDs"])):
                if(self.result2[0]==self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[a]]["options"]["full"][i]):
                    self.tobese=self.CMoptions["IDs"][self.CMoptions["IDs"].keys()[a]]["options"]["IDs"][i]

        self.sp.userSaid(str(self.result2))

        self.choice.kill()
        caressestools.showImg(self.session, caressestools.TABLET_IMG_DEFAULT)
        del self.choice
        self.choice=None

    ## The method implements a strategy to detect the user's intention (perform actions or chitchatting) by checking keywords eventually contained in the pronounced sentence.
    def checkInputDict(self):
        self.intent="talk"
        self.talk=""
        for entry in self.inputDict.keys():
            if "action" in entry:
                for req_par_1 in self.inputDict[entry]["request_parameters_1"]:
                    if req_par_1.lower() in " "+self.user_input.lower()+" *":
                        for req_par_2 in self.inputDict[entry]["request_parameters_2"]:
                            if req_par_2.lower() in " "+self.user_input.lower()+" *":
                                self.intent="action"
                                self.action = self.inputDict[entry]["id_request"]
                                self.confirm = self.inputDict[entry]["confirmation"]


        for entry in self.inputDict.keys():
            if "talk" in entry:
                for req_par_1 in self.inputDict[entry]["request_parameters_1"]:
                    if req_par_1.lower() in self.user_input.lower()+" *":
                        for req_par_2 in self.inputDict[entry]["request_parameters_2"]:
                            if req_par_2.lower() in self.user_input.lower()+" *":
                                self.talk="ok"

    ## Clean the memory and subscribe again otherwise you keep getting the same user_input lots of times
    def cleanMemory(self):

        try:
            self.sMemory.removeData("Audio/RecognizedWords")
        except:
            pass
        try:
            self.sMemory.removeData("caresses/user_input")
            self.sDialog.unsubscribe("free_speech_dialog")
        except:
            pass

    ##   Get the input from the user. According to the value of self.sp._input, the input can be taken through different ways: 0 - CONSOLE: the input is typed on the keyboard, 1 - PC: the input is given verbally to the pc microphone, 2 - SMARTPHONE: the input is given verbally to a smartphone microphone, 3 - ROBOT: the input is given verbally to the robot
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

        try:
            options_str = [a.encode('ascii','ignore') for a in options]
        except:
            pass

        #self.output_handler.writeSupplyMessage("publish", "D11.6", "robotListens")

        while(self.gothread):
            CahrimThreads.socket_handlers.InputMsgHandler.resetSmartphone()
            while (self.gothread and (CahrimThreads.socket_handlers.InputMsgHandler.getSmartphone() is None)):
                pass

            toret = CahrimThreads.socket_handlers.InputMsgHandler.getSmartphone() 
            CahrimThreads.socket_handlers.InputMsgHandler.resetSmartphone()
            if toret is not None and toret.lower() in map(str.lower,options_str) and toret is not "":
                self.sMemory.insertData("WordRecognized", ["<...> "+toret+" <...>", 1])
            #elif toret is not None:
            #   self.output_handler.writeSupplyMessage("publish", "D11.6", "robotListens")

    ## Google Services may be used to retrieve the user's sentences
    def getInputFromGoogle(self):

        input=None
        input = self.sMemory.getData("Audio/RecognizedWords")
        self.start=time.time()
        self.signalID = self.tablet.onTouchUp.connect(self.onTabletTouch)
        self.touched_for_options = False
        self.touched_bumper=False
        touch = self.sMemory.subscriber("LeftBumperPressed")
        id_touch = touch.signal.connect(functools.partial(self.onTouch, "LeftBumperPressed"))

        while input == None or input == []:
            input = self.sMemory.getData("Audio/RecognizedWords")
            killed = self.checkIfKilled()
            if killed:
                raise KillAction
            if not input == None and not input == []:
                self.user_input=" "+input[0][0].decode('utf-8')+" "
            if time.time()-self.start > float(self.max_waiting_time):
                self.user_input=""
                break
            if self.touched_for_options:
                self.tablet.onTouchUp.disconnect(self.signalID)
                self.user_input="[TABLET TOUCHED]"
                self.max_waiting_time=0.0
                break
            if self.touched_bumper:
                self.user_input = self.inputs["KEYWORDS"]["switchculture"][self.language.lower()]
                break

        self.sp.userSaid(self.user_input)

        if(self.touched_for_options):
            self.user_input=""

    ## Callback function
    def onTabletTouch(self, x, y):
        self.touched_for_options = True

    ## Nuance Services may be used to retrieve the user's sentences
    def getInputFromNuance(self):
        self.user_input = self.sMemory.getData("caresses/user_input")

    ## Check if the dialog with the robot has been killed externally.
    # @return killed (Boolean) True if the dialog has been killed, False otherwise
    def checkIfKilled(self):
        try:
            killed = self.sMemory.getData(CAHRIM_KILL_ACTION)
            if killed:
                self.cleanMemory()
                self.sMemory.insertData(CAHRIM_KILL_ACTION, False)
            return killed
        except:
            pass

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

    ## Callback function
    def onTouch(self, msg, value):
        self.touched_bumper=True

    ## Method containing all the instructions that should be executing before terminating the action.
    def stop(self):
        self.going=0
        self.cleanMemory()
        for topic in self.sDialog.getAllLoadedTopics():
            self.sDialog.deactivateTopic(topic)
            self.sDialog.unloadTopic(topic)
        caressestools.setAutonomousAbilities(self.session, False, True, True, True, True)

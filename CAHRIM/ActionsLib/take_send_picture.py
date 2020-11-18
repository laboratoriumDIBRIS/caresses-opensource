# -*- coding: utf-8 -*-
'''
Copyright October 2019 Amélie Eugene & Roberto Menicatti & Università degli Studi di Genova
 
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

Author:      Amélie Eugene, Roberto Menicatti
Email:       roberto.menicatti@dibris.unige.it
Affiliation: Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import datetime
import time
import os
import json
import threading

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech
import caressestools.multipage_choice_manager as mlt

TELEGRAM = "telegram"
LINE = "line"
EMAIL = "email"


## Action "Take and Send Picture"
#
#  Pepper takes a picture and sends it to a person in the contact list if requested to do so.
#  This action requires the installation of the NAOqi app Pictures.
class TakeAndSendPicture(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Contact ID
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.recipient_id = self.apar[0]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        self.recipient_params = self.loadParameters("contacts.json")
        suggested_recipients_IDs = [option.replace('"', '') for option in self.suggestions]
        self.recipient_IDs = self.mergeAndSortIDs(self.recipient_params, suggested_recipients_IDs)
        self.recipient_options = []

        ## Get only the recipients whose email or Telegram address is present
        for id in self.recipient_IDs:
            if not (self.recipient_params["IDs"][id]["email"].encode('utf-8') == "" and self.recipient_params["IDs"][id]["telegram"].encode('utf-8') == ""):
                self.recipient_options.append(self.recipient_params["IDs"][id]["full"].encode('utf-8'))

        # Initialize NAOqi services
        self.sPosture = self.session.service("ALRobotPosture")
        self.sAwareness = self.session.service("ALBasicAwareness")
        self.sPhoto = self.session.service("ALPhotoCapture")
        self.sTablet = self.session.service("ALTabletService")
        self.sBehavior = self.session.service("ALBehaviorManager")
        self.sMemory = self.session.service("ALMemory")
        self.sASR = self.session.service("ASR2")

        # Set the cultural parameters
        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(session, self.volume)
        caressestools.setVoiceSpeed(session, self.speed)
        caressestools.setVoicePitch(session, self.pitch)

        # Set up speech.py app to get information
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(session, caressestools.Settings.robotIP.encode('utf-8'))

        self.extension = "jpg"
        self.path_take = "/data/home/nao/.local/share/PackageManager/apps/%s/html/images/"
        self.path_show = "http://%s/apps/%s/images/%s"
        self.behaviors = {
            "telegram": "pictures/send-by-telegram",
            "email": "pictures/send-by-email",
            "shutter": "pictures/play-shutter-sound",
            "delete": "pictures/delete-picture"
        }

        directory = os.path.dirname(__file__)
        file_path = os.path.join(directory, "aux_files", "email-conf.json")
        with open(file_path) as f:
            email_conf = json.load(f)
        self.address  = email_conf["address"].encode('utf-8')
        self.password = email_conf["password"].encode('utf-8')
        self.smtp     = email_conf["smtp"].encode('utf-8')

        self.asr = asr

    ## Method executed when the thread is started.
    def run(self):

        choice_ready = self.sp.script[self.__class__.__name__][speech.OTHER]["1"][self.language].encode('utf-8')
        line_send = self.sp.script[self.__class__.__name__][speech.OTHER]["5"][self.language].encode('utf-8')
        line_another = self.sp.script[self.__class__.__name__][speech.OTHER]["6"][self.language].encode('utf-8')
        choice_keep_delete = self.sp.script[self.__class__.__name__][speech.OTHER]["8"][self.language].encode('utf-8')
        self.choice_mode = self.sp.script[self.__class__.__name__][speech.OTHER]["10"][self.language].encode('utf-8')

        option_ready = [o.encode('utf-8') for o in self.sp.script[self.__class__.__name__][speech.USER]["0"][self.language]]
        options_keep_del = [self.sp.script[self.__class__.__name__][speech.USER]["keep"][self.language][0].encode('utf-8'),
                           self.sp.script[self.__class__.__name__][speech.USER]["delete"][self.language][0].encode(
                               'utf-8')]
        keywords_keep = [o.encode('utf-8') for o in self.sp.script[self.__class__.__name__][speech.USER]["keep"][self.language]]
        keywords_del = [o.encode('utf-8') for o in self.sp.script[self.__class__.__name__][speech.USER]["delete"][self.language]]

        take_another = True

        while take_another and not self.is_stopped:

            self.choice = mlt.MultiPageChoiceManager(caressestools.Settings.robotIP.encode('utf-8'))

            self.sp.monolog(self.__class__.__name__, "0", tag=speech.TAGS[1])
            caressestools.setAutonomousAbilities(self.session, False, False, False, False, False)
            self.sPosture.goToPosture("Stand", 0.5)
            self.sPhoto.setResolution(3) # 1280*960px (reference at http://doc.aldebaran.com/2-5/family/pepper_technical/video_2D_pep_v18a.html#cameraresolution-ov5640)
            self.sPhoto.setPictureFormat(self.extension)

            if self.sp._input==2:
                self.sp.gothread = True
                thr = threading.Thread(name="getinput", target=self.sp.getOptionsFromSmartphone, args=[option_ready])
                thr.start()
            answer = self.choice.giveChoiceMultiPage(choice_ready, option_ready)
            self.sp.gothread=False

            answer = [unicode(answer[0], "utf-8"), answer[1]]
            self.choice.kill()
            self.sp.checkIfKilledDuringMcm(self.choice, answer)

            self.sp.monolog(self.__class__.__name__, "2", tag=speech.TAGS[1])
            self.sBehavior.startBehavior(self.behaviors["shutter"])

            ## Take picture
            self.pic_file_name = "img_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.sPhoto.takePicture(self.path_take % caressestools.DEF_IMG_APP, self.pic_file_name)
            pic_path = self.path_show % (caressestools.Settings.robotIP, caressestools.DEF_IMG_APP, self.pic_file_name + "." + self.extension)

            ## Show picture
            self.sTablet.preLoadImage(pic_path)
            self.sp.monolog(self.__class__.__name__, "3", tag=speech.TAGS[1])
            self.sTablet.showImage(pic_path)

            ## Keep or delete picture
            time.sleep(3)
            caressestools.setAutonomousAbilities(self.session, False, True, True, True, True)
            self.sp.monolog(self.__class__.__name__, "4", tag=speech.TAGS[4])
            self.sASR.startReco(caressestools.Language.lang_naoqi, False, True)
            user_input = self.sp.getInput()
            if user_input is None:
                user_input = ""
            self.sp.userSaid(user_input)
            not_understood = True
            self.sASR.stopReco()

            while not_understood and not self.is_stopped:
                if any(unicode(keyword, "utf-8") in user_input.lower() for keyword in keywords_keep):
                    if not len(self.recipient_options) == 0:
                        send =self.sp.askYesOrNoQuestion(line_send, speech.TAGS[4], noisy=self.asr)
                        if send:
                            self.sendPicture()
                    take_another = self.sp.askYesOrNoQuestion(line_another, speech.TAGS[11], noisy=self.asr)
                    not_understood = False
                elif any(unicode(keyword, "utf-8") in user_input.lower() for keyword in keywords_del):
                    pic = self.path_take % caressestools.DEF_IMG_APP
                    pic = pic + self.pic_file_name + "." + self.extension
                    self.delPicture(pic)
                    take_another = self.sp.askYesOrNoQuestion(line_another, speech.TAGS[11], noisy=self.asr)
                    not_understood = False
                else:
                    self.choice = mlt.MultiPageChoiceManager(caressestools.Settings.robotIP.encode('utf-8'))

                    self.sp.say(self.sp.script[speech.ADDITIONAL][speech.MISSED_ANSWER][self.language].encode('utf-8'), speech.TAGS[0])
                    self.sp.monolog(self.__class__.__name__, "7", tag=speech.TAGS[4])
                    if self.sp._input==2:
                        self.sp.gothread = True
                        thr = threading.Thread(name="getinput", target=self.sp.getOptionsFromSmartphone, args=[options_keep_del])
                        thr.start()
                    user_input = self.choice.giveChoiceMultiPage(choice_keep_delete, options_keep_del)
                    self.sp.gothread=False
                    user_input = [unicode(user_input[0], "utf-8"), user_input[1]]
                    self.choice.kill()
                    self.sp.checkIfKilledDuringMcm(self.choice, user_input)
                    user_input = user_input[0]

            caressestools.showImg(self.session, caressestools.TABLET_IMG_EXECUTION)

        if not self.is_stopped:
            self.sp.replyAffirmative()

            self.sp.askYesOrNoQuestion(
                self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
            self.sp.monolog(self.__class__.__name__, "1", group="evaluation", tag=speech.TAGS[1])

    ## Send the picture to the chosen contact.
    def sendPicture(self):

        ## Ask for recipient
        if not self.isAvailable(self.recipient_id):
            self.recipient_full = self.sp.dialog(self.__class__.__name__, self.recipient_options, checkValidity=True, askForConfirmation=True, noisy=self.asr)
            self.recipient_id = self.getIDFromAttribute(self.recipient_params, "full", self.recipient_full)
        else:
            self.recipient_full = self.getAttributeFromID(self.recipient_params, self.recipient_id, "full")
            self.sp.monolog(self.__class__.__name__, "with-keyword", param={"$KEYWORD$" : self.recipient_full}, group="parameter-answer", tag=speech.TAGS[1])

        ## Ask for the way to send the picture
        telegram_id = self.getAttributeFromID(self.recipient_params, self.recipient_id, TELEGRAM)
        line_id = self.getAttributeFromID(self.recipient_params, self.recipient_id, LINE)
        email_id = self.getAttributeFromID(self.recipient_params, self.recipient_id, EMAIL)

        sending_ways = [sw[0] for sw in [[TELEGRAM, telegram_id], [EMAIL, email_id]] if not sw[1] == ""]

        if len(sending_ways) == 1:
            send_via = sending_ways[0]
        else:
            self.choice = mlt.MultiPageChoiceManager(caressestools.Settings.robotIP.encode('utf-8'))
            self.sp.monolog(self.__class__.__name__, "9", param={"$RECIPIENT$": self.recipient_full}, tag=speech.TAGS[1])
            if self.sp._input==2:
                self.sp.gothread = True
                thr = threading.Thread(name="getinput", target=self.sp.getOptionsFromSmartphone, args=[sending_ways])
                thr.start()
            send_via = self.choice.giveChoiceMultiPage(self.choice_mode, sending_ways)
            self.sp.gothread=False

            send_via = [unicode(send_via[0], "utf-8"), send_via[1]]
            self.choice.kill()
            self.sp.checkIfKilledDuringMcm(self.choice, send_via)
            send_via = send_via[0]

        self.recipient_send_id = self.getAttributeFromID(self.recipient_params, self.recipient_id, send_via)
        pic = self.path_take % caressestools.DEF_IMG_APP
        pic = pic + self.pic_file_name + "." + self.extension

        email_object = self.sp.script[self.__class__.__name__]["settings"]["email-object"][self.language].replace("$USERNAME$", self.username)
        message = self.sp.script[self.__class__.__name__]["settings"]["message"][self.language].replace("$USERNAME$", self.username).replace("$RECIPIENT$", self.recipient_full)

        ## Insert data in memory [email_object, sender_mail, sender_password, smtp, recipient_address(telegram or line or email), message, pic_path]
        data = [email_object, self.address, self.password, self.smtp,
                self.recipient_send_id, message, pic]

        self.sMemory.insertData("CARESSES_send_pic", data)

        if not self.sBehavior.isBehaviorRunning(self.behaviors[send_via]):
            self.sBehavior.startBehavior(self.behaviors[send_via])

        self.sp.monolog(self.__class__.__name__, "11", param={"$RECIPIENT$": self.recipient_full}, tag=speech.TAGS[1])
        self.recipient_id = '"n/a"'

    ## Delete the picture.
    #  @param pic Name of the picture file
    def delPicture(self, pic):

        self.sMemory.insertData("CARESSES_del_pic", pic)

        if not self.sBehavior.isBehaviorRunning(self.behaviors["delete"]):
            self.sBehavior.startBehavior(self.behaviors["delete"])


if __name__ == "__main__":

    import qi
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default=caressestools.Settings.robotIP,
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

    caressestools.Settings.robotIP = args.ip

    # Run Action
    apar = '"n/a"'
    cpar = "1.0 100 1.1 english John friend&&husband"

    caressestools.startPepper(session, caressestools.Settings.interactionNode)
    action = TakeAndSendPicture(apar, cpar, session, "normal")

    try:
        action.run()
    except speech.StopInteraction as e:
        print e

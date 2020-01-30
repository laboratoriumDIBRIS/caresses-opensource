# -*- coding: utf-8 -*-
'''
Copyright October 2019 Japan Advanced Institute of Science and Technology & Roberto Menicatti & Università degli Studi di Genova

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

Author:      Bui Ha Duong (1), Roberto Menicatti (2)
Email:       (1) bhduong@jaist.ac.jp (2) roberto.menicatti@dibris.unige.it
Affiliation: (1) Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan
             (2) Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech
import caressestools.multipage_choice_manager as mlt
import timeit

## Action "Operate iHouse".
#
#  Pepper operates ECHONET-based smart devices in the iHouse through uAAL_CAHRIM.
#  This action requires the running of uAAL modules.
class OperateiHouse(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) Device, room, operation; separated by a white space.
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param output_handler (Queue.Queue) uAAL-CAHRIM Message Sender module
    # @param input_queue (Queue.Queue) uAAL-CAHRIM Message Receiver module
    # @param provided_event (threading.Event) threading.Event()
    def __init__(self, apar, cpar, session, output_handler, input_queue, provided_event):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.item_id = self.apar[0]
        self.room = self.apar[1]
        self.operation = self.apar[2]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        self.items_params = self.loadParameters("ihouse_items.json")
        suggested_items_IDs = [option.replace('"', '') for option in self.suggestions]
        self.items_IDs = self.mergeAndSortIDs(self.items_params, suggested_items_IDs)
        self.items_options = self.getAllControllableDevices(self.items_params, self.items_IDs, "full")

        # Output handler for sending messages
        self.output_handler = output_handler
        # Input queue for retrieving information
        self.input_queue = input_queue
        self.provided_event = provided_event

        # Initialize NAOqi services
        self.sTablet = self.session.service("ALTabletService")
        self.sMemory = self.session.service("ALMemory")

        # Set the cultural parameters
        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(session, self.volume)
        caressestools.setVoiceSpeed(session, self.speed)
        caressestools.setVoicePitch(session, self.pitch)

        # Set up speech.py app to get information
        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(session, caressestools.Settings.robotIP.encode('utf-8'))

        # self.topic_item = self.__class__.__name__
        self.topic_item = "OperateiHouse"
        self.topic_room = "IoT-iHouse-Room"
    
    ## Method executed when the thread is started.
    def run(self):

        if not self.isAvailable(self.item_id):
            self.item_full = self.sp.dialog(self.topic_item, self.items_options, checkValidity=True,
                                            askForConfirmation=False)
            self.item_id = self.getIDFromAttribute(self.items_params, "full", self.item_full)
        else:
            self.item_full = self.getAttributeFromID(self.items_params, self.item_id, "full")
            self.sp.monolog(self.topic_item, speech.WITH_KEYWORD, param={"$KEYWORD$": self.item_full},
                            group="parameter-answer")

        if not self.isAvailable(self.room):
            room_options = [r.encode('utf-8') for r in self.items_params["IDs"][self.item_id]["locations"]]
            if len(room_options) == 1:
                self.room = room_options[0]
            else:
                self.room = self.sp.dialog(self.topic_room, room_options, checkValidity=True, askForConfirmation=False)

        get_ihouse_error = False
        try:
            current_val, status_str = self.getDeviceStatus(self.item_id, self.room)
        except:
            get_ihouse_error = True
            error = self.sp.script[self.topic_item]["other"]["4"][self.language]
            self.sp.say(error)
            return
            # raise Exception, "No answer from iHouse..."
        finally:
            if get_ihouse_error:
                self.sp.askYesOrNoQuestion(
                    self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'))
                self.sp.say(self.sp.script[self.__class__.__name__]["evaluation"]["1"][self.language].encode('utf-8'))

        if not self.isAvailable(self.operation):
            available_operations = [self.items_params["IDs"][self.item_id]["operations"][op].encode('utf-8') for op in self.items_params["IDs"][self.item_id]["operations"].keys() if not op == status_str]
            ## 1 - by automatically choosing the single possible one
            if len(available_operations) == 1:
                operation_str = available_operations[0]
                question = self.sp.script[self.topic_item]["other"]["3"][self.language].replace("$DEVICE$",
                                                                                                self.item_full).replace(
                    "$STATUS$", status_str).replace("$ACTION$", operation_str).replace("$ROOM$", self.room)
                answer = self.sp.askYesOrNoQuestion(question)
            ## 2 - or by proposing all of the possible ones except for the one which would leave unchanged the status of the device
            else:
                choice = mlt.MultiPageChoiceManager(caressestools.Settings.robotIP.encode('utf-8'))
                import time
                time.sleep(3)
                question = self.sp.script[self.topic_item]["other"]["0"][self.language].replace("$DEVICE$", self.item_full).replace("$STATUS$", status_str)
                self.sp.say(question)
                operation_str = choice.giveChoiceMultiPage(self.item_full, available_operations)[0]
                self.sp.playLine(self.sp.USER, operation_str)
                choice.kill()
                answer = True

            for k in self.items_params["IDs"][self.item_id]["operations"].keys():
                if self.items_params["IDs"][self.item_id]["operations"][k].encode('utf-8') == operation_str:
                    self.operation = k
                    break

        ## ... or from apar
        else:
            operation_str = self.items_params["IDs"][self.item_id]["operations"][self.operation]
            ## If the requested operation has no effect on the device, stop the action
            if self.operation == status_str:
                self.sp.monolog(self.topic_item, "1", param={"$DEVICE$": self.item_full, "$STATUS$": status_str})
                self.stop()
                return
            ## Otherwise execute it
            else:
                operation_str = self.items_params["IDs"][self.item_id]["operations"][self.operation]
                question = self.sp.script[self.topic_item]["other"]["3"][self.language].replace("$DEVICE$",
                                                                                                self.item_full).replace(
                    "$STATUS$", status_str).replace("$ACTION$", operation_str).replace("$ROOM$", self.room)
                # answer = self.sp.askYesOrNoQuestion(question)
                answer = True

        if answer:
            success = False
            try:
                success = self.setDeviceStatus(self.item_id, self.room, self.operation, current_val)
            except:
                error = self.sp.script[self.topic_item]["other"]["4"][self.language]
                self.sp.say(error)
                return
                # raise Exception, "No answer from iHouse..."
            finally:
                if success:
                    self.sp.monolog(self.topic_item, "2")
                self.sp.askYesOrNoQuestion(
                    self.sp.script[self.__class__.__name__]["evaluation"]["0"][self.language].encode('utf-8'))
                self.sp.say(self.sp.script[self.__class__.__name__]["evaluation"]["1"][self.language].encode('utf-8'))
        else:
            self.sp.replyAffirmative()
    
    ## Retrieve the status of the desired room's device as specified by the input parameters.
    #  @param device Device of which the status should be retrieved.
    #  @param room Room in which the device is located.
    def getDeviceStatus(self, device, room):
        msg_type_id = "iHouse.{room}.{device}".format(room=room.replace(" ", "-"), device=device)
        tic = timeit.default_timer()
        self.output_handler.writeQueryMessage("request", "{}#get".format(msg_type_id))
        self.provided_event.wait(15)

        data = None
        value = ""

        while not self.input_queue.empty():
            value = self.input_queue.get()
            if value[0] == "provided" and value[1] == msg_type_id:
                data = value[2].strip()
                if data == "on":
                    status_str = self.items_params["IDs"][self.item_id]["status"]["on"]
                elif data == "off":
                    status_str = self.items_params["IDs"][self.item_id]["status"]["off"]
                elif data == "open":
                    status_str = self.items_params["IDs"][self.item_id]["status"]["open"]
                elif data == "close":
                    status_str = self.items_params["IDs"][self.item_id]["status"]["close"]
                elif data == "operation-fail":
                    raise Exception, "iHouse, operation fail..."
                else:
                    unit = self.items_params["IDs"][self.item_id]["status"]["value"]["unit"]
                    format_str = self.items_params["IDs"][self.item_id]["status"]["value"]["format"]
                    status_str = format_str.replace("$VALUE$", str(int(round(float(data))))).replace("$UNIT$", unit)
                toc = timeit.default_timer()
                self.logger.info("%s correctly retrieved with value: %s" % (msg_type_id, data))
                self.logger.info("%s correctly retrieved with time: %s sec" % (msg_type_id, str(toc-tic)))
                break
            else:
                self.input_queue.put(value)
        return data, status_str

    ## Set the status of the desired room's device as specified by the input parameters.
    #  @param device Device of which the status should be altered.
    #  @param room Room in which the device is located.
    #  @param operation Operation to perform on the device.
    #  @param current_val Current value of the device
    def setDeviceStatus(self, device, room, operation, current_val):
        if operation == ">":
            step = float(self.items_params["IDs"][self.item_id]["range"]["step"])
            min = float(self.items_params["IDs"][self.item_id]["range"]["min"])
            if current_val == "on":
                self.sp.monolog(self.topic_item, "5")
                return None
            elif current_val == "off":
                operation = str(min + step)
            else:
                operation = str(float(current_val) + step)
        elif operation == "<":
            step = float(self.items_params["IDs"][self.item_id]["range"]["step"])
            max = float(self.items_params["IDs"][self.item_id]["range"]["max"])
            if current_val == "on":
                operation = str(max - step)
            elif current_val == "off":
                self.sp.monolog(self.topic_item, "6")
                return None
            else:
                operation = str(float(current_val) - step)
        elif operation == "r":
            operation = "100"

        success = False
        msg_type_id = "iHouse.{room}.{device}".format(room=room.replace(" ", "-"), device=device)
        tic = timeit.default_timer()
        self.output_handler.writeQueryMessage("request", "{msg_type_id}#set.{operation}".format(msg_type_id=msg_type_id, operation=operation))
        self.provided_event.wait(15)

        while not self.input_queue.empty():
            value = self.input_queue.get()
            if value[0] == "provided" and value[1] == msg_type_id:
                data = value[2].strip()
                if data == "operation-successful":
                    success = True
                    toc = timeit.default_timer()
                    self.logger.info("%s correctly set to value: %s" % (msg_type_id, operation))
                    self.logger.info("%s correctly set with time: %s sec" % (msg_type_id, str(toc-tic)))
                elif data == "operation-fail":
                    raise Exception, "iHouse, operation fail..."
                break
            else:
                self.input_queue.put(value)

        return success

    def getAllControllableDevices(self, parameters, ordered_IDs, attribute):
        attributes = []
        for id in ordered_IDs:
            if "operations" in parameters["IDs"][id].keys():
                attributes.append(parameters["IDs"][id][attribute].encode('utf-8'))
        return attributes

if __name__ == "__main__":
    import argparse
    import time
    import qi
    import sys
    import socket
    import Queue
    import traceback
    from threading import Event
    from CahrimThreads.socket_handlers import MsgReceiver, MsgSender, InputMsgHandler, OutputMsgHandler
    from CahrimThreads.actuation_hub import StateObserver

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

    output_queue = Queue.Queue(maxsize=0)
    input_queue  = Queue.Queue(maxsize=0)

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Connect the socket to the port where the server is listening
    server_address = ('localhost', 12345)
    sock.connect(server_address)
    #timeouts (if no subscribed messages are received, go ahead
    sock.settimeout(5)

    provided_event = Event()
    output_handler = OutputMsgHandler(output_queue)
    input_handler = InputMsgHandler(session, output_handler, input_queue, provided_event, "experimental")

    ## Create threads' instances
    threads = []

    threads.append(MsgReceiver(sock, input_handler))
    threads.append(MsgSender(sock, output_queue))

    # threads.append(StateObserver(session, output_handler))

    ## Start all threads
    for t in threads:
        t.start()
        t_name = t.id if hasattr(t, "id") else t.__class__.__name__
        print ("%s started." % t_name)

    print("-----------------------------------------------\n"
          " ===> All threads started.\n"
          "-----------------------------------------------\n")
    
    # Run Action
    apar = u'iHouseAir-conditioner livingroom on'
    cpar = u'0.7 80 1.0 english chouSan iHouseAir-conditioner'

    param = [apar, cpar, session, output_handler, input_queue, provided_event]
    action_class = getattr(sys.modules[__name__], 'OperateiHouse')

    caressestools.startPepper(session, "charger")
    # action = OperateiHouse(apar, cpar, session, output_handler, input_queue, provided_event)
    action = action_class(*param)

    try:
        action.run()
    except speech.StopInteraction as e:
        traceback.print_exc()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        traceback.print_exc()
    finally:
        for t in reversed(threads):
            t.stop()
            time.sleep(0.5)
        sock.sendall("Bye\n".encode())
        sock.close()
        sock.close()
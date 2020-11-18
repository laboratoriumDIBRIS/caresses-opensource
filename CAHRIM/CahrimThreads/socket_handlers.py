# -*- coding: utf-8 -*-
'''
Copyright October 2019 Bui Ha Duong & Roberto Menicatti & Università degli Studi di Genova

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

from threading import Thread
import time
import logging
import sys

from CahrimThreads.actuation_hub import Executor
from sensory_hub import ESModule

log_mr = logging.getLogger('CAHRIM.SocketHandlers.MsgReceiver')
log_ms = logging.getLogger('CAHRIM.SocketHandlers.MsgSender')

## Thread which deals with the reception of messages.
class MsgReceiver(Thread):

    trigger=False
    robotsays=None
    counter=0
    counter2=-1
    smartphone=None

    def __init__(self, sock, input_handler):
        Thread.__init__(self)
        self.id = "Message Receiver"
        self.sock = sock
        self.sock.settimeout(5)
        self.alive = True
        self.input_handler = input_handler
        

    def run(self):
        delimiter = "\n"
        full_msg = ""
        while self.alive:
            try:
                data = self.sock.recv(1024)
                try:
                    full_msg = data.decode('utf-8')
                except:
                    full_msg = data
            except Exception as e:
                continue

            if (delimiter) in full_msg:
                chunks = full_msg.split(delimiter)
                for chunk in chunks[:-1]:
                    if not chunk.startswith("INFO: Message type was valid. Message has been published!"):
                        log_mr.debug("Received message: %s" % chunk)
                    self.input_handler.dispatch(chunk + "\n")
                if chunks[-1] == "":
                    full_msg = ""
                else:
                    full_msg = chunks[-1]
            

        log_mr.info("%s terminated correctly." % self.id)

    def stop(self):
        self.alive = False


## Thread which deals with the dispatch of messages.
class MsgSender(Thread):

    def __init__(self, sock, queue):
        Thread.__init__(self)
        self.id = "Message Sender"
        self.alive = True
        self.sock = sock
        self.queue = queue

    def run(self):
        while self.alive:
            time.sleep(0.05)
            if not self.queue.empty():
                msg = self.queue.get()
                try:
                    self.sock.sendall(msg.encode("utf-8"))
                    log_ms.debug("Sent message: %s" % msg[:-1])
                except Exception as e:
                    log_ms.warning('MsgSender failed to send last message')
                    self.queue.put(msg)

        log_ms.info("%s terminated correctly." % self.id)

    def stop(self):
        self.alive = False


## Handle the incoming messages.
class InputMsgHandler():

    def __init__(self, naoqi_session, output_queue, input_queue, provided_event, cultural, asr):
        self.naoqi_session = naoqi_session
        self.output_queue = output_queue
        self.input_queue = input_queue
        self.provided_event = provided_event
        self.cultural = cultural
        self.asr = asr
        

    def dispatch(self, msg):
        '''
        Dispatch the incoming message to the correct handler.
        :param msg: the incoming message
        :return: ---
        '''

        if not msg.startswith("INFO") and not msg.startswith("ERROR"):
            msg_parts = msg.split("#")
            reception_reason = msg_parts[0]

            if reception_reason in ["subscribed", "requested", "provided", "gotten"]:
                msg_type = msg_parts[1]
                msg_content = msg_parts[2]

                if reception_reason == "subscribed":
                    if msg_type == "D7.1":
                        Executor.handle(msg_content, self.naoqi_session, self.output_queue, self.input_queue, self.provided_event, self.cultural, self.asr)
                    elif msg_type == "iHouse":
                        ESModule.handle(msg_content)
                    elif msg_type == "D7.2":
                        if("chitchat:start" in msg_content):
                            MsgReceiver.trigger=True
                        elif("robotSays" in msg_content):
                            MsgReceiver.robotsays = msg_content.split("[")[1].split("]")[0]
                        elif("chitchat:finished" in msg_content):
                            MsgReceiver.robotsays = msg_content
                        elif("goalFromChitchat" in msg_content):
                            MsgReceiver.robotsays = msg_content.split("[")[1].split("]")[0]
                    elif msg_type=="D11.5":
                        MsgReceiver.smartphone=msg_content.split("[")[1].split("]")[0]

                elif reception_reason == "requested":
                    pass

                elif reception_reason == "provided":
                    self.input_queue.put([reception_reason, msg_type, msg_content])
                    self.provided_event.set()
                    self.provided_event.clear()

                elif reception_reason == "gotten":
                    pass
    @staticmethod
    def triggerCheck():
        return MsgReceiver.trigger

    @staticmethod
    def triggerDone():
        MsgReceiver.trigger=False

    @staticmethod
    def robotsaysCheck():
        return MsgReceiver.robotsays

    @staticmethod
    def robotsaysDone():
        MsgReceiver.robotsays=None

    @staticmethod
    def getCounter():
        return MsgReceiver.counter

    @staticmethod
    def getCounter2():
        return MsgReceiver.counter2

    @staticmethod
    def increaseCounter():
        MsgReceiver.counter=MsgReceiver.counter+1

    @staticmethod
    def increaseCounter2():
        MsgReceiver.counter2=MsgReceiver.counter2+1

    @staticmethod
    def zeroCounter():
        MsgReceiver.counter=0

    @staticmethod
    def zeroCounter2():
        MsgReceiver.counter2=0

    @staticmethod
    def resetSmartphone():
        MsgReceiver.smartphone=None

    @staticmethod
    def getSmartphone():
        return MsgReceiver.smartphone


## Handle the outgoing messages.
class OutputMsgHandler():

    def __init__(self, output_queue):
        self.output_queue = output_queue


    def writeQueryMessage(self, msg_operation, msg_type):
        '''
        Add "request" or "get" output message to the queue polled by socket_handlers.MsgSender thread
        :param msg_operation: a uAAL-Skeleton compatible operation among these two ("request", "get")
        :param msg_type: CARESSES message datatype
        :return: True if message is valid, False otherwise
        '''
        if msg_operation in ["request", "get"]:
            message = "%s#%s\n" % (msg_operation, msg_type)
            self.output_queue.put(message)
            return True
        else:
            log_ms.error("Not valid operation '%s' on output message. Use one among: 'request', 'get'." % msg_operation)
            if msg_operation in ["publish", "provide"]:
                log_ms.info("For the operations 'publish' and 'provide' use the method 'writeSupplyMessage()' instead.")
            return False


    def writeSupplyMessage(self, msg_operation, msg_type, msg_content):
        '''
        Add "publish" or "provide" output message to the queue polled by socket_handlers.MsgSender thread
        :param msg_operation: a uAAL-Skeleton compatible operation among these two ("publish", "provide")
        :param msg_type: CARESSES message datatype
        :param msg_content: content of the message
        :return: True if message is valid, False otherwise
        '''
        if msg_operation in ["publish", "provide"]:
            message = "%s#%s#%s\n" % (msg_operation, msg_type, msg_content)
            self.output_queue.put(message)
            return True
        else:
            log_ms.error("Not valid operation '%s' on output message. Use one among: 'publish', 'provide'." % msg_operation)
            if msg_operation in ["request", "get"]:
                log_ms.info("For the operations 'request' and 'get' use the method 'writeQueryMessage()' instead.")
            return False

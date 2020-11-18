# -*- coding: utf-8 -*-
'''
Copyright October 2019 Roberto Menicatti & Università degli Studi di Genova & Ali Abdul Khaliq

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

Author:      Roberto Menicatti (1), Ali Abdul Khaliq (2)
Email:       (1) roberto.menicatti@dibris.unige.it (2) ali-abdul.khaliq@oru.se
Affiliation: (1) Laboratorium, DIBRIS, University of Genova, Italy (2) ORU, Sweden
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import time
import re
import sys
import inspect
import logging
import os
from threading import Thread

from sensory_hub import OdomConverter

from ActionsLib.action import Action
from ActionsLib.action_fallback import Fallback, KillCAHRIM

from ActionsLib.accept_request import AcceptRequest
from ActionsLib.accompany import Accompany
from ActionsLib.approach_user import ApproachUser
from ActionsLib.chitchat import ChitChat
from ActionsLib.display_instructions import DisplayInstructions
from ActionsLib.display_weather_report import DisplayWeatherReport
from ActionsLib.go_to import GoTo
from ActionsLib.go_to_nogoal import GoToNoGoal
from ActionsLib.greet import Greet
from ActionsLib.greet_bow import GreetBow
from ActionsLib.greet_namaste import GreetNamaste
from ActionsLib.greet_wave import GreetWave
from ActionsLib.load import Load
from ActionsLib.move_closer_farther import MoveCloserFarther
from ActionsLib.operate_iot import OperateIoT
from ActionsLib.play_game_memory import PlayGameMemory
from ActionsLib.play_music_video import PlayMusicAndVideo
from ActionsLib.play_karaoke import PlayKaraoke
from ActionsLib.play_video import PlayVideo
from ActionsLib.privacy_cover_eyes import PrivacyCoverEyes
from ActionsLib.privacy_look_down import PrivacyLookDown
from ActionsLib.privacy_turn_around import PrivacyTurnAround
from ActionsLib.react_to_sound import ReactToSound
from ActionsLib.read_audiobook import ReadAudiobook
from ActionsLib.read_iot import ReadIoT
from ActionsLib.read_menu import ReadMenu
from ActionsLib.read_news import ReadNews
from ActionsLib.read_temperature import ReadTemperature
from ActionsLib.remind import Remind
from ActionsLib.remind_location import RemindLocation
from ActionsLib.send_line_message import SendLineMessage
from ActionsLib.send_telegram_message import SendTelegramMessage
from ActionsLib.set_node import SetNode
from ActionsLib.set_reminder import SetReminder
from ActionsLib.show_pictures import ShowPictures
from ActionsLib.skype_call import SkypeCall
from ActionsLib.take_send_picture import TakeAndSendPicture
from ActionsLib.tell_date_time import TellDateTime
from ActionsLib.unload import Unload

from ActionsLib.caressestools.caressestools import showImg, TABLET_IMG_DEFAULT, TABLET_IMG_EXECUTION, TABLET_IMG_REST, leaveChargerNode, setAutonomousAbilities, Battery, Settings
from ActionsLib.caressestools.speech import StopInteraction, KillAction, CAHRIM_KILL_ACTION, Speech
import ActionsLib.caressestools.speech as speech

log_stateobserver = logging.getLogger('CAHRIM.ActuationHub.StateObserver')
log_executor = logging.getLogger('CAHRIM.ActuationHub.Executor')

## Global list of actions and their status
thread_list = {}
remind_conflicts = [PlayMusicAndVideo.__name__, PlayVideo.__name__, PlayKaraoke.__name__, ReadAudiobook.__name__, DisplayInstructions.__name__]
approach_user_conflicts = [GoTo.__name__]
requiring_AcceptRequest_restart = [AcceptRequest.__name__, GoTo.__name__]


## Run CARESSES actions.
class RunAction(Thread):
    def __init__(self, id, type, session, outputhandler, asr, apar=None, cpar=None, robot=None, action=None):
        Thread.__init__(self)
        self.id = id
        self.type = type
        self.apar = apar
        self.cpar = cpar
        self.robot = robot
        self.action = action
        self.state = 'NotStarted'
        self.session = session
        self.show = True
        self.output_handler = outputhandler
        self.asr = asr
        self.sMemory = session.service("ALMemory")
        self.sBattery = session.service("ALBattery")

    def run(self):

        if self.type == Remind.__name__:
            self.stopConflictingActions(remind_conflicts)
        elif self.type == ApproachUser.__name__:
            self.stopConflictingActions(approach_user_conflicts)
        elif self.type == AcceptRequest.__name__:
            is_running, running_action = self.checkIfRunningAny([Remind.__name__])
            if is_running:
                self.waitForEndOf(running_action)
        elif self.type == MoveCloserFarther.__name__:
            is_running, running_action = self.checkIfRunningAny([GreetWave.__name__, GreetNamaste.__name__, GreetBow.__name__])
            if is_running:
                self.waitForEndOf(running_action)
        elif isinstance(self.action, Greet):
            is_running, running_action = self.checkIfRunningAny([MoveCloserFarther.__name__])
            if is_running:
                self.waitForEndOf(running_action)

        self.state = 'Running'
        log_executor.info("%-17s %3s, %s" % ("Action %s:" % self.state.upper(), str(self.id), self.type))

        if self.show:
            try:
                if self.type != "ChitChat" and self.type != "AcceptRequest" and self.type != "ReactToSound" and not self.type.startswith("Privacy"):
                    showImg(self.session, TABLET_IMG_EXECUTION)
                elif self.type == "ChitChat" or self.type == "AcceptRequest":
                    showImg(self.session, TABLET_IMG_DEFAULT)
                elif self.type == "ReactToSound" or self.type.startswith("Privacy"):
                    showImg(self.session, TABLET_IMG_REST)
            except:
                pass

        try:
            self.sMemory.insertData(CAHRIM_KILL_ACTION, False)

            if self.sBattery.getBatteryCharge() > Battery.BATTERY_LOW:
                Battery.solution_started = False

            ## If the robot needs charge, don't start the AcceptRequest.
            ## However, since CSPEM is trying to achieve the AcceptRequest goal, notify CSPEM the action ran and finished
            ## even if it's not true.
            if Battery.solution_started and self.type == AcceptRequest.__name__:

                self.notifyCspemWithRunningState()

                self.state = 'Finished'
                log_executor.info("%-17s %3s, %s" % ("Action %s:" % self.state.upper(), str(self.id), self.type))

            else:
                self.action.run()
                self.state = 'Finished'

                if not StateObserver.first_accept_request_executed:
                    if self.type == AcceptRequest.__name__:
                        StateObserver.first_accept_request_executed = True

                log_executor.info("%-17s %3s, %s" % ("Action %s:" % self.state.upper(), str(self.id), self.type))

        except StopInteraction as e:
            log_executor.warning(e)
            self.state = 'Finished'
            log_executor.warning("%-17s %3s, %s" % ("Action %s:" % self.state.upper(), str(self.id), self.type))
            ## Start AcceptRequest if GoTo is stopped by the user.
            ## This is necessary because it sends the consecutive goal before returning. In case of failure the whole
            ## system would be blocked because of the lack of any other goal.
            if self.type == GoTo.__name__:
                msg = "[(:goal(?G1 accept-request true))]"
                self.output_handler.writeSupplyMessage("publish", "D5.1", msg)
        except KillAction as e:
            self.state = 'Finished'
            log_executor.warning("%-17s %3s, %s" % ("Action %s:" % self.state.upper(), str(self.id), self.type))
        except KillCAHRIM as e:
            StateObserver.killed_cahrim = True
        except Exception as e:
            log_executor.error(e, exc_info=True)
            self.notifyCspemWithRunningState()
            self.state = 'Failed'
            log_executor.error("%-17s %3s, %s" % ("Action %s:" % self.state.upper(), str(self.id), self.type))

            ## Notify the user of the action failure
            if not self.type == ReactToSound.__name__:
                self.language = self.cpar.split(' ')[3].lower().replace('"', '')
                self.sp = Speech("speech_conf.json", self.language)
                self.sp.enablePepperInteraction(self.session, Settings.robotIP.encode('utf-8'))
                self.sp.say(self.sp.script[speech.ADDITIONAL][speech.FAILURE][self.language].encode('utf-8'), speech.TAGS[0])

            ## Execute AcceptRequest in case of self-failure or GoTo failure
            ## Restart ReactToSound in case of self-failure
            ## Both are necessary because they send the consecutive goal before returning. In case of failure the whole
            ## system would be blocked because of the lack of any other goal.
            if self.type in requiring_AcceptRequest_restart:
                msg = "[(:goal(?G1 accept-request true))]"
                self.output_handler.writeSupplyMessage("publish", "D5.1", msg)
            elif self.type == ReactToSound.__name__:
                msg = "[(:goal(?G1 react-sound true))]"
                self.output_handler.writeSupplyMessage("publish", "D5.1", msg)


        setAutonomousAbilities(self.session, False, True, True, True, True)

        if self.show:
            try:
                if self.type != "ChitChat" and self.type != "AcceptRequest" and self.type != "ReactToSound" and not self.type.startswith("Privacy"):
                    showImg(self.session, TABLET_IMG_EXECUTION)
                elif self.type == "ChitChat" or self.type == "AcceptRequest":
                    showImg(self.session, TABLET_IMG_DEFAULT)
                elif self.type == "ReactToSound" or self.type.startswith("Privacy"):
                    showImg(self.session, TABLET_IMG_REST)
            except:
                pass
        else:
            self.show = True

        ## Send robot to charger if battery is low and start ReactToSound
        if not Battery.solution_started:
            ## We want to recharge the robot only after finishing a task and before accepting a new request, so we check
            ## the battery level at the end of every action except for AcceptRequest
            if not self.type == AcceptRequest.__name__:
                if StateObserver.first_accept_request_executed:
                    if self.sBattery.getBatteryCharge() < Battery.BATTERY_LOW:
                        Battery.solution_started = True
                        self.startLowBatterySolution()

    def notifyCspemWithRunningState(self):
        '''
        Send at least a D6.3 message to CSPEM with "Running" state to avoid crash of CSPEM
        :return:
        '''
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S.000", time.localtime())
        gpos = OdomConverter.getRobotInMap()
        spos = "\"n/a\""  ## this is done to avoid problem with CSPEM

        actions_state = "(%s Running)" % str(self.id)
        parse = timestamp, round(gpos[0], 2), round(gpos[1], 2), round(gpos[2], 2), spos, actions_state
        information_message = '[{(robot pepper-1)(time %s)(gpos %.2f %.2f %.2f)(spos %s)(act {%s})}]' % parse
        self.output_handler.writeSupplyMessage("publish", "D6.3", information_message)
        time.sleep(1)

    def startLowBatterySolution(self):
        log_stateobserver.warning("Battery level is low, sending robot to charger!")

        params = ["False", Executor.last_cpar, self.session, self.output_handler, self.asr]
        Executor.execute(Fallback, params, -1, "Fallback", self.output_handler, self.asr, forced=True)

    def stopConflictingActions(self, conflicting_actions):

        for id in thread_list.keys():
            if not thread_list[id][1].type == self.type:
                if thread_list[id][1].type in conflicting_actions:
                    thread_list[id][1].state = 'Finished'
                    StopAction(thread_list[id][0], id).start()
                    if self.type == Remind.__name__:
                        self.show = True
                else:
                    if self.type == Remind.__name__:
                        self.show = False

    def checkIfRunningAny(self, actions):

        for id in thread_list.keys():
            if not thread_list[id][1].type == self.type:
                if thread_list[id][1].type in actions:
                    if thread_list[id][1].state == 'Running':
                        return True, thread_list[id][1].type

        return False, None

    def waitForEndOf(self, action):
        '''
        If 'action' is running, wait for it to finish. If it's not running, return directly.
        :param action: name of the action to check the state of
        '''

        finished = False
        found = False

        while not finished:

            for id in thread_list.keys():
                if not thread_list[id][1].type == self.type:
                    if thread_list[id][1].type == action:
                        if thread_list[id][1].state == 'Running':
                            pass
                        else:
                            finished = True
                        found = True
                        continue
            if not found:
                break

## Force the termination of an action.
class StopAction(Thread):
    def __init__(self, action, action_id):
        Thread.__init__(self)
        self.action = action
        self.action_id = action_id

    def run(self):
        log_executor.warning("%-17s %3s, %s" % ("Action stopped: ", str(self.action_id), self.action.__class__.__name__))
        self.action.stop()


## Monitor the execution state of the CARESSES actions.
class StateObserver(Thread):

    killed_cahrim = False
    first_action_received = False
    first_accept_request_executed = False
    starting_node = ""

    def __init__(self, session, output_handler, asr):
        Thread.__init__(self)
        self.id = "Actuation Hub - State Observer"
        self.alive = True
        self.session = session
        self.output_handler = output_handler # Output handler for sending messages
        self.asr = asr
        self.publishing_period = 0.5

        self.no_actions_yet = True
        self.nothing_running_timer = None
        self.nothing_running_timer_started = False
        self.printed = False

    def run(self):
        while self.alive:
            time.sleep(self.publishing_period)
            ## Sending state message
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S.000", time.localtime())
            actions_state = ""
            for id in thread_list.keys():
                actions_state += '(' + str(id) + ' ' + str(thread_list[id][1].state) + ')'

            gpos = OdomConverter.getRobotInMap()
            spos = OdomConverter.getCurrentNode()

            spos = "\"n/a\"" ## this is done to avoid problem with CSPEM

            parse = timestamp, round(gpos[0], 2), round(gpos[1], 2), round(gpos[2], 2), spos, actions_state
            information_message = '[{(robot pepper-1)(time %s)(gpos %.2f %.2f %.2f)(spos %s)(act {%s})}]' % parse
            self.output_handler.writeSupplyMessage("publish", "D6.3", information_message)

            for id in thread_list.keys():
                if 'Finished' in thread_list[id][1].state or 'Failed' in thread_list[id][1].state:
                    self.no_actions_yet = False
                    del thread_list[id]

            ## Fallback solution if no more actions are received by CSPEM
            if thread_list.keys() == []:

                if not self.nothing_running_timer_started:
                    if not self.no_actions_yet:
                        self.nothing_running_timer = time.time()
                        self.nothing_running_timer_started = True
                else:
                    if time.time() - self.nothing_running_timer > 90:
                        if self.no_actions_yet:
                            pass
                        else:
                            self.startFallbackSolution()

                        self.nothing_running_timer_started = False

                    elif time.time() - self.nothing_running_timer > 3 and not self.printed:
                        log_stateobserver.warning("No action running, starting a timer...")
                        self.printed = True
            else:
                self.nothing_running_timer_started = False
                self.printed = False

        log_stateobserver.info("%s terminated correctly." % self.id)

    def startFallbackSolution(self):

        log_stateobserver.warning("Still no action running, restarting CSPEM!")
        self.output_handler.writeSupplyMessage("publish", "D5.1", "restart")

        ## Notify user of CSPEM restarting
        self.language = Executor.last_cpar.split(' ')[3].lower().replace('"', '')
        self.sp = Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, Settings.robotIP.encode('utf-8'))
        self.sp.say(self.sp.script[speech.ADDITIONAL][speech.CSPEM_RESTART][self.language].encode('utf-8'), speech.TAGS[0])
        
        ## Remove file planning-problem.uddl
        if os.path.isfile("..\\..\\CSPEM\\planning-problem.uddl"):
            os.remove("..\\..\\CSPEM\\planning-problem.uddl")

        # log_stateobserver.warning("Still no action running, launching fallback solution!")

        # params = ["True", Executor.last_cpar, self.session, self.output_handler, self.asr]
        # Executor.execute(Fallback, params, -1, "Fallback", self.output_handler, self.asr, forced=True)

    def stop(self):
        self.alive = False
        for id in thread_list.keys():
            StopAction(thread_list[id][0], id).start()


## Parse the goal message received by CSPEM and launch the corresponding CARESSES action.
class Executor():

    last_cpar = "1 100 1.1 english user"
    waiting_remind = None

    @staticmethod
    def parse_message(msg):

        srch_id    = re.search(r'\(id [^)]*\)', msg)
        srch_type  = re.search(r'\(type [^)]*\)', msg)
        srch_apar  = re.search(r'\(apar [^)]*\)', msg)
        srch_cpar  = re.search(r'\(cpar [^)]*\)', msg)
        srch_robot = re.search(r'\(robot [^)]*\)', msg)

        id = srch_id.group()
        id = id[4:len(id)-1]
        type = srch_type.group()
        type = type[6:len(type)-1]

        if not srch_apar == None:
            apar = srch_apar.group()
            apar = apar[6:len(apar) - 1].strip('{}')
        else:
            apar = ''

        if not srch_cpar == None:
            cpar = srch_cpar.group()
            cpar = cpar[6:len(cpar) - 1].strip('{}')
        else:
            cpar = ''

        robot = srch_robot.group()
        robot = robot[7:len(robot) - 1]

        return id, type, apar, cpar, robot

    @staticmethod
    def handle(msg, session, output_handler, input_queue, provided_event, cultural, noisy):

        (id, type, apar, cpar, robot) = Executor.parse_message(msg)

        if len(cpar) > 1:
            if len(cpar.split(' ')) == 5:
                Executor.last_cpar = cpar

        params = [apar, cpar, session]

        if 'stop' in apar:
            newThread = StopAction(thread_list[id][0], id)
            newThread.start()

        else:
            # Run the required action
            log_executor.info("%-17s %3s, %s, [%s], [%s]" % ("Action received:", str(id), type, params[0], params[1]))

            try:
                action_class = getattr(sys.modules[__name__], type)
                constructor_params = inspect.getargspec(action_class.__init__)[0]
                if "output_handler" in constructor_params:
                    params.append(output_handler)
                if "input_queue" in constructor_params:
                    params.append(input_queue)
                if "provided_event" in constructor_params:
                    params.append(provided_event)
                if "cultural" in constructor_params:
                    params.append(cultural)
                if "asr" in constructor_params:
                    params.append(noisy)

            except:
                log_executor.warning("%-17s %3s, %s" % ("Action not found:", str(id), type))
                action_class = Action

            Executor.execute(action_class, params, id, type, output_handler, noisy)

    @staticmethod
    def execute(action, params, id, type, output_handler, asr, forced=False):

        session = params[2]

        if forced:
            log_executor.info("%-17s %3s, %s, [%s], [%s]" % ("Action forced:", str(id), type, params[0], params[1]))

        newAction = action(*params)
        newThread = RunAction(id, type, session, output_handler, asr, apar=params[0], cpar=params[1], action=newAction)

        if not StateObserver.first_action_received:
            if not type == ReactToSound.__name__:
                StateObserver.first_action_received = True

                ## Take Pepper off of the docking station if starting from there
                if StateObserver.starting_node == "charger":
                    off = leaveChargerNode(session)
                    if off == False:
                        log_executor.error("An error occured while Pepper was leaving the docking station. Exiting...")

                ## If the Remind action is sent as first action, put it aside for later
                if type == Remind.__name__:
                    Executor.waiting_remind = [newAction, newThread, id]

        if Executor.waiting_remind is None:
            newThread.start()
            thread_list[id] = [newAction, newThread]
        ## If the Remind action is sent as first action, then wait for the robot to approach the user and greet them before
        ## executing it
        else:
            if not type == Remind.__name__:
                if type == AcceptRequest.__name__:

                    Executor.waiting_remind[1].start()
                    thread_list[Executor.waiting_remind[2]] = Executor.waiting_remind[:2]
                    Executor.waiting_remind = None
                    time.sleep(1)

                newThread.start()
                thread_list[id] = [newAction, newThread]



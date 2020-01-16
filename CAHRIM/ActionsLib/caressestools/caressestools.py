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

## @package caressestools
#  Library of functions useful for the different CARESSES actions.


import os
import json
import sys
import qi
import paramiko
import shutil
from colorama import Fore

DEF_IMG_APP = "caresses-multimedia"
TABLET_IMG_DEFAULT = "Logo_CARESSES_tablet.png"
TABLET_IMG_EXECUTION = "Logo_CARESSES_tablet_ExecutionMode.png"
TABLET_IMG_REST = "Logo_CARESSES_tablet_RestMode.png"

MEMORY_CHARGER = "CARESSES_onCharger"
MEMORY_FIXED_POSE = "CARESSES_fixedPose"

########################################################################################################################
## Load the caresses-conf.json file from the root of the Software repository and make the settings available.

directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
file_path = os.path.join(directory, "caresses-conf.json")
try:
    with open(file_path) as config_file:
        settings_dict = json.load(config_file)
except:
    print("ERROR: Something is wrong with your 'carresses-conf.json' file.\n"
          "Check:\n"
          " - that it is present at the root of your local Software repository;\n"
          " - that, inside the file, the IP and Port values are correctly set.")
    sys.exit(1)

conf = {
    "robotIP" : settings_dict["Pepper-conf"]["IP"],
    "robotPort" : settings_dict["Pepper-conf"]["Port"],
    "cahrimIP" : settings_dict["CAHRIM-conf"]["IP"],
    "cahrimPort" : settings_dict["CAHRIM-conf"]["Port"],
    "ckbIP" : settings_dict["CKB-conf"]["IP"],
    "ckbPort" : settings_dict["CKB-conf"]["Port"],
    "cspemIP" : settings_dict["CSPEM-conf"]["IP"],
    "cspemPort" : settings_dict["CSPEM-conf"]["Port"],
    "cahrimDBUser" : settings_dict["CAHRIM-database"]["user"],
    "cahrimDBPassword" : settings_dict["CAHRIM-database"]["password"],
    "cahrimDBHost" : settings_dict["CAHRIM-database"]["host"],
    "cahrimDBDatabase" : settings_dict["CAHRIM-database"]["database"],
    "cahrimDBLayout" : settings_dict["CAHRIM-database"]["layout"],
    "interactionNode" : settings_dict["interaction-node"],
    "dockingStation": settings_dict["docking-station"],
    "input": settings_dict["input"],
    "output": settings_dict["output"]
}

## Load Google credentials from json file for speech recognition

fname = os.path.join(os.path.dirname(__file__), "ASR2.json")
try:
    with open(fname) as f:
        gkey = f.read()
except:
    gkey = None
    print("WARNING: File not found - %s" % fname)

########################################################################################################################

## Contains the settings of the file caresses-conf.json
class Settings():

    robotIP = conf["robotIP"]
    robotPort = conf["robotPort"]
    cahrimIP = conf["cahrimIP"]
    cahrimPort = conf["cahrimPort"]
    ckbIP = conf["ckbIP"]
    ckbPort = conf["ckbPort"]
    cspemIP = conf["cspemIP"]
    cspemPort = conf["cspemPort"]
    databaseUser = conf["cahrimDBUser"]
    databasePassword = conf["cahrimDBPassword"]
    databaseHost = conf["cahrimDBHost"]
    databaseInfo = conf["cahrimDBDatabase"]
    databaseLayout = conf["cahrimDBLayout"]
    interactionNode = conf["interactionNode"]
    docking_station = conf["dockingStation"]
    input_mode = conf["input"]
    output_mode = conf["output"]
    googlekey = gkey


## Defines the language abbreviations to use for different services.
class Language():

    lang_dialogflow = ''
    lang_google     = ''
    lang_naoqi      = ''
    lang_qichat     = ''

    @staticmethod
    def setLanguage(lang):
        '''!
        Set the languages for the different services being used.
        The list of languages is limited to the ones supported by Pepper's TTS Engine and should be extended only
        accordingly.

        - TTS Engine (for lang_naoqi and lang_qichat): http://doc.aldebaran.com/2-5/family/pepper_technical/languages_pep.html
        - Google Speech Recognition (for lang_google): https://cloud.google.com/speech/docs/languages
        - Dialogflow (for lang_dialogflow):            https://dialogflow.com/docs/reference/language

        @param lang %Language (spelled in English) to be set
        '''

        lang = lang.lower()

        if lang == 'japanese':
            Language.lang_dialogflow = 'ja'
            Language.lang_google     = 'ja-JP'
            Language.lang_naoqi      = 'Japanese'
            Language.lang_qichat     = 'jpj'

        elif lang == 'english':
            Language.lang_dialogflow = 'en'
            Language.lang_google     = 'en-US'
            Language.lang_naoqi      = 'English'
            Language.lang_qichat     = 'enu'

        elif lang == 'english-indian':
            Language.lang_dialogflow = 'en'
            Language.lang_google     = 'en-IN'
            Language.lang_naoqi      = 'English'
            Language.lang_qichat     = 'enu'

        elif lang == 'french':
            Language.lang_dialogflow = 'fr'
            Language.lang_google     = 'fr-FR'
            Language.lang_naoqi      = 'French'
            Language.lang_qichat     = 'frf'

        elif lang == 'italian':
            Language.lang_dialogflow = 'it'
            Language.lang_google     = 'it-IT'
            Language.lang_naoqi      = 'Italian'
            Language.lang_qichat     = 'iti'

        elif lang == 'german':
            Language.lang_dialogflow = 'de'
            Language.lang_google     = 'de-DE'
            Language.lang_naoqi      = 'German'
            Language.lang_qichat     = 'ded'

        elif lang == 'spanish':
            Language.lang_dialogflow = 'es'
            Language.lang_google     = 'es-ES'
            Language.lang_naoqi      = 'Spanish'
            Language.lang_qichat     = 'spe'

        elif lang == 'chinese':
            Language.lang_dialogflow = 'zh-CN'
            Language.lang_google     = 'cmn-Hans-CN'
            Language.lang_naoqi      = 'Chinese'
            Language.lang_qichat     = 'mnc'

        elif lang == 'mandarin':
            Language.lang_dialogflow = 'zh-TW'
            Language.lang_google     = 'cmn-Hant-TW'
            Language.lang_naoqi      = 'MandarinTaiwan'
            Language.lang_qichat     = 'mnt'

        elif lang == 'arabic':
            # Language.lang_dialogflow = ''
            Language.lang_google     = 'ar-SA'
            Language.lang_naoqi      = 'Arabic'
            Language.lang_qichat     = 'arw'

        else:
            # Set the default language to English
            Language.lang_dialogflow = 'en'
            Language.lang_google     = 'en-US'
            Language.lang_naoqi      = 'English'
            Language.lang_qichat     = 'enu'


## Defines the threshold for triggering autonomous recharging and the minimum battery level required to resume the interaction.
class Battery():

    solution_started = False
    BATTERY_LOW = 10
    BATTERY_MINIMUM = 30


def connectToPepper(pepperIP, pepperPort):
    '''!
    Connect to Pepper and create a NAOqi session.

    @param pepperIP Pepper's ip address
    @param pepperPort Pepper's port
    @return NAOqi session
    '''
    try:
        print 'Connecting to Pepper...'
        session = qi.Session()
        session.connect("tcp://" + pepperIP + ":" + str(pepperPort))
        print("Connected to Naoqi at ip \"" + pepperIP + "\" on port " + str(pepperPort) + ".\n")

        return session

    except Exception as e:
        print e.message
        print ("Can't connect to Naoqi at ip \"" + pepperIP + "\" on port " + str(pepperPort) + ".\n"
                "Please check your script arguments. Run with -h option for help.")
        exit(2)


def fromAutonomousLifeToAwake(session):
    '''!
    Disable autonomous life and wake up Pepper.

    @param session NAOqi session
    @return: ---
    '''

    sLife = session.service("ALAutonomousLife")
    sMotion = session.service("ALMotion")

    # If enabled, disable Autonomous life
    if sLife.getState() in ["solitary", "interactive"]:
        sLife.setState("disabled")

    # If "sleeping", wake up Pepper
    if not sMotion.robotIsWakeUp():
        sMotion.wakeUp()


def fromAwakeToAutonomousLife(session):
    '''!
    Enable autonomous life.

    @param session: NAOqi session
    @return: ---
    '''

    sLife = session.service("ALAutonomousLife")

    # If disabled, enable Autonomous life
    if sLife.getState() == "disabled":
        sLife.setState("solitary")


def setAutonomousAbilities(session, blinking, background, awareness, listening, speaking):
    '''!
    Enable some of the autonomous abilities.

    @param session NAOqi session
    @param blinking boolean for AutonomousBlinking
    @param background boolean for BackgroundMovement
    @param awareness boolean for BasicAwareness
    @param listening boolean for ListeningMovement
    @param speaking boolean for SpeakingMovement
    @return ---
    '''
    sLife = session.service("ALAutonomousLife")

    sLife.setAutonomousAbilityEnabled("AutonomousBlinking", blinking)
    sLife.setAutonomousAbilityEnabled("BackgroundMovement", background)
    sLife.setAutonomousAbilityEnabled("BasicAwareness",     awareness)
    sLife.setAutonomousAbilityEnabled("ListeningMovement",  listening)
    sLife.setAutonomousAbilityEnabled("SpeakingMovement",   speaking)


def getAutonomousAbilities(session):
    '''!
    Get the state of the autonomous abilities

    @param session NAOqi session
    @return a list containing the state of the 5 autonomous abilities
    @rtype list of bool
    '''
    sLife = session.service("ALAutonomousLife")

    blinking   = sLife.getAutonomousAbilityEnabled("AutonomousBlinking")
    background = sLife.getAutonomousAbilityEnabled("BackgroundMovement")
    awareness  = sLife.getAutonomousAbilityEnabled("BasicAwareness")
    listening  = sLife.getAutonomousAbilityEnabled("ListeningMovement")
    speaking   = sLife.getAutonomousAbilityEnabled("SpeakingMovement")

    return [blinking, background, awareness, listening, speaking]


def startPepper(session, starting_node):
    '''!
    Disable autonomous life, wake up Pepper and enable some autonomous abilities.
    Set human-tracking to mode "Head" only (Pepper will not rotate).
    @param session NAOqi session
    @param starting_node Node in which Pepper is located at startup
    '''

    fromAutonomousLifeToAwake(session)
    setAutonomousAbilities(session, False, True, True, True, True)
    preloadImg(session, TABLET_IMG_DEFAULT)
    preloadImg(session, TABLET_IMG_EXECUTION)
    preloadImg(session, TABLET_IMG_REST)

    sBasicAwareness = session.service("ALBasicAwareness")
    sBasicAwareness.setTrackingMode("Head")
    sBasicAwareness.setEngagementMode("FullyEngaged")

    sMemory = session.service("ALMemory")
    sSpeechReco = session.service("ALSpeechRecognition")

    if starting_node == "charger" and Settings.docking_station == True:
        sMemory.insertData(MEMORY_CHARGER, True)
    else:
        sMemory.insertData(MEMORY_CHARGER, False)

    try:
        if sSpeechReco._isFreeSpeechToTextAvailable():
            sSpeechReco._disableFreeSpeechToText()
    except:
        pass


def stopPepper(session):
    '''!
    Disable autonomous abilities and put Pepper in "stand" position.
    @param session NAOqi session
    '''

    sPosture = session.service("ALRobotPosture")

    setAutonomousAbilities(session, False, False, False, False, False)
    sPosture.goToPosture("Stand", 2)


def preloadImg(session, image_state):
    '''!
    Check whether the given image exists on the robot. If yes, preload the tablet image, otherwise store
    in the robot memory that the image is not found to inform following calls of showImg().
    @param session NAOqi session
    @param image_state State of Pepper
    @return ---
    '''

    sTablet = session.service("ALTabletService")
    sMemory = session.service("ALMemory")

    image_dir = "http://%s/apps/%s/images/" % (sTablet.robotIp(), DEF_IMG_APP)
    img = image_dir + image_state

    try:
        sTablet.preLoadImage(img)
        found = True
    except Exception as err:
        found = False
        print("Error during preLoadImage : %s " % err)

    sMemory.insertData("CARESSES_" + image_state + "_found", found)


def showImg(session, image_state):
    '''!
    Check in the robot memory that the given tablet image was previously found by preloadImg(). If yes, load the
    tablet image, otherwise show the writing "pepper" on the tablet.
    @param session NAOqi session
    @param image_state State of Pepper
    @return ---
    '''

    sTablet = session.service("ALTabletService")
    sMemory = session.service("ALMemory")

    found = sMemory.getData("CARESSES_" + image_state + "_found")
    image_dir = "http://%s/apps/%s/images/" % (sTablet.robotIp(), DEF_IMG_APP)
    img = image_dir + image_state

    if found:
        sTablet.showImage(img)
    else:
        sTablet.setBackgroundColor("#828282")
        sTablet.showImageNoCache("http://198.18.0.1/apps/app-launcher/images/Pepper-white.png")


def unloadImg(session):
    '''!
    Unload the tablet image
    @param session NAOqi session
    @return ---
    '''

    sTablet = session.service("ALTabletService")
    sTablet.hide()


def setRobotLanguage(session, language):
    """!
    Sets the robot language, checks if the desired language is supported

    @param session NAOqi session
    @param language The desired language
    """

    tts = session.service("ALTextToSpeech")

    try:
        assert language in tts.getSupportedLanguages()
        tts.setLanguage(language)

    except AssertionError:
        if language.lower() == "indian":
            print language + " is not supported by the robot, " \
                "language set to English"

            tts.setLanguage("English")


def setVoiceVolume(session, volume):
    """!
    Sets the volume of the tts

    @param session NAOqi session
    @param volume The volume, between 0 and 1
    """

    tts = session.service("ALTextToSpeech")

    try:
        assert volume >= 0 and volume <= 1

    except AssertionError:
        print "Incorrect volume, 0.5 taken into account"
        volume = 0.5

    tts.setVolume(volume)


def setVoiceSpeed(session, speed):
    """!
    Set the speed of the robot's voice

    @param session NAOqi session
    @param speed The speed of the voice, between 50 and 400
    """

    tts = session.service("ALTextToSpeech")

    try:
        assert speed >= 50 and speed <= 400

    except AssertionError:
        print "Incorrect voice speed, resetting to the default speed"
        speed = 100

    tts.setParameter("speed", speed)


def setVoicePitch(session, pitch):
    """!
    Sets the pitch of the robot's voice

    @param session NAOqi session
    @param pitch The pitch (shift) 1.0 to 4, 0 disables the effect.
    """

    tts = session.service("ALTextToSpeech")

    try:
        assert (pitch >= 1.0 and pitch <= 4) or pitch == 0
        tts.setParameter("pitchShift", pitch)

    except AssertionError:
        print "Incorrect pitch value, the pitch won't be modified"


def generatePauseInSentence(speech, commaDuration=300, endSentenceDuration=800):
    """!
    Generates pauses in a sentence: a pause after each comma, and a pause after
    each point

    Parameters:
        - speech: string containing the sentence to be pronounced
        - commaDuration: duration in milliseconds of the pause to be inserted
        after a comma
        - endSentenceDuration: duration in milliseconds of the pause to be
        inserted after the end of a sentence (".", "!", "?")

    Returns:
        - formattedSpeech: string containing the formatted sentence
    """
    try:
        assert isinstance(speech, str)
        assert isinstance(commaDuration, int)
        assert isinstance(endSentenceDuration, int)

    except AssertionError:
        return None

    formattedSpeech = str()
    endSentenceList = [".", "?", "!"]

    for word in speech.split():
        if len(word) == 0:
            continue

        formattedSpeech += word + " "

        if word[-1] == ",":
            formattedSpeech += "\\pau=" + str(commaDuration) + "\\"
        elif word[-1] in endSentenceList:
            formattedSpeech += "\\pau=" + str(endSentenceDuration) + "\\"

    return formattedSpeech



def setTabletVolume(session, volume):
    """!
    Sets the volume of the tablet

    @param session NAOqi session
    @param volume The volume, between 0 and 15
    """

    tab = session.service("ALTabletService")

    try:
        assert volume >= 0 and volume <= 15

    except AssertionError:
        print "Incorrect volume, 15 taken into account"
        volume = 15

    tab.setVolume(volume)


def loadMap():
    '''!
    Load the file of the map.

    @return: boolean expressing whether or not the operation was successful
    '''

    print("-----------------------------------------------")
    go_to_aux_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "aux_files", "go_to")
    map_path = os.path.join(go_to_aux_dir, "map.json")
    maps_dir = os.path.join(go_to_aux_dir, "maps")
    map_info_file = os.path.join(go_to_aux_dir, "using_map.txt")

    if os.path.exists(map_path):
        if os.path.exists(map_info_file):
            with open(map_info_file, "r") as mif:
                content = mif.readlines()
            map_name = content[0]
            print("CAHRIM is currently using map " + Fore.GREEN + map_name)
            change = raw_input("Do you want to change the map? (y/n) > ")
            while not change.lower() in ["y", "n"]:
                change = raw_input("Do you want to change the map? (y/n) > ")
            change = change.lower() == "y"
        else:
            print("No info about the map currently used.")
            change = True
    else:
        print("No map in use.")
        change = True

    if change:

        print("Scanning folder 'CAHRIM/ActionsLib/aux_files/go_to/maps' for maps...")
        all_maps = os.listdir(maps_dir)
        all_maps.remove(".gitignore")
        if all_maps == []:
            print(
            "There are no maps to load. Please put one or more map files inside 'CAHRIM/ActionsLib/aux_files/go_to/maps/' and select one when prompted after launching CAHRIM.")
            return False
        elif len(all_maps) == 1:
            print("Selecting the only map found in the folder: %s" % all_maps[0])
            map_index = 0
        else:
            sure = False
            while not sure:
                print(
                "Please enter the index (the number in brackets) corresponding to the map that you want to load. Press 'q' to quit.")
                for index, m in enumerate(all_maps):
                    print("[%2d]  %s" % ((index + 1), m))
                answer = raw_input("Enter the index > ")
                if answer.lower() == 'q':
                    return False
                else:
                    map_index = int(answer) - 1
                    answer_sure = raw_input(
                        "Are you sure you want to load the map '%s'? (y/n) > " % all_maps[map_index])
                    sure = answer_sure.lower() == "y"
                while not map_index in range(len(all_maps)):
                    print("ERROR: Invalid index! Please, try again.")
                    answer = raw_input("Enter the index > ")
                    if answer.lower() == 'q':
                        return False
                    else:
                        map_index = int(answer) - 1
                        answer_sure = raw_input(
                            "Are you sure you want to load the map '%s'? (y/n) > " % all_maps[map_index])
                        sure = answer_sure.lower() == "y"

        map_name = all_maps[map_index]
        selected_map_path = os.path.join(maps_dir, map_name)
        shutil.copy2(selected_map_path, map_path)

        map_info_file = os.path.join(go_to_aux_dir, "using_map.txt")
        with open(map_info_file, "w") as mif:
            mif.writelines(map_name)
        print("Map selected correctly.")
        return True

    else:
        return True

def leaveChargerNode(session):
    '''!
    Pepper leaves the charger node

    @param session NAOqi session
    @return boolean expressing whether or not the operation was successful
    '''

    if Settings.docking_station == True:
        return getOffTheDockingStation(session)
    else:
        return None

def getOffTheDockingStation(session):
    '''!
    Pepper leaves the docking station

    @param session NAOqi session
    @return boolean expressing whether or not the operation was successful
    '''

    sRecharge = session.service("ALRecharge")
    sMemory = session.service("ALMemory")
    sMotion = session.service("ALMotion")

    sMotion.setOrthogonalSecurityDistance(0.05)
    sMotion.setTangentialSecurityDistance(0.05)

    sRecharge.leaveStation()

    while not sRecharge.getStatus() in [0, 4]:  # idle, error
        pass

    sMotion.setOrthogonalSecurityDistance(0.4)
    sMotion.setTangentialSecurityDistance(0.10)

    if sRecharge.getStatus() == 4:
        return False
    else:
        sMemory.insertData(MEMORY_CHARGER, False)
        return True

def goToDockingStation(session):
    '''!
    Pepper goes to the docking station

    @param session NAOqi session
    @return boolean expressing whether or not the operation was successful
    '''

    sRecharge = session.service("ALRecharge")
    sMemory = session.service("ALMemory")

    sRecharge.goToStation()
    while not sRecharge.getStatus() in [0, 4]:  # idle, error
        pass
    if sRecharge.getStatus() == 4:
        return False
    elif sRecharge.getStatus() == 0:
        sMemory.insertData(MEMORY_CHARGER, True)
        return True

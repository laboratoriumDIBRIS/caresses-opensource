"""
A sample showing how to have a NAOqi service as a Python app.
"""
###########################################################
# Modified by Roberto Menicatti for the CARESSES project
# Universita' degli studi di Genova, DIBRIS
# roberto.menicatti@dibris.unige.it
###########################################################
__version__ = "0.2.2"
__copyright__ = "Copyright 2015, Aldebaran Robotics"
__author__ = 'YOURNAME'
__email__ = 'YOUREMAIL@aldebaran.com'

import qi
import numpy as np
import os
import sys
import time
import shutil
import threading
import logging
import argparse

from vad import VAD
from sound_analyser import SoundAnalyser
#
import abcdk.sound.analyse
from abcdk.leds import LedsDcm

from abcdk.stk import runner
from abcdk.stk import events
from abcdk.stk import services


class AbcdkSoundReceiver(object):
    """
    Service for Autonomous Speech Recognition
    """
    APP_ID = "com.aldebaran.ALMyService"

    def __init__(self, session, qiapp=None, args=None):
        # generic activity boilerplate
        self.session = session
        # self.qiapp = qiapp
        self.events = events.EventHelper(self.session)
        self.s = services.ServiceCache(self.session)

        home = os.path.expanduser("~")
        logDir = home + "/.abcdk/logs"
        if not os.path.isdir( logDir ):
            os.makedirs(logDir)
        logging.basicConfig(filename= logDir + '/AbcdkSoundReceiver.log',
            level=logging.DEBUG,
            format='%(levelname)s %(asctime)s %(threadName)s %(message)s (%(module)s.%(lineno)d)',
            filemode='w')

        self.args = args

    # def on_start(self):
    #     self.start()

    @qi.bind(returnType=qi.Void, paramsType=[qi.String, qi.Bool, qi.Float, qi.Float, qi.Float])
    def start(self, language, useGoogleKey, preVad, postVad, EnergyThreshold):
        """
        Start the module. Will not run.
        To have the module running call "subscribeAudio"
        """
        logging.info("Start module")

        nNbrChannelFlag = 0 
        nDeinterleave = 0
        self.nSampleRate = 48000
        if nNbrChannelFlag == 0:
            self.nNbrChannel = 4
        else:
            self.nNbrChannel = 1
        #nEnergyThreshold = 300 # ears mic
        #nEnergyThreshold = 140 # pepper mic
        nEnergyThreshold = EnergyThreshold
        self.bNoiseDetectedPrev = False
        self.bSpeechDetectedPrev = False
        self.visualFeedback = True
        self.nInhibitEndTime = time.time() - 1000
        self.nDelayAfterSoundGeneration = 0.050 # time to empty soundcard buffer

        self.pause_var = False
        self.is_running = True

        self.sa = SoundAnalyser( self.session,
                                 nSampleRate = self.nSampleRate, 
                                 datatype=np.int16, 
                                 nEnergyThreshold = nEnergyThreshold, 
                                 bActivateSpeechRecognition = True,
                                 bUseAnonymous= not useGoogleKey, #not(self.args.useGoogleKey),
                                 bKeepAudioFiles = False, #self.args.keepAudioFiles,
                                 strUseLang= language, #self.args.language,
                                 rTimePreVAD = preVad,
                                 rTimePostVAD = postVad)

        self.audio = self.session.service("ALAudioDevice")
        self.audio.setClientPreferences("AbcdkSoundReceiver", self.nSampleRate, nNbrChannelFlag, nDeinterleave)

        self.mem = self.session.service("ALMemory")


    @qi.bind(returnType=qi.Void, paramsType=[])
    def subscribeAudio(self):
        """
        Subscribe to AudioDevice. Allows the processRemote function to be called
        when a new audio sample is available
        """
        while self.is_running:
            logging.info("Subscribe to audio")
            try:
                self.audio.subscribe("AbcdkSoundReceiver")
                break
            except AttributeError:
                logging.info("Audio device not available. Retrying.")
                time.sleep(1.)
        logging.info("Subscribed to audio")


    def processRemote( self, nbOfChannels, nbrOfSamplesByChannel, aTimeStamp, aBuffer ):
        """
        Method called automatically when a new buffer is available on AudioDevice
        """
        #try:
        return self._processRemote(nbOfChannels, nbrOfSamplesByChannel, aTimeStamp, aBuffer )
        #except BaseException, err:
        #    logging.error(str(err))

    @qi.bind(returnType=qi.Void, paramsType=[qi.Bool])
    def setVisualFeedback(self, status):
        """
        Stop the service.
        """
        logging.info("Set visual feedback to: " + str(status) )
        self.sa.setVisualFeedback(status)

    @qi.bind(returnType=qi.String, paramsType=[])
    def getLanguage(self):
        """
        Get the current language.
        """
        return self.sa.strUseLang

    @qi.bind(returnType=qi.Void, paramsType=[qi.String])
    def setLanguage(self, strLanguage):
        """
        Set the current language.
        """
        self.sa.strUseLang = strLanguage

    @qi.bind(returnType=qi.Bool, paramsType=[])
    def getKeepAudioFiles(self):
        """
        Return true if the module is currently saving the audio files.
        """
        return self.sa.bKeepAudioFiles

    @qi.bind(returnType=qi.Void, paramsType=[qi.Bool])
    def setKeepAudioFiles(self, bKeepAudioFiles):
        """
        Set to true in order to save the audio files
        """
        self.sa.bKeepAudioFiles = bKeepAudioFiles

    @qi.bind(returnType=qi.Bool, paramsType=[])
    def getUseGoogleKey(self):
        """
        Return true if the module is currently using a google key.
        """
        return not(self.sa.bUseAnonymous)

    @qi.bind(returnType=qi.Void, paramsType=[qi.Bool])
    def setUseGoogleKey(self, bGoogleKey):
        """
        Set to true in order to use a google key.
        """
        self.sa.bUseAnonymous = not(bGoogleKey)


    @qi.bind(returnType=qi.Void, paramsType=[])
    def stop(self):
        """
        Stop the service.
        """
        logging.info("AbcdkSoundReceiver stopped by user request.")
        # self.qiapp.stop()
        logging.info("Cleaning")
        # self.unsubscribeAudio()
        self.sa.stop()
        logging.info("AbcdkSoundReceiver finished.")

    @qi.bind(returnType=qi.Void, paramsType=[qi.Bool])
    def pause(self, pause):
        """
        Pause the service.
        """
        if not isinstance(pause, bool):
            logging.error("Pause argument has to be bool. Found type '%s'" % type(pause))
            return
        self.pause_var = pause
        self.sa.pause()
        if self.pause_var:
            logging.info("AbcdkSoundReceiver pausing ASR.")
        else:
            logging.info("AbcdkSoundReceiver unpausing ASR.")


    @qi.nobind
    def on_stop(self):
        """
        Cleanup
        """
        logging.info("Cleaning")
        self.unsubscribeAudio()
        self.sa.stop()
        logging.info("ALMyService finished.")


    @qi.bind(returnType=qi.Void, paramsType=[])
    def unsubscribeAudio(self):
        logging.info("Unsubscribe from audio")
        self.audio.unsubscribe("AbcdkSoundReceiver")


    def _processRemote(self, nbOfChannels, nbrOfSamplesByChannel, aTimeStamp, aBuffer):
        """
        Main method receiving the audio buffer and returning the recognized words
        """
        logging.debug("Process remote")

        if abcdk.sound.analyse.isAudioOutUsed(self.mem) == True:
            logging.debug("Detected robot speaking")
            self.nInhibitEndTime = time.time() + self.nDelayAfterSoundGeneration

        if time.time() < self.nInhibitEndTime :
            logging.debug("Inhibited => skip buffer analyse" )
            return

        if self.pause_var:
            logging.debug("Analysis paused. Skipping.")
            return

        aSoundDataInterlaced = np.fromstring( str(aBuffer), dtype=np.int16 );

        self.sa.setInputBuffer( aSoundDataInterlaced)


####################
# Setup and Run
####################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Service for Autonomous Speech\
                                                  Recognition')
    parser.add_argument('--qi-url', help='IP of the robot')
    parser.add_argument('--language', default="English",
                        help='Language recognized by the ASR engine')
    parser.add_argument('--keepAudioFiles', default=False, action='store_true',
                        help='Store the wav files analyzed')
    parser.add_argument('--useGoogleKey', default=False, action='store_true',
                        help='Trigger the use of a google account')
    args = parser.parse_args()

    qiapp = runner.init(args.qi_url,parser)
    activityASR,service_idASR = runner.register_activity(AbcdkSoundReceiver, "AbcdkSoundReceiver", 
                                                         qiapp, args)
   # activityLeds,service_idLeds = runner.register_activity(LedsDcm, "LedsDcm", qiapp)
    try:
        time.sleep(1)
        qiapp.session.service("AbcdkSoundReceiver").subscribeAudio()
        qiapp.run()
    finally:
        runner.cleanup(qiapp,activityASR,service_idASR)
        #runner.cleanup(qiapp,activityLeds,service_idLeds)


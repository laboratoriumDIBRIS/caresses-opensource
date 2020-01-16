import numpy as np
import time
import logging
import datetime
import os
import shutil
import math
import timeit
import unicodedata
import functools

from vad import VAD
from abcdk.stk import runner

from abcdk.sound import wav
from abcdk.sound import freespeech
import abcdk.python_speech_features.base as base
from abcdk.leds import LedsDcm

import threading
import thread
recordedFilesMutex = threading.Lock()
ledsMutex = threading.Lock()

class SoundAnalyser:  
    def __init__( self, session,
                        nSampleRate = 16000,
                        datatype=np.int16, 
                        nNbrChannel = 4, 
                        nEnergyThreshold = 300, 
                        bActivateSpeechRecognition = True,
                        bUseAnonymous=True,
                        strUseLang = "", 
                        bKeepAudioFiles = False,
                        rTimePreVAD = 0.150,
                        rTimePostVAD = 0.500):
        """
        analyse chunk of data (must have no specific to robot nor naoqi method)
        - nSampleRate: the sample rate of your sound
        - datatype: the way your sound is stored
        - nNbrChannel: ...
        - nEnergyThreshold: threshold for the sound to be analysed for sound reco
        - rVadThreshold: threshold for confidence of the VAD: Currently not used
        - bActivateSpeechRecognition: do we send the interesting sound to the speech recognition ?
        - bActivateSoundRecognition: 
        - strUseLang: lang to use for speech recognition, eg: "fr-FR", if leaved to "": use language currently in the tts
        """

        self.session = session
        self.nSampleRate = nSampleRate
        self.datatype = datatype
        self.nNbrChannel = nNbrChannel
        self.bActivateSpeechRecognition = bActivateSpeechRecognition
        self.bUseAnonymous = bUseAnonymous
        self.rEnergyThreshold = nEnergyThreshold; # 60 # 10
        self.strUseLang = strUseLang

        self.rTimePreVAD = rTimePreVAD
        self.rTimePostVAD = rTimePostVAD
        
        self.rMfccWindowStepInSec = 0.01
        
        self.nSizePreBuffer = int(self.rTimePreVAD*nSampleRate) # conversion from time to samples
        

        self.bStoringSpeech = False; # are we currently storing for speech reco ?
        self.bStoringNoise = False; # are we currently storing for sound reco ?
        self.aRecognizedSpeech = None
        self.bSpeechDetected = False
        self.bVisualFeedback = True
        self.bSpeechAnalysed = False
        
            
        # all sounds buffer will be stored in monochannel
        self.aStoredDataSpeech = np.array( [], dtype=self.datatype ) # a numpy int16 array storing current sound
        self.aStoredDataNoise = np.array( [], dtype=self.datatype )
        self.aStoredMfccSound = np.array( [], dtype=np.float64 )
        self.aStoredSoundPreBuffer = np.array( [], dtype=self.datatype )
        self.createdFiles = []
        
        self.timeLastBufferReceived = time.time()

        self.timeLastPeak = time.time() - 1000
        self.timeLastVAD = self.timeLastPeak
        
        self.strLastRecognized = "";
        self.strDstPath = "/tmp/"
        self.debug_fileAllSpeech = None
        self.bKeepAudioFiles = bKeepAudioFiles
        self.bIsOnRobot = runner.is_on_robot()
        home = os.path.expanduser("~")
        self.storeDir = home + "/.abcdk/prevWavs"
        if not os.path.isdir( self.storeDir ):
            os.makedirs( self.storeDir )

        self.vad = VAD(self.rTimePreVAD, self.rTimePostVAD )
        self.fs = freespeech.FreeSpeech(self.session)
        self.mem = self.session.service("ALMemory")
        self.leds = LedsDcm.LedsDcm(self.session)
        self.leds.createProxy()
        self.leds.createAliases()
        self.rEndLedLockTime = time.time()
        self.touch = self.mem.subscriber("TouchChanged")
        self.id_touch = self.touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))
        self.touched=False
        self.runningThread = True
        thread.start_new_thread(self.asrOnFile,())

    def __del__( self ):
        self.stop()
        if self.debug_fileAllSpeech != None:
            self.debug_fileAllSpeech.write( self.strDstPath + "concatenated_speechs.wav" )

    def stop(self):
        self.runningThread = False
        pass

    def pause(self):
        # stop the current recording of audio
        self.bStoringSpeech = False
        # reset the stored audio buffer
        self.aStoredDataSpeech = np.array( [], dtype=self.datatype ) 

    def setKeepAudioFiles( self, bNewState ):
        self.bKeepAudioFiles = bNewState

    def setVisualFeedback( self, bNewState ):
        self.bVisualFeedback = bNewState
        
    def _writeBufferToFile( self, datas, strFilename ):
        wavFile = wav.Wav()
        wavFile.new( nSamplingRate = self.nSampleRate, nNbrChannel = 1, nNbrBitsPerSample = 16 )
        wavFile.addData( datas )
        bRetWrite = wavFile.write( strFilename )
        
        if not self.bIsOnRobot:
            if self.debug_fileAllSpeech == None:
                self.debug_fileAllSpeech = wav.Wav()
                self.debug_fileAllSpeech.new( nSamplingRate = self.nSampleRate, nNbrChannel = 1, nNbrBitsPerSample = 16 )
            self.debug_fileAllSpeech.addData( datas )
            self.debug_fileAllSpeech.addData( np.zeros( self.nSampleRate/2, self.datatype) )

        return bRetWrite
            
        
    def _sendToSpeechReco( self, strFilename ):
        """
        Send a file to the speech recognition engine.
        Return: the string of recognized text, + confidence or None if nothing recognized
        """

        logging.info("_sendToSpeechReco: sending to speech reco " + strFilename + " to detect it in " + self.strUseLang)
        retVal = None
        
        timeBegin = timeit.default_timer()
        
        retVal = self.fs.analyse_anonymous( strFilename, strUseLang=self.strUseLang ) if self.bUseAnonymous \
            else self.fs.analyse( strFilename, strUseLang=self.strUseLang )
                
        rProcessDuration = timeit.default_timer() - timeBegin
        
        logging.debug( "SoundAnalyser._sendToSpeechReco: freeSpeech analysis processing takes: %5.2fs" % rProcessDuration )
        
        if( 0 ): # disabled
            self.rSkipBufferTime = rProcessDuration  # if we're here, it's already to zero
        
        if retVal != None:
            retVal = [ retVal[0][0], retVal[0][1] ]
            txtForRenameFile = retVal[0]
        else:
            txtForRenameFile = "Not_Recognized"
            
        if self.bKeepAudioFiles:
            newfilename = strFilename.replace( ".wav", "__%s.wav" % self.convertForFilename(txtForRenameFile) )
            baseFilename = os.path.basename(strFilename)
            newBaseFilename = os.path.basename(newfilename)
            newfilename = self.storeDir + "/" + newBaseFilename
            shutil.move(  strFilename, newfilename )
            logging.info( "Saved wav file in " + newfilename)
        
        return retVal

    def convertForFilename(self, strTxt ):
        """
        convert a text to be usable as filename
        "toto is happy" => "toto_is_happy"
        """
        s = strTxt
        s = s.replace( " ", "_" )
        s = s.replace( "'", "_" )
        s = s.replace( "\"", "_" )
        s = s.replace( ",", "_" )
        s = s.replace( ":", "_" )
        s = s.replace( "/", "_" )
        s = s.replace( "\\", "_" )
        s = s.replace( "-", "_" )
        return s
    # convertForFilename - end

    def _sendFileToRemoteSoundRecognition( self, strFilename ):
        """
        ugly send to the sound recognition in background from a remote computer (just for ears project)
        """        
        #~ os.system( "scp -q %s nao@%s:%s" % (strFilename, self.strNaoIP, strFilename) ) # assume folder exists at destination
        #~ if( self.mem == None ):
            #~ import naoqi
            #~ self.mem = naoqi.ALProxy( "ALMemory", self.strNaoIP, 9559 )
        #~ if( self.mem != None ):
            #~ self.mem.raiseMicroEvent( "SoundRecoAnalyseFilename", strFilename )
        pass
        
    def _sendFileToSoundRecognition( self, buffer ):
        pass
        
    def setInputFile( self, strFilename ):
        """
        analyse a file, return all voice segment
        """
        s = wav.Wav( strFilename )

        if not s.isOpen():
            raise OSError("File not found: " + strFilename)

        timeBegin = time.time()
        aMixedSoundData = s.data
        if s.nNbrChannel > 1:
            aMixedSoundData = aMixedSoundData[0::s.nNbrChannel]+aMixedSoundData[1::s.nNbrChannel] 

        self.nSampleRate = s.nSamplingRate

        nNbrOfSamplesByChannel = len(s.data) / s.nNbrChannel        
        rSoundDataDuration = nNbrOfSamplesByChannel / float(self.nSampleRate)

        return self.analyseBuffer(aMixedSoundData,rSoundDataDuration)
                
    def setInputBuffer(self, aInterlacedSoundData, bVerbose = False ):
        """
        This is THE method that receives all the sound buffers from the "ALAudioDevice" module or the sound card or a file
        - aSoundData: it's an interlaced chunks of wav of a various length
        Return [bNoiseDetected, bSpeechDetected, aRecognizedNoise, aRecognizedSpeech, aRecognizedUser]
            - aRecognizedXxx: a pair [strText, rConfidence, rDuration]
                - strText: the recognized text, or name of the recognized sound
                - rConfidence: [0..1]
                - rDuration: duration of the recognized sound                 
                or [] if nothing recognized
                or None if nothing analized
            - aRecognizedUser: to be defined later
            
        """
        self.bVerbose = bVerbose
        
        nNbrOfSamplesByChannel = len(aInterlacedSoundData) / self.nNbrChannel        
        rSoundDataDuration = nNbrOfSamplesByChannel / float(self.nSampleRate)
        
        logging.debug( "Receiving a buffer of len: %s (equivalent to %5.3fs) (shape:%s)" % (len(aInterlacedSoundData), rSoundDataDuration, str(aInterlacedSoundData.shape)) )
        
        if time.time() > self.timeLastBufferReceived + 0.7:
            # our buffer is now to old (for instance the robot was speaking and we were inhibited)
            logging.info( "Clearing buffer after gap of %5.2fs (after inhibition...)" % (time.time()-self.timeLastBufferReceived) )
            self.bStoringSpeech = False
            self.aStoredDataSpeech = np.array( [], dtype=self.datatype ) # reset
            
        self.timeLastBufferReceived = time.time()
        
        aSoundData = np.reshape( aInterlacedSoundData, (self.nNbrChannel, nNbrOfSamplesByChannel), 'F' );
        
        # sum of two mics
        aMixedSoundData = aSoundData[0]+aSoundData[1]

        self.vadSplitBuffer(aMixedSoundData,rSoundDataDuration)

    def vadSplitBuffer(self,aMixedSoundData,rSoundDataDuration):
        global recordedFilesMutex 

        start = timeit.default_timer()
        computedMfcc = base.mfcc( aMixedSoundData, samplerate=self.nSampleRate, winstep=self.rMfccWindowStepInSec )
        stop = timeit.default_timer()
        logging.debug("Time for mfcc: " +str(stop-start))
        
        start = timeit.default_timer()
        aVadStateChange = self.vad.computeFromMfcc( computedMfcc, self.rMfccWindowStepInSec )
        stop = timeit.default_timer()
        logging.debug( "aVadStateChange: %s" % aVadStateChange )
        logging.debug("Time for vad " +str(stop-start))

        if len(aVadStateChange) > 0:
            nColor = 0x0000ff #blue
            rTime = 0.5
        else:
            nColor = 0x808080 #grey
            rTime = 0.0
        self.visualFeedback(rTime,nColor)
        
        # analyse VAD analyse results
        bStoringSpeechDone = False
        self.bSpeechDetected = False
        self.bSpeechAnalysed = False
        for i in range(len(aVadStateChange)):            
            b, t = aVadStateChange[i]
            if b: 
                if t < 0.:
                    # take datas from preBuffer
                    nNbrSamples = int(-t*self.nSampleRate)
                    self.aStoredDataSpeech = self.aStoredSoundPreBuffer[-nNbrSamples:]
                    
                    t = 0.

                # add data to next changes:
                if i+1 < len(aVadStateChange):
                    rDuration = aVadStateChange[i+1][1]-t
                else:
                    rDuration = rSoundDataDuration-t

                nStart = int(t*self.nSampleRate)
                nDuration = int(rDuration*self.nSampleRate)
                
                self.aStoredDataSpeech = np.concatenate( (self.aStoredDataSpeech, aMixedSoundData[nStart:nStart+nDuration]) );
                
                self.bStoringSpeech = True
                bStoringSpeechDone = True

            else:
                self.bStoringSpeech = False
                self.mem.raiseMicroEvent( "Audio/SpeechDetected", True )

                strFilename = self.strDstPath + datetime.datetime.now().strftime("%Y_%m_%d-%Hh%Mm%Ss%fms") + "_speech.wav";
                logging.debug( "Outputting speech to file: '%s'" % strFilename );

                rDuration = len(self.aStoredDataSpeech) / float(self.nSampleRate)
                start = timeit.default_timer()
                bRetWrite = self._writeBufferToFile( self.aStoredDataSpeech, strFilename  )
                stop = timeit.default_timer()
                logging.debug( "Writting buffer to file: " + str(stop - start) )

                if bRetWrite:
                    recordedFilesMutex.acquire()
                    self.createdFiles.append((strFilename,rDuration))
                    recordedFilesMutex.release()

                # reset the stored speech 
                self.aStoredDataSpeech = np.array( [], dtype=self.datatype ) 

         

        logging.debug( "Lenght aStoredDataSpeech: '%i'" % len(self.aStoredDataSpeech) );

        if self.bStoringSpeech and not bStoringSpeechDone:
            self.aStoredDataSpeech = np.concatenate( (self.aStoredDataSpeech, aMixedSoundData) );
            self.bSpeechDetected = True
            logging.debug("recording!")
            
        if self.bStoringSpeech:
            if len(self.aStoredDataSpeech) > self.nSampleRate*8 or self.touched:
                # if more than 14 sec, keep only 10 last sec
                #logging.warning( "SoundAnalyser.analyse: buffer too long, keeping only 10 last seconds..." )
                #self.aStoredDataSpeech = self.aStoredDataSpeech[self.nSampleRate*4:] # removing by chunk of 4 sec
                if self.touched:
                    logging.warning( "SoundAnalyser.analyse: Pepper touched, forcing analysis" )
                    self.touched=False
                else:
                    logging.warning( "SoundAnalyser.analyse: buffer too long, forcing analysis" )

                ##tobeadded->send audio and start reco again
                self.bStoringSpeech = False
                self.mem.raiseMicroEvent( "Audio/SpeechDetected", True )
                strFilename = self.strDstPath + datetime.datetime.now().strftime("%Y_%m_%d-%Hh%Mm%Ss%fms") + "_speech.wav";
                logging.debug( "Outputting speech to file: '%s'" % strFilename );
                rDuration = len(self.aStoredDataSpeech) / float(self.nSampleRate)
                bRetWrite = self._writeBufferToFile( self.aStoredDataSpeech, strFilename  )
                logging.debug( "Writting buffer to file: ")
                if bRetWrite:
                    recordedFilesMutex.acquire()
                    self.createdFiles.append((strFilename,rDuration))
                    recordedFilesMutex.release()
                self.aStoredDataSpeech = np.array( [], dtype=self.datatype ) 
                nNbrSamples = int(0.3*self.nSampleRate)
                self.aStoredDataSpeech = self.aStoredSoundPreBuffer[-nNbrSamples:]
                self.bStoringSpeech = True


                # rDuration = rSoundDataDuration-t

                #nStart = int(-0.3*self.nSampleRate)
                #nDuration = int(rDuration*self.nSampleRate)
                #self.aStoredDataSpeech = np.concatenate( (self.aStoredDataSpeech, aMixedSoundData[nStart:nStart+nDuration]) );
                #################
        
        # prebuffer store and offseting
        self.aStoredSoundPreBuffer = np.concatenate( (self.aStoredSoundPreBuffer, aMixedSoundData) );
        self.aStoredSoundPreBuffer = self.aStoredSoundPreBuffer[-self.nSizePreBuffer:]

    def asrOnFile(self):
        global recordedFilesMutex 
        
        while self.runningThread == True:

            recordedFilesMutex.acquire()
            if len(self.createdFiles) > 0:
                inputFile,rDuration = self.createdFiles.pop(0)
            else:
                inputFile = ""
            recordedFilesMutex.release()
            
            if inputFile != "":
                ret = self._sendToSpeechReco( inputFile )
                if ret != None:
                    self.aRecognizedSpeech = [ret[0], ret[1], rDuration]
                else:
                    self.aRecognizedSpeech = None
                    
                self.bSpeechDetected = False
                self.bSpeechAnalysed = True
                if self.aRecognizedSpeech != None:                
                    nColor = 0x00ff00 #green
                    self.mem.raiseMicroEvent( "Audio/RecognizedWords", [[self.aRecognizedSpeech[0], self.aRecognizedSpeech[1]]] )
                else:
                    nColor = 0xff0000 #red
                    self.mem.raiseMicroEvent( "Audio/RecognizedWords", [] )
                rTime = 1.0 
                self.visualFeedback(rTime,nColor)

            time.sleep(0.1)

    def onTouch(self, msg, value):
        self.touched = True


    def visualFeedback(self,rTime,nColor):
        if self.bVisualFeedback == True:
            ledsMutex.acquire()
            if time.time() > self.rEndLedLockTime:
                logging.debug("Actually do the feedback")
                self.leds.setEyesOneLed( 1, .0, nColor )
                self.leds.setChestColor( .0, nColor )
                self.rEndLedLockTime = time.time() + rTime
                logging.debug("End lock time: " + str(self.rEndLedLockTime))
            ledsMutex.release()
        


    def computeEnergyBestNumpy(self, aSample ):
        """
        Compute sound energy on a mono channel sample, aSample contents signed int from -32000 to 32000 (in fact any signed value)
        """
        if( len(aSample) < 1 ):
            return 0
        diff = np.diff( aSample )
        diff = np.array(diff, dtype=np.int32)
        diff *= diff
        rEnergy = np.mean(diff)
        nEnergyFinal = int( math.sqrt( rEnergy ) )
        return nEnergyFinal
    # computeEnergyBestNumpy - end
        
    

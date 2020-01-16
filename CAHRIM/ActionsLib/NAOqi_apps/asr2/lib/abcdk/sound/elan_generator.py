###########################################################
# Aldebaran Behavior Complementary Development Kit
# Sound Processor 
# Aldebaran Robotics (c) 2010 All Rights Reserved - This file is confidential.
###########################################################

import system
import os
import time

import logging

import sound
from sound import wav
from AbcdkSoundReceiver.vad import VAD
import python_speech_features

from stk import runner


class ElanGenerator:
    def __init__( self ):
        self.bIsOnRobot = runner.is_on_robot()
        rTimePreVAD = 0.150
        rTimePostVAD = 0.500
        self.vad = VAD(rTimePreVAD, rTimePostVAD )
            
    def generateTimeSegmentsFromFlag( self, aFlag, rFlagDurationInSec ):
        """
        return an array of pair of voice segment [startMs,stopMs]
        """
        out = []
        bPrevIsOn = False
        for i in range( len(aFlag)+1 ):
            rCurrentTime = i*rFlagDurationInSec
            nCurrentTimeMs = int(rCurrentTime*1000)
            if i == len(aFlag):
                bFlag=False # last segment was speech
            else:
                bFlag = aFlag[i]
            if bPrevIsOn != bFlag:
                bPrevIsOn = bFlag
                if bFlag:
                    nStartTimeMs = nCurrentTimeMs
                else:
                    nStopTimeMs = nCurrentTimeMs
                    out.append( [nStartTimeMs,nStopTimeMs] )
        # for - end
        return out
    # generateTimeSegmentFromFlag - end
        
    def generateSoundFromFlag( self, audiodata, samplerate, aFlag, rFlagDurationInSec ):
        """
        generate an audio buffer by removing the data not flagged
        return the generated audio data
        - rFlagDurationInSec: sound duration of each block
        """
        out = []
        nLenData = int(rFlagDurationInSec*samplerate)
        emptyData = np.zeros( nLenData )
        for i in range( len(aFlag) ):
            isrc = int(i*rFlagDurationInSec*samplerate) # recomputed to be more precise
            #if aFlag[i] or ( i+1 < len(aFlag) and aFlag[i+1] ) or ( i+2 < len(aFlag) and aFlag[i+2] ):
            if aFlag[i]: # prehear is now made directly in the vad method
                data = audiodata[isrc:isrc+nLenData]
            else:
                data = emptyData
                data = [] # to remove silence in the destination
            out.extend(data)
        print len(out)
        return out
                
    # generateSoundFromFlag - end
    
    def generateEafFile( self, strDestinationFile, aFlag, rFlagDurationInSec, strAudioReferenceFilename = "" ):
        """
        generate an elan annotation file from a list of time and a sound
        """
        file = open( strDestinationFile, "wt" )
        if not file:
            print( "ERR: generateEafFile: cannot write to '%s'" % strDestinationFile )
            return -1
        absfile = strAudioReferenceFilename
        relfile = ""
        
        out = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<ANNOTATION_DOCUMENT AUTHOR=\"\" DATE=\"2017-01-13T13:07:31+01:00\" FORMAT=\"3.0\" VERSION=\"3.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:noNamespaceSchemaLocation=\"http://www.mpi.nl/tools/elan/EAFv3.0.xsd\">\n\t<HEADER MEDIA_FILE=\"\" TIME_UNITS=\"milliseconds\">\n\t\t<MEDIA_DESCRIPTOR MEDIA_URL=\"file://%s\" MIME_TYPE=\"audio/x-wav\" RELATIVE_MEDIA_URL=\"%s\"/>\n\t\t<PROPERTY NAME=\"URN\">urn:nl-mpi-tools-elan-eaf:730155ec-fa67-43b6-b1d1-120aae988756</PROPERTY>\n\t\t<PROPERTY NAME=\"lastUsedAnnotationId\">1</PROPERTY>\n\t</HEADER>\n"  % (absfile,relfile)
        nNumTimeSlot = 1
        outTimeSlot = ""
        nNumAnnotation = 1
        outAnnotationBlock = ""
        
        rPrevStartTimeMs = -1
        outCompactInfo = ""
        
        outSrtInfo = ""
        
        bPrevIsOn = False
        
        # todo: factorise using generateTimeSegmentFromFlag method
        for i in range( len(aFlag) ):
            rCurrentTime = i*rFlagDurationInSec
            nCurrentTimeMs = int(rCurrentTime*1000)
            if bPrevIsOn != aFlag[i]:
                bPrevIsOn = aFlag[i]
                if aFlag[i]:
                    timeTs = nCurrentTimeMs
                    rPrevStartTimeMs = nCurrentTimeMs
                else:
                    timeTs = nCurrentTimeMs-10                    
                    outAnnotationBlock += "\t\t<ANNOTATION>\n\t\t\t<ALIGNABLE_ANNOTATION ANNOTATION_ID=\"a%d\" TIME_SLOT_REF1=\"ts%d\" TIME_SLOT_REF2=\"ts%d\"><ANNOTATION_VALUE></ANNOTATION_VALUE></ALIGNABLE_ANNOTATION>\n\t\t</ANNOTATION>\n" % (nNumAnnotation, nNumTimeSlot-1,nNumTimeSlot)
                    outCompactInfo += "%9.3f, %9.3f\n" % (rPrevStartTimeMs/1000.,nCurrentTimeMs/1000.)
                    outSrtInfo += "%d\n%s --> %s\n\n\n" % (nNumAnnotation,stringtools.timeMsToSrtStyle(rPrevStartTimeMs),stringtools.timeMsToSrtStyle(nCurrentTimeMs))
                    nNumAnnotation += 1
                    
                outTimeSlot += "\t\t<TIME_SLOT TIME_SLOT_ID=\"ts%d\" TIME_VALUE=\"%d\"/>\n" % (nNumTimeSlot, timeTs)
                nNumTimeSlot += 1
        # for - end
                

        out += "\t<TIME_ORDER>\n"
        out += outTimeSlot
        out += "\t</TIME_ORDER>\n"
        
        out += "\t<TIER LINGUISTIC_TYPE_REF=\"default-lt\" TIER_ID=\"voices\">\n"
        out += outAnnotationBlock
        out += "\t</TIER>\n"
        
        out += "\t<LINGUISTIC_TYPE GRAPHIC_REFERENCES=\"false\" LINGUISTIC_TYPE_ID=\"default-lt\" TIME_ALIGNABLE=\"true\"/>\n\t<CONSTRAINT DESCRIPTION=\"Time subdivision of parent annotation's time interval, no time gaps allowed within this interval\" STEREOTYPE=\"Time_Subdivision\"/>\n\t<CONSTRAINT DESCRIPTION=\"Symbolic subdivision of a parent annotation. Annotations refering to the same parent are ordered\" STEREOTYPE=\"Symbolic_Subdivision\"/>\n\t<CONSTRAINT DESCRIPTION=\"1-1 association with a parent annotation\" STEREOTYPE=\"Symbolic_Association\"/>\n\t<CONSTRAINT DESCRIPTION=\"Time alignable annotations within the parent annotation's time interval, gaps are allowed\" STEREOTYPE=\"Included_In\"/>\n</ANNOTATION_DOCUMENT>"

        #~ print out
        file.write(out)
        file.close()
        print( "INF: generateEafFile: '%s' generated (refering '%s')" % (strDestinationFile,strAudioReferenceFilename) )

        strOutFilenameNoExt = os.path.basename(strAudioReferenceFilename)
        strOutFilenameNoExt = os.path.splitext(strOutFilenameNoExt)[0]
        if 1:
            # output compact file
            strOutFilename = strOutFilenameNoExt + "_seg.txt"
            file = open( "/tmp/" + strOutFilename, "wt" )
            file.write(outCompactInfo)
            file.close()
            print( "INF: generateEafFile: compact '%s' written" % strOutFilename )
        
        if 1:
            # output srt file            
            strOutFilename = strOutFilenameNoExt + "_seg.srt"
            file = open( "/tmp/" + strOutFilename, "wt" )
            file.write(outSrtInfo)
            file.close()
            print( "INF: generateEafFile: srt '%s' written" % strOutFilename )
            
        return 1        
        
        
        
    def computeVADFromMfcc( self, mfcc_res, samplerate ):
        vad = []
        nCptEmptySinceDetected = 1000
        bPrevPotentialVoice = False
            
        # todo: band index should be relative to the samplerate (or perhaps not, in fact)
        # mais surtout au nombre de cep (1 pour 13, 2 pour 26)
        if len(mfcc_res[0]) == 13:
            nFirstBand = 1
            nNbrBandToCheck = 3
            # 10 seems great for 48khz
            nLimit =  11 # 10: ok pour voix, si on veut enlever tout les claquements de doigs et ... il faut 13 voire 16
            nAddThresholdLastBand = 3
            
            if samplerate <= 24000:
                nLimit = 6
            if samplerate <= 12000:
                nLimit = 5

            nVerbottenBandFirst = 8
            nVerbottenBandNbr = 4
            nVerbottenBandLimit = 26 # 5 to remove all music, but voice is lost a bit
            
        else:
            nFirstBand = 1
            nNbrBandToCheck = 3
            nLimit =  10
            nAddThresholdLastBand = 0
            
            # reglage sound reco
            nFirstBand = 1
            nNbrBandToCheck = 3
            nLimit =  11
            nAddThresholdLastBand = 0            
            
            nVerbottenBandFirst = 10
            nVerbottenBandNbr = 6
            nVerbottenBandLimit = 300 # 5 to remove all music, but voice is lost a bit
            # TODO: avec ce reglage idem "soundreco", trouver a partir de quelle bande on vire la musique sans perdre sur la voix
            
        for band_results in mfcc_res:
            res = 0
            bPotentialVoice = False
            for nNumBand in range(nFirstBand,nFirstBand+nNbrBandToCheck):
                
                nLimitToTest = nLimit
                if nNumBand+1 == nFirstBand+nNbrBandToCheck:
                    nLimitToTest += nAddThresholdLastBand

                bPotentialVoice = band_results[nNumBand] > nLimitToTest
                if bPotentialVoice: 
                    break
                
            if 1:
                # when some frequence are in, it's not voice!                
                if bPotentialVoice:
                    for nNumBand in range(nVerbottenBandFirst,nVerbottenBandFirst+nVerbottenBandNbr):                    
                        bPotentialVoice = band_results[nNumBand] <= nVerbottenBandLimit
                        if not bPotentialVoice: 
                            #~ print( "forgotten !!!" )
                            break                    
                
            # todo: have a prePotentialVoice tunable with more than just the previous (for hands_noise)            
            if bPotentialVoice and bPrevPotentialVoice:
                res = 1
                nCptEmptySinceDetected = 0
                preDetect = min(len(vad),15)
                vad[-preDetect:] = [1]*preDetect
            else:
                nCptEmptySinceDetected += 1
                if nCptEmptySinceDetected < 40 and 1: # relative to the window size! #16 => 160ms # 30
                    res = 1
            bPrevPotentialVoice = bPotentialVoice                
            vad.append(res)
        return vad

    def debugPlot(self, res, aVadStateChange):
        import matplotlib.pyplot as plt
        for m in range(1):    
            plt.figure(m)
            plt.subplot(3,1,1)
            
            plt.plot(buffer)
            plt.title("sound")
            
            plt.subplot(3,1,2)

            # draw only some band each time
            reslimited = []
            for b in res:
                nNumFirst = 0
                nNbrBand = 8
                reslimited.append(b[nNumFirst:nNumFirst+nNbrBand])
            res = reslimited
                
            plt.plot(res)
            
            plt.title("mfcc")
            plt.legend(range(len(res)))

            plt.subplot(3,1,3)
            plt.plot(aVadStateChange)
            plt.ylim( 0, 2 )
            plt.title("vad")
        
        plt.show()            
        
    def analyseBuffer( self, buffer, sampleRate, bDrawDebug = True ):
        """
        analyse a mono channel pieces of sound
        - buffer: a numpy buffer containing a part of audio
        """
        # mfcc default: samplerate=16000,winlen=0.025,winstep=0.01,numcep=13, nfilt=26,nfft=512,lowfreq=0,highfreq=samplerate/2,preemph=0.97,ceplifter=22

        numcep = 25
        nfilt = 40
        nfft=1024

        res = python_speech_features.base.mfcc( buffer, samplerate=sampleRate,numcep=numcep, nfilt=nfilt, nfft=nfft )
        aVadStateChange = self.vad.computeFromMfcc( res, samplerate=sampleRate )

        if bDrawDebug and 0 and not self.bIsOnRobot:
            self.debugPlot(res,aVadStateChange)
            
        window_step_in_sec = 0.01 # it's not the window size, but the step that is interesting!
        return [aVadStateChange, window_step_in_sec]


    def analyseFile( self, strFilename ):
        """
        analyse a file, return all voice segment
        """
        strFilename = os.path.expanduser( strFilename )
        s = wav.Wav( strFilename )

        if not s.isOpen():
            logging.error("Could not open the wav file " + strFilename)
            raise Exception("Could not open the wav file")

        timeBegin = time.time()
        audiodata = s.data
        if s.nNbrChannel > 1:
            audiodata = audiodata[0::s.nNbrChannel]+audiodata[1::s.nNbrChannel] # why not the four of them ? # todo: have an automatic test, and test it !
        aFlagVAD, window_step_in_sec = self.analyseBuffer( audiodata[:], s.nSamplingRate )

        duration = time.time() - timeBegin
        logging.info("Buf: %5.0fHz, soundlen: %5.2fs, processing: %5.2fs, realtiming: %5.1fx" % (s.nSamplingRate, s.rDuration, duration, s.rDuration/duration) )

        lenSpeech = sum(aFlagVAD)
        ratioSpeech = lenSpeech/float(len(aFlagVAD))
        lenSpeech = lenSpeech*window_step_in_sec
        print("INF: analyseFile/Buf: lenSpeech: %5.2fs, ratio: %3.2f" % (lenSpeech,ratioSpeech) )
        if 1:
            # debug: output just speech to a sound
            compData = self.generateSoundFromFlag( audiodata, s.nSamplingRate, aFlagVAD, window_step_in_sec )
            newWav = sound.Wav()
            newWav.copyHeader( s )
            newWav.nNbrChannel = 1
            newWav.updateHeaderSize( len(compData) )

            file = open( "/tmp/compfile.wav", "wb" )
            newWav.writeHeader( file )
            newWav.writeSpecificData( file, compData )
            file.close()
        if 1:
            self.generateEafFile( "/tmp/t.eaf", aFlagVAD, window_step_in_sec, strFilename )
            
        aTs = self.generateTimeSegmentsFromFlag( aFlagVAD, window_step_in_sec )
        print("INF: analyseFile/Buf: lenSpeech: %5.2fs, ratio: %3.2f, nbrSegment: %d" % (lenSpeech,ratioSpeech,len(aTs)) )
        return aTs

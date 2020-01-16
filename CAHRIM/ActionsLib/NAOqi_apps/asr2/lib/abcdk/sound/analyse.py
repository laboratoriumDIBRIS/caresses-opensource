# -*- coding: utf-8 -*-
###########################################################
# Aldebaran Behavior Complementary Development Kit
# Sound tools
# Aldebaran Robotics (c) 2010 All Rights Reserved - This file is confidential.
###########################################################

import logging
import ctypes
import math

import numpy as np 
import os
import struct
import sys
import time

from wav import Wav

# import naoqitools
# import system
# import test

try:
    import leds
except:
    pass

import math
try:
    import pylab
    from scipy.io import wavfile
except:
    pass


def isAudioOutUsed( mem ):
    # This checks if a text is said
    bText = mem.getData( "ALTextToSpeech/TextStarted" )
    if not bText:
        # Check if a sound is played on the speakers
        # AudioOutputChanged is of this type:
        # [['Name', 'alsa_output.PCH.output-speakers'], ['Index', 0], ['Mode', 'output'], ['HwType', 'Internal'], ['Volume', [49, 49]], ['BaseVolume', 49], ['Mute', False], ['MonitorStream', 0], ['MonitorStreamName', 'alsa_output.PCH.output-speakers.monitor'], ['State', 'suspended'], ['SampleInfo', [['Rate', 48000], ['Channels', 2], ['Positions', ['front-left', 'front-right']]]]] 
        audioOutputState = mem.getData( "AudioOutputChanged" )
        strMode = audioOutputState[2][1]
        strState = audioOutputState[9][1]
        if strMode == "output" and strState == "running":
            return True
    return bText


global_bUsageNoiseExtractorIsNotPresent = False # cpu optim: if no analyseSound present at first call, then disable test
def analyseSound_pause( bWaitForResume ):
    "pause some running sound analyse"
    "bWaitForResume: True => pause until resume call, False => pause a little times (5sec?)"
    global global_bUsageNoiseExtractorIsNotPresent
    if( global_bUsageNoiseExtractorIsNotPresent ):
        return    
    try:
        analyser = naoqitools.myGetProxy( "UsageNoiseExtractor" )
        nTime = 5
        if( bWaitForResume ):
            nTime = -1
        analyser.inhibitSoundAnalyse( nTime )
    except BaseException, err:
        logging.debug( "analyseSound_pause: ERR: " + str( err ) )
        global_bUsageNoiseExtractorIsNotPresent = True
# analyseSound_pause - end

def analyseSound_resume( bWaitForResume ):
    "resume a previously infinite paused sound analyse"
    global global_bUsageNoiseExtractorIsNotPresent
    if( global_bUsageNoiseExtractorIsNotPresent ):
        return
    if( bWaitForResume ):
        try:
            analyser = naoqitools.myGetProxy( "UsageNoiseExtractor" )
            analyser.inhibitSoundAnalyse( 0 )
        except BaseException, err:
            logging.debug( "analyseSound_resume: ERR: " + str( err ) )
            global_bUsageNoiseExtractorIsNotPresent = True
# analyseSound_resume - end

def removeBlankFromFile( strFilename, b16Bits = True, bStereo = False ):
  "remove blank at begin and end of a raw sound file, a blank is a 0 byte."
  "bStereo: if set, it remove only by packet of 4 bytes (usefull for raw in stereo 16 bits recording)"
  try:
    file = open( strFilename, "rb" )
  except BaseException, err:
    print( "WRN: removeBlankFromFile: ??? (err:%s)" % ( str( err ) ) )

    return False
    
  try:
    aBuf = file.read()
  finally:
    file.close()
    
  try:  
    nNumTrimAtBegin = 0
    nNumTrimAtEnd = 0
    nFileSize = len( aBuf )
    for i in range( nFileSize ):
  #    print( "aBuf[%d]: %d" % (i, ord( aBuf[i] )  ) )
      if( ord( aBuf[i] ) != 0 ):
  #      print( "i1:%d" % i )
        if( bStereo and b16Bits ):
          i = (i/4)*4 # don't cut between channels
        elif( bStereo or b16Bits ):
          i = (i/2)*2
        break
    nNumTrimAtBegin = i

    for i in range( nFileSize - 1, 0, -1 ):
  #    print( "aBuf[%d]: %d" % (i, ord( aBuf[i] )  ) )
      if( ord( aBuf[i] ) != 0 ):
  #      print( "i2:%d" % i )
        if( bStereo ):
          i = ((i/4)*4)+4
        elif( bStereo or b16Bits ):
          i = ((i/2)*2)+2
        break
    nNumTrimAtEnd = i

  #  debug( "sound::removeBlankFromFile: nNumTrimAtBegin: %d, nNumTrimAtEnd: %d, nFileSize: %d" % (nNumTrimAtBegin, nNumTrimAtEnd, nFileSize ) )
    if( nNumTrimAtBegin > 0 or nNumTrimAtEnd < nFileSize - 1 ):
        print( "sound::removeBlankFromFile: trim at begin: %d pos trim at end: %d (data trimmed:%d)" % ( nNumTrimAtBegin, nNumTrimAtEnd, nNumTrimAtBegin + ( nFileSize - nNumTrimAtEnd ) ) );
        aBuf = aBuf[nNumTrimAtBegin:nNumTrimAtEnd]
        try:
            file = open( strFilename, "wb" )
        except BaseException, err:
            print( "WRN: sound::removeBlankFromFile: dest file open error (2) (err:%s)" % ( str( err ) ) )
            return False
        try:
            file.write( aBuf )
        finally:            
            file.close()
  except BaseException, err:
    print( "sound::removeBlankFromFile: ERR: something wrong occurs (file not found or ...) err: " + str( err ) )
    return False
  return True
# removeBlankFromFile - end

def loadSound16( strFileIn, nNbrChannel = 1 ):
    "load a sound file and return an array of samples (16 bits) (in mono)"
    "return [] on error"
    aSamplesMono = []    
    try:
        file = open( strFileIn, "rb" )
    except BaseException, err:
        print( "sound::loadSound16: ERR: something wrong occurs: %s" % str( err ) )
        return []
    try:
        aBuf = file.read()  
        file.close()
        nOffset = 0
        lenFile = len( aBuf )
        strHeaderTag = struct.unpack_from( "4s", aBuf, 0 )[0]
        if( strHeaderTag == "RIFF" ):
            print( "sound::loadSound16: skipping wav header found in %s" % strFileIn )
            nOffset += 44 # c'est en fait un wav, on saute l'entete (bourrin)
        
        print( "sound::loadSound16: reading file '%s' of size %d interpreted as %d channel(s)" % ( strFileIn, lenFile, nNbrChannel ) )
        while( nOffset < lenFile ):
            nValSample = struct.unpack_from( "h", aBuf, nOffset )[0]
            aSamplesMono.append( nValSample ) # ici c'est lourd car on alloue un par un (pas de reserve) (des essais en initialisant le tableau  avec des [0]*n, font gagner un petit peu (5.0 sec au lieu de 5.4)
            nOffset += 2
            if( nNbrChannel > 1 ):
                nOffset += 2 # skip right channel
        # while - end
    except BaseException, err:
        print( "sound::loadSound16: ERR: something wrong occurs: %s" % str( err ) )
        pass
        
    print( "=> %d samples" %  len( aSamplesMono ) )    
    return aSamplesMono
# loadSound16 - end

def computePeak16( strFilename ):
    """
    analyse a sound to found the peak of a 16 bits wav (quick and dirty)
    return a max as a float [0..1]
    """
    aMonoSound = loadSound16( strFilename, 1 )
    if( len( aMonoSound ) < 1 ):
        return 0.

    nMax = 0
    nOffset = 0
    nNbrSample = len( aMonoSound )
    print( "computeMax16: analysing %d sample(s)" % nNbrSample )
    while( nOffset < nNbrSample ):
        nVal = aMonoSound[nOffset]
        if( nVal < 0 ):
            nVal =-nVal
        if( nVal > nMax ):
            nMax = nVal
        nOffset += 1
    # while - end
    
    return nMax / float(32767)
# computePeak16 - end

def computeEnergyBest( aSample ):
        "Compute sound energy on a mono channel sample, aSample contents signed int from -32000 to 32000 (in fact any signed value)"

        # Energy(x_centered) = Energy(x) - Nsamples * (Mean(x))^2
        # Energy = Energy(x_centered)/ ( 65535.0f * sqrtf((float)nNbrSamples ) # en fait c'est mieux sans le sqrtf

        nEnergy = 0
#	nMean = 0
        nNumSample = len( aSample )

        for i in xrange( 1, nNumSample ):
#		nMean += aSample[i]
                nDiff = aSample[i] - aSample[i-1]
                nEnergy += nDiff*nDiff

#	rMean = nMean / float( nNumSample )

#	print( "computeEnergyBest: nNumSample: %s, sum: %s, mean: %s, energy: %s" % ( str( nNumSample ),  str( nMean ), str( rMean ), str( nEnergy )) )
#	print( "computeEnergyBest: nNumSample: %d, sum: %d, mean: %f, energy: %d" % ( nNumSample,  nMean, rMean, nEnergy ) )
#	nEnergy -= int( rMean * rMean * nNumSample ) # on n'enleve pas la moyenne: ca n'a aucun interet (vu que c'est deja des diff)
        nEnergyFinal = int( float( nEnergy ) / (nNumSample-1) )
#	nEnergyFinal /= 32768
        nEnergyFinal = int( math.sqrt( nEnergyFinal ) )
#	print( "computeEnergyBest: nEnergy: %f - nEnergyFinal: %s " % ( nEnergy,  str( nEnergyFinal ) ) )
        return nEnergyFinal
# computeEnergyBest - end



def convertEnergyToEyeColor_Intensity( nValue, nMax ):
    "convert energy[0,nMax] in eye color intensity"
    return ( nValue / float( nMax ) ) * 1.0 + 0.00 # add 0.2 pour la possibilité de ne pas etre tout noir
# convertEnergyToEyeColor_Intensity - end

def analyseSpeakSound( strRawFile, nSampleLenMs = 50, bStereo = False ):
    "Analyse a raw stereo or mono sound file, and found the light curve relative to sound (for further speaking)"
    print( "analyseSpeakSound: analysing '%s' (time:%d)" % ( strRawFile, int( time.time() ) ) )
    nNbrChannel = 1
    if( bStereo ):
        nNbrChannel = 2
    aMonoSound = loadSound16( strRawFile, nNbrChannel )
    if( len( aMonoSound ) < 1 ):
        return []

    #analyse every 50ms sound portion (because 50ms is the average latency of leds)
    anLedsColorSequency = [] # for every time step, an int corresponding to the RGB colors
    nSizeAnalyse = int( (22050*nSampleLenMs)/1000 ) # *50 => un sample chaque 50ms
    nMax = 0
    nOffset = 0
    nNbrSample = len( aMonoSound )
    print( "analyseSpeakSound: analysing %d sample(s)" % nNbrSample )
    while( nOffset < nNbrSample ):
        anBuf = aMonoSound[nOffset:nOffset+nSizeAnalyse]
        nOffset += nSizeAnalyse
        nValue = computeEnergyBest( anBuf )
        if( nValue > nMax ):
            nMax = nValue
        # storenValue to nColor
        anLedsColorSequency.append( nValue )
    # while - end

    # convert nValue to nColor (using max energy)
    nOffset = 0
    nNbrComputed = len( anLedsColorSequency )
    print( "analyseSpeakSound: converting %d energy to leds light (max=%d)" % ( nNbrComputed, nMax) )
    while( nOffset < nNbrComputed ):
        anLedsColorSequency[nOffset] = convertEnergyToEyeColor_Intensity( anLedsColorSequency[nOffset], nMax )
        nOffset += 1
    # while - end

    print( "analyseSpeakSound: analysing '%s' (time:%d) - end" % ( strRawFile, int( time.time() ) ) )
    return anLedsColorSequency
# analyseSpeakSound - end


def convertRaw2432ToWav( strRawFileName, strDstFileName = None, nDstDepth = 16, nUseSampleRate = 16000 ):
    """
    an application (a dsp devboard has dumped a wav file, it was 32 bits int from some 24bits sample), let's create a 16bits wav from that.
    """
    if( strDstFileName == None ):
        strDstFileName = strRawFileName.replace( ".raw", ".wav" )
        
    data = np.fromfile( strRawFileName, dtype=np.int32 )
    for i in range(4):
        print( "data[%d]: %s (0x%x)" % (i, data[i], data[i]) )
        
    wav = Wav()
    wav.new( nSamplingRate = nUseSampleRate, nNbrChannel = 1, nNbrBitsPerSample = nDstDepth )
    nMax = wav.getSampleMaxValue()
    for i in range( len(data) ):
        nVal = data[i]
        if( nVal > nMax ):
            nVal = nMax
        if( nVal < -nMax ):
            nVal = -nMax        
        wav.data.append( nVal )

    for i in range(4):
        print( "wav.data[%d]: %s (0x%x)" % (i, wav.data[i], wav.data[i]) )

    wav.updateHeaderSizeFromDataLength()
    wav.write( strDstFileName )
    
    print( "INF: convertRaw2432ToWav: '%s' => '%s' (sample nbr:%d)" % (strRawFileName, strDstFileName, len(wav.data)) )
# convertRaw2432ToWav - end

def convertRaw2432InterlacedToWav( strRawFileName, nNbrChannel = 16, strDstFileName = None, nDstDepth = 16, nUseSampleRate = 16000 ):
    """
    an application (a dsp devboard has dumped a wav file, it was 32 bits int from some 24bits sample), let's create a 16bits wav from that.
    """
    if( strDstFileName == None ):
        strDstFileName = strRawFileName.replace( ".raw", "_%02d.wav" )
        
    data = np.fromfile( strRawFileName, dtype=np.int32 )
    for i in range(4):
        print( "data[%d]: %s (0x%x)" % (i, data[i], data[i]) )
        
    nNbrSamplePerChannel = len(data)/nNbrChannel
    for nNumChannel in range( nNbrChannel ):
        wav = Wav()
        wav.new( nSamplingRate = nUseSampleRate, nNbrChannel = 1, nNbrBitsPerSample = nDstDepth )
        nMax = wav.getSampleMaxValue()
        for i in range( nNbrSamplePerChannel ):
            #nVal = data[i*nNbrChannel+nNumChannel]
            nVal = data[nNumChannel*nNbrSamplePerChannel+i]
            if( nVal > nMax ):
                nVal = nMax
            if( nVal < -nMax ):
                nVal = -nMax        
            wav.data.append( nVal )

        for i in range(4):
            print( "wav.data[%d]: %s (0x%x)" % (i, wav.data[i], wav.data[i]) )

        wav.updateHeaderSizeFromDataLength()
        wav.write( strDstFileName % nNumChannel )
        
        print( "INF: convertRaw2432ToWav: '%s' => '%s' (sample nbr:%d)" % (strRawFileName, strDstFileName, len(wav.data)) )
    # for - end
# convertRaw2432InterlacedToWav - end

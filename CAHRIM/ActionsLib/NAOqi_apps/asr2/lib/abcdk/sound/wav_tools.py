
def isEqual( strFilename1, strFilename2 ):
    wav1 = Wav()
    if( not wav1.load( strFilename1 ) ):
        return False
    wav2 = Wav()
    if( not wav2.load( strFilename2 ) ):
        return False
    return wav1.isEqual( wav2 )    
# isEqual - end    

def getInfoFromWav( strFilename, bReadData = False ):
    """
    Return a string describing wav info
    """
    wav = Wav()
    wav.load( strFilename, bLoadData = bReadData, bUnpackData = False )
    return str( wav )
# getInfoFromWav - end

def substract( strFilename1, strFilename2, strFilenameOut ):
    """
    substract 2 from 1
    """
    
    wav1 = Wav()
    wav1.load( strFilename1, bLoadData = True, bUnpackData = False )
    wav2 = Wav()
    wav2.load( strFilename2, bLoadData = True, bUnpackData = True )
    
    if( wav1.nNbrChannel != wav2.nNbrChannel ):
        print( "ERR: sound.Wav.substract: the two sources must have same channel numbers" )
        return False    
    if( wav1.nSamplingRate != wav2.nSamplingRate ):
        print( "ERR: sound.Wav.substract: the two sources must have same sampling rate" )
        return False
    if( wav1.nNbrBitsPerSample != wav2.nNbrBitsPerSample ):
        print( "ERR: sound.Wav.substract: the two sources must have same bits per sample" )
        return False                
    wav1.replaceData( 0, wav2.data, -1 )    
    return wav1.write( strFilenameOut )
# substract - end    
        
def cleanAllWavInOneDirectory( strPath, nCleanMode = 1, bOverwriteSourceFile = False ):
    """
    - nCleanMode:
      1: for speech
      2: for sample (tracker)
    """
    if( False ):
        w = Wav( "c:\\temp\\01_Patients_annonce.wav" )
        #~ w = Wav( "c:\\temp\\08_Patients_ma_chambre.wav" )
        timeBegin = time.time()
        w.removeGlitch()
        #~ w.ensureSilence( rTimeAtBegin = 0.2, rTimeAtEnd = 2., bRemoveIfTooMuch=True, rSilenceTresholdPercent=0.8 )
        #~ w.normalise()
        #~ w.normalise()
        print( "time taken: %5.3fs" % (time.time() - timeBegin ) )
        #w.data=w.data[::-1]
        w.write( "c:\\temp\\output.wav" )
        substract( "c:\\temp\\01_Patients_annonce.wav", "c:\\temp\\output.wav", "c:\\temp\\output2.wav" )
        
    for strFilename in sorted( os.listdir( strPath ) ):
        if( not ".wav" in strFilename ):
            continue
        if( "_clean.wav" in strFilename ):
            continue            
        w = Wav( strPath + strFilename )
        timeBegin = time.time()
        if( nCleanMode == 1 ):
            w.removeGlitch()
            w.ensureSilence( rTimeAtBegin = 0.2, rTimeAtEnd = 2., bRemoveIfTooMuch=True, rSilenceTresholdPercent=0.8 )
            w.normalise()
        if( nCleanMode == 2 ):
            w.normalise()            
            # we normalise before so the threshold is higher !
            w.ensureSilence( rTimeAtBegin = 0.0, rTimeAtEnd = 0., bRemoveIfTooMuch=True, rSilenceTresholdPercent=1.7 ) 
        
        print( "time taken: %5.3fs" % (time.time() - timeBegin ) )
        if( bOverwriteSourceFile ):
            strFilenameOut = strFilename
        else:
            strFilenameOut = strFilename.replace( ".wav", "_clean.wav" )
        w.write( strPath + strFilenameOut )
# cleanAllWavInOneDirectory - end

#cleanAllWavInOneDirectory( "C:\\perso\\sound\\new\\" )
#~ for strType in ["laaa", "naaa", "mmm", "ouu", "piano", "laaa_pitched"]:
    #~ cleanAllWavInOneDirectory( "C:\\work\\Dev\\git\\appu_shared\\sdk\\abcdk\\data\\wav\\tracker\\%s\\" % strType, nCleanMode = 2, bOverwriteSourceFile = True )
#~ exit()


def convertWavFile( strSrc, strDst, nNewSamplingFrequency = -1, nNewNbrChannel = -1, bAsRawFile = False ):
    """
    convert a file to another sampling/channel or to raw
    - nNewSamplingFrequency: new frequency, -1 if same
    - nNewNbrChannel: new channel number, -1 if same    
    - bAsRawFile: if True: save it as a raw file, (else it's a standard raw)
    return True if ok
    """
    timeBegin = time.time()
    wavSrc = Wav()
    bRet = wavSrc.load( strSrc, bUnpackData = True )
    #~ print( "DBG: abcdk.sound.convertWavFile: src:" + str(wavSrc) )
    if( not bRet ):
        print( "ERR: abcdk.sound.convertWavFile: source file '%s' not found" % ( strSrc ) )
        return False
    if( nNewSamplingFrequency == -1 ):
        nNewSamplingFrequency = wavSrc.nSamplingRate
    if( nNewNbrChannel == -1 ):
        nNewNbrChannel = wavSrc.nNbrChannel
    nNewBitPerSample = wavSrc.nNbrBitsPerSample
    print( "INF: abcdk.sound.convertWavFile: '%s' [%dHz, %d channel(s), %d bits] => '%s' [%dHz, %d channel(s), %d bits]" % (strSrc, wavSrc.nSamplingRate, wavSrc.nNbrChannel, wavSrc.nNbrBitsPerSample, strDst, nNewSamplingFrequency, nNewNbrChannel, nNewBitPerSample) )
    wavDst = Wav()
    wavDst.new( nSamplingRate = nNewSamplingFrequency, nNbrChannel = nNewNbrChannel, nNbrBitsPerSample =  nNewBitPerSample )
    nNumSample = 0
    rNumSamplePrecise = 0 # point the real avancing for inflating
    nNumPrevSample = 0
    
    dataBuf = [] # np.zeros( 0, dtype = wavSrc.dataType ); TODO: initiate an np array with a good final size !
    while( nNumSample < wavSrc.nNbrSample ):
        #~ if( nNumSample < 1000 ):
            #~ print( "nNumSample: %s" % nNumSample )
        aSample = wavSrc.data[nNumSample*wavSrc.nNbrChannel:(nNumSample+1)*wavSrc.nNbrChannel].tolist()
        # resampling
        if( nNewSamplingFrequency == wavSrc.nSamplingRate ):
            nNumSample += 1
        else:
            if( nNewSamplingFrequency < wavSrc.nSamplingRate ):
                if( nNumSample - nNumPrevSample > 1 ):
                    # antialiasing:
                    # add a part of the previous missed sample values, to this one
                    for n in range( nNumPrevSample, nNumSample ):
                        for i in range( wavSrc.nNbrChannel ):
                            aSample[i] += wavSrc.data[n*wavSrc.nNbrChannel+i]
                    for i in range( wavSrc.nNbrChannel ):
                        aSample[i] /= (nNumSample - nNumPrevSample)+1
                # prepare next sample
                nNumPrevSample = nNumSample
                #~ nNumSample += int(round(wavSrc.nSamplingRate/float(nNewSamplingFrequency))) # this works only when division is integer (22050=>11025...)
                rNumSamplePrecise += wavSrc.nSamplingRate/float(nNewSamplingFrequency) # for non integer div: (22050=>14000...) in that case we should interpolate
                nNumSample = int( rNumSamplePrecise ) # don't round it ! (or?)
            else:
                # inflate
                # here we should interpolate value between original sample (currently the same value is pasted a number of time)
                if( nNumSample+1 < wavSrc.nNbrSample ):
                    aNextSample = wavSrc.data[(nNumSample+1)*wavSrc.nNbrChannel:(nNumSample+2)*wavSrc.nNbrChannel]
                    temp = [0]*wavSrc.nNbrChannel
                    rRatioNextData = rNumSamplePrecise - nNumSample
                    for i in range( wavSrc.nNbrChannel ):
                        temp[i] = aSample[i] * (1.-rRatioNextData) + aNextSample[i] *rRatioNextData
                    aSample = temp
                nNumPrevSample = nNumSample
                rNumSamplePrecise += wavSrc.nSamplingRate/float(nNewSamplingFrequency)
                nNumSample = int( rNumSamplePrecise ) # don't round it !
                
                
        # convert channels
        if( nNewNbrChannel != wavSrc.nNbrChannel ):
            if( nNewNbrChannel > wavSrc.nNbrChannel ):
                # expand
                for i in range( wavSrc.nNbrChannel, nNewNbrChannel ):
                    aSample.append( aSample[i%wavSrc.nNbrChannel] ) # L,R => L,R,L,R
            else:
                # reduce: 
                if( nNewNbrChannel == 1 ):
                    # L, R => S: (L+R)/2
                    # 2,3,4 channels  => S: 1 avg (channel)                           
                    aSample = [sum( aSample ) / len( aSample )]
                elif( nNewNbrChannel == 2 ):
                    # C1, C2, C3 => L:(C1+C3)/2, R:(C2+C3)/2
                    # C1,C2,C3,C4 => L:(C1+C3)/2, R:(C2+C4)/2                                    
                    temp = [0]*nNewNbrChannel
                    temp[0]  = ( aSample[0]+aSample[2] ) / 2
                    temp[1]  = ( aSample[2]+aSample[-1] ) / 2 # [-1] => C3 or C4 depending on the channel number
                    aSample = temp
                else:
                    print( "ERR: abcdk.sound.convertWavFile: while converting file '%s': unhandled channel conversion (%d=>%d)" % ( strSrc,  nNewNbrChannel, nNewNbrChannel) )
                    return False
                    
        #~ wavDst.addData( aSample ) # not optimal: a lot of jumps to addData there... # for a 19sec long sound, gain was from 10s to 2.8s by removing this call !
        for val in aSample:
            dataBuf.append( val )
    # while - end
    #print( "len( dataBuf ): %d" % len( dataBuf ) )
    wavDst.data = np.array( dataBuf, dtype = wavDst.dataType )
    #print( "len( wavDst.data ): %d" % len( wavDst.data ) )
    wavDst.updateHeaderSizeFromDataLength()
    
    wavDst.write( strDst, bAsRawFile = bAsRawFile )
    #~ print( "DBG: abcdk.sound.convertWavFile: dst:" + str(wavDst) )
    print( "INF: abcdk.sound.convertWavFile: done in %.2fs" % ( time.time() - timeBegin ) )
    return True
# convertWavFile - end

def correctHeader( strWavFile ):
    """
    Open a wav, and write it with a corrected header (if header was bad)
    """
    timeBegin = time.time()
    wav = Wav()
    bRet = wav.load( strWavFile, bUnpackData = True )
    #~ print( "DBG: abcdk.sound.convertWavFile: src:" + str(wavSrc) )
    if( not bRet ):
        print( "ERR: abcdk.sound.correctHeader: source file '%s' not found" % ( strWavFile ) )
        return False
    wav.write(strWavFile)
    rDuration = time.time() - timeBegin
    print( "INF: correctHeader: rewriting wav '%s' (in %5.2fs) [OK]" % (strWavFile, rDuration) )
# correctHeader - end

def correctHeaderInFolder( strPath ):
    """
    Open all wav in a folder, and write them with a corrected header (if header was bad)
    """
    for strFilename in sorted( os.listdir( strPath ) ):
        if( not ".wav" in strFilename ): # don't analyse this one!
            continue
        correctHeader( strPath + os.sep + strFilename )    
# correctHeaderInFolder - end

def setUsingAudioOut(qiapp, bUsingIt = True ):
    """
    Inform the system that sounds are outputted from the audio speakers
    (so that you could stop analysing sound, speech, ...
    """
    global_nAudioOutUser = 0
    if( bUsingIt ):
        global_nAudioOutUser += 1
    else:
        global_nAudioOutUser -= 1
    if( global_nAudioOutUser <= 0 or global_nAudioOutUser == 1 ):
        mem = qiapp.session.service( "ALMemory" )
        mem.raiseMicroEvent( "AudioOutUsed", global_nAudioOutUser >= 1 )
# setUsingAudio - end

def getLength( strFilename ):
    "return the length in sec"
    wav = Wav()
    if( not wav.load( strFilename, bUnpackData = False ) ):
        print( "ERR: sound.getLength: can't load wav '%s'" % strFilename )
        return 0
    print( "INF: sound.getLength: wav loaded: %s" % str( wav ) )
    return wav.rDuration
# getLength - end

def repair( wavFile, bQuiet = False ):
    """
    Correct sound found incorrect (bad header or ...)
    Return True when corrected
    """
    wav = Wav( wavFile, bQuiet  = bQuiet )
    if( not wav.bHeaderCorrected ):
        return False
    print( "INF: rewriting '%s' with correct header" % wavFile )
    wav.write( wavFile )
    return True
# repair - end

def normaliseFile( strFileToModify ):
    """
    Normalise a file.
    Return 1 if normalied or 0 if already full power
    """
    wav = Wav()
    wav.load( strFileToModify )
    if not wav.normalise():
        return 0
    wav.write( strFileToModify )
    return 1
# normaliseFile - end


def ensureSampleRate( strFilename, nNewSampleRate ):
    """
    resample a file if needed
    """
    wav = Wav()
    wav.load( strFilename, bLoadData = False )
    if( wav.nSamplingRate ==  nNewSampleRate ):
        return 0
    wav.load( strFilename ) # reload data
    
    wavNew = Wav()
    wavNew.new( nSamplingRate = nNewSampleRate, nNbrChannel = wav.nNbrChannel, nNbrBitsPerSample = wav.nNbrBitsPerSample )
    
    #currently handle only multiple or division
    if( nNewSampleRate > wav.nSamplingRate ):
        rMultiple = float(nNewSampleRate) / wav.nSamplingRate
        if( rMultiple != int(rMultiple) ):
            print( "ERR: ensureSampleRate: can't change sample rate if not multiple or plain divisor file: '%s' (%s !=> %s)" % (strFilename, wav.nSamplingRate, nNewSampleRate) )
            return -1
        nMultiple = int(rMultiple)
        wavNew.data = wav.data.repeat( nMultiple)
        
    else:
        assert(0)  # TODO

    wav.updateHeaderSizeFromDataLength()
    wavNew.write( strFilename )
# ensureSampleRate - end
#~ ensureSampleRate( "/tmp2/nimoy_spock_test2.wav", 48000 )
#~ exit(0)

def convertToOneChannel( strFileIn, strFileOut, nIdxChannelToTake = 0 ):
    """
    convert a multichannel file to a mono file one
    """
    wav = Wav()
    if not wav.load( strFileIn ):
        print( "ERR: can't open '%s'" % strFileIn )
        return -1
    if not wav.extractOneChannelAndSaveToFile( strFileOut, nNumChannel = nIdxChannelToTake ):
        print( "ERR: can't write to '%s'" % strFileOut )
        return -2
    return 1
# convertToOneChannel - end

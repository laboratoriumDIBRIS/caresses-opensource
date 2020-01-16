
def playSound( strFilename, bWait = True, bDirectPlay = False, nSoundVolume = 100 , bUseLedEars=True):
    "Play a sound, return True if ok"
    "bDirectPlay: play it Now! (could fragilise system and video drivers"
    "nSoundVolume: [0..100] will play the sound with a specific volume (ndev on some version, and if using bDirectPlay )"
    "bUseLedEars: do a a circleLedEars"
    
    print( "playSound( '%s', bWait = %s, bDirectPlay = %s, nSoundVolume = %d )" % ( strFilename, str( bWait ), str( bDirectPlay ), nSoundVolume ) )
    
    if( config.bRemoveDirectPlay ):
        print( "WRN: DISABLING_DIRECTPLAY SETTINGS for testing/temporary purpose" )
        bDirectPlay = False
    
    try:
        if bUseLedEars:
            if( system.isOnRomeo() ):
                #leds.dcmMethod.setEyesColor()
                leds.setBrainLedsIntensity( 1., 100, bDontWait = True )
            else:
                leds.setEarsLedsIntensity( 1., 100, bDontWait = True )
        # If strFilename has an absolute path, go ahead with this path !
        if strFilename.startswith( pathtools.getDirectorySeparator() ):
            strSoundFile = strFilename
        else:
            strSoundFile = pathtools.getApplicationSharedPath() + "wav/0_work_free/" + strFilename
            if( not filetools.isFileExists( strSoundFile ) ):
                # then try another path
                strSoundFile = pathtools.getApplicationSharedPath() + "wav/1_validated/" + strFilename
            if( not filetools.isFileExists( strSoundFile ) ):
                # and another path
                strSoundFile = pathtools.getApplicationSharedPath() + "wav/0_work_copyright/" + strFilename
            if( not filetools.isFileExists( strSoundFile ) ):
                # and another path
                strSoundFile = pathtools.getApplicationSharedPath() + "wav/" + strFilename
            if( not filetools.isFileExists( strSoundFile ) ):
                # and another path
                strSoundFile = pathtools.getNaoqiPath() + "/share/naoqi/wav/" + strFilename
            if( not filetools.isFileExists( strSoundFile ) ):
                # and another path
                strSoundFile = pathtools.getABCDK_Path() + "data/wav/" + strFilename
            if( not filetools.isFileExists( strSoundFile ) ):
                print( "ERR: appu.playSound: can't find file '%s'" % strFilename )
                return False

        setUsingAudioOut( True )
        analyseSound_pause( bWait )
        if( bDirectPlay ):
            system.mySystemCall( "aplay -q " + strSoundFile, bWait )
        else:
            global_proxyAudioPlayer = naoqitools.myGetProxy( "ALAudioPlayer" )            
            if( global_proxyAudioPlayer == None ):
                print( "ERR: sound.playSound: can't find module 'ALAudioPlayer'" )
            else:
                try:
                    # try with specific volume
                    if( bWait ):
                        global_proxyAudioPlayer.playFile( strSoundFile, nSoundVolume / 100., 0. )
                    else:
                        global_proxyAudioPlayer.post.playFile( strSoundFile, nSoundVolume / 100., 0. )
                except BaseException, err:
                    print( "DBG: sound.playSound: this version can't handle volume? (err:%s)" % str(err) )    
                    if( bWait ):
                        global_proxyAudioPlayer.playFile( strSoundFile )
                    else:
                        global_proxyAudioPlayer.post.playFile( strSoundFile )
                    
        analyseSound_resume( bWait )
        setUsingAudioOut( False )
    except BaseException, err:
        debug.debug( "playSound: ERR: " + str( err ) )
        print( "errr: " + str( err ) )
        
    if bUseLedEars:
        if( system.isOnRomeo() ):
            #~ leds.dcmMethod.setEyesColor( nColor = 0 )
            leds.setBrainLedsIntensity( 0., 100, bDontWait = True )
        else:
            leds.setEarsLedsIntensity( 0., 100, bDontWait = True )
        
    return True
# playSound - end

def stopSound( strFilename = None, bDirectPlay = False ):
    """
    Stop a sound or every sound !
    strFilename: when at None: stop all playing sound
    """
    if( not bDirectPlay ):
        ap = naoqitools.myGetProxy( "ALAudioPlayer" )
        if( ap != None ):
            ap.stopAll() # TODO: kill the right sound !
            analyseSound_resume( True )
            return
    os.system( "killall aplay" )
    analyseSound_resume( True ) # TODO: kill the right sound !
# stopSound - end

def playMusic( strFilename, bWait ):
  print( "appuPlaySound: avant cnx sur audioplayer (ca lagge?)" )
  #myAP = naoqitools.myGetProxy( "ALAudioPlayer" )
  print( "appuPlaySound: apres cnx sur audioplayer (ca lagge?)" )
  ap = naoqitools.myGetProxy( "ALAudioPlayer" )
  if( bWait ):
    ap.playFile( getApplicationSharedPath() + "/mp3/" + strFilename )
  else:
    ap.post.playFile( getApplicationSharedPath() + "/mp3/" + strFilename )

  #if( not bNaoqiSound ):
  #  strSoundFile = getApplicationSharedPath() + "/mp3/" + strFilename
  #else:
  #  strSoundFile = getNaoqiPath() + "/data/mp3/" + strFilename
  #system.mySystemCall( getSystemMusicPlayerName() + " " +  strSoundFile, bWait )

# playMusic - end

def playSoundHearing():
  "play the standard appu sound before earing user command"
#  time.sleep( 0.4 ) # time to empty all sound buffers
  playSound( "jingle_earing.wav", bDirectPlay = True )
  time.sleep( 0.05 ) # time to empty all sound buffers ?
# playSoundHearing - end

def playSoundSpeaking():
  "play the standard appu sound before speaking to user"
  playSound( "jingle_speaking.wav", bDirectPlay = True )
# playSoundSpeaking - end

def playSoundUnderstanding():
  "play the standard appu sound to show a command is understood"
  playSound( "jingle_understanded.wav", bDirectPlay = True )
# playSoundUnderstanding - end

# sound volume (premisse of the robot's class)

def getCurrentMasterVolume():
    "get nao master sound system volume (in %)"
    "return 0 on error or problem (not on nao or ...)"
    "deprecated: you should use getMasterVolume()"
    return getMasterVolume()
# getCurrentMasterVolume - end

def volumeFadeOut( rApproxTime = 1. ):
    "Fade out master sound system"
    nVol = getCurrentMasterVolume()
    print( "volumeFadeOut: %d -----> 0" % nVol )
    nCpt = 0
    nApproximateCall = 20
    while( nVol > 0 and nCpt < 30 ): # when concurrent calls are made with other fade type, it could go to a dead lock. because getCurrentMasterVolume take some time, we prefere to add some counter
        ++nCpt
        # ramping
        if( nVol > 55 ):
            nVol -= 3
        else:
            nVol -= 9
        (nVol)
#        print( "volout: %d" % nVol )
        setMasterVolume(nVol)
        time.sleep( float( rApproxTime ) / nApproximateCall ) # approximation of the time to make it

def volumeFadeIn( nFinalVolume, rApproxTime = 1. ):
    "Fade in master sound system"
    nVol = getCurrentMasterVolume()
    print( "volumeFadeIn: %d -----> %d" % ( nVol, nFinalVolume ) )
    nCpt = 0
    nApproximateCall = 20
    while( nVol < nFinalVolume and nCpt < 30 ): # when concurrent calls are made with other fade type, it could go to a dead lock. because getCurrentMasterVolume take some time, we prefere to add some counter
        ++nCpt
        if( nVol > 55 ):
            nVol += 3
        else:
            nVol += 9
#        print( "volin: %d" % nVol )
        setMasterVolume(nVol)
        time.sleep( float( rApproxTime ) / nApproximateCall ) # approximation of the time to make it

def setMasterMute( bMute ):
  "mute nao sound volume"
  if( bMute ):
    strVal = "off"
  else:
    strVal = "on"
  debug.debug( "setMasterMute: %s" % strVal )
  system.mySystemCall( "amixer -q sset Master " + strVal )
  if( not bMute ):
    system.mySystemCall( "amixer -q sset PCM " + strVal )  # to be sure   
# setMasterMute - end

def isMasterMute():
  "is nao sound volume muted?"
  strOutput = system.executeAndGrabOutput( "amixer sget Master | grep 'Front Right: Playback' | cut -d[ -f4 | cut -d] -f1", True )
  strOutput = strOutput.strip()
  bMute = ( strOutput == "off" )
  debug.debug( "isMasterMute: %d (strOutput='%s')" % ( bMute, strOutput ) )
  return bMute
# isMasterMute - end

def setMasterPanning( nPanning = 0 ):
    "change the sound master panning: 0: center -100: left +100: right"
    "current bug: currently volume is louder when at border, than at center, sorry"
    try:
        debug.debug( "setMasterPanning to %d" % nPanning )
        nVol = getCurrentMasterVolume()
        nCoefR = nVol + nVol*nPanning/100
        nCoefL = nVol - nVol*nPanning/100
        nCoefR = nCoefR * 32 / 100
        nCoefL = nCoefL * 32 / 100
        system.mySystemCall( "amixer -q sset Master %d,%d" % ( nCoefL, nCoefR ) )
        system.mySystemCall( "amixer -q sset PCM 25" )
        system.mySystemCall( "amixer -q sset \"Master Mono\" 32" )
    except BaseException, err:
        print( "setMasterPanning: error '%s'" % str( err ) )
# setMasterPanning - end

 # pause music
def pauseMusic():
  "pause the music player"
  debug.debug( "pauseMusic" )
  system.mySystemCall( "killall -STOP mpg321b" )

# restart music
def unPauseMusic():
  debug.debug( "unPauseMusic" )
  system.mySystemCall( "killall -CONT mpg321b" )

def ensureVolumeRange( nMinValue = 58, nMaxValue = 84 ):
    "analyse current volume settings, and change it to be in a specific range"
    "default range is the 'confort' range"
    nCurrentVolume = getCurrentMasterVolume()
    if( nCurrentVolume >= nMinValue and nCurrentVolume <= nMaxValue ):
        return
    # set the volume sound nearest the min or max range
    nNewVolume = 0
    if( nCurrentVolume < nMinValue ):
        nNewVolume = nMinValue
    else:
        nNewVolume = nMaxValue
    setMasterVolume( nNewVolume )
# ensureVolumeAbove - end


def getMasterVolume( bForceSystemCall = False ):
    "get nao master sound system volume (in %)"
    "bForceSystemCall: set to true to use system call instead of ALAudioDevice (some version are buggy and set the PCM to only 65%)"
    
    if( not bForceSystemCall ):
        try:
            ad = naoqitools.myGetProxy( 'ALAudioDevice' )
            nVal = ad.getOutputVolume()
            debug.debug( "getMasterVolume: %d%%" % ( nVal ) )
            return nVal
        except BaseException, err:
            print( "getMasterVolume: error '%s'" % str( err ) )
        
    print( "WRN: => using old one using fork and shell!" )
  
    strOutput = system.executeAndGrabOutput( "amixer sget Master | grep 'Front Right: Playback' | cut -d[ -f2 | cut -d% -f1", True )
    nValR = int( strOutput )
    strOutput = system.executeAndGrabOutput( "amixer sget Master | grep 'Front Left: Playback' | cut -d[ -f2 | cut -d% -f1", True )
    nValL = int( strOutput )
    nVal = ( nValR + nValL ) / 2
    debug.debug( "getMasterVolume: %d%% (%d,%d)" % ( nVal, nValL, nValR ) )
    return nVal
# getMasterVolume - end

def setMasterVolume( nVolPercent, bForceSystemCall = False ):
    "change the master volume (in %)"
    "bForceSystemCall: set to true to use system call instead of ALAudioDevice (some version are buggy and set the PCM to only 65%)"
    " => in fact it's my v3.2 configurated as a v3.3, see  /media/internal/DeviceHeadInternalGeode.xml"
    
    if( nVolPercent < 0 ):
        nVolPercent = 0
    if( nVolPercent > 100 ):
        nVolPercent = 100
    debug.debug( "setMasterVolume to %d%%" % nVolPercent )

    if( not bForceSystemCall ):
        try:
            ad = naoqitools.myGetProxy( 'ALAudioDevice' )
            ad.setOutputVolume( nVolPercent )
            return
        except BaseException, err:
            print( "getCurrentMasterVolume: error '%s'" % str( err ) )
        
    print( "WRN: => using old one using fork and shell!" )
        
    strCommand = "amixer -q sset Master " + str( nVolPercent * 32 / 100 )
    strCommand += " amixer  -q sset \"Master Mono\" 32";
    strCommand += " amixer  -q sset PCM 25";    
    system.mySystemCall( strCommand )
# setMasterVolume - end



def changeMasterVolume( nRelativeChange ):
    "change current volume, by adding a value (-100,+100)"
    nLimit = 3
    if( nRelativeChange < 0 and nRelativeChange > -nLimit ):
        nRelativeChange = -nLimit
    if( nRelativeChange > 0 and nRelativeChange < nLimit ):
        nRelativeChange = +nLimit
    setMasterVolume( getMasterVolume() + nRelativeChange )
# changeMasterVolume - end

def getInputVolume():
    "get the input volume (in %)(0..100)"
    strOutput = system.executeAndGrabOutput( "amixer sget Capture | grep 'Front Left: Capture' | cut -d[ -f2 | cut -d% -f1", True )
    nValR = int( strOutput )
    strOutput = system.executeAndGrabOutput( "amixer sget Capture | grep 'Front Right: Capture' | cut -d[ -f2 | cut -d% -f1", True )
    nValL = int( strOutput )
    nVal = ( nValR + nValL ) / 2
    debug.debug( "getInputVolume: %d%% (%d,%d)" % ( nVal, nValL, nValR ) )
    return nVal
# getInputVolume - end

def setInputVolume( nVolPercent ):
    "set the input volume (in %)(0..100)"
    if( nVolPercent < 0 ):
        nVolPercent = 0
    if( nVolPercent > 100 ):
        nVolPercent = 100
    debug.debug( "setInputVolume to %d%%" % nVolPercent )    
    strCommand = "amixer -q sset Capture " + str( nVolPercent ) + "%" # seems like it's by 1/15 value (so sending less than 7% could remain to nothing
    system.mySystemCall( strCommand )# getInputVolume - end
    # change ear led color
    leds = naoqitools.myGetProxy( "ALLeds" )
    leds.setIntensity( "EarLeds", nVolPercent / 100. )
# setInputVolume - end

def changeInputVolume( nRelativeChange ):
    "change current inmput, by adding a value (-100..-7 and 7..+100)"
    nLimit = 7
    if( nRelativeChange < 0 and nRelativeChange > -nLimit ):
        nRelativeChange = -nLimit
    if( nRelativeChange > 0 and nRelativeChange < nLimit ):
        nRelativeChange = +nLimit    
    setInputVolume( getInputVolume() + nRelativeChange )
# changeMasterVolume - end

# -*- coding: utf-8 -*-

###########################################################
# Aldebaran Behavior Complementary Development Kit
# Leds tools
# Aldebaran Robotics (c) 2010 All Rights Reserved - This file is confidential.
###########################################################

import math
import random
import sys
import time

class LedsDcm:
    "This class is intended to put (and get) color to eyes leds, with the less cpu and thread (ab)uses"
    def __init__( self, session):
        self.session = session
        self.bIsOnRomeo = False
            

    def getDCMProxy(self):
        """
        Get a proxy on DCM, to use to send leds.
        (so if you've got a multi dcm robot, it will be the one managing leds)
        """
        if self.bIsOnRomeo:
            strLedName = "DCM_video";
        else:
            strLedName = "DCM";
        try:
            dcm = self.session.service( strLedName );
        except Exception, err:
            print( "ERR: getDCM_ProxyForLeds: can't connect to '%s'" % strLedName );
            dcm = None;
        return dcm;
    # getDCM_ProxyForLeds - end    
        
    def createProxy(self):
        self.dcm = self.getDCMProxy();
        self.dcmDefault = self.session.service( "DCM" );
        self.mem = self.session.service( "ALMemory" );
        if( self.mem == None ):
            print( "WRN: leds.DcmMethod: ALMemory/Naoqi not found" );
            return False;
        if( self.dcm == None ):
            print( "WRN: leds.DcmMethod: DCM proxy/Naoqi not found" );
            return False;            
        return True;
            
    def reset(self):
        if( self.dcm == None ):
            if( not self.createProxy() ):
                return;
        self.createAliases();
        # some memory for EyeCircle: 
        self.nEyeCircle_NextLedPosition = 0; # position of next led to lighten
        self.tEyeCircle_timeNextSent = -sys.maxint; # time at when lighten this led (in dcm time)
        self.EarsLoading_bLastLit = False; # a flip flop to make the blinking
        self.EarsLoading_nLastNbrEarToLit=-1; # last number to prevent erasing too much
        self.EarsLoading_timeLastCall = time.time()-1000;
        
        self.tBrainCircle_timeNextSent = time.time()-100; # time at when lighten this led (in python time)
        
        self.nNbrBrainSegment = 12;        
        
    def createAliases( self ):
        # create alias for easy access: all eyes, and one leds by one for each side or both
        
        bVerbose = False;
        
        strEyeTemplate = "Device/SubDeviceList/Face/Led/%s/%s/%dDeg/Actuator/Value"; # color, side, angle
        astrColorRGB = ["Red", "Green", "Blue"];
        astrSide = ["Left", "Right"];
        anOrientation = [0,45,90,135,180,225,270,315];
        
        self.eyesDevice = [];
        self.eyesAliasName = "Face";
        for strSide in astrSide:
            for nAngle in anOrientation:    
                for strColor in astrColorRGB:
                    self.eyesDevice.append( strEyeTemplate % ( strColor, strSide, nAngle ) );
        self.dcm.createAlias( [self.eyesAliasName, self.eyesDevice] );
        
        self.eyesDeviceL = [];
        self.eyesDeviceR = [];        
        self.eyesAliasNameL = "FaceL";
        self.eyesAliasNameR = "FaceR";
        for nAngle in anOrientation:
            for strColor in astrColorRGB:
                self.eyesDeviceL.append( strEyeTemplate % ( strColor, astrSide[0], nAngle ) );
                self.eyesDeviceR.append( strEyeTemplate % ( strColor, astrSide[1], nAngle ) );
        self.dcm.createAlias( [self.eyesAliasNameL, self.eyesDeviceL] );
        self.dcm.createAlias( [self.eyesAliasNameR, self.eyesDeviceR] );
        
        # one by one: creating FaceL0, FaceL1, ... and FaceR0,... and Face0,... (but not saving alias name)
        strTemplateNameL = "FaceL%d";
        strTemplateNameR = "FaceR%d";
        strTemplateName = "Face%d";        
        for nIdxAngle, nValAngle in enumerate(anOrientation):
            self.eyesDeviceL = [];
            self.eyesDeviceR = [];
            self.eyesDevice = [];            
            for strColor in astrColorRGB:
                strL = strEyeTemplate % ( strColor, astrSide[0], anOrientation[7-nIdxAngle] );
                strR = strEyeTemplate % ( strColor, astrSide[1], nValAngle );
                self.eyesDeviceL.append( strL );
                self.eyesDeviceR.append( strR );
                self.eyesDevice.append( strL );
                self.eyesDevice.append( strR );
            strAliasName = strTemplateNameL % nIdxAngle;
            #~ print( "DBG: leds.DcmMethod.createAliases: '%s' => %s" % (strAliasName,self.eyesDeviceL) );
            self.dcm.createAlias( [strAliasName, self.eyesDeviceL] );
            strAliasName = strTemplateNameR % nIdxAngle;
            if( bVerbose ):
                print( "DBG: leds.DcmMethod.createAliases: '%s' => %s" % (strAliasName,self.eyesDeviceR) );            
            self.dcm.createAlias( [ strAliasName, self.eyesDeviceR] );
            strAliasName = strTemplateName % nIdxAngle;
            if( bVerbose ):
                print( "DBG: leds.DcmMethod.createAliases: '%s' => %s" % (strAliasName,self.eyesDevice) );
            self.dcm.createAlias( [strAliasName, self.eyesDevice] );
        # for - end
        
        strChestTemplate = "Device/SubDeviceList/ChestBoard/Led/%s/Actuator/Value";
        aChestDevice = [];
        for strColor in astrColorRGB:
            strDevice = strChestTemplate % ( strColor );
            aChestDevice.append( strDevice );
        self.strChestAliasName = "Chest";
        self.dcm.createAlias( [self.strChestAliasName, aChestDevice] );
        if( bVerbose ):
            print( "DBG: leds.DcmMethod.createAliases: '%s' => %s" % (self.strChestAliasName,aChestDevice) );
        
        # Creating Ears, EarL, EarR, Ears0, EarsL0, ...
        nNbrEarSegment = 10;
        strTemplate = "Device/SubDeviceList/Ears/Led/%s/%dDeg/Actuator/Value";
        aAllDevice = [];
        aAllDeviceLR = [[],[]];
        for i in range( nNbrEarSegment ):
            aBothDevice = [];
            for idx,side in enumerate(astrSide):
                strDevice = strTemplate % ( side, (i*36) );
                aAllDevice.append( strDevice );
                aAllDeviceLR[idx].append( strDevice );
                aBothDevice.append( strDevice );
                self.dcm.createAlias( ["Ear%s%d"%(astrSide[idx][0],i), [strDevice]] );
            self.dcm.createAlias( ["Ear%d"%i, aBothDevice] );
        for idx,side in enumerate(astrSide):
            self.dcm.createAlias( ["Ear"+astrSide[idx][0], aAllDeviceLR[idx]] );    
        self.dcm.createAlias( ["Ears", aAllDevice] );
        
        # Romeo Leds mouth
        if self.bIsOnRomeo:
            aAllDevice = [];
            strTemplate = "Device/SubDeviceList/FaceBoard/%sLed%d/Value";
            for i in range(3):
                for strColor in astrColorRGB:
                    strDevice = strTemplate % ( strColor, i+1 );
                    aAllDevice.append( strDevice );
            self.dcm.createAlias( ["Mouth", aAllDevice] );            
        
            # Alternate mouth commanded by the brain alias
            aAllDevice = [];
            nIdxBrainLed = 3;
            for i in range(3):
                nInvertRGB = 2;
                for strColor in astrColorRGB:
                    strDevice = getBrainLedName( nIdxBrainLed+nInvertRGB ); nIdxBrainLed += 1;nInvertRGB-=2;
                    aAllDevice.append( strDevice );
            #~ print( "aAllDevice-MouthAlt: name: %s" % aAllDevice );
            self.dcm.createAlias( ["MouthAlt", aAllDevice] );
        
    # createAliases - end
    
    def getEyesAliasName( self, nEyesMask = 0x3 ):
        "nEyesMask: 1: left, 2: right, 3: both"
        if( self.dcm == None ):
            self.reset();
        if( nEyesMask == 0x3 ):
            return self.eyesAliasName;
        if( nEyesMask == 0x1 ):
            return self.eyesAliasNameL;
        if( nEyesMask == 0x2 ):
            return self.eyesAliasNameR;
    # getEyesAliasName - end
    
    def setEyesIntensity( self, rTime, rIntensity = 1. ):
        "set a grey intensity to all face leds"
        nRiseTime = self.dcm.getTime(int(rTime*1000));
        self.dcm.set( [self.eyesAliasName, "Merge",  [[ float( rIntensity ), nRiseTime ]] ] ); # set only grey intensity    
    # setEyesIntensity - end
    
    def setEyesColor( self, rTime = 0.1, nColor = 0xFFFFFF, nEyesMask = 0x3 ):
        """
        set a color to all face leds (non blocking method)
        - nEyesMask: 1: left, 2: right, 3: both
        - rTime: time to set them (in sec)
        """
        if( self.dcm == None ):
            self.reset();        
        rIntensityB = (( nColor  & 0xFF ) >> 0 ) / 255.;
        rIntensityG = (( nColor  & 0xFF00 ) >> 8 ) / 255.;
        rIntensityR = (( nColor  & 0xFF0000 ) >> 16 ) / 255.; 
        riseTime = self.dcm.getTime(int(rTime*1000));
        commands = [];
        nNbrLum = 8;
        if( nEyesMask == 0x3 ):
            nNbrLum *= 2;
        for i in range( nNbrLum ):
            commands.append( [[ rIntensityR, riseTime ]] );
            commands.append( [[ rIntensityG, riseTime ]] );
            commands.append( [[ rIntensityB, riseTime ]] );            
    #    print( " commands: %s" % str( commands ) );
        self.dcm.setAlias( [self.getEyesAliasName(nEyesMask), "Merge",  "time-mixed", commands] );
    # setEyesColor - end

    def setChestColor( self, rTime = 0.1, nColor = 0xFFFFFF ):
        """
        set a color to all face leds (non blocking method)
        - rTime: time to set them (in sec)
        """
        if( self.dcm == None ):
            self.reset();        
        rIntensityB = (( nColor  & 0xFF ) >> 0 ) / 255.;
        rIntensityG = (( nColor  & 0xFF00 ) >> 8 ) / 255.;
        rIntensityR = (( nColor  & 0xFF0000 ) >> 16 ) / 255.; 
        riseTime = self.dcm.getTime(int(rTime*1000));
        commands = [];
        commands.append( [[ rIntensityR, riseTime ]] );
        commands.append( [[ rIntensityG, riseTime ]] );
        commands.append( [[ rIntensityB, riseTime ]] );            
    #    print( " commands: %s" % str( commands ) );
        self.dcm.setAlias( [self.strChestAliasName, "Merge",  "time-mixed", commands] );
    # setChestColor - end
    
    def setMouthColor( self, rTime = 0.1, color = 0xFFFFFF, bUseAltDevice = False ):
        """
        set a color to all face leds (non blocking method)
        - color: an int or an array of 3 ints (one for each led: left top, bottom, and right top) and for each value an hexa 0xRRGGBB
        - rTime: time to set them (in sec)
        """
        if( self.dcm == None ):
            self.reset();        
        riseTime = self.dcm.getTime(int(rTime*1000));
        commands = [];
        if( isinstance( color, int ) ):
            color = [color]*3;
        assert( len(color) == 3 );
        for nColor in color:
            rIntensityB = (( nColor  & 0xFF ) >> 0 ) / 255.;
            rIntensityG = (( nColor  & 0xFF00 ) >> 8 ) / 255.;
            rIntensityR = (( nColor  & 0xFF0000 ) >> 16 ) / 255.; 
            commands.append( [[ rIntensityR, riseTime ]] );
            commands.append( [[ rIntensityG, riseTime ]] );
            commands.append( [[ rIntensityB, riseTime ]] );

        strAliasName = "Mouth";
        if( bUseAltDevice ):
            strAliasName = "MouthAlt";
        self.dcm.setAlias( [strAliasName, "Merge",  "time-mixed", commands] );
    # setMouthColor - end
    
    
    
    def setMouthOneLed( self, nLedIndex = 0, rTime = 0.1, rIntensity = 1., nColorIndex = 0 ):
        """
        set a color to all face leds (non blocking method)
        - nIndex: 0: left top, 1: right top, 2: bottom
        - rTime: time to set them (in sec)
        - nColorIndex: 0: blue, 1: green, 2: red (because on romeo mouth, it's so blinking that we don't want to erase other leds just for nothing)
        """
        if( self.dcm == None ):
            self.reset();        
        riseTime = self.dcm.getTime(int(rTime*1000));
        nIndexBrain = 3+nColorIndex+nLedIndex*3;
        strDeviceName = getBrainLedName( nIndexBrain );
        #~ print( "strDeviceName: %s" % strDeviceName );
        self.dcm.set( [ strDeviceName, "Merge",  [[ rIntensity, riseTime ]] ] );    # setMouthColor - end     
    # setMouthOneLed - end
    
    def setEyesOneLed( self, nIndex, rTime, nColor = 0xFFFFFF, nEyesMask = 0x3 ):
        """
        set a color to one face leds
        - nIndex: 0-7
        - rTime: in sec
        - nEyesMask: 1: left, 2: right, 3: both
        """
        if( self.dcm == None ):
            self.reset();        
        if self.dcm == None: return
        rIntensityB = (( nColor  & 0xFF ) >> 0 ) / 255.;
        rIntensityG = (( nColor  & 0xFF00 ) >> 8 ) / 255.;
        rIntensityR = (( nColor  & 0xFF0000 ) >> 16 ) / 255.; 
        riseTime = self.dcm.getTime(int(rTime*1000));
        commands = [];
        
        strAliasName = "Face";
        if( nEyesMask == 1 ):
            strAliasName += "L";
        elif( nEyesMask == 2 ):
            strAliasName += "R";
        strAliasName += str( nIndex );
        
        nNbrLum = 1;
        if( nEyesMask == 0x3 ):
            nNbrLum *= 2;
        for i in range( nNbrLum ):
            commands.append( [[ rIntensityR, riseTime ]] );
        for i in range( nNbrLum ):
            commands.append( [[ rIntensityG, riseTime ]] );
        for i in range( nNbrLum ):
            commands.append( [[ rIntensityB, riseTime ]] );            
    #    print( " commands: %s" % str( commands ) );
        self.dcm.setAlias( [strAliasName, "Merge",  "time-mixed", commands] );
    # setEyesOneLed - end    
    
    
    def setEyesRandom( self, rTime, rLuminosityMax = 1. ):
        "set random eyes colors"
        riseTime = self.dcm.getTime(int(rTime*1000));
        commands = [];
        for i in range( 2*8*3 ):
            commands.append( [[ random.random()%rLuminosityMax, riseTime ]] );
        self.dcm.setAlias( [self.eyesAliasName, "Merge",  "time-mixed", commands] );
    # setEyesColor - end       
        
    def getEyesState( self, nEyesMask = 0x3 ):
        """
        return current eyes configuration
        nEyesMask: 1: left, 2: right, 3: both
        """
        if( self.dcm == None ):
            self.reset();        
        if( nEyesMask == 0x3 ):
            return self.mem.getListData( self.eyesDevice );
        if( nEyesMask == 0x1 ):
            return self.mem.getListData( self.eyesDeviceL );
        if( nEyesMask == 0x2 ):
            return self.mem.getListData( self.eyesDeviceR );
    # getEyesState - end
    
        
    def setEyesState( self, arVal, rTime = 1., nEyesMask = 0x3 ):
        """
        set previously saved eyes configuration
        nEyesMask: 1: left, 2: right, 3: both
        """        
        if( self.dcm == None ):
            self.reset();        
        riseTime = self.dcm.getTime(int(rTime*1000));
        commands = [];
        
        nNbrLum = 8*3;
        if( nEyesMask == 0x3 ):
            nNbrLum *= 2;        
        
        for i in range( nNbrLum ):
            commands.append( [[ arVal[i], riseTime ]] );
        self.dcm.setAlias( [self.getEyesAliasName(nEyesMask), "Merge",  "time-mixed", commands] ); 
    # setEyesState - end
    
    def mulEyesIntensity( self, rTime, rMul ):
        "change the intensity of each leds, without changing too much the color (although a multiplication by 0. or a small value will erase all colors informations)"
        allVal = self.getEyesState();
        riseTime = self.dcm.getTime(int(rTime*1000));
        commands = [];
        for i in range( len( allVal ) ):
            rNewVal = allVal[i] * rMul;
            rNewVal = max( min( rNewVal, 1. ), 0. );
            commands.append( [[ rNewVal, riseTime ]] );
    #    print( " commands: %s" % str( commands ) );        
        self.dcm.setAlias( [self.eyesAliasName, "Merge",  "time-mixed", commands] );    
    # mulIntensity - end
    
    def rotateEyes( self, rTime, nDec = 1 ):
        # rotate eyes, using current color (even a mixed color on every eyes)
        if( self.dcm == None ):
            self.reset();        
        allVal = self.getEyesState();
        print( "current val: %s" % str( allVal ) );        
        riseTime = self.dcm.getTime(int(rTime*1000));
        commands = [];
        for j in range( 2 ):        
            for i in range( 8 ):    
                commands.append( [[ allVal[j*8*3+((i+nDec)%8)*3+0], riseTime ]] );
                commands.append( [[ allVal[j*8*3+((i+nDec)%8)*3+1], riseTime ]] );
                commands.append( [[ allVal[j*8*3+((i+nDec)%8)*3+2], riseTime ]] );
            nDec *=-1; # invert direction after first eye
        print( "commands: %s" % str( commands ) );
        self.dcm.setAlias( [self.eyesAliasName, "Merge",  "time-mixed", commands] );        
    # rotateEyes - end
    
    def updateEyeCircle( self, nColor1, nColor2 = 0, rSpeed = 1 ):
        """
        this method is intended to be called frequently to update eyes color in a circling movement, 
        without taking any thread and enabling to make an infinity of contiguous circle.
        Just call it about every 250ms (we send 500ms moves in the future)
        
        - rSpeed: time to make one turn in sec
        """
        
        currentTime = self.dcm.getTime(0);
        timeToEndMove = self.tEyeCircle_timeNextSent - currentTime;
        
        #~ print( "DBG: leds.DcmMethod.updateEyeCircle: next: %s, current: %s, timeToEndMove: %s" % (str(self.tEyeCircle_timeNextSent ), str(currentTime), str(timeToEndMove) ) );

        if( timeToEndMove > 350 ):
            return False;
        if( timeToEndMove < -500 ):
            # it's a first call, reset time
            #~ print( "DBG: leds.DcmMethod.updateEyeCircle: First call ? next: %s, current: %s" % (str(self.tEyeCircle_timeNextSent ), str(currentTime)) );
            self.tEyeCircle_timeNextSent = currentTime;

        rIntensityB1 = (( nColor1  & 0xFF ) >> 0 ) / 255.;
        rIntensityG1 = (( nColor1  & 0xFF00 ) >> 8 ) / 255.;
        rIntensityR1 = (( nColor1  & 0xFF0000 ) >> 16 ) / 255.;
        rIntensityB2 = (( nColor2  & 0xFF ) >> 0 ) / 255.;
        rIntensityG2 = (( nColor2  & 0xFF00 ) >> 8 ) / 255.;
        rIntensityR2 = (( nColor2  & 0xFF0000 ) >> 16 ) / 255.;

        # the number of leds to send in the future is depending on the speed
        nMoves = int(math.ceil(8 * 0.5 /  rSpeed)); # 0.5 for 500ms
        rDT = rSpeed * 1000 / 8. ; # DT in ms
        
        #~ print( "DBG: leds.DcmMethod.updateEyeCircle: Sending nMoves: %d, dt: %f " % (nMoves, rDT) );
        
        for i in range( nMoves ):
            nLedOn = ( i + self.nEyeCircle_NextLedPosition ) % 8;
            nLedOff = ( i + self.nEyeCircle_NextLedPosition -1) % 8;
            riseTime = int( self.tEyeCircle_timeNextSent + i*rDT );
            
            #~ print( "nLedOn: %d, nLedOff: %d, riseTime: %d" % (nLedOn, nLedOff,riseTime) );
            
            strAliasName = "FaceL%d" % nLedOn;            
            commands = [];
            commands.append( [[ rIntensityB1, riseTime ]] );
            commands.append( [[ rIntensityG1, riseTime ]] );
            commands.append( [[ rIntensityR1, riseTime ]] );
            self.dcm.setAlias( [strAliasName, "Merge",  "time-mixed", commands] );
            
            strAliasName = "FaceL%d" % nLedOff;
            commands = [];
            commands.append( [[ rIntensityB2, riseTime ]] );
            commands.append( [[ rIntensityG2, riseTime ]] );
            commands.append( [[ rIntensityR2, riseTime ]] );
            self.dcm.setAlias( [strAliasName, "Merge",  "time-mixed", commands] );

            strAliasName = "FaceR%d" % (nLedOn);
            commands = [];
            commands.append( [[ rIntensityB1, riseTime ]] );
            commands.append( [[ rIntensityG1, riseTime ]] );
            commands.append( [[ rIntensityR1, riseTime ]] );
            self.dcm.setAlias( [strAliasName, "Merge",  "time-mixed", commands] );
            
            strAliasName = "FaceR%d" % (nLedOff);
            commands = [];
            commands.append( [[ rIntensityB2, riseTime ]] );
            commands.append( [[ rIntensityG2, riseTime ]] );
            commands.append( [[ rIntensityR2, riseTime ]] );
            self.dcm.setAlias( [strAliasName, "Merge",  "time-mixed", commands] );

            # this should work also:
            #~ strAliasName = "FaceL%d" % nLedOn;            
            #~ commands = [];
            #~ commands.append( [[ rIntensityB2, riseTime ]] );
            #~ commands.append( [[ rIntensityG2, riseTime ]] );
            #~ commands.append( [[ rIntensityR2, riseTime ]] );            
            #~ commands.append( [[ rIntensityB1, riseTime+int(rDT) ]] );
            #~ commands.append( [[ rIntensityG1, riseTime+int(rDT) ]] );
            #~ commands.append( [[ rIntensityR1, riseTime+int(rDT) ]] );
            #~ commands.append( [[ rIntensityB2, riseTime+int(rDT*2) ]] );
            #~ commands.append( [[ rIntensityG2, riseTime+int(rDT*2) ]] );
            #~ commands.append( [[ rIntensityR2, riseTime+int(rDT*2) ]] );
            
            #~ self.dcm.setAlias( [strAliasName, "Merge",  "time-mixed", commands] );
        
        self.nEyeCircle_NextLedPosition = (self.nEyeCircle_NextLedPosition+nMoves)%8;
        self.tEyeCircle_timeNextSent += nMoves*rDT;

        return True;
    # updateEyeCircle - end
    
    def updateBrainCircle( self, rPeriod = 1., rIntensity = 1. ):
        """
        Update the brain rotation, you should call this from time to time, at least a bit faster than every "period time" sec
        for instance, for a rPeriod of 1 sec, 0.9 is enough :)        
        if you call it too slowly the movement will be slower or irregular, but there's no problem to call it too often...
        - rPeriod: period of one full lap
        """
        currentTime = time.time();
        timeBeforeNextSent = self.tBrainCircle_timeNextSent - currentTime;
        
        #~ print( "DBG: leds.DcmMethod.updateBrainCircle: time: %s, tBrainCircle_timeNextSent: %s, timeBeforeNextSent: %s" % (time.time(), str(self.tBrainCircle_timeNextSent), str(timeBeforeNextSent) ) );

        if( timeBeforeNextSent > rPeriod ):
            # wait a bit more
            #~ print( "DBG: leds.DcmMethod.updateBrainCircle: waiting to send for next call..." );
            return False;
        if( timeBeforeNextSent < 0 ):
            # we miss it, damn, let's send it now !
            #~ print( "DBG: leds.DcmMethod.updateBrainCircle: First call ? or missed, resetting to now" );
            self.tBrainCircle_timeNextSent = currentTime;

        rIntensity = float(rIntensity); # le float ici est ultra important car sinon venant de chorégraphe 1.0 => 1 (depuis les sliders de params)
        nFirstRaiseMs = int((self.tBrainCircle_timeNextSent - currentTime)*1000);
        nTimeForEachLedsMs = int( rPeriod * 1000 / self.nNbrBrainSegment );
        
        for nLedIndex in range( self.nNbrBrainSegment ):
            nRiseDecay = nFirstRaiseMs+nTimeForEachLedsMs*nLedIndex;
            #~ print( "DBG: leds.DcmMethod.updateBrainCircle: rise decay allumage led %d: %s" % ( nLedIndex, nRiseDecay ) );
            strDeviceName = getBrainLedName( nLedIndex );
            preDownTime = self.dcm.getTime( nRiseDecay - nTimeForEachLedsMs);
            riseTime = self.dcm.getTime( nRiseDecay );
            downTime = self.dcm.getTime( nRiseDecay + nTimeForEachLedsMs);
            self.dcm.set( [ strDeviceName, "Merge",  [[ 0., preDownTime ]] ] );
            self.dcm.set( [ strDeviceName, "Merge",  [[ rIntensity, riseTime ]] ] );
            self.dcm.set( [ strDeviceName, "Merge",  [[ 0., downTime ]] ] );
        self.tBrainCircle_timeNextSent += rPeriod;
    # updateBrainCircle - end
    
    def setBrainIntensity( self, rTime, rIntensity = 1. ):
        nTime = self.dcmDefault.getTime( int(rTime*1000) );
        for nLedIndex in range( self.nNbrBrainSegment ):
            strDeviceName = getBrainLedName( nLedIndex );        
            self.dcmDefault.set( [ strDeviceName, "Merge",  [[ rIntensity, nTime ]] ] );
    # setBrain - end
    
    def setEarsLoading( self, rProgress, rBlinkingTime = 1., bHadAnimatedChest = True ):
        """
        Update the ears to make them represent the progression of something 
        (the last segment is blinking after each update, so you should call it regularly even if the progress hasn't changed)
        - rProgress: progression to represent[0..1]
        - rBlinkingTime: blinking time in sec
        """
        #~ print( "INF: setEarsLoading: rProgress: %s, rBlinkingTime: %s" % ( rProgress, rBlinkingTime ) );
        nNbrEarSegment = 10;
        nNbrEarToLit = int( rProgress * nNbrEarSegment );

        currentTime = self.dcm.getTime(0);        
        # instant light of current progression:
        if( self.EarsLoading_nLastNbrEarToLit != nNbrEarToLit or time.time() - self.EarsLoading_timeLastCall > 10. ): # every x sec we force a full refresh (because ears could be used by other process)
            self.EarsLoading_nLastNbrEarToLit = nNbrEarToLit;
            self.EarsLoading_timeLastCall = time.time();
            commands = [];
            commands.append( [[ 1., currentTime ]] );
            for i in range( nNbrEarToLit ):
                self.dcm.setAlias( ["Ear%d"%i, "Merge",  "time-mixed", commands*nNbrEarToLit*2] );
            commands[0][0][0]=0.;
            for i in range( nNbrEarToLit+1, nNbrEarSegment ):
                self.dcm.setAlias( ["Ear%d"%i, "Merge",  "time-mixed", commands*(nNbrEarSegment-nNbrEarToLit)*2] );            
                
        # blinking animation (even if we're full, we make the chest blink)
        riseTime = currentTime + int(rBlinkingTime*1000);            
        commands = [];
        commands.append( [[ 0., riseTime ]] );
        nChestColor = 0;
        if( self.EarsLoading_bLastLit ):
            commands[0][0][0]=1.;
            nChestColor = 0xFF;
        if( nNbrEarToLit < nNbrEarSegment - 1 ):
            self.dcm.setAlias( ["Ear%d"%nNbrEarToLit, "Merge",  "time-mixed", commands*2] );
        if( bHadAnimatedChest ):
            self.setChestColor( rBlinkingTime, nChestColor );
        self.EarsLoading_bLastLit = not self.EarsLoading_bLastLit;
    # setEarsLoading - end
    
# class LedsDcm - end
#try:
#    import qi
#    ledsDcm = LedsDcm(qi.Application())
#except:
#    print( "TODO: regler ce probleme de qiapp" )
#    ledsDcm = None
#
#def autoTest():
#    for i in range( 100 ):
#        ledsDcm.setEarsLoading( i ),
#        time.sleep(0.1)
#
#
#if( __name__ == "__main__" ):
#    autoTest();

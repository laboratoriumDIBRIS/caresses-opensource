def generateFatBass( rSoundDuration = 1., rFrequency = 440. ):
    ##### TODO: rewrite with np !!!
    timeBegin = time.time()
    wav = Wav()
    wav.new()
    #~ wav.addData( [0,30000, -30000] )
    rT = 0.
    nSampling = 44100
    nMax = 0x7FFF
    rBaseFrequencyCounter = -nMax
    rResonanceFrequencyCounter = -nMax
    rSlightDelta = 50 # 50 is like in the wikipedia
    dataBuf = ""
    strFormat = "h"
    while( rT < rSoundDuration ):
        
        #~ nVal = nMax * math.sin( rT*2*math.pi*rFrequency ) # simple sinus
        
        if( 0 ):
            # Simulating a resonant filter, as seen in http://en.wikipedia.org/wiki/Phase_distortion_synthesis
            
            rBaseFrequencyCounter += rFrequency*nMax/nSampling
            if( rBaseFrequencyCounter > nMax ):
                rBaseFrequencyCounter = -nMax
                rResonanceFrequencyCounter = -nMax # resetted by base

            rResonanceFrequencyCounter += (rFrequency+rSlightDelta)*nMax/nSampling
            if( rResonanceFrequencyCounter > nMax ):
                rResonanceFrequencyCounter = -nMax
            
            #~ nVal = rBaseFrequencyCounter            
            #~ nVal = rResonanceFrequencyCounter
            #~ nVal =  nMax * math.sin( rResonanceFrequencyCounter*2*math.pi/nMax )
            nVal =  nMax * math.sin( rResonanceFrequencyCounter*2*math.pi/nMax ) * (-rBaseFrequencyCounter/nMax)
            
        if( 0 ):
            # a variation about a square signal from the sinus formulae:
            # x(t) = (pi/4) * sum[0,+inf][ ( sin((2k+1)2*pi*f*t) / (2k+1) ]
            #~ nDegrees = int( 6 * math.sin( rT / 10. ) ) + 1
            nDegrees = 6
            rVal = 0.            
            for k in range( nDegrees ):
                rVal += math.sin((2*k+1)*2*math.pi*rFrequency*rT) / (2*k+1)
            nVal = int( rVal * (nMax * math.pi/4) )
        
        if( 0 ):
            nVal = nMax * math.sin( rT*2*math.pi*rFrequency )
            nVal += nMax * math.sin( rT*2*math.pi*(rFrequency+0.5))
            
        if( 1 ):
            # a sum of sinus
            rVal = 0.
            nNbrSinus = 2
            for k in range( nNbrSinus ):
                rVal += math.sin(rT*2*math.pi*(rFrequency+(10.8*math.sin(k*0.5*rT)) ))
            nVal = int( rVal * nMax/nNbrSinus )

        # hard clipping
        if( nVal > nMax ):
            nVal = nMax
        if( nVal < -nMax ):
            nVal = -nMax

        
        rT += 1./nSampling
        # wav.addData( [nVal] ) # not optimal
        
        dataBuf += struct.pack( strFormat, nVal )
    # while - end
    wav.data = dataBuf
    self.updateHeaderSizeFromDataLength()
    
    wav.write( "/tmp/generated.wav" )
    rDuration = time.time()-timeBegin
    print( "INF: sound.generateFatBass: generating a sound of %5.3fs in %5.3fs (%5.2fx RT)" % (rSoundDuration,rDuration,rSoundDuration/rDuration) )

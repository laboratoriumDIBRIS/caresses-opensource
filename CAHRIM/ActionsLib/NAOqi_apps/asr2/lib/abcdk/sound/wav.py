import logging
import numpy as np
import struct
import time

def findFirstValueHigher( data, limit ):
    """
    find the first value higher than a limit (in absolute value). 
    return -1 if no value higher in the array
    """
    # NB: argmax could return 0 if all remaining sample are equal to zero (the index of equal value are the one of the first element)
    # min( np.argmax( self.data>nLimit ), np.argmax( self.data<-nLimit ) ); => pb if no neg or no positive value => 0 => min => 0 and so we think there's no value, even if other sign has some # eg: [15,15,-1,-1] and limit = 2    
    # for long sound with a lot of silence and noise, it's faster to recode it having a return well placed.
    idx = np.argmax( np.abs(data)>limit );
    if( abs(data[idx])<= limit ):
        return -1
    return idx    

def findFirstTrueValue( data ):
    """
    find the first value true.
    return -1 if no value true in the array
    """
    # for long sound with a lot of silence and noise, it's faster to recode it having a return well placed. (8sec => 0.052sec)
    n = len(data);
    i = 0;    
    while( i < n ):
        if( data[i] ):
            return i
        i += 1
    return -1    

def findFirstFalseValue( data ):
    """
    find the first value true.
    return -1 if no value true in the array
    """
    #~ idx = np.argmin( data ); 
    #~ if( data[idx] ):
        #~ return -1;
    #~ return idx;
    
    # argmin seems far less efficient than argmax...   (and seems to compute all the list)
    n = len(data);
    i = 0;    
    while( i < n ):
        if( not data[i] ):
            return i;
        i += 1;
    return -1;
# findFirstFalseValue - end 

class Wav:
    # load and extract properties from a wav
    """
    Wave file format specification

    Field name	                            Size and format	    Meaning
    File description header	            4 bytes (DWord)	    The ASCII text string "RIFF" (0x5249 0x4646) The procedure converiting 4-symbol string into dword is included in unit Wave
    Size of file	                            4 bytes (DWord)	    The file size not including the "RIFF" description (4 bytes) and file description (4 bytes). This is file size - 8.
    
    WAV description header	        4 bytes (DWord)	    The ASCII text string "WAVE"
    Format description header	        4 bytes (DWord)	    The ASCII text string "fmt "(The space is also included)
    Size of WAVE section chunck	    4 bytes (DWord)	    The size of the WAVE type format (2 bytes) + mono/stereo flag (2 bytes) + sample rate (4 bytes) + bytes per sec (4 bytes) + block alignment (2 bytes) + bits per sample (2 bytes). This is usually 16.
    WAVE type format	                2 bytes (Word)	    Type of WAVE format. This is a PCM header = $01 (linear quntization). Other values indicates some forms of compression.
    Number of channels	                2 bytes (Word)	    mono ($01) or stereo ($02). You may try more channels...
    Samples per second	                4 bytes (DWord)	    The frequency of quantization (usually 44100 Hz, 22050 Hz, ...)
    Bytes per second	                    4 bytes (DWord)	    Speed of data stream = Number_of_channels*Samples_per_second*Bits_per_Sample/8
    Block alignment	                    2 bytes (Word)	    Number of bytes in elementary quantization = Number_of_channels*Bits_per_Sample/8
    Bits per sample	                    2 bytes (Word)	    Digits of quantization (usually 32, 24, 16, 8). I wonder if this is, for example, 5 ..?
    
    Data description header	        4 bytes (DWord)	    The ASCII text string "data" (0x6461 7461).
    Size of data	                        4 bytes (DWord)	    Number of bytes of data is included in the data section.
    Data	                                    -?-	                    Wave stream data itself. Be careful with format of stereo (see below)

    Notes.

    Note the order of samples in stereo wave file.
    Sample 1 - Left	Sample 1 - Right	Sample 2 - Left	Sample 2 - Right	Sample 3 - Left	 ...

    In case of 8 - bit quantization the sample is unsigned byte (0..255),
    in case of 16 - bit - signed integer (-32767..32767)
    
    Vocabulary:
    - sample: all data for a slice of time, so for a multichannel sound, it's an array.
    - element or value: an elementary value, so for a multichannel sound a sample is an array of element
    so:    
      - nbrSample: number of sample, a 44100Hz Stereo file has 44100 sample per sec
      - nbrElement: number of element, a 44100Hz Stereo file has 88200 element per sec
      - data size: the size in byte, a 44100Hz Stereo file has 176400 byte per sec
      - offset: often exprimed in element offset or in byte (depending of the context)
    
    WARNING: 
    WARNING: TESTED ONLY ON some Channels and depth bits ! (not tested for 24/32 bits)
    WARNING: 
    
    """
    def __init__( self, strLoadFromFile = None, bQuiet = True ):
        self.reset()
        if( strLoadFromFile != None ):
            self.load( strLoadFromFile, bQuiet = bQuiet )
    # __init__ - end
        
    def reset( self ):
        self.strFormatTag = "WAVEfmt "
        self.nNbrChannel = 0
        self.nSamplingRate = 0
        self.nAvgBytesPerSec = 0
        self.nSizeBlockAlign = 0
        self.nNbrBitsPerSample = 0
        self.nDataSize = 0 # the data size (in byte)
        self.nNbrSample = 0 # number of sample (1 sample in stereo 16 bits => 4 bytes)
        self.dataType = -1
        self.rDuration = 0. # duration in seconds
        self.info = {} # extra info (name, date, title, ...)
        self.data = [] # temp array. Will be filled by interlaced sound datas
        self.bHeaderCorrected = False # when loading header wasn't good...
        #~ self.dataUnpacked = [] # an array of samples stereo unpacked (eg in string python format): [L0, R0, L1, R1, ...] multi chan: [chan0-s0, chan1-s0, chan2-s0,chan3-s0,chan0-s1, chan1-s1, ...]
        
    def isOpen( self ):
        return self.nNbrChannel > 0
        
    def new( self, nSamplingRate = 44100, nNbrChannel = 1, nNbrBitsPerSample = 16 ):
        """
        generate a new empty sound
        """
        self.reset()
        self.nNbrChannel = nNbrChannel
        self.nSamplingRate = nSamplingRate
        self.nNbrBitsPerSample = nNbrBitsPerSample        
        self.updateHeaderComputedValues()
    # new - end
    
    def updateHeaderSize( self, nNewDataSize ):
        """
        Update header information relative to the data size to match new data size
        - nNewDataSize: total size of data in bytes
        
        NB: updateHeaderComputedValues() needs to be called before that if you've changed your header properties
        """
        self.nDataSize = int( nNewDataSize )
        self.nNbrSample = int( self.nDataSize * 8 / self.nNbrChannel / self.nNbrBitsPerSample )
        self.rDuration = self.nDataSize / float( self.nAvgBytesPerSec )        
    
    def updateHeaderSizeFromDataLength( self ):
        """
        Update header information relative to the data in current self.data
        NB: updateHeaderComputedValues() needs to be called before that if you've changed your header properties
        """
        self.updateHeaderSize( int( len( self.data ) * self.nNbrBitsPerSample / 8 ) )
    # updateHeaderSizeFromDataLength - end
    
    def updateHeaderComputedValues( self ):
        """
        Update variable that are computed from properties
        """
        self.nAvgBytesPerSec = int( self.nNbrChannel*self.nSamplingRate*self.nNbrBitsPerSample/8 )
        self.nSizeBlockAlign = int( self.nNbrChannel*self.nNbrBitsPerSample/8 )
        self.dataType = Wav.getDataType( self.nNbrBitsPerSample )
    # updateHeaderComputedValue - end
    
    @staticmethod
    def getDataType( nNbrBitsPerSample ):
        logging.debug("in get data type: "+ str(nNbrBitsPerSample))
        if( nNbrBitsPerSample == 8 ):
            return np.int8
        if( nNbrBitsPerSample == 16 ):
            return np.int16
        if( nNbrBitsPerSample == 32 ):
            return np.int32 #TODO NOT TESTED: float?
        raise( BaseException("TODO: handle this NDEV case of unhandled bits per samples" ))
    # getDataType - end
    
    def getNumpyDataType( self ):
        return Wav.getDataType( self.nNbrBitsPerSample )
        
    def getSampleMaxValue( self ):
        if( self.nNbrBitsPerSample == 8 ):
            return 0x7F
        if( self.nNbrBitsPerSample == 16 ):
            return 0x7FFF
        if( self.nNbrBitsPerSample == 32 ):
            return 0x7FFFFF # NOT TESTED: float ? TODO

        raise( BaseException("TODO: handle this NDEV case of unhandled bits per samples" ) )
    # getSampleMaxValue - end
    
    #~ def durationToNbrSample( self, rDuration ):
        #~ return 
        
    #~ def nbrSampleToDuration( self, nNbrSample ):
        #~ return int( nNbrSample / self.nSamplingRate )
    
    def readListData( self, file, bQuiet = True ):
        """
        Takes an open file already located on data just after "LIST" and extract list data.
        Leave the file pointer to the first field after the list data
        Return the length of the field or 0 if it's not a list data field 
        """
        nSizeOfSectionChunck = struct.unpack_from( "i", file.read( 4 ) )[0]
        logging.debug( "nSizeOfSectionChunck: %d"  % nSizeOfSectionChunck )
        data = file.read( 4 )
        #print debug.dumpHexa( data )
        if( data[0] == 'I' and data[3] == 'O' ):
            self.readInfoData( file, nSizeOfSectionChunck - 4, bQuiet = bQuiet )
            return nSizeOfSectionChunck
        return 0
    # readListData - end
    
    def readInfoData( self, file, nChunckSize, bQuiet = True ):
        """
        Takes an open file already located on List-INFO just after INFO and extract INFO data.
        Leave the file pointer to the first field after that chunck
        - nChunckSize: length of data to analyse
        """
        
        aDictConvNameField = {
            "INAM": "Name",
            "IART": "Artist",
            "ICMT": "Comments",
            "ICRD": "Date",
            "ISFT": "Software",
        }
        
        nCpt = 0
        
        while( nCpt < nChunckSize ):
            strFieldName = file.read( 4 ) 
            nCpt += 4
            if( not bQuiet ):
                logging.debug( "strFieldName: '%s'" % strFieldName )
            nFieldDataSize = struct.unpack_from( "i", file.read( 4 ) )[0] 
            nCpt += 4
            if( ( nFieldDataSize % 2 ) == 1 ):
                nFieldDataSize += 1 # some software doesn't output the padded size => padding
            if( not bQuiet ):
                logging.debug( "nFieldDataSize: %s" % nFieldDataSize )
            strFieldContents = file.read( nFieldDataSize ) 
            nCpt += nFieldDataSize
            
            while( strFieldContents[len(strFieldContents)-1] == '\0' ):
                strFieldContents = strFieldContents[:-1]
            if( not bQuiet ):
                logging.debug( "strFieldContents: '%s'" % strFieldContents )
            self.info[aDictConvNameField[strFieldName]] = strFieldContents
            
    # readInfoData - end

    def load( self, strFilename, bLoadData = True, bUnpackData = False, bQuiet = True ):
        """
        load a wav file in the Wav object
        return true if ok
        - bLoadData: when set: raw data are loaded in self.data
        - bUnpackData: DEPRECATED
        """
        logging.debug( "Loading '%s'" % strFilename )
        
        timeBegin = time.time()
        try:
            file = open( strFilename, "rb" )
        except BaseException, err:
            logging.error( "Can't load '%s', err: %s" % (strFilename, err) )
            return False
        # look for the header part
        file.seek( 8L, 0 )
        self.strFormatTag = file.read( 8 )
        if( self.strFormatTag != "WAVEfmt " ):
            file.close()
            logging.error( "Unknown format: '%s'" % self.strFormatTag )
            return False
            
        nSizeOfWaveSectionChunck = struct.unpack_from( "i", file.read( 4 ) )[0]
        
        nWaveTypeFormat = struct.unpack_from( "h", file.read( 2 ) )[0] # Type of WAVE format. This is a PCM header = $01 (linear quntization). Other values indicates some forms of compression.
        
        self.nNbrChannel  = struct.unpack_from( "h", file.read( 2 ) )[0] # mono ($01) or stereo ($02). You may try more channels...

        self.nSamplingRate  = struct.unpack_from( "i", file.read( 4 ) )[0] # The frequency of quantization (usually 44100 Hz, 22050 Hz, ...)

        self.nAvgBytesPerSec  = struct.unpack_from( "i", file.read( 4 ) )[0] # Speed of data stream = Number_of_channels*Samples_per_second*Bits_per_Sample/8
        
        self.nSizeBlockAlign  = struct.unpack_from( "h", file.read( 2 ) )[0] # Number of bytes in elementary quantization = Number_of_channels*Bits_per_Sample/8

        self.nNbrBitsPerSample  = struct.unpack_from( "h", file.read( 2 ) )[0] # Digits of quantization (usually 32, 24, 16, 8). I wonder if this is, for example, 5 ..?
        
        strDataTag = file.read( 4 )
        if( strDataTag != "data" ):
            if( strDataTag == "LIST" ):
                self.readListData( file, bQuiet = bQuiet )
                strDataTag = file.read( 4 )

        if( strDataTag != "data" ):
            if( ord(strDataTag[0]) == 0x16 and ord(strDataTag[1]) == 0x0 and ord(strDataTag[2]) == 0x10 and ord(strDataTag[3]) == 0x0 ):
                logging.warning( "Exotic header found, trying to patch it..." )
                # parecord generate another flavoured head, weird...
                file.seek( 20, 1 )
                strDataTag = file.read( 4 )
        if( strDataTag != "data" ):
            nCurrentPos = file.tell()
            logging.error( "Unknown data chunk name: '%s' (0x%x 0x%x 0x%x 0x%x) (at: %d) - opening failed" % (strDataTag, ord(strDataTag[0]), ord(strDataTag[1]), ord(strDataTag[2]), ord(strDataTag[3]), nCurrentPos - 4 ) )
            if( 1 ):
                logging.error( "Contents of file from begin to 64 after:" )
                file.seek( 0 )
                #print debug.dumpHexa( file.read(nCurrentPos+64) )
            file.close()
            return False
            
        self.nDataSize  = struct.unpack_from( "i", file.read( 4 ) )[0]
        
        self.dataType = Wav.getDataType( self.nNbrBitsPerSample )
        
        self.updateHeaderSize( self.nDataSize )
        
        if( bLoadData ):
            try:
                self.data=np.fromfile( file, dtype=self.dataType )
            except BaseException, err:
                logging.error( "While loading data: err: %s (file:'%s')" % ( err, strFilename ) )
                file.close()
                return False
            
            nNbrBytesPerSample = int( self.nNbrBitsPerSample / 8 )
            nRealDataSize = len( self.data ) * nNbrBytesPerSample
            
            if( nRealDataSize != self.nDataSize ):
                # try to decode info field at the end of the file
                if( nRealDataSize > self.nDataSize ):
                    nLenExtraData = int( (nRealDataSize-self.nDataSize) / nNbrBytesPerSample )
                    for i in range(nLenExtraData):
                        logging.debug( "After data %d: %d 0x%x (%c%c)" % (i, self.data[self.nDataSize/nNbrBytesPerSample+i], self.data[self.nDataSize/nNbrBytesPerSample+i],self.data[self.nDataSize/nNbrBytesPerSample+i]&0xFF,(self.data[self.nDataSize/nNbrBytesPerSample+i]>>8)&0xFF) )                    

                    if( self.data[self.nDataSize/nNbrBytesPerSample] == 0x494c and self.data[self.nDataSize/nNbrBytesPerSample+1] == 0x5453  ):
                        # "LIST"
                        nOffsetFromEnd = nLenExtraData*nNbrBytesPerSample - 4
                        if not bQuiet: logging.warning( "Raw info field is present (at offset from end: %d (0x%x))" % (nOffsetFromEnd,nOffsetFromEnd) )
                        file.seek( -nOffsetFromEnd, os.SEEK_END )
                        nReadSize = self.readListData(file)
                        nReadSize += 8
                        nRealDataSize -= nReadSize
                        self.data = self.data[:-int((nReadSize)/nNbrBytesPerSample)]
            
            if( nRealDataSize != self.nDataSize ):
                if not bQuiet: logging.warning( "In '%s', effective data is different than information from header... changing header... (real: %d, header: %d)" % (strFilename,nRealDataSize,self.nDataSize) )
                self.bHeaderCorrected = True
                self.updateHeaderSizeFromDataLength()

        file.close()

        if not bQuiet: logging.debug( "Loading '%s' - success (loading takes %5.3fs)" % ( strFilename, time.time() - timeBegin ) )
        return True
    # load - end
    
    def loadFromRaw( self, strFilename, nNbrChannel = 2, nSamplingRate = 44100, nNbrBitsPerSample = 16 ):
        """
        load from a raw file, default settings are for CD quality
        """
        self.reset()
                
        logging.info( "Loading '%s'" % strFilename )
        timeBegin = time.time()
        try:
            file = open( strFilename, "rb" )
        except BaseException, err:
            logging.error( "Can't load '%s'" % strFilename )
            return False
            
        self.nNbrChannel = nNbrChannel
        self.nSamplingRate = nSamplingRate
        self.nNbrBitsPerSample = nNbrBitsPerSample
        
        self.updateHeaderComputedValues()
        
        self.data = np.fromfile( file, dtype=self.dataType )
        
        self.nDataSize = int( len(self.data) * nNbrBitsPerSample/8 )
        
        self.updateHeaderSize( self.nDataSize )
        
        file.close()
        
        return True
    # loadFromRaw - end
    
    
    def write( self, strFilename, bAsRawFile = False, bQuiet = False ):
        """
        write current object to a file
        bAsRawFile: just output sound data
        return False on error (empty wav or ...)
        """
        if( len( self.data ) < 1 ):
            logging.warning( "Wav is empty, NOT saving it (to '%s')." % (strFilename) )            
            return False
        timeBegin = time.time()
        file = open( strFilename, "wb" )
        if( not bAsRawFile ):
            self.writeHeader( file )
        self.writeData( file, bAddBeginOfDataChunk = not bAsRawFile )
        file.close()
        rDuration = time.time() - timeBegin
        if not bQuiet: logging.info( "sound.Wav: successfully saved wav to '%s', duration: %5.3fs, datasize: %d (saving takes %5.3fs)" % (strFilename, self.rDuration, self.nDataSize, rDuration) )
        return True
    # write - end
    
    def writeHeader( self, file, bAddBeginOfDataChunk = False, nDataSize = -1 ):
        """
        Write header to the open file
            - bAddBeginOfDataChunk: should be write data chunk in this method ?
            - nDataSize: specific data to write in headers (instead of object current one)
        """
        file.write( "RIFF" )
        if( nDataSize == -1 ):
            nDataSize = self.nDataSize # default use data size from object
        file.write( struct.pack( "I", 4 + nDataSize + 44 + 4 - 16 ) )
        
        file.write( "WAVE" )
        file.write( "fmt " )
        file.write( struct.pack( "I", 16 ) )
        file.write( struct.pack( "h", 1) ) # self.nWaveTypeFormat
        file.write( struct.pack( "h", self.nNbrChannel) )
        file.write( struct.pack( "i", self.nSamplingRate) )
        file.write( struct.pack( "i", self.nAvgBytesPerSec) )
        file.write( struct.pack( "h", self.nSizeBlockAlign) )
        file.write( struct.pack( "h", self.nNbrBitsPerSample) )        
        
        if( bAddBeginOfDataChunk ):
            file.write( "data" )
            file.write( struct.pack( "I", nDataSize ) )
    # writeHeader - end
    
    def writeData( self, file, bAddBeginOfDataChunk = True ):
        """
        Write current sound data to file
        """
        self.writeSpecificData( file, self.data, bAddBeginOfDataChunk = bAddBeginOfDataChunk )
    # writeData - end
    
    def writeSpecificData( self, file, data, bAddBeginOfDataChunk = True ):
        """
        Write random data to file
        """
        if( not isinstance( data, np.ndarray ) ):
            data = np.array( data, dtype = self.dataType )
        if( bAddBeginOfDataChunk ):
            file.write( "data" )
            file.write( struct.pack( "I", len(data)*self.nNbrBitsPerSample/8 ) )
        data.tofile( file )
    # writeSpecificData - end
    
    def copyHeader( self, rhs ):
        """
        Copy header from a Wav object to another one
        """
        self.reset()
        self.strFormatTag = rhs.strFormatTag
        self.nNbrChannel = rhs.nNbrChannel
        self.nSamplingRate = rhs.nSamplingRate
        self.nAvgBytesPerSec = rhs.nAvgBytesPerSec
        self.nSizeBlockAlign = rhs.nSizeBlockAlign
        self.nNbrBitsPerSample = rhs.nNbrBitsPerSample
        self.nDataSize = rhs.nDataSize
        self.nNbrSample = rhs.nNbrSample
        self.dataType = rhs.dataType        
        self.rDuration = rhs.rDuration
    # copyHeader - end
    
    def extractOneChannel( self, nNumChannel = 0 ):
        """
        get one channel from some multiband sound
        """
        if( nNumChannel >= self.nNbrChannel ):
            logging.error( "You ask for a non existing channel, returning empty data list (nbr channel: %d, asked: %d)" %(self.nNbrChannel,nNumChannel) )
            return []
        return self.data[nNumChannel::self.nNbrChannel]
    # extractOneChannel - end

    def extractOneChannelAndSaveToFile( self, strOutputFilename, nNumChannel = 0 ):
        """
        Extracting one channel from a wav and saving to some file
        - strOutputFilename: output file
        - nNumChannel: channel to extract
        """
        logging.info( "Extracting channel %d to file '%s'" % (nNumChannel, strOutputFilename ) )
        if( self.nDataSize < 1 or len( self.data ) < 2 ):
            logging.info( "Original wav has no data (use bLoadData option at loading)" )
            return False
        timeBegin = time.time()
        
        newWav = Wav()
        newWav.copyHeader( self )
        newWav.nNbrChannel = 1
        newWav.updateHeaderComputedValues()        
        newWav.updateHeaderSize( self.nDataSize * newWav.nNbrChannel / self.nNbrChannel )
        
        newData = []
        idx = nNumChannel # positionnate on good channel
        nIncIdx = int( (self.nNbrChannel) / newWav.nNbrChannel )
        
        newData = self.data[nNumChannel::nIncIdx]

        file = open( strOutputFilename, "wb" )
        newWav.writeHeader( file )
        newWav.writeSpecificData( file, newData )
        file.close()
        logging.info( "Done (datasize: %d, nbrsample: %d) (duration: %5.3fs)" % (newWav.nDataSize, newWav.nNbrSample, time.time() - timeBegin) )
        return True
    # extractOneChannelAndSaveToFile - end
    
    def addData( self, anValue ):
        """
        Add data at the end of the current sound.
        - anValue: unpacked value  (python value), could be just a value, or a bunch of value eg for a stereo: [val1_chan1, val1_chan2, val2_chan1, val2, chan2 ...]
        return False on error
        """
        nNbrData = len(anValue) 
        nNbrSample = nNbrData/self.nNbrChannel
        if( self.nNbrChannel*nNbrSample != nNbrData ):
            logging.error( "You should provide a number of data multiple of you channel number ! (data:%d, nbrChannel: %d)" % ( nNbrData, self.nNbrChannel ) )
            return False

        if( not isinstance( anValue, np.ndarray ) ):
            anValue = np.array( anValue, dtype = self.dataType )
        
        if( len( self.data ) == 0 ):
            self.data = np.copy( anValue ) # so we copy the type !!!
        else:
            self.data = np.concatenate( ( self.data, anValue) )
        self.updateHeaderSizeFromDataLength()        
        return True
    # addData - end
    
    def insertData( self, nOffset, anValue ):
        """
        Insert data at a random point
        - nOffset: offset, in number of sample.
        - anValue: unpacked value  (python value), could be just a value, or a bunch of value eg for a stereo: [val1_chan1, val1_chan2, val2_chan1, val2, chan2 ...]
        return False on error
        """
        nNbrDataSize = len(anValue) 
        nNbrSample = nNbrDataSize/self.nNbrChannel
        if( self.nNbrChannel*nNbrSample != nNbrDataSize ):
            logging.error( "You should provide a number of data multiple of your channel number ! (data size:%d, nbrChannel: %d)" % ( nNbrDataSize, self.nNbrChannel ) )
            return False
        # update header:
        self.rDuration += float(nNbrSample)/self.nSamplingRate        
        self.nDataSize += int( nNbrDataSize*self.nNbrBitsPerSample/8 )
        self.nNbrSample += nNbrSample
        # update data:
        #~ self.dataUnpacked.append( anValue )
        strFormat = "B"
        if( self.nNbrBitsPerSample == 16 ):
            strFormat = "h"
        
        newData = ""
        for i in range( nNbrDataSize ):
            newData += struct.pack( strFormat, anValue[i] )
        
        nInsertPoint = nOffset*self.nNbrChannel*self.nNbrBitsPerSample/8
        self.data = self.data[:nInsertPoint] + newData + self.data[nInsertPoint:]

        return True
    # insertData - end
    
    def replaceData( self, nOffset, anValue, nOperation = 0 ):
        """
        Change data at a random point
        - nOffset: offset, in number of sample.
        - anValue: unpacked value  (python value), could be just a value, or a bunch of value eg for a stereo: [val1_chan1, val1_chan2, val2_chan1, val2, chan2 ...]
        - nOperation: 0: replace, 1: add to data, -1: substract from data
        return False on error
        """
        nNbrElementNew = len(anValue) 
        nNbrSampleNew = int(nNbrElementNew/self.nNbrChannel)
        
        logging.info( "Replacing %d samples (nbr element:%d)" % (nNbrSampleNew,nNbrElementNew) )
        if( self.nNbrChannel*nNbrSampleNew != nNbrElementNew ):
            logging.error( "You should provide a number of element multiple of you channel number ! (data size:%d, nbrChannel: %d)" % ( nNbrElementNew, self.nNbrChannel ) )
            return False

        if( nNbrSampleNew + nOffset > self.nNbrSample ):
            logging.error( "Too much data to replace sound (nbrSampleToReplace: %d, offset: %d, total sample in sound: %d) (nbrChannel: %d)" % ( nNbrSampleNew, nOffset, self.nNbrSample, self.nNbrChannel ) )
            return False
        
        nInPoint = nOffset*self.nNbrChannel
        if( nOperation == 0 ):
            self.data[nInPoint:nInPoint+nNbrElementNew] = anValue
        elif( nOperation == 1 ):
            self.data[nInPoint:nInPoint+nNbrElementNew] += anValue
        else:
            self.data[nInPoint:nInPoint+nNbrElementNew] -= anValue
            
        return True
    # insertData - end    
    
    def delData( self, nOffset, nNbrSample = 1 ):
        """
        Remove data at a random point
        - nOffset: offset, in number of sample.    
        - nNbrSample: number of sample to remove
        """
        nNbrDataSize = nNbrSample * self.nNbrChannel
        # update header:
        self.nDataSize -= int( nNbrDataSize*self.nNbrBitsPerSample/8 )
        self.rDuration -= float(nNbrSample)/self.nSamplingRate        
        self.nNbrSample -= nNbrSample
        self.data = self.data[:nOffset*self.nNbrChannel*self.nNbrBitsPerSample/8] + self.data[((nOffset+nNbrSample)*self.nNbrChannel*self.nNbrBitsPerSample/8):]
        return True
    # delData - end
    
    def trim( self, rSilenceTresholdPercent = 0. ):
        """
        Remove silence at begin or end
        - rSilenceTresholdPercent: threshold to detect a silence [0..100]
        """
            
        return self.ensureSilence( rTimeAtBegin = 0., rTimeAtEnd = 0., bRemoveIfTooMuch = True, rSilenceTresholdPercent = rSilenceTresholdPercent )
    # trim - end
    
    def addSilence( self, rSilenceDuration = 1., nOffsetNDEV = -1 ):
        nNbrSample = int( self.nSamplingRate * self.nNbrChannel * rSilenceDuration )
        aRawSilence = [0] * nNbrSample # TODO: np.zeros
        self.addData( aRawSilence )
    # addSilence - end
    
    #
    # Processing
    #
    
    def ensureSilenceAtBegin( self, rTimeAtBegin = 1., bRemoveIfTooMuch = False, rSilenceTresholdPercent = 0. ):
        
        nLimit = int( self.getSampleMaxValue() * rSilenceTresholdPercent / 100 )
        
        # beginning        
        nFirstNonSilenceIndex = findFirstValueHigher( self.data, nLimit )
        if( nFirstNonSilenceIndex == -1 ):
            logging.warning( "This sound seems to have only silence!!!" )
            nFirstNonSilenceIndex = len(self.data) - 1
        nNumFirstSample = (nFirstNonSilenceIndex/self.nNbrChannel)*self.nNbrChannel
        nNbrWantedSilenceSample = rTimeAtBegin * self.nSamplingRate
        if( nNbrWantedSilenceSample > nNumFirstSample ):
            # add silence:
            logging.info( "Adding %d sample at beginning (or end)" % nMissingSample )
            nMissingSample = nNbrWantedSilenceSample-nNumFirstSample
            self.data = np.concatenate( (np.zeros( nMissingSample*self.nNbrChannel, dtype=self.dataType ), self.data ) )
        elif( bRemoveIfTooMuch and nNbrWantedSilenceSample < nNumFirstSample ):
            # remove some
            nRemovingSample = nNumFirstSample-nNbrWantedSilenceSample
            logging.info( "Removing %d sample at beginning (or end)" % nRemovingSample )
            self.data = self.data[nRemovingSample*self.nNbrChannel:]
            
        # end (reverse order ? lazy ?)
        #~ nLastNonSilenceIndex = min( np.argmax( self.data>nLimit ), np.argmax( self.data<-nLimit ) )
        
        self.updateHeaderSizeFromDataLength()
    # ensureSilenceAtBegin - end
    
    def ensureSilence( self, rTimeAtBegin = 1., rTimeAtEnd = 1., bRemoveIfTooMuch = False, rSilenceTresholdPercent = 0. ):
        """
        Ensure there's enough silence at begin or end of a sound
        - timeAtBegin: time in sec at begin of the sound
        - timeAtEnd: ...
        - bRemoveIfTooMuch: if there's more silence than required, did we remove some ?
        - rSilenceTresholdPercent: how to qualify silence ?
        """
        self.ensureSilenceAtBegin( rTimeAtBegin = rTimeAtBegin, bRemoveIfTooMuch = bRemoveIfTooMuch, rSilenceTresholdPercent = rSilenceTresholdPercent )
        self.data = self.data[::-1] # reverse data (WRN: left and right are swapped too, but our computation is doing the same on each channels)
        self.ensureSilenceAtBegin( rTimeAtBegin = rTimeAtEnd, bRemoveIfTooMuch = bRemoveIfTooMuch, rSilenceTresholdPercent = rSilenceTresholdPercent )
        self.data = self.data[::-1] # revert it back
    # def ensureSilence - end
    
    def removeGlitch( self, rGlitchMaxTresholdPercent = 5., rGlitchMaxDurationSec = 0.01, rSilenceTresholdPercent = 1., rSilenceMinDurationSec = 0.020 ):
        """
        Remove glitch, by replacing them with samples at 0.
        A glitch is defined to be a small noise in peak and duration, surrounded by blank
        
        - rGlitchMaxTresholdPercent: the absolute peak of the glitch has to be lower than this value
        - rGlitchMaxDurationSec: the peak duration must be shorter or equal to that duration (for reference a 's' short is about 0.084 sec, and a small lingual glitch is 0.003s, a 'p' as in handicap is a 0.058s length (but hard part is only 0,025 long) with a very small peak: 812)
        - rSilenceTresholdPercent: the maximum volume to detect silence
        - rSilenceMinDurationSec: the minimal duration of no sound surrounding the peak
        
        NB: This method will also remove all constant lower sound (bruit de fond) < rMaxGlitchTresholdPercent
        """
        timeBegin = time.time()
        nGlitchLimit =  int( self.getSampleMaxValue() * rGlitchMaxTresholdPercent / 100 )
        nSilenceLimit = int( self.getSampleMaxValue() * rSilenceTresholdPercent / 100 )
        
        nGlitchNumSampleMaxDuration = int( rGlitchMaxDurationSec * self.nSamplingRate )
        nSilenceNumSampleMinDuration = int( rSilenceMinDurationSec * self.nSamplingRate )
                    
        rMarginAroundSilenceBlanking = 0.1 # in sec
        nSilenceAroundSilenceBlanking = int( rMarginAroundSilenceBlanking * self.nSamplingRate )
        
        logging.debug( "nSilenceLimit: %d, nGlitchLimit: %d, nGlitchNumSampleMaxDuration: %d, nSilenceNumSampleMinDuration: %d" % ( nSilenceLimit, nGlitchLimit, nGlitchNumSampleMaxDuration, nSilenceNumSampleMinDuration ) )
                    
        aPosGlitchBegin = [0]*self.nNbrChannel # for each channel, the position of beginning glitch
        aPosSilenceBegin = [0]*self.nNbrChannel # for each channel, the position of beginning silence
        aPosLastSoundEnd = [0]*self.nNbrChannel # for each channel, the last time with sound
        anState = [0]*self.nNbrChannel # for each channel: the nature of current sound: 0: real silence, 1: glitch, 2: sound, 3: short silence after glitch, 4: short silence after sound

        nNbrGlitch = 0
        nNumSample = 0
        nNbrSampleReplace = 0
        while( True ):
            for nNumChannel in range( self.nNbrChannel ):
                val = self.data[(nNumSample*self.nNbrChannel)+nNumChannel]
                val = abs(val)
                nCurrentState = anState[nNumChannel]
                newState = nCurrentState
                    
                if( nCurrentState == 0 ):
                    if( val > nGlitchLimit ):
                        newState = 2
                    elif( val > nSilenceLimit ):
                        newState = 1
                        aPosGlitchBegin[nNumChannel] = nNumSample
                elif( nCurrentState == 1 ):
                    if( val > nGlitchLimit ):
                        newState = 2
                    elif( val < nSilenceLimit ):
                        newState = 3
                        aPosSilenceBegin[nNumChannel] = nNumSample
                    elif( nNumSample - aPosGlitchBegin[nNumChannel] >= nGlitchNumSampleMaxDuration ):
                        # too long => sound
                        newState = 2
                elif( nCurrentState == 2 ):
                    if( val < nSilenceLimit ):
                        newState = 4
                        aPosSilenceBegin[nNumChannel] = nNumSample
                        aPosLastSoundEnd[nNumChannel] = nNumSample
                elif( nCurrentState == 3 ):
                    if( val > nGlitchLimit ):
                        newState = 2
                    elif( val > nSilenceLimit ):
                        newState = 1
                    elif( nNumSample - aPosSilenceBegin[nNumChannel] >= nSilenceNumSampleMinDuration ):
                        newState = 0
                        # erase this glitch
                        logging.info( "Channel%d: Erasing glitch between %s (%5.3fs) and %s (%5.3fs)" % (nNumChannel, aPosGlitchBegin[nNumChannel],aPosGlitchBegin[nNumChannel]/float(self.nSamplingRate), nNumSample, nNumSample/float(self.nSamplingRate) ) )
                        nNbrGlitch += 1
                        self.data[ (aPosGlitchBegin[nNumChannel]*self.nNbrChannel)+nNumChannel:(nNumSample*self.nNbrChannel)+nNumChannel:self.nNbrChannel]=[0]*(nNumSample-aPosGlitchBegin[nNumChannel])
                elif( nCurrentState == 4 ):
                    if( val > nSilenceLimit ):
                        newState = 2
                    elif( nNumSample - aPosSilenceBegin[nNumChannel] >= nSilenceNumSampleMinDuration ):
                        newState = 0
                        # nothing to do!
                        
                if( newState != nCurrentState ):
                    if( nNumSample < 300000 ):
                        logging.debug( "Channel%d: sample: %d (%5.3fs), new state: %d, data: %d" % (nNumChannel,nNumSample,nNumSample/float(self.nSamplingRate), newState,val) )
                    anState[nNumChannel] = newState
                    if( newState == 2 ):
                        # we add a small respiration to leave sound trail and attacks
                        if( aPosLastSoundEnd[nNumChannel] == 0 ):
                            nBegin = 0
                        else:
                            nBegin = aPosLastSoundEnd[nNumChannel] + nSilenceAroundSilenceBlanking
                        nEnd = nNumSample - nSilenceAroundSilenceBlanking
                        if( nBegin < nEnd ):
                            logging.debug( "Channel%d: Blanking silence between %s (%5.3fs) and %s (%5.3fs)" % ( nNumChannel, nBegin, nBegin/float(self.nSamplingRate), nEnd, nEnd/float(self.nSamplingRate) ) )
                            self.data[ (nBegin*self.nNbrChannel)+nNumChannel:(nEnd*self.nNbrChannel)+nNumChannel:self.nNbrChannel]=[0]*(nEnd-nBegin)
                        
            # for each chan - end
            nNumSample += 1
            if( nNumSample % 10000 == 0 ):
                #TODO: unpack to be able to modify  just a bit of the chain OR look how to remove a bit of the chain without compy everything (super long)
                logging.debug( "nNumSample: %d (state[0]: %d)" % (nNumSample, anState[0]) )  
            
            if( nNumSample >= self.nNbrSample ):
                break
        # while - end
        
        rDuration = time.time()-timeBegin
        
        logging.info( "removeGlitch: nNbrGlitch: %d, (time taken: %5.3fs)" % (nNbrGlitch, rDuration ) )
        
        return True
    # removeGlitch - end
    
    def getPeakValue( self ):
        """
        Return the peak value [0..1] of the sound (represent the fact that the sound is loud or not) (cheaper than rms power)
        """
        nCurrentMax = max( self.data.max(), -self.data.min() )
        return float(nCurrentMax) / self.getSampleMaxValue()
    # getPeakValue - end
    
    def normalise( self, rWantedMax = 100. ):
        """
        Normalise sound to achieve maximum power (just a scale)
        - rWantedMax: value of peak to achieve (in %)
        Return True if modification has been made, False if no modification was apply
        """
        nWantedMax = int( self.getSampleMaxValue() * rWantedMax / 100)
        nCurrentMax = max( self.data.max(), -self.data.min() )
        rRatio = nWantedMax / float(nCurrentMax)
        if( nCurrentMax == nWantedMax ):
            return False
        logging.info( "nCurrentMax: %s" % nCurrentMax )
        logging.info( "nWantedMax: %s" % nWantedMax )            
        logging.info( "applying a %f ratio to the whole sound" % rRatio )
        self.data *= rRatio  # another option is to make a np.round(self.data*rRatio), but it's perhaps less linear (on a linear elevation for example)
        return True
    # normalise - end
    
    def isEqual( self, rhs ):
        if( not self.hasSameProperties( rhs ) ):
            return False
        bRet = np.all( self.data == rhs.data )
        if( not bRet ):
            if( len( self.data ) != len( rhs.data ) ):
                logging.info( "Length of data is different: %d != %d" % ( len( self.data ), len( rhs.data ) ) )
            bLookForDifference = True
            if( bLookForDifference ):
                # automatic method:
                #~ listdiff = self.data - rhs.data
                #~ u, inv = np.unique(listdiff, return_inverse=True)
                #~ print u
                #~ print inv # we should the one pointing remove zero ! TODO !!!
                # manual method:
                nNbrDiff = 0
                for i in range( len( self.data ) ):
                    if( self.data[i] != rhs.data[i] ):
                        if( nNbrDiff < 20 ):
                            print( "INF: sound.Wav.isEqual: DIFFERENCE at offset %d: data: %d (0x%02x) and %d (0x%02x)"  % ( i, self.data[i],self.data[i],rhs.data[i],rhs.data[i] ) )
                        nNbrDiff += 1
                print( "INF: sound.Wav.isEqual: %d DIFFERENCE(s) found..." % nNbrDiff )
            
        return bRet
    # isEqual - end

    def hasSameProperties( self, rhs ):
        if( self.nNbrChannel != rhs.nNbrChannel ):
            print( "INF: sound.Wav.hasSameProperties: different nbr channel: %s != %s" % ( self.nNbrChannel,  rhs.nNbrChannel) )
            return False
        if( self.nSamplingRate != rhs.nSamplingRate ):
            print( "INF: sound.Wav.hasSameProperties: different sampling rate: %s != %s" % ( self.nSamplingRate,  rhs.nSamplingRate) )
            return False
        if( self.nAvgBytesPerSec != rhs.nAvgBytesPerSec ):
            print( "INF: sound.Wav.hasSameProperties: different nAvgBytesPerSec: %s != %s" % ( self.nAvgBytesPerSec,  rhs.nAvgBytesPerSec) )
            return False
        if( self.nSizeBlockAlign != rhs.nSizeBlockAlign ):
            print( "INF: sound.Wav.hasSameProperties: different nSizeBlockAlign: %s != %s" % ( self.nSizeBlockAlign,  rhs.nSizeBlockAlign) )
            return False
        if( self.nNbrBitsPerSample != rhs.nNbrBitsPerSample ):
            print( "INF: sound.Wav.hasSameProperties: different nNbrBitsPerSample: %s != %s" % ( self.nNbrBitsPerSample,  rhs.nNbrBitsPerSample) )
            return False
        #~ if( self.nDataSize != rhs.nDataSize ):
            #~ print( "INF: sound.Wav.hasSameProperties: different nNbrBitsPerSample: %s != %s" % ( self.nDataSize,  rhs.nDataSize) )
            #~ return False
        return True
    # hasSameProperties - end
    
    def split( self, rSilenceTresholdPercent = 0.1, rSilenceMinDuration = 0.3, nExtractJustFirsts = -1 ):
        """
        split a wav into a bunch of wav
        - rSilenceTresholdPercent: how to qualify silence ?
        - rSilenceMinDuration: how to qualify silence ? (in second)
        - nExtractJustFirsts: limit extraction to the n'th first
        return a list of new created wav
        """
        nLimit = int( self.getSampleMaxValue() * rSilenceTresholdPercent / 100 )        
        print( "INF: sound.Wav.split: splitting a sound of %5.3fs, using silence limits at %d for %5.3fs" % (self.rDuration, nLimit, rSilenceMinDuration) ) 
        aSplitted = []
        
        precalcWavIsNotSilence = np.abs(self.data)>nLimit

        #~ print self
        
        nCurrentPos = 0 # in data index (not sample)
        nSilenceMinLenData = rSilenceMinDuration * self.nAvgBytesPerSec * 8 / self.nNbrBitsPerSample
        while( nCurrentPos < len(self.data) ):
            
            # first find the beginning of a sound            
            nFirstNonSilenceIndex = findFirstTrueValue( precalcWavIsNotSilence[nCurrentPos:] )
            #~ print( "nFirstNonSilenceIndex (brut): %d" % nFirstNonSilenceIndex )
            if( nFirstNonSilenceIndex == -1 ):
                # all remaining sound are silence!
                break
            nFirstNonSilenceIndex += nCurrentPos
            nNumFirstSample = nFirstNonSilenceIndex/self.nNbrChannel
            print( "INF: sound.Wav.split: found a sound at sample %d" % nNumFirstSample )
            nCurrentPos = nFirstNonSilenceIndex # so at the end, we're stopping
            
            # then find end
            nEndOfSilence = nNumFirstSample*self.nNbrChannel # init of the loop
            while( nEndOfSilence < len(self.data) ):
                #nFirstSilenceIndex = np.argmax( np.abs(self.data[nEndOfSilence:])<=nLimit )
                nFirstSilenceIndex = findFirstFalseValue( precalcWavIsNotSilence[nEndOfSilence:] )                
                #~ print( "nFirstSilenceIndex (brut): %d (from %d)" % (nFirstSilenceIndex, nEndOfSilence) )
                if( nFirstSilenceIndex == -1 ):
                    break
                nFirstSilenceIndex += nEndOfSilence
                # ensure there's enough silence
                nEndOfSilence = findFirstTrueValue( precalcWavIsNotSilence[nFirstSilenceIndex:] )
                #~ print( "nEndOfSilence (brut): %d (data: %d) (offset: %d)" % (nEndOfSilence, self.data[nFirstSilenceIndex+nEndOfSilence],nEndOfSilence + nFirstSilenceIndex) )
                # positionnate onto the end of the silence for next time
                if( nEndOfSilence == -1 ):
                    nCurrentPos = len(self.data)
                else:
                    nCurrentPos = nEndOfSilence + nFirstSilenceIndex
                    
                if( nEndOfSilence > nSilenceMinLenData or nEndOfSilence == -1 ):
                    break
                nEndOfSilence += nFirstSilenceIndex
            # while - end
            
            # each time we're out, we've got a silence or we're at the end => new split
            if( nFirstSilenceIndex == -1 ):
                break
            nNumLastSample = nFirstSilenceIndex/self.nNbrChannel
            print( "INF: sound.Wav.split: found the end of that sound at sample %d" % nNumLastSample )
            if( nNumLastSample - nNumFirstSample > 4000 ):
                w = Wav()
                w.copyHeader( self )
                w.data = np.copy(self.data[nNumFirstSample*self.nNbrChannel:nNumLastSample*self.nNbrChannel])
                nPeakMax = max( max( w.data ), -min( w.data ) )
                if( nPeakMax > self.getSampleMaxValue() / 8 ): # remove glitch sound
                    w.updateHeaderSizeFromDataLength()
                    print( "INF: sound.Wav.split: new split of %5.2fs" % w.rDuration )
                    aSplitted.append( w )
            #~ print( "nCurLocalVs: %s" % nCurLocalVs )
            if( nExtractJustFirsts != -1 and nExtractJustFirsts == len(aSplitted) ):
                print( "WRN: sound.Wav.split: got enough split (%d), leaving..." % len(aSplitted) )
                break
        # while - end
        print( "INF: sound.Wav.split: created %d wav(s)" % len( aSplitted ) )
        return aSplitted
    # split - end
    
    def __str__( self ):
        strOut = ""
        strOut += "- strFormatTag: '%s'\n" % self.strFormatTag
        strOut += "- nNbrChannel: %s\n" % str( self.nNbrChannel )
        strOut += "- nSamplingRate: %s\n" % self.nSamplingRate # print with "%s" so we detect floating stuffs
        strOut += "- nAvgBytesPerSec: %s\n" % self.nAvgBytesPerSec
        strOut += "- nSizeBlockAlign: %s\n" % self.nSizeBlockAlign        
        strOut += "- nNbrBitsPerSample: %s\n" % self.nNbrBitsPerSample
        strOut += "- nDataSize: %s\n" % self.nDataSize
        strOut += "- nNbrSample: %s\n" % self.nNbrSample
        strOut += "- rDuration: %f\n" % self.rDuration
        strOut += "- info: %s\n" % self.info
        strOut += "- data (size)(in type): %d\n" % len( self.data )
        strOut += "- dataType: %s\n" % self.dataType
        if( len( self.data ) > 0 ):
            for i in range( min(16, len(self.data) ) ):
                strOut += "- data[%d]: 0x%x (%d)\n" % ( i, self.data[i], self.data[i] )
            strOut += "- ..."
        #~ strOut += "- dataUnpacked (size): %d\n" % len( self.dataUnpacked )            
        #~ if( len( self.dataUnpacked ) > 0 ):
            #~ for i in range( min(4,len(self.dataUnpacked) ) ):
                #~ strOut += "- dataUnpacked[%d]: 0x%x (%d)\n" % ( i, self.dataUnpacked[i], self.dataUnpacked[i] )
        return strOut
# class Wav - end

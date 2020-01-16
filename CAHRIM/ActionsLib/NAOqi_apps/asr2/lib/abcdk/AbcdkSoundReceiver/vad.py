import logging

class VAD:
    """
    receive mfcc ad compute a vad (keep current state from previous buffer)
    """
    def __init__(self, rPreTime = 0.150, rPostTime = 0.40 ):
        self.rPreTime = rPreTime
        self.rPostTime = rPostTime
        self.bPrevFrameHasPotentialVoice = False
        self.bCurrentStatus = False
        self.nCptNoVoiceSinceDetected = 1000
        
    def computeFromMfcc( self, computedMfcc, rWindowStepInSec ):
        """
        Detect Voice Activity from buffer slices
        return an array of state change in second, relative to the origin of the first window
        [sc1, sc2, sc3, ...]
        with sc: [True, -0.15]: voice start 150ms from now or [False, 0.3]: voice stop in 0.3 sec...
        """
        aSc = []
        rCurrentTime = 0.
        nNbrWindowRelativeToPostTime = int(self.rPostTime / rWindowStepInSec)
        step = 0
        
        for band_results in computedMfcc:
            step += 1
            res = 0
            # TODO: band index should be relative to the samplerate
            # TODO: have a prePotentialVoice tunable with more than just the previous (for hands_noise)
            # TODO: check the litterature on how to build a heuristic for VAD based on mfcc

            bPotentialVoice = band_results[0] > 18 and band_results[1] > -10

            #logging at debug level for eavaluation purpose
            logging.debug(str(step * rWindowStepInSec) + "," + str(band_results[0]) + "," + str(band_results[1]) + "," + str(band_results[2]) + "," + str(band_results[3]) + "," + str(band_results[4])+ "," + str(band_results[5]) + "," + str(int(bPotentialVoice)))

            if bPotentialVoice and self.bPrevFrameHasPotentialVoice:
                res = 1
                self.nCptNoVoiceSinceDetected = 0
            else:
                self.nCptNoVoiceSinceDetected += 1
                if self.nCptNoVoiceSinceDetected < nNbrWindowRelativeToPostTime:
                    res = 1
            self.bPrevFrameHasPotentialVoice = bPotentialVoice
            
            if res != self.bCurrentStatus:
                self.bCurrentStatus = res
                scTime = rCurrentTime
                if res == 1:
                    scTime -= self.rPreTime # add pretime
                aSc.append( [res, scTime] )
            
            rCurrentTime += rWindowStepInSec

        return aSc

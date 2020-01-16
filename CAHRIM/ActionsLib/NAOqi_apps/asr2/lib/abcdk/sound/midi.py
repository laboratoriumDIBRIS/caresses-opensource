def midiNoteToFreq(nNote):
    """
    @param nNote: midiNote (from 0 to 128)
    @return: corresponding freq.
    """
    if nNote in range(0, 128):
        return 440 * 2**((nNote-69.0)/12.0)
    else:
        return 0

def freqToMidiNote(freq):
    """
    @param freq: frequence in Hz
    @return: correspond clossest midi Note
    """
    if freq == 0:
        return -1
    return round(12 * np.log2(freq/440.0) + 69.0 )  # le 0.5 c'est pour passer a la note au dessus si on est plus proche d'elle
    

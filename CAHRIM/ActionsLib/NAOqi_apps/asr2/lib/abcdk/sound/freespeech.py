# -*- coding: utf-8 -*-
###########################################################
# Aldebaran Behavior Complementary Development Kit
# Speech Recognition tools (alternate or ...)
# Aldebaran Robotics (c) 2010 All Rights Reserved - This file is confidential.
###########################################################
###########################################################
# Modified by Roberto Menicatti for the CARESSES project
# Universita' degli studi di Genova, DIBRIS
# roberto.menicatti@dibris.unige.it
###########################################################

import sys
sys.path.append("/data/home/nao/.local/share/PackageManager/apps/asr2/lib/otherlibs/")

import os
import io
import json
import logging
import time
import qi


from oauth2client.client import GoogleCredentials
from googleapiclient.discovery import build
import googleapiclient.errors
import googleapiclient.http

try:
    import otherlibs.speech_recognition as speech_recognition
except:
    pass

try:
    from bs4 import BeautifulSoup 
except:
    pass

from abcdk.sound import language_tools

# Define the singleton metaclass
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class FreeSpeech():
    """
    Freespeech with google
    """
    #specify that FreeSpeech is an instantiation of the metaclass Singleton
    __metaclass__ = Singleton
    
    def __init__( self, session ):
        self.session = session
        self.lt = language_tools.LanguageTools(self.session)

    def cleanText(self, rawResume):
        """ encode with bs4 for handle special character """
        soup = BeautifulSoup(rawResume)

        for script in soup(["script", "style"]):                                                
            script.extract()                                                                    
        
        text = soup.get_text()                                           
        lines = (line.strip() for line in text.splitlines())                       
        chunks = (phrase.strip() for line in lines for phrase in line.split("  ")) 
        text = '\n'.join(chunk for chunk in chunks if chunk)                  
        text = text.encode('utf-8', 'ignore')
        return text
        
    def cleanText2( self, txt ):
        try:
            txt = str(txt)
        except BaseException, err:
            logging.debug( "can't convert text to ascii?" )
            try:
                txt = self.cleanText(txt)
            except:
#                    logging.warning("freespeech : analyse : you need to install beautifulsoup4")
                #Methode with "ai"
                unicoded = unicode(txt).encode('utf8')
                logging.debug( "unicoded: %s" % unicoded )
                utxt = str(unicoded)
                logging.debug( "txt: %s" % utxt )
                txt = ""
                for c in utxt:
                    if ord(c) < 128:
                        txt += c
                    else:
                        logging.debug( "bad char: %s %d" % (c, ord(c) ) )
                        ordc = ord(c)
                        if( ordc in [168, 169, 170, 171] ):
                            txt += "ai"
                        if( ordc in [160] ):
                            txt += "a"
                        
            logging.debug( "txt2: %s" % txt )
        return txt
        

    def analyse_anonymous( self, strSoundFilename, strUseLang = "", bStoreToEvents = False ):
        """
        Send a file to the speech recognition engine.
        Return: an array [[strRecognizedText, rConfidence], [strAlternateRecognizedText, rConfidence] ...]
        or None if nothing recognized
        """
        try:
            import otherlibs.speech_recognition as speech_recognition
        except:
            logging.error( "FreeSpeech.analyse: remote free speech server is not available... (speech_recognition: is not installed on this robot ? copy some binary to the site-library" )
            return None

        #~ logging.info( "FreeSpeech.analyse: sending to speech reco '%s'" % strSoundFilename )

        strAnsiLang = ""
        if( strUseLang == "" ):
            strAnsiLang = self.lt.getSpeakLanguageAnsiCode( self.lt.getSpeakLanguage() )
            logging.debug( "After autodetection, using Lang input: %s" % strAnsiLang )
        else:
            strAnsiLang = self.lt.getSpeakLanguageAnsiCode( strUseLang )
            logging.debug( "Using Lang input: %s" % strUseLang )

        retVal = None

        timeBegin = time.time()

        r = speech_recognition.Recognizer()

        with speech_recognition.WavFile(strSoundFilename) as source:
            audio = r.record(source) # read the entire WAV file
        # recognize speech using Google Speech Recognition
        try:
            # for testing purposes, we're just using the default API key
            # if you wish to use your own key, use the following line instead:
            retFromReco = r.recognize_google(audio, language=strAnsiLang, show_all=True)
            logging.debug( "retFromReco: %s" % retFromReco )
            if retFromReco != []:

                alt = retFromReco['alternative']
                strTxt = alt[0]['transcript']

                # when reco does not return a confidence, use -1 as an error code
                if 'confidence' in alt[0]:
                    rConf = alt[0]['confidence']
                else:
                    logging.debug('no confidence returned')
                    rConf = -1.0

                # strTxt = self.cleanText2( strTxt )
                logging.info("Google Speech Recognition thinks you said: '%s' (conf:%5.2f)\n" % (strTxt, rConf) )
                retVal = [ [strTxt,rConf] ]

        except speech_recognition.UnknownValueError:
            pass

        except speech_recognition.RequestError as e:
            logging.error("Could not request results from Google Speech Recognition service; {0}".format(e))

        rProcessDuration = time.time() - timeBegin
        self.rSkipBufferTime = rProcessDuration  # if we're here, it's already to zero

        if retVal == None: logging.info("Google Speech Recognition could not understand audio\n")

        return retVal

    def analyse( self, strSoundFilename, strUseLang = "", bStoreToEvents = False ):
        """
        Send a file to the speech recognition engine.
        Return: an array [[strRecognizedText, rConfidence], [strAlternateRecognizedText, rConfidence] ...]
        or None if nothing recognized
        """
        try:
            import otherlibs.speech_recognition  as speech_recognition
        except:
            logging.error( "FreeSpeech.analyse: remote free speech server is not available... (speech_recognition: is not installed on this robot ? copy some binary to the site-library" )
            return None

        #~ logging.info( "FreeSpeech.analyse: sending to speech reco '%s'" % strSoundFilename )

        strAnsiLang = ""
        if( strUseLang == "" ):
            strAnsiLang = self.lt.getSpeakLanguageAnsiCode( self.lt.getSpeakLanguage() )
            logging.debug( "After autodetection, using Lang input: %s" % strAnsiLang )
        else:
            strAnsiLang = self.lt.getSpeakLanguageAnsiCode( strUseLang )
            logging.debug( "Using Lang input: %s" % strUseLang )

        retVal = None

        timeBegin = time.time()

        r = speech_recognition.Recognizer()

        with speech_recognition.WavFile(strSoundFilename) as source:
            audio = r.record(source) # read the entire WAV file
        # recognize speech using Google Speech Recognition
        try:
            retFromReco = r.recognize_google_cloud(audio, language=strAnsiLang, show_all=True, preferred_phrases=None)
            logging.debug( "retFromReco: %s" % retFromReco )
            if retFromReco != {}:

                alt = retFromReco['results'][0]['alternatives']
                strTxt = alt[0]['transcript']

                # when reco does not return a confidence, use -1 as an error code
                if 'confidence' in alt[0]:
                    rConf = alt[0]['confidence']
                else:
                    logging.debug('no confidence returned')
                    rConf = -1.0

                # strTxt = self.cleanText2( strTxt )
                logging.info("Google Speech Recognition thinks you said: '%s' (conf:%5.2f)\n" % (strTxt, rConf) )
                retVal = [ [strTxt,rConf] ]

        except speech_recognition.UnknownValueError:
            pass

        except speech_recognition.RequestError as e:
            logging.error("Could not request results from Google Speech Recognition service; {0}".format(e))

        rProcessDuration = time.time() - timeBegin
        self.rSkipBufferTime = rProcessDuration  # if we're here, it's already to zero

        if retVal == None: logging.info("Google Speech Recognition could not understand audio\n")

        return retVal

# def analyse( self, strSoundFilename, strUseLang="", bStoreToEvents=False ):
#     """Transcribe the given audio file."""
#     logging.info("Analysing sound file %s" % strSoundFilename)
#     try:
#         from google.cloud.speech_v1.gapic import speech_client
#         from google.cloud.speech_v1.gapic import enums
#         from google.cloud.speech_v1.proto import cloud_speech_pb2
#     except:
#         logging.error("Google cloud api is not installed. Try installing it with\
#         pip install google-cloud-speech==0.31.0")
#         return None

#     client = speech_client.SpeechClient()

#     with io.open(strSoundFilename, 'rb') as audio_file:
#         content = audio_file.read()

#     strAnsiLang = self.lt.getSpeakLanguageAnsiCode( strUseLang )

#     phrases = ['Pepper', 'hello Pepper', 'how are you Pepper']

#     audio = cloud_speech_pb2.RecognitionAudio(content=content)
#     config = cloud_speech_pb2.RecognitionConfig(
#         encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
#         sample_rate_hertz=48000,
#         language_code=strAnsiLang,
#         speech_contexts=[cloud_speech_pb2.SpeechContext(phrases=phrases)]
#         )

#     try:
#         response = client.recognize(config, audio, timeout=1)
#         print response
#     except Exception as e:
#         print e
#         return None

#     ret_val = []

#     try:
#         alternatives = response.results[0].alternatives
#         if alternatives:
#             for alternative in alternatives:
#                 when reco does not return a confidence, use -1 as an error code
#                 try:
#                     r_conf = alternative.confidence
#                 except:
#                     logging.debug('No confidence returned')
#                     r_conf = -1.0

#                 logging.info("Google Speech Recognition thinks you said: '%s' (conf:%5.2f)\n"
#                              % (alternative.transcript, r_conf))
#                 ret_val.append([alternative.transcript, r_conf])
#     except Exception as e:
#         logging.error("Google didn't recognise anything: '%s'" % e)

#     return ret_val if ret_val else None

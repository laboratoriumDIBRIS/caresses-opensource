# -*- coding: utf-8 -*-
'''
Copyright October 2019 Amélie Eugene & Roberto Menicatti & Università degli Studi di Genova

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

***

Author:      Amélie Eugene, Roberto Menicatti
Email:       roberto.menicatti@dibris.unige.it
Affiliation: Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import time
import functools

from action import Action
import caressestools.caressestools as caressestools
import caressestools.speech as speech
from aux_files.read_news_lib import cleanText, getArticle, obtainHeadsAndLinks


## Action "Read News".
#
#  Pepper reads aloud the news of the day.
class ReadNews(Action):

    ## The constructor.
    # @param self The object pointer.
    # @param apar (string) News source, news stopic; separated by a white space.
    # @param cpar (string) Volume, speed, pitch, language, username, suggestions; separated by a white space.  <b>Volume</b>, <b>speed</b> and <b>pitch</b> must be compliant with NAOqi ALTextToSpeech requirements. <b>Language</b> must be the full language name lowercase (e.g. english). <b>Suggestions</b> should be a series of IDs as listed in the related parameter file, separated by "&&".
    # @param session (qi session) NAOqi session.
    # @param asr (string) Environment noise level, either "normal" or "noisy".
    def __init__(self, apar, cpar, session, asr):
        Action.__init__(self, apar, cpar, session)

        # Parse the action parameters
        self.apar = self.apar.split(' ')

        self.source_id = self.apar[0]
        self.topic_id = self.apar[1]

        # Parse the cultural parameters
        self.cpar = self.cpar.split(' ')

        self.volume = float(self.cpar[0])
        self.speed = float(self.cpar[1])
        self.pitch = float(self.cpar[2])
        self.language = self.cpar[3].lower().replace('"', '')
        self.username = self.cpar[4].replace('"', '')
        self.suggestions = self.cpar[5].split(self.options_delimiter)

        self.source_params = self.loadParameters("news_sources.json")
        suggested_source_IDs = [option.replace('"', '') for option in self.suggestions]
        self.source_IDs = self.mergeAndSortIDs(self.source_params, suggested_source_IDs)
        self.source_options = self.getAllParametersAttributes(self.source_params, self.source_IDs, "full")

        self.topic_params = self.loadParameters("news_topics.json")
        self.topic_IDs = self.mergeAndSortIDs(self.topic_params, [])
        self.topic_options = self.getAllParametersAttributes(self.topic_params, self.topic_IDs, "full")

        # Initialize NAOqi services
        self.sMemory = self.session.service("ALMemory")
        self.sTablet = self.session.service("ALTabletService")
        self.sTts = self.session.service("ALTextToSpeech")
        self.sSpeechReco = self.session.service("ALSpeechRecognition")

        caressestools.Language.setLanguage(self.language)

        caressestools.setRobotLanguage(self.session, caressestools.Language.lang_naoqi)
        caressestools.setVoiceVolume(self.session, self.volume)
        caressestools.setVoiceSpeed(self.session, self.speed)
        caressestools.setVoicePitch(self.session, self.pitch)

        self.sp = speech.Speech("speech_conf.json", self.language)
        self.sp.enablePepperInteraction(self.session, caressestools.Settings.robotIP.encode('utf-8'))

        self.speech_source = self.__class__.__name__ + "-Source"
        self.speech_topic  = self.__class__.__name__ + "-Topic"

        self.headlines_per_time = 4
        self.paragraphs_per_time = 5

        self.is_touched = False
        self.asr=asr

    ## Method executed when the thread is started.
    def run(self):

        if not self.isAvailable(self.source_id):
            self.source_full = self.sp.dialog(self.speech_source, self.source_options, checkValidity=True,
                                              askForConfirmation=True, noisy=self.asr)
            self.source_id = self.getIDFromAttribute(self.source_params, "full", self.source_full)
            self.source_url = self.getAttributeFromID(self.source_params, self.source_id, "url-root")
            self.source_url_article = self.getAttributeFromID(self.source_params, self.source_id, "url-article")
        else:
            self.source_full = self.getAttributeFromID(self.source_params, self.source_id, "full")
            self.sp.monolog(self.speech_source, speech.WITH_KEYWORD, param={"$KEYWORD$": self.source_full},
                            group="parameter-answer", tag=speech.TAGS[1])
            self.source_url = self.getAttributeFromID(self.source_params, self.source_id, "url-root")
            self.source_url_article = self.getAttributeFromID(self.source_params, self.source_id, "url-article")

        self.links, heads = obtainHeadsAndLinks(self.source_url)

        chosen_article = None

        line_read_article   = self.sp.script[self.speech_source][speech.OTHER]["1"][self.language].encode('utf-8')
        line_next_headlines = self.sp.script[self.speech_source][speech.OTHER]["3"][self.language].encode('utf-8')
        self.line_read_aloud     = self.sp.script[self.speech_source][speech.OTHER]["4"][self.language].encode('utf-8')
        self.line_keep_reading   = self.sp.script[self.speech_source][speech.OTHER]["5"][self.language].encode('utf-8')
        self.line_another_article = self.sp.script[self.speech_source][speech.OTHER]["7"][self.language].encode('utf-8')
        lines_ok = [l.encode('utf-8') for l in self.sp.script[speech.ADDITIONAL][speech.OK][self.language]]

        ## Choose the article
        for headline_index, headline in enumerate(heads):

            if self.is_stopped:
                break
            try:
                self.sp.monolog(self.speech_source, "0", param={"$ART_NUMBER$": str(headline_index + 1), "$ART_HEAD$": unicode(headline,"utf-8")}, tag=speech.TAGS[1])
            except:
                self.sp.monolog(self.speech_source, "0", param={"$ART_NUMBER$": str(headline_index + 1), "$ART_HEAD$": headline}, tag=speech.TAGS[1])
            article_is_chosen = self.sp.askYesOrNoQuestion(line_read_article, speech.TAGS[4], noisy=self.asr)
            if article_is_chosen:
                chosen_article = headline_index
                self.showArticle(chosen_article)
                if self.is_stopped:
                    ## Exit action
                    break
                else:
                    self.again = self.sp.askYesOrNoQuestion(self.line_another_article, speech.TAGS[11], noisy=self.asr)
                    if self.again:
                        self.is_touched = False
                    else:
                        self.sp.replyAffirmative()
                        ## Exit action
                        break
            if headline_index + 1 == len(heads):
                self.sp.monolog(self.speech_source, "2", tag=speech.TAGS[1])
            elif (headline_index + 1) % self.headlines_per_time == 0:
                go_on = self.sp.askYesOrNoQuestion(line_next_headlines % self.headlines_per_time, speech.TAGS[4], noisy=self.asr)
                if go_on:
                    pass
                else:
                    self.sp.replyAffirmative()
                    break

        if not self.is_stopped:
            self.sp.askYesOrNoQuestion(
                self.sp.script[self.speech_source]["evaluation"]["0"][self.language].encode('utf-8'), speech.TAGS[3], noisy=self.asr)
            self.sp.monolog(self.speech_source, "1", group="evaluation", tag=speech.TAGS[1])


    ## Show and read the chosen article.
    #  @param chosen_article The article chosen by the user.
    def showArticle(self, chosen_article):

        if chosen_article is not None and not self.is_stopped:
            complete_url = self.source_url_article + self.links[chosen_article]
            # print complete_url
            article_body = getArticle(self.source_id, complete_url)
            if article_body is not None:
                read_aloud = self.sp.askYesOrNoQuestion(self.line_read_aloud, speech.TAGS[4], noisy=self.asr)
                self.sTablet.showWebview(complete_url)
                # Register events
                # 'TouchChanged'
                self.touch = self.sMemory.subscriber("TouchChanged")
                self.id_touch = self.touch.signal.connect(functools.partial(self.onTouch, "TouchChanged"))

                if read_aloud:
                    for period_index, period in enumerate(article_body):

                        if self.is_stopped or self.is_touched:
                            break

                        self.sp.enableAnimatedSpeech(False)
                        try:
                            self.sp.say(unicode(period, 'utf-8'), speech.TAGS[1])
                        except:
                            self.sp.say(period, speech.TAGS[1])
                        self.sp.enableAnimatedSpeech(True)
                        # print(period)

                        time.sleep(0.7)
                        if (period_index + 1) % self.paragraphs_per_time == 0 and not period_index + 1 == len(article_body):
                            time.sleep(1)
                            try:
                                #trick to check if the ALTabletService is still active
                                self.sTablet.getBrightness()
                            except:
                                self.sTablet = self.session.service("ALTabletService")
                                self.sp.enablePepperTablet(self.session)
                            go_on = self.sp.askYesOrNoQuestion(self.line_keep_reading, speech.TAGS[4], noisy=self.asr)
                            if go_on:
                                self.sTablet.showWebview(complete_url)
                                pass
                            else:
                                self.sp.replyAffirmative()
                                break
                else:
                    self.sp.replyAffirmative()
                    self.sp.monolog(self.speech_source, "6", tag=speech.TAGS[1])

                    while not self.is_stopped and not self.is_touched:
                        pass

    ## Callback
    def onTouch(self, msg, value):
        self.touch.signal.disconnect(self.id_touch)
        self.is_touched = True


if __name__ == "__main__":

    import argparse
    import qi
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default=caressestools.Settings.robotIP,
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    args = parser.parse_args()

    try:
        # Initialize qi framework.
        session = qi.Session()
        session.connect("tcp://" + args.ip + ":" + str(args.port))
        print("\nConnected to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) + ".\n")

    except RuntimeError:
        print ("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) + ".\n"
                                                                                              "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)

    caressestools.Settings.robotIP = args.ip

    # Run Action
    caressestools.startPepper(session, caressestools.Settings.interactionNode)

    apar = 'bBC "n/a"'
    cpar = "0.7 90 1.0 english John skyNews"

    action = ReadNews(apar, cpar, session, "normal")
    try:
        action.run()
    except speech.StopInteraction as e:
        print e

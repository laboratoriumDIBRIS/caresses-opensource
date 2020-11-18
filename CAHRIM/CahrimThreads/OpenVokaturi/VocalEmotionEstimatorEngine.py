# -*- coding: utf-8 -*-
'''
Copyright October 2019 Bui Ha Duong

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

Author:      Bui Ha Duong
Email:       bhduong@jaist.ac.jp
Affiliation: Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import sys
import audioop
import math

sys.path.append("./api")
import Vokaturi
import numpy as np

from collections import deque
from pyaudio import PyAudio, paInt16

Vokaturi.load("./lib/open/linux/OpenVokaturi-3-0-linux64.so")

class VocalEmotionEstimatorEngine():
    CHUNK = 2048  
    RATE = 16000
    THRESHOLD = 1500  
    SILENCE_LIMIT = 1  
    PREV_AUDIO = 0.5  

    def __init__(self):
        self.data = []
        self.audio2send = []                
        self.rel = VocalEmotionEstimatorEngine.RATE/VocalEmotionEstimatorEngine.CHUNK
        self.slid_win = deque(maxlen=VocalEmotionEstimatorEngine.SILENCE_LIMIT * self.rel)
        self.prev_audio = deque(maxlen=VocalEmotionEstimatorEngine.PREV_AUDIO * self.rel) 
        self.started = False
        self.emotion = None

    def processRemote(self, inputChannels, inputSamples, timeStamp, inputBuff):
        cur_data = inputBuff[:VocalEmotionEstimatorEngine.CHUNK]
        cur_data = str(cur_data)
        if self.started:
            self.data.append(inputBuff)
        self.slid_win.append(math.sqrt(abs(audioop.avg(cur_data, 4))))
        if(sum([x > VocalEmotionEstimatorEngine.THRESHOLD for x in self.slid_win]) > 0):
            if(not self.started):
                self.started = True
            self.audio2send.append(cur_data)
        elif (self.started is True):
            self.detectEmotion()
            # Reset all
            self.started = False
            self.slid_win = deque(maxlen=VocalEmotionEstimatorEngine.SILENCE_LIMIT * self.rel)
            self.prev_audio = deque(maxlen=0.5 * self.rel) 
            self.audio2send = []
        else:
            self.prev_audio.append(cur_data)

    def detectEmotion(self):
        sample_rate = VocalEmotionEstimatorEngine.RATE
        samples = np.fromstring(''.join(self.audio2send), dtype=np.int16)
        buffer_length = len(samples)
        c_buffer = Vokaturi.SampleArrayC(buffer_length)
        if samples.ndim == 1:  # mono
            c_buffer[:] = samples[:] / 32768.0
        else:  # stereo
            c_buffer[:] = 0.5*(samples[:,0]+0.0+samples[:,1]) / 32768.0
        voice = Vokaturi.Voice (sample_rate, buffer_length)
        voice.fill(buffer_length, c_buffer)
        quality = Vokaturi.Quality()
        emotionProbabilities = Vokaturi.EmotionProbabilities()
        voice.extract(quality, emotionProbabilities)

        if quality.valid:
            self.emotion = [emotionProbabilities.neutrality,
            emotionProbabilities.happiness,
            emotionProbabilities.sadness,
            emotionProbabilities.anger,
            emotionProbabilities.fear]
            print self.emotion

        voice.destroy()
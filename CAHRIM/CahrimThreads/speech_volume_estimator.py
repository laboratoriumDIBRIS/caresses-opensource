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

from threading import Thread
import time
import logging
import sys
import math

from SpeechVolumeAdaptation.sva_model import SVAModel

logger = logging.getLogger("CAHRIM.SpeechVolumeEstimator")

'''
Please install tensorflow, keras and keras-rl
- pip install tensorflow==1.14.0
- pip install keras==2.3.1
- pip install keras-rl==0.4.2
'''
class SpeechVolumeEstimator(Thread):
    def __init__(self, session):
        Thread.__init__(self, name="SpeechVolumeEstimator")
        self.id = "Speech Volume Estimator"

        self.session = session
        self.audio_device = session.service('ALAudioDevice')
        self.audio_device.enableEnergyComputation()
        self.memory_service = session.service("ALMemory")

        self.sva_volume = 0
        self.alive = False
        self.is_talking = False

    def get_mic_energy(self):
        audio_device = self.audio_device
        energy =  max(audio_device.getFrontMicEnergy(), audio_device.getRearMicEnergy(), audio_device.getLeftMicEnergy(), audio_device.getRightMicEnergy())
        energy =  int(math.ceil((energy / 8000.0) * 100.0))
        if energy < 0:
            energy = 0
        if energy > 100:
            energy = 100
        return energy

    def update_volume_sva(self):
        buffer_mic_energy = []
        for _ in range(10):
            buffer_mic_energy.append(self.get_mic_energy())
            time.sleep(0.1)
        svamodel = SVAModel(buffer_mic_energy)
        # logger.info("UpdateSVAThread is ready")
        logger.info("Speech Volume Estimator is ready")
        while self.alive:
            while self.is_talking:
                pass
            self.sva_volume = svamodel.get_volume(self.get_mic_energy())
            # self.audio_device.setOutputVolume(self.sva_volume)
            # print (self.sva_volume)
            time.sleep(0.1)
        # logger.info("UpdateSVAThread is shutting down")
    
    def set_volume(self, volume=None):
        if not volume:
            volume = self.sva_volume
        self.audio_device.setOutputVolume(volume)

    def run(self):
        self.alive = True
        thread_update_volume_sva = Thread(target=self.update_volume_sva, name="UpdateSVAThread")
        thread_update_volume_sva.start()
        time.sleep(5)
        # logger.info("Speech Volume Estimator is ready")
        while self.alive:
            # logger.info("Robot is running")
            time.sleep(1)
        thread_update_volume_sva.join()
        logger.info("Speech Volume Estimator terminated correctly.")
    
    def stop(self):
        self.alive = False
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

import Queue
import numpy as np
from keras.models import Sequential
from keras.layers import Dense, Activation, Flatten
from keras.optimizers import Adam

from rl.agents.dqn import DQNAgent
from rl.policy import EpsGreedyQPolicy
from rl.memory import SequentialMemory

import logging
import os

# turn off tensorflow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

logger = logging.getLogger("CAHRIM.SpeechVolumeEstimator")

class SVAModel(object):
    def __init__(self, buffer_mic_energy):
        self.dqn = None
        self.volume = None
        self.load_model()

        self.weights = np.array([0.033, 0.033, 0.033, 0.05, 0.05, 0.1, 0.1, 0.2, 0.2, 0.2])
        self.volumes = Queue.Queue()
        for mic_energy in buffer_mic_energy:
            volume = self.predict_volume(mic_energy)
            self.volumes.put(volume)

    def load_model(self):
        self.model = Sequential()
        self.model.add(Flatten(input_shape=(1,) + (101,)))
        self.model.add(Dense(64, activation='relu'))
        self.model.add(Dense(64, activation='relu'))
        self.model.add(Dense(64, activation='relu'))
        self.model.add(Dense(64, activation='relu'))
        self.model.add(Dense(21, activation='linear'))

        memory = SequentialMemory(limit=300000, window_length=1)
        policy = EpsGreedyQPolicy(eps=0.5)
        self.dqn = DQNAgent(model=self.model, nb_actions=21, memory=memory, nb_steps_warmup=100,
                    target_model_update=10000, policy=policy, enable_double_dqn=True, enable_dueling_network=True)
        self.dqn.compile(Adam(lr=1e-3), metrics=['mae'])

        path = os.path.abspath(os.path.dirname(__file__))
        path = path + '/model_sva_weights.h5f'

        self.dqn.load_weights(path)

    def predict_volume(self, mic_energy):
        one_hot = np.zeros(101)
        one_hot[mic_energy] = 1
        input_vector = one_hot.reshape(1,1,101)
        output_vector = self.dqn.model.predict(input_vector)
        volume = int(np.argmax(output_vector) * 5)
        if (volume > 90):
            volume = 90
        return volume

    def get_volume(self, mic_energy):        
        current_volume = self.predict_volume(mic_energy)
        self.volumes.get()
        self.volumes.put(current_volume)

        volumes = np.array(list(self.volumes.queue))
        weights = self.weights
        volume = volumes * weights
        volume = int(np.sum(volume))

        # logger.debug(volumes)
        # logger.info(volume)

        return volume
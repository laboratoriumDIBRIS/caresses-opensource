# -*- coding: utf-8 -*-
'''
Copyright October 2019 Roberto Menicatti & Università degli Studi di Genova

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

Author:      Roberto Menicatti
Email:       roberto.menicatti@dibris.unige.it
Affiliation: Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import time

from caressestools import setAutonomousAbilities, fromAutonomousLifeToAwake, Settings, Language

SPEECH_RECO_EVENT = "Audio/RecognizedWords"

class TestAsr:

	def __init__(self, session, useGoogleKey):
		self.session = session
		self.useGoogleKey = useGoogleKey

		## These two functions are just to start some autonomous abilities and see the effect of Pepper disabling them
		## when starting speech recognition if the blockHead parameter of startReco(language, useGoogleKey, blockHead) 
		## is set to True. The ASR2 will automatically reset the abilities to their previous value when stopReco() is called.
		fromAutonomousLifeToAwake(self.session)
		setAutonomousAbilities(self.session, False, True, True, True, True)

		self.sAsr = self.session.service("ASR2")
		self.sMemory = self.session.service("ALMemory")

		Language.setLanguage("english")

		self.block_head_motion = True

		## If using new Google Cloud Platform API...
		if self.useGoogleKey:
			## COMPULSORY - Set Google credentials
			self.sAsr.setGoogleCredentials(Settings.googlekey)
			## OPTIONAL - Set extra sentences
			phrases = ["CARESSES", "Pepper"]
			self.sAsr.setPreferredPhrases(phrases)

	def run(self):

		## Start recognition
		self.sAsr.startReco(Language.lang_naoqi, self.useGoogleKey, self.block_head_motion)

		try:
			while True:
				print self.sMemory.getData(SPEECH_RECO_EVENT)
				time.sleep(0.2)
		except KeyboardInterrupt:
			## Stop recognition
			self.sAsr.stopReco()


if __name__ == "__main__":

	import argparse
	import qi
	import sys

	parser = argparse.ArgumentParser()
	parser.add_argument("--ip", type=str, default=Settings.robotIP,
						help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
	parser.add_argument("--port", type=int, default=9559,
						help="Naoqi port number")
	parser.add_argument("--useGoogleKey", "-u", action='store_true',
                        help="Use Google Cloud Platform")

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

	t = TestAsr(session, args.useGoogleKey)
	t.run()

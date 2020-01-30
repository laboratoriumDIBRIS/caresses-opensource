# -*- coding: utf-8 -*-
'''
Copyright October 2019 Japan Advanced Institute of Science and Technology

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

import sqlite3

db = sqlite3.connect('youtube-history-db.sqlite', check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE yt_history (id TEXT PRIMARY KEY, last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP, stop_seconds REAL DEFAULT 0.0)")

db.commit()
db.close()

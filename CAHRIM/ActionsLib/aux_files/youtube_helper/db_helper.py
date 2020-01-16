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

import sqlite3
import os

INSERT_SQL = "INSERT INTO yt_history (id) VALUES ('{id}')"
UPDATE_BY_ID = "UPDATE yt_history SET last_modified=CURRENT_TIMESTAMP, stop_seconds={stop_seconds} WHERE id='{id}'"
GET_ALL_SQL = "SELECT * FROM yt_history"
GET_BY_ID_SQL = "SELECT * FROM yt_history WHERE id='{id}'"

class DatabaseHelper(object):
    def __init__(self):
        path = os.path.abspath(os.path.dirname(__file__))
        path = path + '/youtube-history-db.sqlite'
        self.db = sqlite3.connect(path, check_same_thread=False)

    def insert(self, id):
        cursor = self.db.cursor()
        try:
            cursor.execute(INSERT_SQL.format(id=id))
        except sqlite3.IntegrityError as sql_ex:
            print sql_ex
        except Exception as ex:
            print ex
        finally:
            self.db.commit()

    def update_by_id(self, id, stop_seconds):
        cursor = self.db.cursor()
        try:
            cursor.execute(UPDATE_BY_ID.format(stop_seconds=stop_seconds, id=id))
        except Exception as ex:
            print ex
        finally:
            self.db.commit()

    def get_by_id(self, id):
        cursor = self.db.cursor()
        cursor.execute(GET_BY_ID_SQL.format(id=id))
        row = cursor.fetchone()
        if row:
            return row
        else:
            return None

    def get_all(self):
        cursor = self.db.cursor()
        cursor.execute(GET_ALL_SQL)
        all_rows = cursor.fetchall()
        if all_rows:
            print all_rows
        else:
            print 'No data'

    def get_start_seconds(self, id):
        target = self.get_by_id(id)
        start_seconds = 0
        if target:
            start_seconds = target[2]
        # else:
        #     self.insert(id)
        return start_seconds

    def update_stop_seconds(self, id, stop_seconds):
        target = self.get_by_id(id)
        if not target:
            self.insert(id)
        self.update_by_id(id, stop_seconds)

    def close(self):
        self.db.close()

if __name__ == '__main__':
    db = DatabaseHelper()

    # db.insert('EqPtz5qN7HM')
    # db.insert('123456')
    # db.get_all()
    # db.get_by_id('123456')
    # db.get_by_id('1234567')

    # db.update_by_id(1234567, 100)
    # db.get_all()

    # db.update_by_id('123456', 200)
    db.get_all()

    db.close()

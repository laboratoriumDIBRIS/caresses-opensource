import timeit
import time
import os
import logging
import mysql.connector
from mysql.connector import errorcode
from threading import Thread
from datetime import datetime
from datetime import timedelta

import ActionsLib.caressestools.caressestools as caressestools


log_ra = logging.getLogger('CAHRIM.Activity&LocationRecognition')


class ActivityAndLocationRecognition(Thread):

    def __init__(self, output_handler):
        Thread.__init__(self)
        self.id = "User Behaviour Analysis - Activity and Location Recognition"
        self.alive = True
        self.output_handler = output_handler # Output handler for sending messages

        self.cnx = []
        self.folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ActivityAndLocationRecognition")

        self.database_info = caressestools.Settings.databaseInfo
        self.layout = caressestools.Settings.databaseLayout

        self.config = {
            'user': caressestools.Settings.databaseUser,
            'password': caressestools.Settings.databasePassword,
            'host': caressestools.Settings.databaseHost,
            'database': self.database_info,
            'raise_on_warnings': True,
        }

        try:
            self.cnx = mysql.connector.connect(**self.config)
            self.cnx.autocommit = True
            self.connected = True
        except mysql.connector.Error as err:
            self.connected = False

            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                log_ra.error("Something is wrong with your user name or password.")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                log_ra.error("Database does not exist.")
            else:
                log_ra.error(err)

            log_ra.warning("Thread '%s' will terminate immediately." % self.id)

        if self.connected:

            self.cursor = self.cnx.cursor(dictionary=True)

            # reading activity info file which contains the description of the activity-intention
            activityInfoFile = open(os.path.join(self.folder, "activityInfo_" + self.layout + ".txt"), "r")
            self.activityInfoMatrix = []
            activityInfoFile.readline()  # first line only have the labels

            for line in activityInfoFile:
                if not line.strip(): continue
                self.activityInfoMatrix.append(line.split(":", 1)[1].replace("\n", ""))

            # reading conditional file into conditional conditionalMatrix
            conditionalFile = open(os.path.join(self.folder, "conditionalFile_" + self.layout + ".txt"), "r")
            self.conditionalMatrix = []
            conditionalFile.readline()  # first line only have the labels

            for line in conditionalFile:
                if not line.strip(): continue
                self.conditionalMatrix.append(line.split(":", 1)[1].replace("\n", ""))

            #reading location info file
            locationInfo = open(os.path.join(self.folder, "locationInfo_" + self.layout + ".txt"), "r")
            self.locationSensorNumber = []
            self.locationName = []
            locationInfo.readline() #first line only have the labels
            self.userLocation = "n/a"
            self.activity = "n/a"

            for line in locationInfo:
                if not line.strip(): continue
                self.locationSensorNumber.append(line.split(":",1)[0].replace("\n",""))
                self.locationName.append(line.split(":",1)[1].replace("\n",""))
            

    def run(self):

        if self.connected:

            while self.alive:
                # start activity recognition part

                # start query time
                time_t0 = timeit.default_timer()

                todaydetail = datetime.today()
                end_frame = todaydetail.strftime("%H:%M:%S:%f")[:-7]
                day = str(todaydetail.year) + "-" + str(todaydetail.month) + "-" + str(todaydetail.day)

                # building the activity frame based in the output
                activity_frame_size = 5
                (end_frame_h, end_frame_m, end_frame_s) = end_frame.split(':')
                end_frame_timedelta = timedelta(hours=int(end_frame_h), minutes=int(end_frame_m), seconds=int(end_frame_s))

                start_frame = end_frame_timedelta - timedelta(seconds=activity_frame_size)
                activity_frame = "( time >= '" + str(start_frame) + "' and time <= '" + str(end_frame) + "' )";
                mysql_command = (
                        "select * from " + self.database_info + ".envstatus_" + self.layout + " where date='" + str(
                    day) + "' and time='" + str(start_frame) + "'")

                try:
                    self.cursor.execute(mysql_command)
                    rows = self.cursor.fetchall()
                    desc = self.cursor.description
                except mysql.connector.Error as err:
                    log_ra.error(err)

                var_info = "date,time"
                for c in range(2, len(desc)):
                    var_info = var_info + ",AVG(" + desc[c][0] + ")"

                # query end time
                time_t1 = timeit.default_timer()
                time_deltat = time_t1 - time_t0
                n_condition = 0
                for condition in self.conditionalMatrix:
                    # check if the condition for the current index activity-intention is present inside the activity frame
                    mysql_command = "select " + var_info + " from " + self.database_info + ".envstatus_" + self.layout + " where date='" + day + "' and " + activity_frame + " having " + condition + " order by time"
                    n_condition = n_condition + 1
                    try:
                        self.cursor.execute(mysql_command)
                    except mysql.connector.Error as err:
                        log_ra.error(err)

                    if (len(self.cursor.fetchall()) >= 1):
                        # insert the recognized activity into activity database
                        mysql_command = "INSERT INTO " + self.database_info + ".activity_" + self.layout + " (date, time, activityID) VALUES ('" + day + "', '" + end_frame + "', " + str(
                            n_condition) + ");"
                        try:
                            self.cursor.execute(mysql_command)
                        except mysql.connector.Error as err:
                            log_ra.error(err)

                        self.activity = self.activityInfoMatrix[n_condition - 1]
                        break
                    else:
                        self.activity = "n/a"

                #location tracking
                locationTracking_i = 0
                self.userLocation = "n/a"
                for locationTracking in self.locationSensorNumber:

                    mysql_command = "select AVG("+locationTracking+") from "+self.database_info+".envstatus_"+self.layout+" where date='"+day+"' and " + activity_frame +"  order by time ;"
                    try:
                        self.cursor.execute(mysql_command)
                        resultSetLocation = self.cursor.fetchall()
                    except mysql.connector.Error as err:
                        log_ra.error(err)

                    for resultSet in resultSetLocation:
                        resultSet = ((str(resultSet).replace("{", "")).replace("}", "")).split(":",1)[1]
                        if ( ("None" in resultSet) ):
                            self.userLocation = "n/a"
                            break
                        if (float(resultSet) > 0):
                            self.userLocation = str(self.locationName[locationTracking_i])

                        locationTracking_i = locationTracking_i + 1
                #end of location tracking

                # Send D6.1 message containing the recognized activity and the position of the user
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S.000", time.localtime())
                message_D6_1 = "[{(time %s)(activity %s)(position %s)}]" % (timestamp, self.activity.lower(), self.userLocation.lower())
                self.output_handler.writeSupplyMessage("publish", "D6.1", message_D6_1)

                # wait 1 second until next loop
                while time_deltat < 1:
                    time_t1 = timeit.default_timer()
                    time_deltat = time_t1 - time_t0

                # end of the activity recognition part

        log_ra.info("%s terminated correctly." % self.id)

    def stop(self):
        self.alive = False

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

import json
import os
import re
import datetime
import calendar

## Constants

DATE_AS_STRING = "date-as-string"
TIME_AS_STRING = "time-as-string"
DAY_DELIMITER = "day-delimiter"
DATE_ADVERBS = "date-adverbs"
WEEKDAY = "weekday"
DAY = "day"
MONTH = "month"
MONTHS = "months"
YEAR = "year"
DAY_MONTH_YEAR = "day-month-year"
MONTH_YEAR = "month-year"
DAY_MONTH = "day-month"
PREPOSITION = "preposition"
TODAY = "today"
TOMORROW = "tomorrow"
DAY_AFTER_TOMORROW = "day-after-tomorrow"
YESTERDAY = "yesterday"
DAY_BEFORE_YESTERDAY = "day-before-yesterday"

##----------------------------------------------------------------------------------------------------------------------

class Date():
    '''A class to represent unique and recurrent dates.

    Unique dates are unambiguous expressions of a certain period: year, year + month, year + month + day
    Recurrent dates are: month + day, month, day, weekday.
    There exist many class methods as "constructors" for this class according to the type of date desired.
    Missing date elements are set to None. This class can be used in place of datetime.date when it is required
    to express an incomplete, but still meaningful, date.
    '''
    def __str__(self):
        y = str(self.year) if self.year is not None else "YYYY"
        m = str(self.month) if self.month is not None else "MM"
        d = str(self.day) if self.day is not None else "DD"
        wd = str(self.weekday) if self.weekday is not None else "wd"
        fmt = "%s-%s-%s, %s" % (y, m, d, wd)
        return fmt

    def __init__(self):
        self.year = None
        self.month = None
        self.day = None
        self.weekday = None

    @classmethod
    def asFullDate(cls, year, month, day):
        pydate = datetime.date(year, month, day)
        date = Date()
        date.year = year
        date.month = month
        date.day = day
        date.weekday = pydate.isoweekday()
        return date

    @classmethod
    def asYearAndMonth(cls, year, month):
        assert isinstance(year, int)
        assert isinstance(month, int)
        assert year in range(0, 9999), "Well... do you really need a date so far in time?"
        assert month in range(1, 13), "Month out of range 1 ... 12"
        date = Date()
        date.year = year
        date.month = month
        return date

    @classmethod
    def asYear(cls, year):
        assert isinstance(year, int)
        assert year in range(0, 9999), "Well... do you really need a date so far in time?"
        date = Date()
        date.year = year
        return date

    ## Recurrent dates

    @classmethod
    def asMonthAndDay(cls, month, day):
        assert isinstance(month, int)
        assert isinstance(day, int)
        assert month in range(1, 13), "Month out of range 1 ... 12"
        if month in [1, 3, 5, 7, 8, 10, 12]:
            assert day in range(1, 32), "Day out of range for month %d: 1 ... 31" % month
        elif month in [4, 6, 9, 11]:
            assert day in range(1, 31), "Day out of range for month %d: 1 ... 30" % month
        elif month == 2:
            assert day in range(1, 30), "Day out of range for month %d: 1 ... 29" % month

        date = Date()
        date.month = month
        date.day = day
        return date

    @classmethod
    def asMonth(cls, month):
        assert isinstance(month, int)
        assert month in range(1, 13), "Month out of range 1 ... 12"
        date = Date()
        date.month = month
        return date

    @classmethod
    def asDay(cls, day):
        assert isinstance(day, int)
        assert day in range(1, 32), "Day out of range 1 ... 31"
        date = Date()
        date.day = day
        return date

    @classmethod
    def asWeekday(cls, weekday):
        assert isinstance(weekday, int)
        assert weekday in range(1, 8), "Weekday out of range 1 (monday) ... 7 (sunday)"
        date = Date()
        date.weekday = weekday
        return date

    ##----------

    @classmethod
    def asList(cls, list):

        if list[0] is not None:
            if list[1] is not None:
                if list[2] is not None:
                    return Date.asFullDate(list[0], list[1], list[2])
                else:
                    return Date.asYearAndMonth(list[0], list[1])
            else:
                return Date.asYear(list[0])
        else:
            if list[1] is not None:
                if list[2] is not None:
                    return Date.asMonthAndDay(list[1], list[2])
                else:
                    return Date.asMonth(list[1])
            else:
                if list[2] is not None:
                    return Date.asDay(list[2])
                else:
                    if list[3] is not None:
                        return Date.asWeekday(list[3])
                    else:
                        return Date()

    def toList(self):
        return [self.year, self.month, self.day, self.weekday]


class TimeDateParser():
    '''A class to retrieve from a string time and date expressed as human-like expressions.

    The configuration file "timedateparser_conf.json" can be extended to be valid for other languages.
    All the fields must be present for the added language.
    '''

    def __init__(self, lang):

        self._lang = lang.lower()
        self._conf = None
        self._loadConfFromFile("timedateparser_conf.json")
        self._supported_languages = self._conf[WEEKDAY].keys()

        assert self._lang in self._supported_languages, "Language '%s' is not supported." % self._lang

        self.regex_24h = r"(\D|^)((0?[0-9]|1[0-9]|2[0-4])(:|\.)([0-5]\d?))"
        self.regex_12h = r"(\D|^)((0?[1-9]|1[0-2])(:|\.)([0-5]\d) (p|P|a|A)\.?(m|M)\.?)"
        self.regex_oclock = r"(\D|^)((0?[1-9]|1[0-2])\s?o\'\s?clock)"
        self.regex_24h_short = r"(\D|^)(2[0-4]|1[0-9]|0?[0-9])(\D|$)"
        self.regex_12h_short = r"(\D|^)((0?[1-9]|1[0-2])\s*(p|P|a|A)\.?(m|M)\.?)"

        self.regex_weekday_lang = self._conf[WEEKDAY][self._lang]
        self.regex_WEEKDAY = self._composeORRegex(self.regex_weekday_lang)

        self.regex_day_number = r"(3[0-1]|[1-2][0-9]|0?[1-9])"
        self.regex_day_delimiter_lang = self._conf[DAY_DELIMITER][self._lang]
        self.regex_day_delimiter = r"(" + self.regex_day_delimiter_lang + r")"
        self.regex_DAY = r"(\D|^)" + self.regex_day_number + self.regex_day_delimiter + r"?(\D|$)"

        self.regex_months_number = r"(1[0-2]|0?[1-9])"
        self.regex_months_lang = self._conf[MONTHS][self._lang]
        self.regex_MONTHS = self._composeORRegex(self.regex_months_lang)

        self.regex_preposition_lang = self._conf[PREPOSITION][self._lang]
        self.regex_preposition = r"(" + self.regex_preposition_lang + r")"

        self.regex_year = r"(\d{4})"
        self.regex_year_short = r"(\d{2})" # TODO add to numeric date
        self.regex_YEAR = r"(\D|^)" + self.regex_year + r"(\D|$)"

        self.regex_date_delimiter = r"(\-|\\|\/|\.)"

        self.regex_WEEKDAY_DAY = self.regex_WEEKDAY + r",?\s*" + self.regex_day_number + self.regex_day_delimiter + r"?(\s|$)"
        self.regex_DAY_MONTH = r"(\D|^)" + self.regex_day_number + self.regex_day_delimiter + r"?\s*(" + self.regex_preposition + r"\s?)?" + self.regex_MONTHS
        self.regex_MONTH_DAY = self.regex_MONTHS + r",?\s*" + self.regex_day_number + self.regex_day_delimiter + r"?(\D|$)"
        self.regex_MONTH_YEAR = self.regex_MONTHS + r"\s*(" + self.regex_preposition + r"\s?)?,?\s?" + self.regex_year
        self.regex_WEEKDAY_DAY_MONTH = self.regex_WEEKDAY + r",?\s*" + self.regex_DAY_MONTH
        self.regex_WEEKDAY_MONTH_DAY = self.regex_WEEKDAY + r",?\s*" + self.regex_MONTH_DAY
        self.regex_DAY_MONTH_YEAR = self.regex_DAY_MONTH + r"\s*(" + self.regex_preposition + r"\s?)?,?\s?" + self.regex_year
        self.regex_MONTH_DAY_YEAR = self.regex_MONTH_DAY + r"(,\s*|\s*)" + r"\s*(" + self.regex_preposition + r"\s?)?,?\s?" + self.regex_year
        self.regex_WEEKDAY_DAY_MONTH_YEAR = self.regex_WEEKDAY_DAY_MONTH + r"\s*(" + self.regex_preposition + r"\s?)?,?\s?" + self.regex_year
        self.regex_WEEKDAY_MONTH_DAY_YEAR = self.regex_WEEKDAY_MONTH_DAY + r"(,\s*|\s*)" + r"\s*(" + self.regex_preposition + r"\s?)?" + self.regex_year

        self.regex_NUMERIC_DAY_MONTH_YEAR = r"(\D|^)" + self.regex_day_number + self.regex_date_delimiter + self.regex_months_number + self.regex_date_delimiter + self.regex_year
        self.regex_NUMERIC_MONTH_DAY_YEAR = r"(\D|^)" + self.regex_months_number + self.regex_date_delimiter + self.regex_day_number + self.regex_date_delimiter + self.regex_year

    def _loadConfFromFile(self, filename):
        '''
        Load configuration (language-dependent expressions) from an external json file. If <filename> is an absolute path
        to an existing file, open it, if it is not try looking for it in the same directory of this script.
        :param str filename: name or absolute path of the json file
        '''
        if os.path.isfile(filename):
            conf = filename
        else:
            conf = os.path.join(os.path.dirname(__file__), filename)
            if not os.path.isfile(conf):
                raise Exception, "File cannot be found: %s" % filename
        with open(conf) as f:
            self._conf = json.load(f)

    def _loadConfFromDict(self, dict):
        '''
        Load configuration (language-dependent expressions) from a dictionary.
        :param dict dict: configuration dictionary
        '''
        self._conf = dict

    def _composeORRegex(self, elements):
        '''
        Compose a regular-expression of mutually exclusive expressions (<elements>).
        :param list of str elements: expressions to be joined by OR regex
        :return: the raw string of the regular expression
        :rtype: str
        '''
        regexOR = r"("
        for index, element in enumerate(elements):
            if not index == len(elements) - 1:
                add = r"|"
            else:
                add = r")"
            regexOR = regexOR + element + add
        return regexOR

    def _getPossibleDay(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Look for any single or pair of digits.
        :param str line: line to parse
        :return: the digits found
        :rtype: str
        '''
        match = re.search(self.regex_DAY, line, re.IGNORECASE | re.UNICODE)
        if match is None:
            return None
        else:
            return [match.group(2)]

    def _getPossibleYear(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Look for any group of 4 digits.
        :param str line: line to parse
        :return: the digits found
        :rtype: str
        '''
        match = re.search(self.regex_YEAR, line, re.IGNORECASE | re.UNICODE)
        if match is None:
            return None
        else:
            return [match.group(2)]

    def _getDayAndMonth(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Parse a line to look for day and month.
        :param str line: line to parse
        :return: day and month in the format ['DD' or 'D', <month>]
        :rtype: list of str
        '''
        match = re.search(self.regex_DAY_MONTH, line, re.IGNORECASE | re.UNICODE)
        if match is None:
            match = re.search(self.regex_MONTH_DAY, line, re.IGNORECASE | re.UNICODE)
            if match is None:
                return None
            else:
                return [match.group(2), match.group(1)]
        else:
            return [match.group(2), match.group(6)]

    def _getMonthAndYear(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Parse a line to look for month and year (there must be no day in between).
        :param str line: line to parse
        :return: month and year in the format [<month>, 'YYYY']
        :rtype: list of str
        '''
        match = re.search(self.regex_MONTH_YEAR, line, re.IGNORECASE | re.UNICODE)
        if match is None:
            return None
        else:
            return [match.group(1), match.group(4)]

    def _getDayAndMonthAndYear(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Parse a line to look for day, month and year.
        :param str line: line to parse
        :return: day and month and year in the format ['DD' or 'D', <month>, 'YYYY']
        :rtype: list of str
        '''
        match = re.search(self.regex_DAY_MONTH_YEAR, line, re.IGNORECASE | re.UNICODE)
        if match is None:
            match = re.search(self.regex_MONTH_DAY_YEAR, line, re.IGNORECASE | re.UNICODE)
            if match is None:
                return None
            else:
                return [match.group(2), match.group(1), match.group(8)]
        else:
            return [match.group(2), match.group(6), match.group(9)]

    def _getWeekdayAndDay(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Parse a line to look for weekday and day.
        :param str line: line to parse
        :return: weekday and day in the format ['wd', 'DD' or 'D']
        :rtype: list of str
        '''
        match = re.search(self.regex_WEEKDAY_DAY, line, re.IGNORECASE | re.UNICODE)
        if match is None:
            return None
        else:
            return [match.group(1), match.group(2)]

    def _getWeekdayAndDayAndMonth(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Parse a line to look for weekday, day and month.
        :param str line: line to parse
        :return: weekday, day and month in the format ['wd, 'DD' or 'D', <month>]
        :rtype: list of str
        '''
        match = re.search(self.regex_WEEKDAY_DAY_MONTH, line, re.IGNORECASE | re.UNICODE)
        if match is None:
            match = re.search(self.regex_WEEKDAY_MONTH_DAY, line, re.IGNORECASE | re.UNICODE)
            if match is None:
                return None
            else:
                return [match.group(1), match.group(3), match.group(2)]
        else:
            return [match.group(1), match.group(3), match.group(7)]

    def _getWeekdayAndDayAndMonthAndYear(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Parse a line to look for weekday, day, month and year.
        :param str line: line to parse
        :return: weekday, day, month and year in the format ['wd', 'DD' or 'D', <month>, 'YYYY']
        :rtype: list of str
        '''
        match = re.search(self.regex_WEEKDAY_DAY_MONTH_YEAR, line, re.IGNORECASE | re.UNICODE)
        if match is None:
            match = re.search(self.regex_WEEKDAY_MONTH_DAY_YEAR, line, re.IGNORECASE | re.UNICODE)
            if match is None:
                return None
            else:
                return [match.group(1), match.group(3), match.group(2), match.group(9)]
        else:
            return [match.group(1), match.group(3), match.group(7), match.group(10)]

    def lookForDateAdverbs(self, line):
        '''
        Look for date adverbs in the sentence and return the corresponding date.
        :param str line: line to parse
        :return: a timedateparser.Date object if a date is found, None otherwise
        :rtype: Date
        '''
        today = datetime.datetime.now()
        line = line.lower()

        if self._conf[DATE_ADVERBS][TODAY][self._lang] in line:
            date = today
        elif self._conf[DATE_ADVERBS][DAY_AFTER_TOMORROW][self._lang] in line:
            date = today + datetime.timedelta(days=2)
            date = datetime.date(date.year, date.month, date.day)
        elif self._conf[DATE_ADVERBS][DAY_BEFORE_YESTERDAY][self._lang] in line:
            date = today - datetime.timedelta(days=2)
            date = datetime.date(date.year, date.month, date.day)
        elif self._conf[DATE_ADVERBS][TOMORROW][self._lang] in line:
            date = today + datetime.timedelta(days=1)
            date = datetime.date(date.year, date.month, date.day)
        elif self._conf[DATE_ADVERBS][YESTERDAY][self._lang] in line:
            date = today - datetime.timedelta(days=1)
            date = datetime.date(date.year, date.month, date.day)
        else:
            return None

        return Date.asFullDate(date.year, date.month, date.day)

    def getWeekday(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Find weekday in line.
        :param str line: line to parse
        :return: the integer corresponding to the day of the week according to ISO-8601 if present, None otherwise
        :rtype: int
        '''
        finders = [self._getWeekdayAndDayAndMonthAndYear, self._getWeekdayAndDayAndMonth, self._getWeekdayAndDay]
        for finder in finders:
            date = finder(line)
            if date is not None:
                return self.weekdayStringToNumeric(date[0])
        match = re.search(self.regex_WEEKDAY, line, re.IGNORECASE | re.UNICODE)
        if match is not None:
            return self.weekdayStringToNumeric(match.group(1))
        else:
            return None
        
    def getDay(self, line, forceResearch=False): #TODO make it valid for multiple dates in the same line
        '''
        Find day in line. If forceResearch is set to False, days on their own like "on the 12th" are not detected as it
        cannot be guaranteed that the number refers to a date e.g. "on the 12th month of the year".
        :param str line: line to parse
        :param bool forceResearch: if True, look for any single or pair of digits
        :return: the integer corresponding to the day of the month according to ISO-8601 if present, None otherwise
        :rtype: int
        '''
        finders = [self._getWeekdayAndDayAndMonthAndYear, self._getWeekdayAndDayAndMonth, self._getWeekdayAndDay]
        for finder in finders:
            date = finder(line)
            if date is not None:
                return int(date[1])
        date = self._getDayAndMonth(line)
        if date is not None:
            return int(date[0])
        if forceResearch:
            date = self._getPossibleDay(line)
            if date is not None:
                return int(date[0])
        return None

    def getMonth(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Find month (in word form) in line.
        :param str line: line to parse
        :return: the integer corresponding to the month according to ISO-8601 if present, None otherwise
        :rtype: int
        '''
        finders = [self._getWeekdayAndDayAndMonthAndYear, self._getWeekdayAndDayAndMonth]
        for finder in finders:
            date = finder(line)
            if date is not None:
                return self.monthStringToNumeric(date[2])
        date = self._getMonthAndYear(line)
        if date is not None:
            return self.monthStringToNumeric(date[0])
        match = re.search(self.regex_MONTHS, line, re.IGNORECASE | re.UNICODE)
        if match is not None:
            return self.monthStringToNumeric(match.group(1))
        else:
            return None

    def getYear(self, line, forceResearch=False): #TODO make it valid for multiple dates in the same line
        '''
        Find year in line. If forceResearch is set to False, years on their own like "on 2018" are not detected as it
        cannot be guaranteed that the number refers to a date e.g. "I've climbed a mountain 2018 meters high".
        :param str line: line to parse
        :param bool forceResearch: if True, look for any group of 4 digits
        :return: the integer corresponding to the year according to ISO-8601 if present, None otherwise
        :rtype: int
        '''
        date = self._getWeekdayAndDayAndMonthAndYear(line)
        if date is not None:
            return int(date[3])
        date = self._getDayAndMonthAndYear(line)
        if date is not None:
            return int(date[2])
        date = self._getMonthAndYear(line)
        if date is not None:
            return int(date[1])
        if forceResearch:
            date = self._getPossibleYear(line)
            if date is not None:
                return int(date[0])
        return None

    def getDate(self, line): #TODO make it valid for multiple dates in the same line
        '''
        Get a date expressed in words in a sentence. It returns a timedateparser.Data object where the year, the month,
        the day and the weekday numbered according to ISO-8601. If one of these data cannot be found, its value is
        returned as None.
        :param str line: line to parse
        :return: a timedateparser.Date object
        :rtype: Date
        '''

        date = self.lookForDateAdverbs(line)
        if date is None:
            date = self._getWeekdayAndDayAndMonthAndYear(line)
            if date is None:
                date = self.getNumericDate(line, dayBeforeMonth=True)
                if date is None:
                    try:
                        date = Date.asList([self.getYear(line), self.getMonth(line), self.getDay(line), self.getWeekday(line)])#[self.getYear(line), self.getMonth(line), self.getDay(line), self.getWeekday(line)]
                    except (ValueError, AssertionError) as e:
                        raise e
            else:
                try:
                    date = Date.asList([int(date[3]), self.monthStringToNumeric(date[2]), int(date[1]), self.weekdayStringToNumeric(date[0])])#[int(date[3]), self.monthStringToNumeric(date[2]), int(date[1]),  self.weekdayStringToNumeric(date[0])]
                except (ValueError, AssertionError) as e:
                    raise e

        return date

    def getNumericDate(self, line, dayBeforeMonth=None):
        #TODO make it valid for multiple dates in the same line
        '''
        Parse a line to look for a date in numeric format 'DD/MM/YYYY' or 'MM/DD/YYYY', with different possibles
        date delimiters (\, /, -, .). It returns the found date: if not specified by the parameter dayBeforeMonth, and
        if it is not possible to distinguish the day from the month (both are minor or equal 12), two possible dates are
        returned.
        :param str line: line to parse
        :param bool dayBeforeMonth: True if the date to look for is ordered 'DD MM YYYY', False if ordered 'MM DD YYYY'
        :return: a timedateparser Date object if a date is found, None otherwise
        :rtype: Date
        '''
        match_1 = re.search(self.regex_NUMERIC_DAY_MONTH_YEAR, line)
        match_2 = re.search(self.regex_NUMERIC_MONTH_DAY_YEAR, line)

        if match_1 is not None and match_2 is None:
            d = [int(match_1.group(6)), int(match_1.group(4)), int(match_1.group(2))]
            return Date.asFullDate(d[0], d[1], d[2])
        elif match_1 is None and match_2 is not None:
            d = [int(match_2.group(6)), int(match_2.group(2)), int(match_2.group(4))]
            return Date.asFullDate(d[0], d[1], d[2])
        elif match_1 is not None and match_2 is not None:
            if dayBeforeMonth is True:
                d = [int(match_1.group(6)), int(match_1.group(4)), int(match_1.group(2))]
                return Date.asFullDate(d[0], d[1], d[2])
            elif dayBeforeMonth is False:
                d = [int(match_2.group(6)), int(match_2.group(2)), int(match_2.group(4))]
                return Date.asFullDate(d[0], d[1], d[2])
            else:
                d1 = [int(match_1.group(6)), int(match_1.group(4)), int(match_1.group(2))]
                d2 = [int(match_2.group(6)), int(match_2.group(2)), int(match_2.group(4))]
                return Date.asFullDate(d1[0], d1[1], d1[2]), Date.asFullDate(d2[0], d2[1], d2[2])
        else:
            return None

    def getTime(self, line):
        '''
        Parse a line to look for the time, expressed in different possible formats (12h clock, 24h clock, "o'clock" expressions).
        :param str line: line to parse
        :return: a list containing (1) the time as string as it is retrieved in the sentence, and (2) a datetime.time
        object of the retrieved time
        :rtype: (str, datetime.time)
        '''

        matches = re.finditer(self.regex_12h, line, re.IGNORECASE | re.UNICODE)
        times = []
        for match in matches:
            full = match.group(2)
            hh = int(match.group(3))
            if "p" in full and hh != 12:
                hh += 12
            if "a" in full and hh == 12:
                hh = 0
            MM = 0 if match.group(5) is None else int(match.group(5))
            times.append([full, datetime.time(hh, MM)])
        if len(times) is not 0: return times

        matches = re.finditer(self.regex_24h, line, re.IGNORECASE | re.UNICODE)
        times = []
        for match in matches:
            full = match.group(2)
            hh = int(match.group(3))
            MM = 0 if match.group(5) is None else int(match.group(5))
            times.append([full, datetime.time(hh, MM)])
        if len(times) is not 0: return times

        matches = re.finditer(self.regex_oclock, line, re.IGNORECASE | re.UNICODE)
        times = []
        for match in matches:
            full = match.group(2)
            hh = int(match.group(3))
            MM = 0
            times.append([full, datetime.time(hh, MM)])
        if len(times) is not 0: return times

        matches = re.finditer(self.regex_12h_short, line, re.IGNORECASE | re.UNICODE)
        times = []
        for match in matches:
            full = match.group(2)
            hh = int(match.group(3))
            if "p" in full and hh != 12:
                hh += 12
            if "a" in full and hh == 12:
                hh = 0
            MM = 0
            times.append([full, datetime.time(hh, MM)])
        if len(times) is not 0: return times

        matches = re.finditer(self.regex_24h_short, line, re.IGNORECASE | re.UNICODE)
        times = []
        for match in matches:
            full = match.group(2)
            hh = int(match.group(2))
            MM = 0
            times.append([full, datetime.time(hh, MM)])
        if len(times) is not 0: return times

        return None

    def weekdayStringToNumeric(self, weekday):
        '''
        Convert the word name of a weekday expressed to its relative ISO-8601 number.
        :param str weekday: the weekday name to be converted
        :return: the number corresponding to the weekday
        :rtype: int
        '''
        weekdays = [w.lower() for w in self.regex_weekday_lang]
        if weekday is not None:
            return weekdays.index(weekday.lower()) + 1

    def monthStringToNumeric(self, month):
        '''
        Convert the word name of a month expressed to its relative ISO-8601 number.
        :param str month: the month name to be converted
        :return: the number corresponding to the month
        :rtype: int
        '''
        months = [m.lower() for m in self.regex_months_lang]
        if month is not None:
            return months.index(month.lower()) + 1

    def weekdayNumericToString(self, index):
        '''
        Convert the weekday expressed as a number to its relative word name in the currently set language.
        :param int index: the weekday number to be converted
        :return: the word name of the weekday
        :rtype: str
        '''
        return self.regex_weekday_lang[index - 1].encode('utf-8')

    def monthNumericToString(self, index):
        '''
        Convert the month expressed as a number to its relative word name in the currently set language.
        :param int index: the month number to be converted
        :return: the word name of the month
        :rtype: str
        '''
        return self.regex_months_lang[index - 1]

    def dayNumericToString(self, index):
        '''
        Convert the month-day expressed as a number to a string and add the required suffix.
        :param int index: the day number to be converted
        :return: the day as it should appear in a not-numeric date
        :rtype: str
        '''
        ending = ""
        endings = self._conf[DAY_DELIMITER][self._lang].split("|")

        if self._lang == "english":
            return TimeDateParser.ordinal(index)
        else:
            return str(index) + ending

    @staticmethod
    def ordinal(num):
        '''
        Author: Jackson Cooper, https://www.pythoncentral.io/validate-python-function-parameters-and-return-types-with-decorators/
        Returns the ordinal number of a given integer, as a string.
        eg. 1 -> 1st, 2 -> 2nd, 3 -> 3rd, etc.
        :param int num: number to be converted to ordinal
        :return: the ordinal number
        :rtype: str
        '''
        if 10 <= num % 100 < 20:
            return '%dth' % num
        else:
            ord = {1: 'st', 2: 'nd', 3: 'rd'}.get(num % 10, 'th')
            return '%d%s' % (num, ord)

    def guessFullDate(self, date):
        '''
        Guess a complete date starting from the available information.
        If only the <weekday> is available, assume the date to correspond to the first upcoming <weekday> even if in the following week.
        If only the <month> is available, assume the date to correspond to the following upcoming <month> even if in the following year.
        If only the <month> and the <day> are available, assume the date to correspond to the following upcoming <month> and <day> even if in the following year.
        By creating a datetime.date object this function also "checks" if the date is valid or not.
        :param Date date: a timedateparser.Date object indicating the complete or incomplete date
        :return: a datetime.date object of the guessed date, and the guessed weekday
        :rtype: (datetime.date, int)
        '''
        #TODO: at the moment the valid timedateparser.Date "29th of February" is not accepted in getDate()
        #todo: unless the upcoming February is leap because this function tries to instantiate a datetime.date object... fix it!

        today = datetime.datetime.now()

        if date.year is not None and date.month is not None and date.day is not None and date.weekday is not None:
            guess = datetime.date(date.year, date.month, date.day)
            return guess, guess.isoweekday()

        elif date.year is not None and date.month is not None and date.day is not None and date.weekday is None:
            guess = datetime.date(date.year, date.month, date.day)
            return guess, guess.isoweekday()

        elif date.year is None and date.month is None and date.day is None and date.weekday is not None:
            wd = date.weekday
            if today.isoweekday() < wd <= 7:
                guess = today + datetime.timedelta(days = wd - today.isoweekday())
            else:
                guess = today + datetime.timedelta(days = 7 - today.isoweekday() + wd)

            guess = datetime.date(guess.year, guess.month, guess.day)
            return guess, guess.isoweekday()

        elif date.year is None and date.month is None and date.day is not None:
            d = date.day
            if today.day < d <= calendar.monthrange(today.year, today.month)[1]:
                guess = datetime.date(today.year, today.month, d)
            else:
                guess = today + datetime.timedelta(days = d + calendar.monthrange(today.year, today.month)[1] - today.day)
                guess = datetime.date(guess.year, guess.month, guess.day)
            return guess, guess.isoweekday()

        elif date.year is None and date.month is not None and date.day is not None:
            d = date.day
            m = date.month
            if today.month < m <= 12:
                guess = datetime.date(today.year, m, d)
            else:
                guess = datetime.date(today.year + 1, m, d)
            return guess, guess.isoweekday()

        else:
            return None, None

    def composeStringDate(self, required, date):
        '''
        Return the given <date> in a human-like expression, e.g. "on the 4th of June 2018". The date required elements
        are expected to be not None in <date>.
        :param list of bool required: list of booleans which specify if a data element must be retrieved or not in this order YYYY, MM, DD, ww
        :param Date date: a timedateparser.Date object of the date to be formatted
        :return: the date as human-like expression, None if the string cannot be composed
        :rtype: str
        '''
        year = date.year
        month = date.month
        day = date.day
        weekday = date.weekday

        today = datetime.datetime.now()
        if year == today.year:
            if month == today.month:
                if day == today.day:
                    return self._conf[DATE_ADVERBS][TODAY][self._lang]
                elif day == today.day + 1:
                    return self._conf[DATE_ADVERBS][TOMORROW][self._lang]
                elif day == today.day + 2:
                    return self._conf[DATE_ADVERBS][DAY_AFTER_TOMORROW][self._lang]
                elif day == today.day + 3:
                    return self._conf[DATE_AS_STRING][WEEKDAY][self._lang] % (self.weekdayNumericToString(weekday))
                elif day == today.day + 4:
                    return self._conf[DATE_AS_STRING][WEEKDAY][self._lang] % (self.weekdayNumericToString(weekday))
                elif day == today.day + 5:
                    return self._conf[DATE_AS_STRING][WEEKDAY][self._lang] % (self.weekdayNumericToString(weekday))
                elif day == today.day + 6:
                    return self._conf[DATE_AS_STRING][WEEKDAY][self._lang] % (self.weekdayNumericToString(weekday))
                elif day == today.day + 7:
                    return self._conf[DATE_AS_STRING][WEEKDAY][self._lang] % (self.weekdayNumericToString(weekday))
                elif day == today.day -1:
                    return self._conf[DATE_ADVERBS][YESTERDAY][self._lang]
                elif day == today.day -2:
                    return self._conf[DATE_ADVERBS][DAY_BEFORE_YESTERDAY][self._lang]

        if required == [True, True, True, False] or required == [True, True, True, True]:
            return self._conf[DATE_AS_STRING][DAY_MONTH_YEAR][self._lang] % (self.dayNumericToString(day), self.monthNumericToString(month), str(year))
        elif required == [True, True, False, False]:
            return self._conf[DATE_AS_STRING][MONTH_YEAR][self._lang] % (self.monthNumericToString(month), str(year))
        elif required == [True, False, False, False]:
            return self._conf[DATE_AS_STRING][YEAR][self._lang] % (str(year))
        elif required == [False, True, True, False]:
            return self._conf[DATE_AS_STRING][DAY_MONTH][self._lang] % (self.dayNumericToString(day), self.monthNumericToString(month))
        elif required == [False, True, False, False]:
            return self._conf[DATE_AS_STRING][MONTH][self._lang] % (self.monthNumericToString(month))
        elif required == [False, False, True, False]:
            return self._conf[DATE_AS_STRING][DAY][self._lang] % (self.dayNumericToString(day))
        elif required == [False, False, False, True]:
            return self._conf[DATE_AS_STRING][WEEKDAY][self._lang] % (self.weekdayNumericToString(weekday))
        # elif format == "weekday-day":
        #     return self._conf[DATE_AS_STRING]["weekday-day"][self._lang] % (self.weekdayNumericToString(weekday), self.dayNumericToString(day))

        return None

    def composeStringTime(self, time):
        '''
        Return the given <time> with the correct preposition for a human-like expression, e.g. "at 5 p.m.".
        :param str time: the time as string
        :return: the time as human-like expression
        :rtype: str
        '''

        return self._conf[TIME_AS_STRING][self._lang] % time

    def getCurrentDate(self):
        '''
        Return today's date in the format 'DD/MM/YY'. If the language is "english" the format is 'MM/DD/YY'.
        :return: today's date
        :rtype: str
        '''
        today = datetime.datetime.now()
        if self._lang == "english":
            return today.strftime("%m/%d/%y")
        else:
            return today.strftime("%d/%m/%y")

    def getCurrentWeekday(self):
        '''
        Return today's weekday name according to the currently set language.
        :return: today's weekday name
        :rtype: str
        '''
        today = datetime.datetime.now()
        return unicode(self.weekdayNumericToString(today.weekday() + 1),"utf-8")

    def getCurrentTime12(self):
        '''
        Return current time in the 12h clock format.
        :return: current time in 12h clock format
        :rtype: str
        '''
        today = datetime.datetime.now()
        return today.strftime("%I:%M %p")

    def getCurrentTime24(self):
        '''
        Return current time in the 24h clock format.
        :return: current time in 24h clock format
        :rtype: str
        '''
        today = datetime.datetime.now()
        return today.strftime("%H:%M")

    def setLanguage(self, language):
        '''
        Set the language used in the sentence being parsed.
        :param str language: language to use
        '''
        self._lang = language

    def getLanguage(self):
        '''
        Get the currently set language.
        :return str: the current language
        :rtype: str
        '''
        return self._lang


if __name__ == '__main__':

    tdp = TimeDateParser("english")

    try:
        import sys
        while True:
            line = raw_input("Write a date > ").decode(sys.stdin.encoding)
            date = tdp.getDate(line)
            print date
            line = raw_input("Write the time > ").decode(sys.stdin.encoding)
            time = tdp.getTime(line)
            print time
    except KeyboardInterrupt:
        import sys
        sys.exit()

# -*- coding: utf-8 -*-
'''
Copyright October 2019 Bui Ha Duong & Roberto Menicatti & Università degli Studi di Genova

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

Author:      Bui Ha Duong (1), Roberto Menicatti (2)
Email:       (1) bhduong@jaist.ac.jp (2) roberto.menicatti@dibris.unige.it
Affiliation: (1) Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan
             (2) Laboratorium, DIBRIS, University of Genova, Italy
Project:     CARESSES (http://caressesrobot.org/en/)
'''
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from urlparse import urlparse, parse_qs
import isodate
import urllib2
import re

DEVELOPER_KEY = 'AIzaSyCr-g1oTB-sOgydsCEUjhdNhZZdg6XoxoY'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
YOUTUBE_EMBED_LINK = "https://www.youtube.com/embed/%s?autoplay=1&mute=0"


class YoutubeHelper(object):
    def __init__(self):
        self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                             developerKey=DEVELOPER_KEY)

        self.max_results = 10

    def get_video_id(self, url):
        url_pars = urlparse(url)
        query_v = parse_qs(url_pars.query).get('v')
        if (query_v):
            return query_v[0]
        return None

    def checkIfEmbeddable(self, id):

        response = self.youtube.videos().list(
            part='id,snippet,status',
            id=id
        ).execute()

        for search_result in response.get('items', []):
            return eval(str(search_result['status']['embeddable']))

    def checkIfPlayable(self, id):
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
        headers = {'User-Agent': user_agent}
        url = YOUTUBE_EMBED_LINK % id

        req = urllib2.Request(url, headers=headers)
        f = urllib2.urlopen(req)
        html_doc = f.read()

        playable = re.search(r'playabilityStatus\\":{\\"status\\":\\"(.*)\\"}}', html_doc)

        return playable.group(1) == "OK"


    def search_video_id(self, keyword):
        # Call the search.list method to retrieve results matching the specified
        # query term.
        search_response = self.youtube.search().list(
            q=keyword.replace(" ", "+"),
            part='id,snippet',
            order='relevance',
            maxResults=30,
            type='video',
            videoEmbeddable='true'
        ).execute()

        title = None
        url = None

        ids = []

        for search_result in search_response.get('items', []):
            if search_result['id']['kind'] == 'youtube#video':
                title = search_result['snippet']['title']
                video_id = search_result['id']['videoId']
                url = video_id
                if self.checkIfPlayable(url):
                    ids.append(url)
                if len(ids) == self.max_results:
                    break

        return ids

    def get_video_duration(self, video_id):
        video_info = self.youtube.videos().list(
            part='contentDetails',
            id=video_id
        ).execute()
        return isodate.parse_duration(video_info['items'][0]['contentDetails']['duration']).total_seconds()


if __name__ == '__main__':
    yt = YoutubeHelper()
    # print yt.get_video_id("https://www.youtube.com/watch?v=hT_nvWreIhg")
    # print yt.get_video_id("hello")
    # print yt.search_video_id("Girls like you lyric")
    print yt.get_video_duration('EmGFdalXd-w')
    print yt.checkIfEmbeddable('EmGFdalXd-w')
    print yt.checkIfPlayable('EmGFdalXd-w')

# -*- coding: utf-8 -*-
'''
Copyright October 2019 Amélie Eugene & Roberto Menicatti & Università degli Studi di Genova & Bui Ha Duong

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

Author:      Amélie Eugene (1), Roberto Menicatti (1), Bui Ha Duong (2)
Email:       (1) roberto.menicatti@dibris.unige.it (2) bhduong@jaist.ac.jp
Affiliation: (1) Laboratorium, DIBRIS, University of Genova, Italy
             (2) Robotics Laboratory, Japan Advanced Institute of Science and Technology, Japan
Project:     CARESSES (http://caressesrobot.org/en/)
'''

import urllib2
import argparse
import feedparser
import re
import time
from bs4 import BeautifulSoup

urls = {
    "ndtv":{
        "full": "NDTV",
        "url-article": "",
        "url-root": "http://feeds.feedburner.com/ndtvnews-india-news"
    },
    "theHindu":{
        "full": "The Hindu",
        "url-article": "",
        "url-root": "https://www.thehindu.com/news/national/feeder/default.rss"
    },
    "bBC":{
        "full": "BBC News",
        "url-article": "",
        "url-root": "http://feeds.bbci.co.uk/news/uk/rss.xml"
    },
    "skyNews":{
        "full": "Sky News",
        "url-article": "",
        "url-root": "http://feeds.skynews.com/feeds/rss/uk.xml"
    },
    "reuters":{
        "full": "ロイター",
        "url-article": "",
        "url-root": "https://assets.wor.jp/rss/rdf/reuters/top.rdf"
    },
    "nhkNews":{
        "full": "NHKニュース",
        "url-article": "",
        "url-root": "https://www3.nhk.or.jp/rss/news/cat0.xml"
    },
    "corriereDellaSera":{
        "full": "Corriere della Sera",
        "url-article": "",
        "url-root": "http://xml2.corriereobjects.it/rss/homepage.xml"
    }
}

## If testing fails, modify the following functions

def getArticle(source, url):

    user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
    headers = {'User-Agent': user_agent}

    req = urllib2.Request(url, headers=headers)
    f = urllib2.urlopen(req)

    intro = []
    paragraphs = []

    if source == "skyNews":

        html_doc = f.read()
        soup = BeautifulSoup(html_doc, 'html.parser')
        article_body = soup.find("div", {'class':['sdc-article-body sdc-article-body--lead']})
        paras = article_body.find_all("p")
        for para in paras:
            if para.text:
                paragraphs.append(para.text.lstrip().rstrip())

    elif source == "bBC":

        html_doc = f.read()
        soup = BeautifulSoup(html_doc, 'html.parser')
        article_body = soup.find("div", {'class':[re.compile('^story-body')]})
        paras = article_body.find_all("p")
        for para in paras:
            if para.has_attr('class') and para['class'][0].startswith('twite'):
                continue
            if para.text:
                paragraphs.append(para.text.lstrip().rstrip())

    elif source == "theHindu":
        
        html_doc = f.read()
        soup = BeautifulSoup(html_doc, 'html.parser')
        article_body = soup.find("div", {'id':[re.compile('^content-body')]})
        paras = article_body.find_all("p")
        for para in paras:
            if para.text:
                paragraphs.append(para.text.lstrip().rstrip())

    elif source == "ndtv":

        html_doc = f.read()
        soup = BeautifulSoup(html_doc, 'html.parser')
        article_body = soup.find("div", {'class':['ins_storybody']})
        paras = article_body.find_all("p")
        for para in paras:
            if para.has_attr('class') and para['class'][0] == 'static_txt':
                continue
            if para.text:
                paragraphs.append(para.text.lstrip().rstrip())

    elif source == "nhkNews":

        html_doc = f.read()
        soup = BeautifulSoup(html_doc, 'html.parser')
        article_texts = soup.find_all("div", {'id':['news_textbody', 'news_textmore']})
        for article_text in article_texts:
            for text in article_text.stripped_strings:
                paragraphs.append(text.lstrip().rstrip())
        article_texts = soup.find_all("div", {'class':['news_add']})
        for article_text in article_texts:
            for text in article_text.stripped_strings:
                paragraphs.append(text.lstrip().rstrip())
        
    elif source == "reuters":

        html_doc = f.read()
        soup = BeautifulSoup(html_doc, 'html.parser')
        article_body = soup.find("div", {'class':['StandardArticleBody_body']})
        paras = article_body.find_all("p")
        for para in paras:
            if para.has_attr('class') and para['class'][0] == 'Attribution_content':
                continue
            if para.text:
                paragraphs.append(para.text.lstrip().rstrip())

    elif source == "corriereDellaSera":

        html_doc = f.read()
        soup = BeautifulSoup(html_doc, 'html.parser')
        article_body = soup.find("div", {'class':['content']})
        paras = article_body.find_all("p")
        for para in paras:
            if para.has_attr('class') and para['class'][0] == 'Attribution_content':
                continue
            if para.text:
                paragraphs.append(para.text.lstrip().rstrip())

    if not paragraphs == []:
        paragraphs = intro + paragraphs
        return paragraphs
    else:
        return None

def cleanText(text):

    remove = re.search(r'<iframe(.*\s*.*)</iframe>', text)
    if remove is not None:
        to_remove = [remove.group(0)]
    else:
        to_remove = []

    also_remove = re.search(r'Copyright.*', text)
    if also_remove is not None:
        to_remove.append(also_remove.group(0))

    also_remove = re.search(r'<script.*</script>', text)
    if also_remove is not None:
        to_remove.append(also_remove.group(0))

    also_remove = re.search(r'(<a .*>)(.*?)(?=</a>)(</a>)', text)
    if also_remove is not None:
        to_remove.append(also_remove.group(1))
        to_remove.append(also_remove.group(3))

    also_remove = re.search(r'<img (.*?)(?=/>)/>', text)
    if also_remove is not None:
        to_remove.append(also_remove.group(0))

    to_remove = to_remove + ["<strong>", "</strong>", "<br/>", "<br />", "<em>", "</em>", "<p>", "</p>", "<noscript>", "<i>", "</i>"]

    for removable in to_remove:
        if removable in text:
            text = text.replace(removable, "")

    return text

def obtainHeadsAndLinks(url):
    """
    Function to obtain a list of the news of the day from the given news channel
    :return: the list of urls, the list of headlines
    :rtype: ([str], [str])
    """
    NewsFeed = feedparser.parse(url)
    links = [entry.link for entry in NewsFeed.entries]
    heads = [entry.title for entry in NewsFeed.entries]
    return links, heads

class ReadNewsTester():

    def __init__(self, source):

        self.source_id = source
        self.source_full = urls[self.source_id]["full"]
        self.source_url = urls[self.source_id]["url-root"]
        self.source_url_article = urls[self.source_id]["url-article"]

        self.links, self.heads = obtainHeadsAndLinks(self.source_url)


    def test(self, index):
        self.complete_url = self.source_url_article + self.links[index]
        article_body = getArticle(self.source_id, self.complete_url)
        
        print("\n\n")
        print("====================================================")
        print(" Channel: %s") % self.source_full 
        print(" Article: %s") % self.heads[index]
        print(" Link:    %s") % self.complete_url
        print("====================================================")
        
        if article_body is not None:
            for period_index, period in enumerate(article_body):
                print(period.encode('utf-8'))

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--index", "-i", type=int, default=0, help="Index of the news article.")

    args = parser.parse_args()
    for channel in urls.keys():
        ReadNewsTester(channel).test(args.index)

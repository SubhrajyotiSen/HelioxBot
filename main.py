import StringIO
import sys
sys.path.insert(0, 'libs')
import logging
import random
import urllib
import urllib2
import cStringIO
import json
from bs4 import BeautifulSoup
import html2text

# for sending images
from PIL import Image
import multipart


# standard app engine imports
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

TOKEN = YOUR_BOT_API_KEY

BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'

# ================================

class EnableStatus(ndb.Model):
    # key name: str(chat_id)
    enabled = ndb.BooleanProperty(indexed=False, default=False)


# ================================

def setEnabled(chat_id, yes):
    es = EnableStatus.get_or_insert(str(chat_id))
    es.enabled = yes
    es.put()

def getEnabled(chat_id):
    es = EnableStatus.get_by_id(str(chat_id))
    if es:
        return es.enabled
    return False


# ================================

class MeHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe'))))


class GetUpdatesHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getUpdates'))))


class SetWebhookHandler(webapp2.RequestHandler):
    def get(self):
        urlfetch.set_default_fetch_deadline(60)
        url = self.request.get('url')
        if url:
            self.response.write(json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': url})))))


class WebhookHandler(webapp2.RequestHandler):
    def post(self):
        urlfetch.set_default_fetch_deadline(60)
        body = json.loads(self.request.body)
        logging.info('request body:')
        logging.info(body)
        self.response.write(json.dumps(body))

        update_id = body['update_id']
        try:
            message = body['message']
        except:
            message = body['edited_message']
        message_id = message.get('message_id')
        date = message.get('date')
        text = message.get('text')
        fr = message.get('from')
        chat = message['chat']
        chat_id = chat['id']

        if not text:
            logging.info('no text')
            return

        def reply(msg=None):
            if msg:
                resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                    'chat_id': str(chat_id),
                    'text': msg ,
                    'disable_web_page_preview': 'true',
                    'reply_to_message_id': str(message_id),
                })).read()
            else:
                logging.error('no msg or img specified')
                resp = None

            logging.info('send response:')
            logging.info(resp)

        def getSoup(url):
            # required header
            hdr = {'User-Agent':
                   ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 '
                    '(KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'),
                   'Accept':
                   ('text/html,application/xhtml+xml,'
                    'application/xml;q=0.9,*/*;q=0.8'),
                   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
                   'Accept-Encoding': 'none',
                   'Accept-Language': 'en-US,en;q=0.8',
                   'Connection': 'keep-alive'}
            # configure reuqest
            req = urllib2.Request(url, headers=hdr)
            # open the URL and get the response
            page = urllib2.urlopen(req)
            # use HTML parser in the page response
            soup = BeautifulSoup(page, "html.parser")
            # return the parse HTML
            return soup


        if text.startswith('/'):
            if text == '/start':
                reply('Bot enabled')
                setEnabled(chat_id, True)
            elif text == '/stop':
                reply('Bot disabled')
                setEnabled(chat_id, False)
            elif text == '/help' :
                reply('You can search for lyrics by entering the artist name followed by song name')

        # CUSTOMIZE FROM HERE

        elif 'who are you' in text.lower():
            reply('An awesome bot, created by SubhrajyotiSen: https://github.com/SubhrajyotiSen')
        elif 'what time' in text.lower():
            reply('look at the corner of your screen!')
        else:
            if getEnabled(chat_id):
                link = None
                text = text.strip();
                textCopy = text.lower()
                text = text.replace(' ','%20')
                 # generate the API request URL
                url = 'http://search.azlyrics.com/search.php?q='+text
                soup = getSoup(url)
                # find divs with class 'panel'
                segments = soup.body.findAll("div", {"class": "panel"})
                # find the div that contains the song results
                for segment in segments:
                    if segment.find("div", "panel-heading").find("b").text == "Song results:":
                        link = segment.find("td", {"class": "text-left visitedlyr"}).find("a")['href']
                # if a song result is found
                if link is not None:
                    soup = getSoup(link)
                    # get the lyrics
                    lyrics = soup.body.find(
                        "div", {"class": "col-xs-12 col-lg-8 text-center"}).findAll("div")[6].prettify()
                    reply(html2text.html2text(lyrics).encode('ascii','ignore'))
                else:
                    reply("Song not found")

            else:
                logging.info('not enabled for chat_id {}'.format(chat_id))


app = webapp2.WSGIApplication([
    ('/me', MeHandler),
    ('/updates', GetUpdatesHandler),
    ('/set_webhook', SetWebhookHandler),
    ('/webhook', WebhookHandler),
], debug=True)

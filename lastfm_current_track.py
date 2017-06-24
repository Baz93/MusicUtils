import requests
import json

user = 'bazzzzz93'
api_key = '879994ea88f415ced5d444104729a263'


def get_current_track():
    r = requests.get('http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%s&api_key=%s&limit=1&format=json' % (user, api_key))
    result = json.loads(r.text)
    track = result['recenttracks']['track'][0]
    return (track['artist']['#text'], track['album']['#text'], track['name'])


print("%s - %s - %s" % get_current_track())

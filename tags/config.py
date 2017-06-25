from typing import List
import mutagen.id3
from mutagen.easyid3 import EasyID3

from .applier import Action, get_id3, AllId3TagsActionGenerator


class DoNothing(Action):
    def apply(self, tags: EasyID3):
        pass

    def key(self):
        return "DoNothing"


class DeleteTag(Action):
    def __init__(self, id3_tag_key: str):
        self.id3_tag_key = id3_tag_key

    def apply(self, tags: EasyID3) -> None:
        del get_id3(tags)[self.id3_tag_key]

    def key(self) -> str:
        return "DeleteTag %s" % self.id3_tag_key


class DeleteUnacceptableTags(AllId3TagsActionGenerator):
    def __init__(self, acceptable_tags: List[str]):
        self.acceptable_tags = acceptable_tags

    def of_tag(self, key: str) -> Action:
        if key in self.acceptable_tags:
            return DoNothing()
        else:
            return DeleteTag(key)


class FixLyricsAttributes(Action):
    def apply(self, tags: EasyID3) -> None:
        lyrics_list = get_id3(tags).getall('USLT')
        if len(lyrics_list) == 0:
            return
        lyrics = max(lyrics_list, key=lambda l: len(l.text)).text
        get_id3(tags).delall('USLT')
        tags['lyrics'] = lyrics

    def key(self) -> str:
        return "FixLyricsAttributes"


def lyrics_get(id3, key):
    return list(id3["USLT::eng"])


def lyrics_set(id3, key, value):
    assert len(value) == 1
    id3.add(mutagen.id3.USLT(text=value[0], lang='eng'))


def lyrics_delete(id3, key):
    del(id3["USLT::eng"])


def configure():
    EasyID3.RegisterKey("lyrics", lyrics_get, lyrics_set, lyrics_delete)

    EasyID3.RegisterTXXXKey('group', 'GROUP')
    EasyID3.RegisterTXXXKey('country', 'COUNTRY')
    EasyID3.RegisterTXXXKey('large_series', 'LARGESERIESINDICATOR')
    EasyID3.RegisterTXXXKey('ext_artist', 'EXTENDEDARTIST')
    EasyID3.RegisterTXXXKey('ext_album', 'EXTENDEDALBUM')
    EasyID3.RegisterTXXXKey('ext_title', 'EXTENDEDTITLE')
    EasyID3.RegisterTXXXKey('rym_type', 'RYMTYPE')
    EasyID3.RegisterTXXXKey('rym_album', 'RYMALBUM')
    EasyID3.RegisterTXXXKey('rym_artist', 'RYMARTIST')
    EasyID3.RegisterTXXXKey('sec_genres', 'SECONDARYGENRES')


action_list = [
    FixLyricsAttributes(),
    DeleteUnacceptableTags([
        'APIC:', 'TALB', 'TPE1', 'TPE2', 'TCON', 'TIT2', 'TCOM', 'TDRC', 'TRCK', 'USLT::eng',
        'TXXX:YEARORDER', 'TXXX:YEARORDERDIGITS', 'TXXX:TRACKDIGITS', 'TXXX:PERFORMER',
        'TXXX:GROUP', 'TXXX:LARGESERIESINDICATOR', 'TXXX:SERIES', 'TXXX:COUNTRY',
        'TXXX:SUPERGENRE', 'TXXX:SUBGENRE', 'TXXX:GENRESPECIFIER', 'TXXX:SECONDARYGENRES',
        'TXXX:ALBUMTRANSLATION', 'TXXX:ARTISTTRANSLATION', 'TXXX:TITLETRANSLATION',
        'TXXX:ARTISTAPPENDIX', 'TXXX:ALBUMAPPENDIX', 'TXXX:TITLEAPPENDIX',
        'TXXX:EXTENDEDARTIST', 'TXXX:EXTENDEDALBUM', 'TXXX:EXTENDEDTITLE',
        'TXXX:RYMARTIST', 'TXXX:RYMALBUM', 'TXXX:RYMTYPE',
        'TXXX:SERIESEXCEPTION', 'TXXX:ALBUMARTISTEXCEPTION',
        'TXXX:ALBUMEXCEPTION', 'TXXX:ARTISTEXCEPTION', 'TXXX:TITLEEXCEPTION',
        'TXXX:RYMARTISTEXCEPTION', 'TXXX:RYMALBUMEXCEPTION', 'TXXX:RYMTYPEEXCEPTION',
    ]),
]
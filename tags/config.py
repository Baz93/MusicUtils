from typing import List
import mutagen.id3
from mutagen.id3 import ID3v1SaveOptions

from .applier import Action, ActionGenerator, EasyID3Tags

__all__ = [
    'MyTags', 'AllId3TagsActionGenerator', 'DoNothing', 'DeleteTag',
    'DeleteUnacceptableTags', 'FixLyricsAttributes', 'action_list',
]


class MyTags(EasyID3Tags):
    def write(self, path: str):
        self.save(path, v1=ID3v1SaveOptions.CREATE, v2_version=3)


def lyrics_get(id3, key):
    return list(id3["USLT::eng"])


def lyrics_set(id3, key, value):
    assert len(value) == 1
    id3.add(mutagen.id3.USLT(text=value[0], lang='eng'))


def lyrics_delete(id3, key):
    del (id3["USLT::eng"])


MyTags.RegisterKey("lyrics", lyrics_get, lyrics_set, lyrics_delete)

MyTags.RegisterTXXXKey('group', 'GROUP')
MyTags.RegisterTXXXKey('country', 'COUNTRY')
MyTags.RegisterTXXXKey('large_series', 'LARGESERIESINDICATOR')
MyTags.RegisterTXXXKey('ext_artist', 'EXTENDEDARTIST')
MyTags.RegisterTXXXKey('ext_album', 'EXTENDEDALBUM')
MyTags.RegisterTXXXKey('ext_title', 'EXTENDEDTITLE')
MyTags.RegisterTXXXKey('rym_type', 'RYMTYPE')
MyTags.RegisterTXXXKey('rym_album', 'RYMALBUM')
MyTags.RegisterTXXXKey('rym_artist', 'RYMARTIST')
MyTags.RegisterTXXXKey('sec_genres', 'SECONDARYGENRES')


class AllId3TagsActionGenerator(ActionGenerator):
    def generate(self, tags: MyTags):
        return [self.of_tag(tag) for tag in tags.get_id3()]

    def of_tag(self, key: str) -> Action:
        raise NotImplementedError()


class DoNothing(Action):
    def apply(self, tags: MyTags):
        pass

    def key(self):
        return "DoNothing"


class DeleteTag(Action):
    def __init__(self, id3_tag_key: str):
        self.id3_tag_key = id3_tag_key

    def apply(self, tags: MyTags) -> None:
        del tags.get_id3()[self.id3_tag_key]

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
    def apply(self, tags: MyTags) -> None:
        lyrics_list = tags.get_id3().getall('USLT')
        if len(lyrics_list) == 0:
            return
        lyrics = max(lyrics_list, key=lambda l: len(l.text)).text
        tags.get_id3().delall('USLT')
        tags['lyrics'] = lyrics

    def key(self) -> str:
        return "FixLyricsAttributes"


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
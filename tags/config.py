import sys
import os
from typing import List, Any
from tempfile import NamedTemporaryFile
from contextlib import contextmanager

import mutagen.id3
from mutagen.id3 import ID3v1SaveOptions, ID3

from dimensions import dimensions

from .applier import Action, ActionGenerator, EasyID3Tags, prepare

__all__ = [
    'MyTags', 'AllId3TagsActionGenerator', 'DoNothing', 'DeleteTag',
    'DeleteUnacceptableTags', 'FixLyricsAttributes', 'action_list',
]


def recursive_delete_empty_folders(path: str) -> None:
    while len(os.listdir(path)) == 0:
        os.rmdir(path)
        path = os.path.dirname(path)


class MyTags(EasyID3Tags):
    def __init__(self, path) -> None:
        assert os.path.abspath(path) == path
        super().__init__(path)
        self.__original_path = path

    def path(self) -> str:
        return self.__original_path

    def _copy(self) -> Any:
        return self.filename, super()._copy()

    def _restore(self, value: Any) -> None:
        self.filename, id3_value = value
        super()._restore(id3_value)

    @classmethod
    def _diff2(cls, value1: Any, value2: Any) -> List[str]:
        filename1, id3_value1 = value1
        filename2, id3_value2 = value2

        result = []
        if filename1 != filename2:
            result.append("path. %s --> %s" % (prepare(filename1), prepare(filename1)))

        result.extend(super()._diff2(id3_value1, id3_value2))
        return result

    def write(self) -> None:
        assert os.path.abspath(self.filename) == self.filename
        if not os.path.isdir(os.path.dirname(self.filename)):
            os.makedirs(os.path.dirname(self.filename))
        os.rename(self.__original_path, self.filename)
        recursive_delete_empty_folders(os.path.dirname(self.__original_path))
        self.save(v1=ID3v1SaveOptions.CREATE, v2_version=3)


@contextmanager
def temp_input(data):
    temp = NamedTemporaryFile(delete=False)
    temp.write(data)
    temp.close()
    try:
        yield temp.name
    finally:
        os.unlink(temp.name)


def image_info(data: bytes):
    with temp_input(data) as image:
        return dimensions(image)[:3]


def lyrics_get(id3: ID3, key: str) -> List[str]:
    return [id3["USLT::eng"].text]


def lyrics_set(id3: ID3, key: str, value: List[str]) -> None:
    assert len(value) == 1
    id3.add(mutagen.id3.USLT(text=value[0], lang='eng'))


def lyrics_delete(id3: ID3, key: str) -> None:
    del id3["USLT::eng"]


def picture_get(id3: ID3, key: str) -> List[bytes]:
    return [id3["APIC:"].data]


def picture_set(id3: ID3, key: str, value: List[bytes]) -> None:
    assert len(value) == 1
    id3.add(mutagen.id3.APIC(data=value[0], mime=image_info(value[0])[2]))


def picture_delete(id3: ID3, key: str) -> None:
    del id3["APIC:"]


MyTags.RegisterKey("lyrics", lyrics_get, lyrics_set, lyrics_delete)
MyTags.RegisterKey("picture", picture_get, picture_set, picture_delete)

MyTags.RegisterTXXXKey('group', 'GROUP')
MyTags.RegisterTXXXKey('country', 'COUNTRY')
MyTags.RegisterTXXXKey('series', 'SERIES')
MyTags.RegisterTXXXKey('large_series', 'LARGESERIESINDICATOR')
MyTags.RegisterTXXXKey('artist_trans', 'ALBUMTRANSLATION')
MyTags.RegisterTXXXKey('album_trans', 'ALBUMTRANSLATION')
MyTags.RegisterTXXXKey('title_trans', 'TITLETRANSLATION')
MyTags.RegisterTXXXKey('artist_app', 'ALBUMAPPENDIX')
MyTags.RegisterTXXXKey('album_app', 'ALBUMAPPENDIX')
MyTags.RegisterTXXXKey('title_app', 'TITLEAPPENDIX')
MyTags.RegisterTXXXKey('ext_artist', 'EXTENDEDARTIST')
MyTags.RegisterTXXXKey('ext_album', 'EXTENDEDALBUM')
MyTags.RegisterTXXXKey('ext_title', 'EXTENDEDTITLE')
MyTags.RegisterTXXXKey('series_exc', 'SERIESEXCEPTION')
MyTags.RegisterTXXXKey('album_artist_exc', 'ALBUMEARTISTXCEPTION')
MyTags.RegisterTXXXKey('artist_exc', 'ALBUMEXCEPTION')
MyTags.RegisterTXXXKey('album_exc', 'ALBUMEXCEPTION')
MyTags.RegisterTXXXKey('title_exc', 'TITLEEXCEPTION')
MyTags.RegisterTXXXKey('rym_type', 'RYMTYPE')
MyTags.RegisterTXXXKey('rym_album', 'RYMALBUM')
MyTags.RegisterTXXXKey('rym_artist', 'RYMARTIST')
MyTags.RegisterTXXXKey('year_order', 'YEARORDER')
MyTags.RegisterTXXXKey('year_order_digits', 'YEARORDERDIGITS')
MyTags.RegisterTXXXKey('track_digits', 'TRACKDIGITS')
MyTags.RegisterTXXXKey('performer', 'PERFORMER')
MyTags.RegisterTXXXKey('super_genre', 'SUPERGENRE')
MyTags.RegisterTXXXKey('sub_genre', 'SUBGENRE')
MyTags.RegisterTXXXKey('genre_specifier', 'GENRESPECIFIER')
MyTags.RegisterTXXXKey('sec_genres', 'SECONDARYGENRES')


class AllId3TagsActionGenerator(ActionGenerator):
    def generate(self, tags: MyTags) -> List[Action]:
        return [self.of_tag(tag) for tag in tags.get_id3()]

    def of_tag(self, key: str) -> Action:
        raise NotImplementedError()


class DoNothing(Action):
    def apply(self, tags: MyTags) -> None:
        pass

    def key(self) -> str:
        return "DoNothing"


class DeleteTag(Action):
    def __init__(self, id3_tag_key: str) -> None:
        self.id3_tag_key = id3_tag_key

    def apply(self, tags: MyTags) -> None:
        del tags.get_id3()[self.id3_tag_key]

    def key(self) -> str:
        return "DeleteTag %s" % self.id3_tag_key


class CapitulateTXXXTag(Action):
    def __init__(self, txxx_desc: str) -> None:
        self.txxx_desc = txxx_desc

    def apply(self, tags: MyTags) -> None:
        tag_from = 'TXXX:' + self.txxx_desc
        tag_to = 'TXXX:' + self.txxx_desc.upper()
        if tag_from in tags.get_id3() and tag_from != tag_to:
            tags.get_id3()[tag_to] = tags.get_id3()[tag_from]
            tags.get_id3()[tag_to].desc = self.txxx_desc.upper()
            del tags.get_id3()[tag_from]

    def key(self) -> str:
        return "CapitulateTXXXTag %s" % self.txxx_desc


class DeleteUnacceptableTags(AllId3TagsActionGenerator):
    def __init__(self, acceptable_tags: List[str]) -> None:
        self.acceptable_tags = acceptable_tags

    def of_tag(self, key: str) -> Action:
        if key in self.acceptable_tags:
            return DoNothing()
        else:
            return DeleteTag(key)


class CapitulateTXXXTags(AllId3TagsActionGenerator):
    def of_tag(self, key: str) -> Action:
        if key.startswith('TXXX:'):
            return CapitulateTXXXTag(key[5:])
        else:
            return DoNothing()


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


class CheckPicture(Action):
    def apply(self, tags: MyTags) -> None:
        if 'APIC:' not in tags.get_id3():
            print("%s has no picture" % prepare(tags.path()))
            return
        picture = tags.get_id3()['APIC:']
        width, height, mime = image_info(picture.data)
        side = min(width, height)
        if mime != 'image/jpeg':
            print("%s has bad picture mime: %s" % (prepare(tags.path()), mime))
        if side != 500:
            print("%s has bad picture size: (%d, %d)" % (prepare(tags.path()), width, height))
        tags.mime = mime

    def key(self) -> str:
        return "CheckPicture"


action_list = [
    CapitulateTXXXTags(),
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
    CheckPicture(),
]

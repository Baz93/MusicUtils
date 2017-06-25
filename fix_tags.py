import os
import sys
from argparse import ArgumentParser
from typing import Any, Tuple, Union, Callable, List
import mutagen.id3
from mutagen.id3 import ID3, ID3v1SaveOptions
from mutagen.easyid3 import EasyID3


def get_id3(tags: EasyID3):
    return tags._EasyID3__id3


class ActionGenerator:
    def generate(self, tags: EasyID3) -> List['Action']:
        raise NotImplementedError()


class Action(ActionGenerator):
    def generate(self, tags: EasyID3) -> List['Action']:
        return [self]

    def apply(self, tags: EasyID3) -> None:
        raise NotImplementedError()

    def key(self) -> str:
        raise NotImplementedError()


class AllId3TagsActionGenerator(ActionGenerator):
    def generate(self, tags: EasyID3):
        return [self.of_tag(tag) for tag in get_id3(tags)]

    def of_tag(self, key: str) -> Action:
        raise NotImplementedError()


def prepare(s: str) -> str:
    s = s.encode('utf-8').decode('ascii', 'replace')
    if len(s) > 500:
        s = s[:400] + '...' + s[:100]
    return s


def parent_name(path: str, num: int) -> str:
    if num == 0:
        return os.path.basename(path)
    return parent_name(os.path.dirname(path), num - 1)


def id3_diff(value1, value2) -> List[str]:
    if value1 == value2:
        return []

    if value1 is None or value2 is None:
        return ["%s --> %s" % (prepare(repr(value1)), prepare(repr(value2)))]

    items1, subs1 = value1
    items2, subs2 = value2
    map1 = dict(items1)
    map2 = dict(items2)
    result = []

    for key in sorted(set(map1) | set(map2)):
        before = map1[key] if key in map1 else None
        after = map2[key] if key in map2 else None
        if before != after:
            result.append("%s. %s --> %s" % (key, prepare(repr(before)), prepare(repr(after))))
        before_sub = subs1[key] if key in subs1 else None
        after_sub = subs2[key] if key in subs2 else None
        for change in id3_diff(before_sub, after_sub):
            result.append('. '.join(key, change))

    return result


class Applier:
    def __init__(self, generators: List[ActionGenerator]) -> None:
        self.yes_to_all = set()
        self.no_to_all = set()
        self.generators = generators

    @staticmethod
    def ask(question: str) -> Tuple[bool, bool]:
        print(question)
        response = sys.stdin.readline().rstrip('\n')
        if response == 'N':
            return False, False
        if response == 'Y':
            return True, False
        if response == 'NA':
            return False, True
        if response == 'YA':
            return True, True
        return Applier.ask("Please, input one of these: ['N', 'Y', 'NA', 'YA']")

    def decide_action(self, path: str, key: str, diff: List[str]) -> bool:
        if key in self.no_to_all:
            return False
        if key in self.yes_to_all:
            return True
        answer, assign_to_all = self.ask(
            "Perform action %s on %s?\n%s" % (prepare(key), prepare(path), '\n'.join(diff))
        )
        if assign_to_all:
            if answer:
                self.yes_to_all.add(key)
            else:
                self.no_to_all.add(key)
        return answer

    def process_action(self, path: str, tags: EasyID3, action: Action) -> bool:
        prev_value = get_id3(tags)._copy()
        action.apply(tags)
        new_value = get_id3(tags)._copy()
        diff = id3_diff(prev_value, new_value)
        if len(diff) == 0:
            return False
        if self.decide_action(path, action.key(), diff):
            return True
        get_id3(tags)._restore(prev_value)
        return False

    def apply(self, path: str) -> None:
        try:
            assert os.path.isfile(path)

            filename, extension = os.path.splitext(os.path.basename(path))

            if extension != '.mp3':
                print("%s has extension different from '.mp3'" % prepare(path))
                return

            tags = EasyID3(path)
            tags_changed = False

            for generator in self.generators:
                for action in generator.generate(tags):
                    if self.process_action(path, tags, action):
                        tags_changed = True

            if tags_changed:
                tags.save(path, v1=ID3v1SaveOptions.CREATE, v2_version=3)

        except:
            print("Error occured while processing %s" % prepare(path))
            raise

    def recursive_apply(self, path: str) -> None:
        if os.path.isdir(path):
            if os.path.basename(path) in ['__Unsorted', '.sync', 'Rubbish']:
                return
            if len(os.listdir(path)) == 0:
                print("%s is empty" % prepare(path))
            for f in os.listdir(path):
                self.recursive_apply(os.path.join(path, f))
        else:
            self.apply(path)

    def apply_to_all(self, paths: List[str]) -> None:
        for path in paths:
            self.recursive_apply(path)


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


def parse_arguments() -> Any:
    parser = ArgumentParser(description='Process some integers.')
    parser.add_argument('--path', '-p', action='append', required=True, type=str, help='path to music')
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    Applier([
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
    ]).apply_to_all([os.path.abspath(path) for path in args.path])


if __name__ == '__main__':
    main()

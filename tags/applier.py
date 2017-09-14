import os
import sys
from copy import deepcopy
from fnmatch import fnmatchcase

from unidecode import unidecode
from typing import List, Tuple, Any, Callable
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3

__all__ = [
    'id3_diff', 'Tags', 'ID3Tags', 'EasyID3Tags', 'prepare',
    'Action', 'ActionGenerator', 'Applier',
]


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
            result.append('. '.join((key, change)))

    return result


class Tags:
    def __init__(self, path) -> None:
        super().__init__(path)
        self.__backup = None
        self.apply()

    def apply(self) -> None:
        self.__backup = deepcopy(self._copy())

    def cancel(self) -> None:
        self._restore(self.__backup)

    def _copy(self) -> Any:
        raise NotImplementedError()

    def _restore(self, value: Any) -> None:
        raise NotImplementedError()

    @classmethod
    def _diff2(cls, value1: Any, value2: Any) -> List[str]:
        raise NotImplementedError()

    def diff(self) -> List[str]:
        return self._diff2(self.__backup, self._copy())

    def write(self) -> None:
        raise NotImplementedError()


class ID3Tags(Tags, ID3):
    @classmethod
    def _diff2(cls, value1: Any, value2: Any) -> List[str]:
        return id3_diff(value1, value2)


class EasyID3Tags(Tags, EasyID3):
    def get_id3(self) -> ID3:
        return self._EasyID3__id3

    def _copy(self) -> Any:
        return self.get_id3()._copy()

    def _restore(self, value: Any) -> None:
        return self.get_id3()._restore(value)

    @classmethod
    def _diff2(cls, value1: Any, value2: Any) -> List[str]:
        return id3_diff(value1, value2)


class ActionGenerator:
    def generate(self, tags: Tags) -> List['Action']:
        raise NotImplementedError()


class Action(ActionGenerator):
    def generate(self, tags: Tags) -> List['Action']:
        return [self]

    def apply(self, tags: Tags) -> None:
        raise NotImplementedError()

    def key(self) -> str:
        raise NotImplementedError()


def prepare(s: str) -> str:
    s = unidecode(s)
    s = ''.join(repr(c)[1:-1] if c.isspace() else c for c in s)
    if len(s) > 500:
        s = s[:400] + '...' + s[:100]
    return s


def parent_name(path: str, num: int) -> str:
    if num == 0:
        return os.path.basename(path)
    return parent_name(os.path.dirname(path), num - 1)


class Applier:
    def __init__(self, get_tags: Callable[[str], Tags], generators: List[ActionGenerator]) -> None:
        self.to_all = {}
        self.get_tags = get_tags
        self.generators = generators

    @staticmethod
    def ask(question: str) -> Tuple[bool, bool]:
        print(question)
        while True:
            response = sys.stdin.readline().rstrip('\n')
            if response == 'N':
                return False, False
            if response == 'Y':
                return True, False
            if response == 'NA':
                return False, True
            if response == 'YA':
                return True, True
            print("Please, input one of these: ['N', 'Y', 'NA', 'YA']")

    @staticmethod
    def get_pattern(key: str) -> str:
        print("Enter a pattern for the key: %s" % prepare(key))
        while True:
            response = sys.stdin.readline().rstrip('\n')
            if fnmatchcase(key, response):
                return response
            print("Key doesn't match the pattern")

    def decide_action(self, path: str, key: str, diff: List[str]) -> bool:
        for pattern, value in self.to_all.items():
            if fnmatchcase(key, pattern):
                return value
        answer, assign_to_all = self.ask(
            "Perform action %s on %s?\n%s" % (prepare(key), prepare(path), '\n'.join(diff))
        )
        if assign_to_all:
            pattern = self.get_pattern(key)
            self.to_all[pattern] = answer
        return answer

    def process_action(self, path: str, tags: Tags, action: Action) -> bool:
        action.apply(tags)
        diff = tags.diff()
        if len(diff) == 0:
            return False
        if self.decide_action(path, action.key(), diff):
            tags.apply()
            return True
        tags.cancel()
        return False

    def apply(self, path: str) -> None:
        try:
            assert os.path.isfile(path)

            filename, extension = os.path.splitext(os.path.basename(path))

            if extension != '.mp3':
                print("%s has extension different from '.mp3'" % prepare(path))
                return

            tags = self.get_tags(path)
            tags_changed = False

            for generator in self.generators:
                for action in generator.generate(tags):
                    if self.process_action(path, tags, action):
                        tags_changed = True

            if tags_changed:
                tags.write()

            # print(path)
            # print(tags.get_id3().keys())
            # print(tags.keys())

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

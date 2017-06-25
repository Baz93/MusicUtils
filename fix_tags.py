import os
from argparse import ArgumentParser
from typing import Any

from tags.config import MyTags, action_list
from tags.applier import *


def parse_arguments() -> Any:
    parser = ArgumentParser(description='Process some integers.')
    parser.add_argument('--path', '-p', action='append', required=True, type=str, help='path to music')
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    Applier(MyTags, action_list).apply_to_all([os.path.abspath(path) for path in args.path])


if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import argparse
import os
import sys

from librarianlib.management import LibraryManager
from librarianlib.command_interface import LibraryCommandInterface
from librarianlib.exceptions import LibraryException


CONFIG_FILE_NAME = '.libconf.yaml'
CONFIG_SEARCH_DIRS = [os.path.dirname(os.path.realpath(__file__)), os.getcwd(),
                      os.path.expanduser('~')]


def parse_args(cmd_interface):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='Command.')

    # Link parser.
    link_parser = subparsers.add_parser(
            'link',
            aliases=['ln'],
            help='Create a symlink to a document in the archive.')
    link_parser.add_argument('-f', '--fix', action='store_true',
                             help='Fix a broken symlink into the library.')
    link_parser.add_argument('key', help='Key for document to symlink.')
    link_parser.add_argument('name', nargs='?', help='Name for the link.')
    link_parser.set_defaults(func=cmd_interface.link)

    # Browse parser.
    browse_parser = subparsers.add_parser('browse', aliases=['search'],
                                          help='Filter documents.')
    browse_parser.add_argument('--key', help='Filter by key.')
    browse_parser.add_argument('--author', help='Filter by author.')
    browse_parser.add_argument('--title', help='Filter by title.')
    browse_parser.add_argument('--year', help='Filter by publication year.')
    browse_parser.add_argument('--venue', help='Filter by publication venue.')
    browse_parser.add_argument('--type', help='Filter by document type.')
    browse_parser.add_argument('--text', help='Filter by document text.')

    browse_parser.add_argument('-s', '--sort',
                               choices=['key', 'title', 'year', 'added',
                                        'recent', 'matches'],
                               help='Sort the results.')
    browse_parser.add_argument('-n', '--number', type=int,
                               help='Limit the number of results.')
    browse_parser.add_argument('-v', '--verbose', action='count',
                               help='Specify verbosity.')
    browse_parser.add_argument('-r', '--reverse', action='store_true',
                               help='Reverse sorting order.')
    browse_parser.set_defaults(func=cmd_interface.browse)

    # Add parser.
    add_parser = subparsers.add_parser(
            'add',
            help='Add a new document to the library.')
    add_parser.add_argument('pdf', help='PDF file.')
    add_parser.add_argument('bibtex', help='Associated bibtex file.')
    add_parser.add_argument('-d', '--delete', action='store_true',
                            help='Delete files after archiving.')
    add_parser.add_argument('-b', '--bookmark', action='store_true',
                            help='Also create a bookmark to this document.')
    add_parser.set_defaults(func=cmd_interface.add)

    # Open parser.
    open_parser = subparsers.add_parser('open',
                                        help='Open a document for viewing.')
    open_parser.add_argument('key', help='Key for document to open.')
    open_parser.add_argument('-b', '--bib', '--bibtex', action='store_true',
                             help='Open bibtex files.')
    open_parser.set_defaults(func=cmd_interface.open)

    # Compile subcommand.
    compile_parser = subparsers.add_parser('compile')
    compile_parser.add_argument('-b', '--bib', '--bibtex', action='store_true',
                                help='Compile bibtex files.')
    compile_parser.add_argument('-t', '--text', action='store_true',
                                help='Compile PDF documents.')
    compile_parser.set_defaults(func=cmd_interface.compile)

    # Where subcommand.
    where_parser = subparsers.add_parser('where',
                                         help='Print library directories.')
    where_parser.add_argument('-a', '--archive', action='store_true',
                              help='Print location of archive.')
    where_parser.add_argument('-s', '--shelves', action='store_true',
                              help='Print location of shelves.')
    where_parser.add_argument('-b', '--bookmarks', action='store_true',
                              help='Print location of bookmarks.')
    where_parser.set_defaults(func=cmd_interface.where)

    # Bookmark subcommand.
    bookmark_parser = subparsers.add_parser('bookmark', aliases=['bm'],
                                            help='Bookmark a document.')
    bookmark_parser.add_argument('key', help='Key for document to bookmark.')
    bookmark_parser.add_argument('name', nargs='?',
                                 help='Name for the bookmark.')
    bookmark_parser.set_defaults(func=cmd_interface.bookmark)

    # Hidden subcommand for generating non-trivial completion lists for
    # commands.
    complete_parser = subparsers.add_parser('complete', help=argparse.SUPPRESS)
    complete_parser.add_argument('cmd')
    complete_parser.set_defaults(func=cmd_interface.complete)

    rekey_parser = subparsers.add_parser(
            'rekey', aliases=['rename'],
            help='Change the name of a key.')
    rekey_parser.add_argument('key', help='The key to change.')
    rekey_parser.add_argument('new-key', nargs='?', help='New key name.')
    rekey_parser.set_defaults(func=cmd_interface.rekey)

    # Every subparser has an associated function, that we extract here.
    args = parser.parse_args()
    args = vars(args)
    func = args.pop('func')
    return args, func


def main():
    if len(sys.argv) <= 1:
        print('Usage: lib command [opts] [args]. Try --help.')
        return 1

    # Load the library manager and command interface.
    try:
        manager = LibraryManager(CONFIG_SEARCH_DIRS, CONFIG_FILE_NAME)
        cmd_interface = LibraryCommandInterface(manager)
    except LibraryException as e:
        print(e.message)
        return 1

    args, func = parse_args(cmd_interface)

    try:
        func(**args)
    except LibraryException as e:
        print(e.message)
        return 1
    return 0


if __name__ == '__main__':
    ret = main()
    exit(ret)

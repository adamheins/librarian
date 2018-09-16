# Built-in.
import os
import shutil
import sys
import textwrap
import yaml

# Third party.
import bibtexparser
from bibtexparser.bwriter import BibTexWriter

# Ours.
from .document import DocumentPaths, ArchivalDocument, DocumentTemplate
from .exceptions import LibraryException
from . import style


def _find_config(search_dirs, config_name):
    ''' Find the path to the configuration file. '''
    for search_dir in search_dirs:
        path = os.path.join(search_dir, config_name)
        if os.path.exists(path):
            return path
    return None


def _key_from_bibtex(bib_path):
    ''' Extract the document key from a bibtex file. '''
    with open(bib_path) as bib_file:
        bib_info = bibtexparser.load(bib_file)

    keys = list(bib_info.entries_dict.keys())
    if len(keys) > 1:
        raise LibraryException('More than one entry in bibtex file.')

    return keys[0]


def _create_count_message(key, count):
    ''' Create a message about count of matches for the given key. '''
    if count == 1:
        return '{}: 1 match'.format(style.bold(key))
    elif count > 1:
        return '{}: {} matches'.format(style.bold(key), count)


def _match_highlighter(match):
    ''' Highlight match. '''
    return style.yellow(match.group(0))


def _summarize_doc(doc, count, verbosity):
    ''' Create a string summary of a document. '''
    if count > 0:
        count_phrase = ' (Matches = {count})'
    else:
        count_phrase = ''

    if doc.venue:
        venue_phrase = '\n{venue}'
    else:
        venue_phrase = ''

    if verbosity == 1:
        tmpl = ''.join(['{title}\n{year} ({key})', count_phrase, '\n{author}'])
    elif verbosity == 2:
        tmpl = ''.join(['{title}\n{year} ({key})', count_phrase, '\n{author}',
                        venue_phrase])
    else:
        tmpl = ''.join(['{key}', count_phrase])

    # Wrap the title at 80 chars.
    title = textwrap.fill(doc.title, width=80)

    # Only apply styling if output is a terminal.
    if sys.stdout.isatty():
        title = style.bold(title)

    return tmpl.format(title=title, year=doc.year, key=doc.key,
                       author='; '.join(doc.authors), venue=doc.venue,
                       count=count)


class LibraryManager(object):
    def __init__(self, search_dirs, config_name):
        config_file_path = _find_config(search_dirs, config_name)
        if config_file_path is None:
            raise LibraryException('Could not find config file.')

        with open(config_file_path) as f:
            config = yaml.load(f)

        self.path = os.path.expanduser(config['library'])
        self.archive_path = os.path.join(self.path, 'archive')
        self.shelves_path = os.path.join(self.path, 'shelves')
        self.bookmarks_path = os.path.join(self.path, 'bookmarks')

        # Check if each of these directories exist.
        for path in [self.path, self.archive_path, self.shelves_path]:
            if not os.path.isdir(path):
                msg = '{} does not exist!'.format(path)
                raise LibraryException(msg)

    def has_key(self, key):
        ''' Returns True if the key is in the archive, false otherwise. '''
        return os.path.isdir(os.path.join(self.archive_path, key))

    def all_docs(self):
        ''' Return all documents in the library. '''
        docs = []
        for key in os.listdir(self.archive_path):
            paths = DocumentPaths(self.archive_path, key)
            docs.append(ArchivalDocument(key, paths))
        return docs

    def all_keys(self):
        ''' List all keys without the overhead of creating full documents for
            each. '''
        return os.listdir(self.archive_path)

    def get_doc(self, key):
        ''' Return a single document from the library. '''
        if not self.has_key(key):
            raise Exception('Key {} not found in archive.'.format(key))
        paths = DocumentPaths(self.archive_path, key)
        return ArchivalDocument(key, paths)

    # def bibtex_dict(self, extra_customization=None):
    #     ''' Load bibtex information as a dictionary. '''
    #     def _bibtex_customizations(record):
    #         record = customization.convert_to_unicode(record)
    #
    #         # Make authors semicolon-separated rather than and-separated.
    #         record['author'] = record['author'].replace(' and', ';')
    #
    #         # Apply extra customization function is applicable.
    #         if extra_customization:
    #             record = extra_customization(record)
    #         return record
    #
    #     # We parse each string of bibtex separately and then merge the
    #     # resultant dictionaries together, so that we can handle malformed
    #     # bibtex files individually.
    #     entries_dict = {}
    #     for doc in self.all_docs():
    #         bib_text = doc.bibtex
    #         # common_strings=True lets us parse the month field as "jan",
    #         # "feb", etc.
    #         parser = bibtexparser.bparser.BibTexParser(
    #                 customization=_bibtex_customizations,
    #                 common_strings=True)
    #         try:
    #             d = bibtexparser.loads(bib_text, parser=parser).entries_dict
    #         except:
    #             bib_file = os.path.basename(doc.paths.bib_path)
    #             print('Encountered an error while processing {}.'.format(bib_file))
    #             continue
    #         entries_dict.update(d)
    #     return entries_dict

    def add(self, pdf_src_path, bib_src_path):
        ''' Add a new document to the archive. Returns the document. '''
        key = _key_from_bibtex(bib_src_path)

        if self.has_key(key):
            msg = 'Archive already contains key {}. Aborting.'.format(key)
            raise LibraryException(msg)

        # Create document structure.
        paths = DocumentPaths(self.archive_path, key)
        os.mkdir(paths.key_path)
        os.mkdir(paths.metadata_path)
        shutil.copy(pdf_src_path, paths.pdf_path)
        shutil.copy(bib_src_path, paths.bib_path)

        return ArchivalDocument(key, paths)

    def rekey(self, old_key, new_key):
        ''' Change the key of an existing document in the archive. '''
        old_paths = self.get_doc(old_key).paths

        # If a new key has not been supplied, we take the key from the bibtex
        # file.
        if new_key is None:
            new_key = _key_from_bibtex(old_paths.bib_path)

        if self.has_key(new_key):
            msg = 'Archive already contains key {}. Aborting.'.format(new_key)
            raise LibraryException(msg)

        new_paths = DocumentPaths(self.archive_path, new_key)

        shutil.move(old_paths.pdf_path, new_paths.pdf_path)
        shutil.move(old_paths.bib_path, new_paths.bib_path)
        shutil.move(old_paths.key_path, new_paths.key_path)

        # Write the new_key to the bibtex file
        with open(new_paths.bib_path, 'r+') as f:
            bib_info = bibtexparser.load(f)
            bib_info.entries[0]['ID'] = new_key
            bib_writer = BibTexWriter()
            f.write(bib_writer.write(bib_info))

    def link(self, key, path):
        ''' Create a symlink to a document in the archive. '''
        path = path if path is not None else key

        src = self.get_doc(key).paths.key_path

        if os.path.isabs(path):
            dest = path
        else:
            dest = os.path.join(os.getcwd(), path)

        if os.path.exists(dest):
            message = 'Symlink {} already exists. Aborting.'.format(path)
            raise LibraryException(message)

        os.symlink(src, dest)

    def fix_link(self, link):
        ''' Fix a link that has broken due to the library being moved. '''
        if not os.path.islink(link):
            raise LibraryException('{} is not a symlink.'.format(link))

        key = os.path.basename(os.readlink(link))

        if not self.has_key(key):
            print('{} does not point to a document in the archive.'.format(link))
            return 1

        # Recreate the link, pointing to the correct location.
        os.remove(link)
        self.link(key, link)

    def fix_links(self, directory):
        ''' Fix all broken links in the directory. '''
        files = os.listdir(directory)
        for link in filter(os.path.islink, files):
            self.fix_link(link)

    def bookmark(self, key, name):
        ''' Create a bookmark 'name' pointing to the key. '''
        # Create the bookmarks directory if it doesn't already exist.
        if not os.path.isdir(self.bookmarks_path):
            os.mkdir(self.self.bookmarks_path)
            print('Created bookmarks directory at: {}'.format(self.bookmarks_path))

        name = name if name is not None else key
        path = os.path.join(self.bookmarks_path, name)
        self.link(key, path)

    def search_text(self, regex, oneline, verbose=False):
        ''' Search for the regex in the PDF documents. '''
        # We assume that we want to search the whole corpus. For single
        # document searches, open the doc in a PDF viewer.
        results = []
        for doc in self.all_docs():
            text, new = doc.text()
            if text is None:
                print('Failed to parse {}.'.format(doc.key))
                continue
            elif new:
                print('Successfully parsed {}.'.format(doc.key))

            count = len(regex.findall(text))
            if count > 0:
                results.append({'key': doc.key, 'count': count, 'detail': ''})

        # Sort and parse the results.
        output = []
        for result in sorted(results, key=lambda result: result['count'],
                             reverse=True):
            msg = _create_count_message(result['key'], result['count'])
            output.append(msg)

        if len(output) == 0:
            return 'No matches in text.'
        elif oneline:
            return '\n'.join(output)
        else:
            return '\n'.join(output) # TODO when more detail is given, use two \n\n

    def search_bibtex(self, regex, oneline):
        ''' Search for the regex in bibtex file. '''
        results = []

        for key, info in self.bibtex_dict().items():
            count = 0
            detail = []
            for field, value in info.items():
                # Skip the ID field; it's already a composition of parts of
                # other fields.
                if field == 'ID':
                    continue

                # Find all the matches.
                matches = regex.findall(value)
                count += len(matches)
                if len(matches) == 0:
                    continue

                # Highlight the matches.
                s = regex.sub(_match_highlighter, value)
                detail.append('  {}: {}'.format(field, s))

            if count > 0:
                results.append({'key': key, 'count': count, 'detail': detail})

    def search_docs(self, key=None, title=None, author=None, year=None,
                    venue=None, entrytype=None, text=None, sort=None,
                    number=None, reverse=False, verbosity=0):
        ''' Search documents for those that match the provided filters and
            produce a summary of the results. '''
        # Find documents matching the criteria.
        tmpl = DocumentTemplate(key, title, author, year, venue, entrytype,
                                text)
        docs = []
        counts = []
        for doc in self.all_docs():
            result, count = doc.matches(tmpl)
            if result:
                docs.append(doc)
                counts.append(count)

        # Sort the matching documents.
        if sort:
            def _doc_sort_key(doc_count_tuple):
                doc, count = doc_count_tuple

                if sort == 'key':
                    return doc.key
                if sort == 'title':
                    return doc.bibtex['title'].lower()
                if sort == 'year':
                    return doc.bibtex['year']
                if sort == 'added':
                    return doc.added_date
                if sort == 'recent':
                    return doc.accessed_date
                if sort == 'matches':
                    return count
                return doc.bibtex['year']

            if sort not in ['key', 'title']:
                reverse = not reverse
            docs_counts = sorted(zip(docs, counts), key=_doc_sort_key,
                                 reverse=reverse)
            docs, counts = tuple(zip(*docs_counts))

        # Limit the number of results.
        if number:
            docs = docs[:number]

        # Format the results.
        summaries = []
        for doc, count in zip(docs, counts):
            summaries.append(_summarize_doc(doc, count, verbosity))

        if len(summaries) == 0:
            return ''
        elif verbosity > 0:
            summary = '\n\n'.join(summaries)
        else:
            summary = '\n'.join(summaries)
        return summary

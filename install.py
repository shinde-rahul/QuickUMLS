from __future__ import unicode_literals, division, print_function

# built in modules
import os
import sys
import time
import codecs
import argparse

# project modules
from toolbox import countlines, CuiSemTypesDB, SimstringDBWriter, mkdir
from constants import HEADERS_MRCONSO, HEADERS_MRSTY

try:
    from unidecode import unidecode
except ImportErrror:
    pass


def get_semantic_types(path, headers):
    sem_types = {}
    with codecs.open(path, encoding='utf-8') as f:
        for i, ln in enumerate(f):
            content = dict(zip(headers, ln.strip().split('|')))

            sem_types.setdefault(content['cui'], []).append(content['sty'])

    return sem_types


def get_mrconso_iterator(path, headers):
    with codecs.open(path, encoding='utf-8') as f:
        for i, ln in enumerate(f):
            content = dict(zip(headers, ln.strip().split('|')))

            if content['lat'] != 'ENG':
                continue

            yield content


def extract_from_mrconso(
        mrconso_path, mrsty_path, opts,
        mrconso_header=HEADERS_MRCONSO, mrsty_header=HEADERS_MRSTY):

    start = time.time()
    print('loading semantic types...', end=' ')
    sys.stdout.flush()
    sem_types = get_semantic_types(mrsty_path, mrsty_header)
    print('done in {:.2f} s'.format(time.time() - start))

    start = time.time()

    mrconso_iterator = get_mrconso_iterator(mrconso_path, mrconso_header)

    total = countlines(mrconso_path)

    processed = set()

    for i, content in enumerate(mrconso_iterator, start=1):

        if i % 100000 == 0:
            delta = time.time() - start
            status = (
                '{:,} in {:.2f} s ({:.2%}, {:.1e} s / term)'
                ''.format(i, delta, i / total, delta / i)
            )
            print(status)

        concept_text = content['str'].strip()

        if opts.lowercase:
            concept_text = concept_text.lower()

        if opts.normalize_unicode:
            concept_text = unidecode(concept_text)

        if concept_text in processed:
            continue
        else:
            processed.add(concept_text)

        yield (concept_text, content['cui'], sem_types[content['cui']])


def parse_and_encode_ngrams(extracted_it, simstring_dir, cuisty_dir):
    # Create destination directories for the two databases
    mkdir(simstring_dir)
    mkdir(cuisty_dir)

    ss_db = SimstringDBWriter(simstring_dir)

    cuisty_db = CuiSemTypesDB(cuisty_dir)

    for i, (term, cui, stys) in enumerate(extracted_it, start=1):
        ss_db.insert(term)
        cuisty_db.insert(term, cui, stys)


def driver(opts):
    if opts.normalize_unicode:
        try:
            unidecode
        except NameError:
            err = ('`unidecode` is needed for unicode normalization'
                   'please install it via the `[sudo] pip install '
                   'unidecode` command.')
            print(err, file=sys.stderr)
            exit(1)

        flag_fp = os.path.join(opts.destination_path, 'normalize-unicode.flag')
        open(flag_fp, 'w').close()

    if opts.lowercase:
        flag_fp = os.path.join(opts.destination_path, 'lowercase.flag')
        open(flag_fp, 'w').close()

    mrconso_path = os.path.join(opts.umls_installation_path, 'MRCONSO.RRF')
    mrsty_path = os.path.join(opts.umls_installation_path, 'MRSTY.RRF')

    mrconso_iterator = extract_from_mrconso(mrconso_path, mrsty_path, opts)

    simstring_dir = os.path.join(opts.destination_path, 'umls-simstring.db')
    cuisty_dir = os.path.join(opts.destination_path, 'cui-semtypes.db')

    parse_and_encode_ngrams(mrconso_iterator, simstring_dir, cuisty_dir)

    print('Completed!')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument(
        'umls_installation_path',
        help=('Location of UMLS installation files (`MRCONSO.RRF` and '
              '`MRSTY.RRF` files)')
    )
    ap.add_argument(
        'destination_path',
        help='Location where the necessary QuickUMLS files are installed'
    )
    ap.add_argument(
        '-L', '--lowercase', action='store_true',
        help='Consider only lowercase version of tokens'
    )
    ap.add_argument(
        '-U', '--normalize-unicode', action='store_true',
        help='Normalize unicode strings to their closest ASCII representation'
    )
    opts = ap.parse_args()

driver(opts)

import csv
import sys
import argparse
from io import StringIO
import requests
import hashlib
import logging


logger = logging.getLogger('evr')


class VerificationException(Exception):
    pass


def manifest_rows(base_url):
    response = requests.get(base_url + 'manifest.csv')
    response.raise_for_status()
    reader = csv.reader(StringIO(response.text))
    rows = list(reader)
    rows.reverse()
    return rows


def verify_blockchain(rows):
    latest_hash = ''
    for line in rows:
        hasher = hashlib.sha256()
        hasher.update(latest_hash.encode('ascii'))
        hasher.update(line[1].encode('ascii'))
        latest_hash = hasher.hexdigest()
        if latest_hash != line[2]:
            raise VerificationException('Mismatch on day {}: Expected {}, got {}'.format(
                line[0], latest_hash, line[2]
            ))
    return True


def date_hash(base_url, date):
    response = requests.get(base_url + 'archive/' + date + '.csv')
    response.raise_for_status()
    hasher = hashlib.sha256(response.content)
    h = hasher.hexdigest()
    logging.debug('Day %s has hash %s', date, h)
    return h


def fast_forward(base_url, start):
    rows = manifest_rows(base_url)
    verify_blockchain(rows)
    found = start == ''
    for row in rows:
        if row[2] == start:
            found = True
        elif found:
            h = date_hash(base_url, row[0])
            if h != row[1]:
                raise VerificationException('Mismatch on day {}: Expected {}, got {}'.format(
                    row[0], row[1], h
                ))
    if found:
        return rows[-1][2]
    else:
        raise VerificationException('Start hash not found')


description = """
coloradolottery.com EVR verification.

Given a previous hash, this script will verify:
- Hashes of the daily files after the start hash
- Blockchain hashes after the start hash, to return a new start hash for the
  next round of verification.

For the first run, provide an empty string as the start hash, and all daily
files in the manifest will be verified.
"""


def main():
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('previous_hash', nargs=1)
    parser.add_argument(
        '--base', dest='base_url', default='https://www.coloradolottery.com/evr/'
    )
    parser.add_argument('-v', '--verbose', help='Include debug output', action='store_true')
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    try:
        next_hash = fast_forward(args.base_url, args.previous_hash[0])
    except VerificationException as e:
        sys.stderr.write(repr(e))
        sys.stderr.write('\n')
        sys.exit(1)
    else:
        print(next_hash)
        sys.exit(0)


if __name__ == '__main__':
    main()

import re
import click
from datetime import datetime, date
from difflib import SequenceMatcher
from collections import defaultdict

try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract

month_name_to_int_map = {
    'jan': 1,
    'febr': 2,
    'marc': 3,
    'márc': 3,
    'ápr': 4,
    'máj': 5,
    'jun': 6,
    'jul': 7,
    'aug': 8,
    'szept': 9,
    'okt': 10,
    'nov': 11,
    'dec': 12,
}


@click.command()
@click.argument('files', nargs=-1)
def cli(files):
    """ Read transactions from images passed as a glob (expansion happens at shell)
        Usage:
        python main.py images/*
    """

    output = []
    for name in files:
        print(f'processing file... {name}')
        rows = pytesseract.image_to_string(Image.open(name)).splitlines()
        # Remove empty lines
        rows = filter(None, rows)
        output.extend(rows)
        print(f'processed file!')

    transactions = defaultdict(list)
    transaction_date = None

    for row in output:

        # Revolut prints transaction date as 'Ma' for today, here we trust OCR that it is able to read that
        if row == 'Ma':
            transaction_date = date.today()
            continue

        match = re.search('([0-9]{2}) ([A-Za-z]+)\. ?([0-9]{4})?', row)
        if match is not None:
            day, month, year = match.groups()
            if year is None:
                year = date.today().year

            # map hungarian month name to integer
            month = month_name_to_int_map[month]

            transaction_date = date(*map(int, (year, month, day)))
            continue

        # TODO: Make this python3 assignment expr
        else:
            # Match Stock and amount
            # Order matters here as stock is easier to match and will be always UPPER
            payment_type = None
            match = re.search('([A-Z]+) ([-+] ?\d+ ?0?\d+?,\d+)', row)
            if match is not None:
                stock, amount = match.groups()

                # Convert amount to float format
                amount = float(amount.replace(' ', '').replace(',', '.'))

                if transaction_date is not None:
                    transactions[transaction_date].append((stock, amount))

                continue

            # Match other payment
            match = re.search('([\w ]+) ([-+] ?\d+ ?0?\d?,?\d+)', row)
            if match is not None:
                payment_type, amount = match.groups()

                # Convert amount to float format
                amount = float(amount.replace(' ', '').replace(',', '.'))

                types = ['Egyszeri befizetés', 'Letétkezelési dij', 'Kivétel', 'Osztalék']

                payment_type = [t for t in types if SequenceMatcher(None, t, payment_type).ratio() > 0.6]


                if payment_type:
                    if transaction_date:
                        transactions[transaction_date].append((payment_type[0], amount))

            # if not payment_type:
            #     print(row)

    transactions = {k: set(v) for k,v in transactions.items()}
    for k, vs in transactions.items():
        for v in vs:
            # Print rows in dummy csv format for Google sheet
            print('{};{};{}'.format(k,v[0], str(v[1]).replace('.', ',')))

if __name__ == '__main__':
    cli()
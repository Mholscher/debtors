#    Copyright 2020 Menno Hölscher
#
#    This file is part of debtors.

#    debtors is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    debtors is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with debtors.  If not, see <http://www.gnu.org/licenses/>.

""" This module contains functions for formatting and checking monetary
    values.

    Currently it is part of debtors, it will be a separate package later.
    """

from collections import Counter
from iso4217 import raw_table
from locale import localeconv

def edited_amount(amount, precision=2, currency=None):
    """ This routine edits an amount

    The amount is edited with "precision" digits following the decimal
    point/comma. However, you can also pass in a currency code, which makes
    it default to the fraction as in iso4217 (currency table).

    The decimal separation character is taken from the locale of the machine
    the program is running on. That means the editing may look "weird" to
    some of the users. E.g. an amount in US Dollars will have comma as decimal
    separation character if the server has a German locale...
    """

    def thousand_separator_step(start, end, step):
        """ Geef de posities terug waar we een duizendtalscheiding moeten
        aanbrengen.
        """

        while start > end:
            yield start
            start += step

    ldb = localeconv()
    if currency:
        try:
            precision = int(raw_table[currency]['CcyMnrUnts'])
        except KeyError as ke:
            raise ValueError(currency + ' is not a valid currency')
    edited = str(amount)
    x = len(edited)
    if x <= precision:
        edited = ('0' * (precision -x + 1)) + edited
    edited = edited[:-1 * precision] + ldb['mon_decimal_point'] +\
        edited[-1 * precision:] if precision > 0\
            else edited

    decimal_char_pos = edited.find(ldb['mon_decimal_point'])
    if decimal_char_pos == -1:
        decimal_char_pos = len(edited)
    for pos in thousand_separator_step(decimal_char_pos - 3, 0, -3):
        edited = edited[:pos] + ldb['mon_thousands_sep'] + edited[pos:]

    return edited

def internal_amount(amount_string):
    """ This routine translates an amount string to a smallest unit amount

    The decimal separator is removed from the amount, as are the "thousand"
    separators.
    """

    amount_string = ''.join(amount_string.split(sep=','))
    amount_string = ''.join(amount_string.split(sep='.'))
    amount_string = ''.join(amount_string.split(sep=' '))
    return int(amount_string)

def validate_amount(amount_string, precision=2, currency=None):
    """ Validate that the passed in string contains a valid amount 
    
    It returns an internal amount if it succeeds, throws a ValueError
    in case of failure.
    """

    if currency:
        try:
            precision = int(raw_table[currency]['CcyMnrUnts'])
        except KeyError as ke:
            raise ValueError(currency + ' is not a valid currency')
    ldb = localeconv()

    if precision == 0 and ldb['mon_decimal_point'] in amount_string:
        raise ValueError('The amount cannot contain a decimal separator')

    c = Counter(amount_string)
    no_of_decimal_separators = c[ldb['mon_decimal_point']]
    if no_of_decimal_separators > 1:
        raise ValueError('Only one decimal point separator allowed')

    if no_of_decimal_separators == 1:
        amount_split = amount_string.split(sep=ldb['mon_decimal_point'])
        if len(amount_split[-1]) > precision:
            raise ValueError('Too many decimal places')

    sign = '+'
    if amount_string[-1] == ldb['negative_sign']\
        or amount_string[-1] == ldb['positive_sign'] :
        sign = amount_string[-1]
        amount_string = amount_string[:-1]
    try:
        internal =  internal_amount(amount_string)
    except ValueError as ve:
        raise ValueError('Value is not a valid amount')
    if sign == ldb['negative_sign']:
        internal = internal * -1

    if no_of_decimal_separators == 0:
        internal = internal * (10 ** precision)
    else:
        if len(amount_split[-1]) < precision:
            internal = internal * (10 ** (precision - len(amount_split[-1])))

    return internal


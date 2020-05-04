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

import unittest
import locale
from debtviews.monetary import edited_amount, internal_amount, validate_amount

class TestMoneyConversions(unittest.TestCase):

    # These tests assume a locale where nl_langinfo(RADIXCHAR) is ','
    def setUp(self):

        locale.setlocale(locale.LC_ALL, '')

    def test_convert_cents_to_string(self):
        """ We can convert an integer to an amount """

        amount_cents = 22654
        edited = edited_amount(amount_cents, precision=2)
        self.assertEqual('226,54', edited, 'Incorrect conversion')

    def test_convert_whole_to_string(self):
        """ We can convert an integer to an amount without decimals """

        amount_cents = 24454
        edited = edited_amount(amount_cents, precision=0)
        self.assertEqual('24454', edited, 'Incorrect conversion')

    def test_convert_tenths_to_string(self):
        """ We can convert an integer to an amount with 1 decimal position """

        amount_cents = 1624654
        edited = edited_amount(amount_cents, precision=1)
        self.assertEqual('162465,4', edited, 'Incorrect conversion')

    def test_length_amount_less_precision(self):
        """ We can convert an amount with length less than precision """

        amount_cents = 4
        edited = edited_amount(amount_cents, precision=2)
        self.assertEqual('0,04', edited, 'Incorrect conversion')

    def test_length_amount_large_precision(self):
        """ We can convert an amount with large precision """

        amount_cents = 27
        edited = edited_amount(amount_cents, precision=4)
        self.assertEqual('0,0027', edited, 'Incorrect conversion')


class TestConvertToInternal(unittest.TestCase):

    def test_convert_amount_cents(self):
        """ We can convert an edited amount to an internal amount """

        amount_string = '17,66'
        internal = internal_amount(amount_string)
        self.assertEqual(1766, internal, 'Conversion 2 decimal places failed')

    def testconvert_amount_no_precision(self):


        amount_string = '17366'
        internal = internal_amount(amount_string)
        self.assertEqual(17366, internal, 'Conversion no decimal places failed')

    def test_convert_amount_precision_4(self):
        """ We can convert an amount with 4 decimal places """

        amount_string = '11.7366'
        internal = internal_amount(amount_string)
        self.assertEqual(117366, internal, 'Conversion 4 decimal places failed')

    def test_convert_with_thousand_separator_point(self):
        """ We can convert an amount wih thousand separator '.' """

        amount_string = '1.011,66'
        internal = internal_amount(amount_string)
        self.assertEqual(101166, internal, 'Conversion 1000-separator failed')

    def test_convert_with_thousand_separator_space(self):
        """ We can convert an amount wih thousand separator ' ' """

        amount_string = '1 071,61'
        internal = internal_amount(amount_string)
        self.assertEqual(107161, internal, 'Conversion 1000-separator failed')

    def test_invalid_character_in_amount_fails(self):
        """ An invalid character in an amount makes conversion fail """

        amount_string = '$ 1 702.88'
        with self.assertRaises(ValueError):
            internal = internal_amount(amount_string)

    def test_amount_no_decimal_to_cents(self):

        amount_string = ''.join(('884665'))
        a = validate_amount(amount_string, precision=2)
        self.assertEqual(88466500, a, 'Number of decimals wrong')


class TestWithCurrency(unittest.TestCase):

    def test_currency_with_precision_2(self):
        """ A currency with cents formats with 2 digit precision """

        amount_cents = 22778
        edited = edited_amount(amount_cents, currency='EUR')
        self.assertEqual('227,78', edited, 'Incorrect conversion')

    def test_currency_precision_0(self):
        """ A currency with no precision formats correctly """

        amount_cents = 22368
        edited = edited_amount(amount_cents, currency='JPY')
        self.assertEqual('22368', edited, 'Incorrect conversion')

    def test_invalid_ccy_fails(self):
        """ We get an error if we try a non-existing currency """

        amount_cents = '70281'
        with self.assertRaises(ValueError):
            edited = edited_amount(amount_cents, currency='BSB')

    def test_currency_and_precision(self):
        """ If a currency and precision are passed, prefer currency """

        amount_cents = 71544
        edited = edited_amount(amount_cents, precision=2, currency='JPY')
        self.assertEqual('71544', edited, 'Incorrect conversion')


class TestAmountFormat(unittest.TestCase):
    """ Make sure a string 'amount' is properly formatted """

    def setUp(self):

        locale.setlocale(locale.LC_ALL, '')

    def test_decimal_precision_0_fails(self):
        """ The amount contains no decimal separator """

        ldb = locale.localeconv()
        amount_string = ''.join(('27659', ldb['mon_decimal_point'], '88'))
        with self.assertRaises(ValueError):
            a = validate_amount(amount_string, precision=0)

    def test_one_decimal_position(self):
        """ The amount contains only one decimal separator """

        ldb = locale.localeconv()
        amount_string = ''.join(('27676', ldb['mon_decimal_point'], '17'))
        a = validate_amount(amount_string, precision=2)
        self.assertEqual(2767617, a, 'Validation failed unexpectedly')

    def test_two_decimal_separators_fail(self):
        """ We cannot have two decimal separators """

        ldb = locale.localeconv()
        amount_string = ''.join(('27274', ldb['mon_decimal_point'], '98',
                                 ldb['mon_decimal_point'], '3'))
        with self.assertRaises(ValueError):
            a = validate_amount(amount_string, precision=2)

    def test_thousand_separators_are_not_checked(self):
        """ We can put thousand separators where we want """

        ldb = locale.localeconv()
        amount_string = ''.join(('27274', ldb['mon_thousands_sep'], '98',
                                 ldb['mon_thousands_sep'],'665'))
        a = validate_amount(amount_string, precision=0)
        self.assertEqual(2727498665, a, 'Value validated incorrectly')

    def test_negative_sign_leading(self):
        """ A negative sign leading is processed correctly """

        ldb = locale.localeconv()
        amount_string = ''.join(('-4', ldb['mon_thousands_sep'], '665'))
        a = validate_amount(amount_string, precision=2)
        self.assertEqual(-466500, a, 'Negative value validated wrongly')

    def test_negative_sign_trailing(self):
        """ A negative sign trailing is processed correctly """

        ldb = locale.localeconv()
        amount_string = ''.join(('66', ldb['mon_thousands_sep'], '875-'))
        a = validate_amount(amount_string, precision=2)
        self.assertEqual(-6687500, a, 'Negative value validated wrongly')

    def test_positive_sign_leading(self):
        """ A leading positive sign make no difference """

        ldb = locale.localeconv()
        amount_string = ''.join(('+4', ldb['mon_thousands_sep'], '903'))
        a = validate_amount(amount_string, precision=4)
        self.assertEqual(49030000, a, 'Positive value validated wrongly')


if __name__ == '__main__' :
    unittest.main()

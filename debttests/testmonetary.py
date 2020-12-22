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
from werkzeug.datastructures import ImmutableMultiDict
from debtors import app
try:
    from debtviews.wtformsmonetary import AmountField
    from wtforms import Form, StringField
    wtforms_present = True
except ImportError:
    wtforms_present = False

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
        self.assertEqual('24 454', edited, 'Incorrect conversion')

    def test_convert_tenths_to_string(self):
        """ We can convert an integer to an amount with 1 decimal position """

        amount_cents = 1624654
        edited = edited_amount(amount_cents, precision=1)
        self.assertEqual('162 465,4', edited, 'Incorrect conversion')

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

    def setUp(self):

        locale.setlocale(locale.LC_ALL, '')

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

    def setUp(self):

        locale.setlocale(locale.LC_ALL, '')

    def test_currency_with_precision_2(self):
        """ A currency with cents formats with 2 digit precision """

        amount_cents = 22778
        edited = edited_amount(amount_cents, currency='EUR')
        self.assertEqual('227,78', edited, 'Incorrect conversion')

    def test_currency_precision_0(self):
        """ A currency with no precision formats correctly """

        amount_cents = 22368
        edited = edited_amount(amount_cents, currency='JPY')
        self.assertEqual('22 368', edited, 'Incorrect conversion')

    def test_invalid_ccy_fails(self):
        """ We get an error if we try a non-existing currency """

        amount_cents = '70281'
        with self.assertRaises(ValueError):
            edited = edited_amount(amount_cents, currency='BSB')

    def test_currency_and_precision(self):
        """ If a currency and precision are passed, prefer currency """

        amount_cents = 71544
        edited = edited_amount(amount_cents, precision=2, currency='JPY')
        self.assertEqual('71 544', edited, 'Incorrect conversion')

    def test_amount_no_precision_with_comma_fails(self):
        """ Currency has no precision, entering an amount with comma fails """

        amount_string = '8 875,90'
        with self.assertRaises(ValueError):
            internal = validate_amount(amount_string, currency='JPY')


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


class AmountHolder():

    def __init__(self, integer_amount=0, currency=None):

        self.amount = integer_amount


if wtforms_present:
    class FormWithAmount(Form):

        a_field = StringField("The stringfield")
        amount = AmountField()

    class FormWithAmountNoPrecision(Form):

        a_field = StringField("The stringfield")
        amount = AmountField("The label", currency='JPY')

class TestWTFormsAmountField(unittest.TestCase):

    def setUp(self):

        locale.setlocale(locale.LC_ALL, '')
        self.amount_holder = AmountHolder(6654)

    @unittest.skipIf(not wtforms_present, 'No wtforms amountfield found')
    def test_set_amount_value(self):
        """ We can set a value in the amount field """

        # Populate the amount field
        with app.test_request_context('/bill/new', data=dict()):
            amount_form = FormWithAmount(amount=self.amount_holder.amount)
        self.assertEqual(6654, amount_form.amount.data,
                         'Not correctly populated')

    @unittest.skipIf(not wtforms_present, 'No wtforms amountfield found')
    def test_set_amount_from_obj(self):
        """ We can set a value in the amount field """

        # Populate the amount field
        with app.test_request_context('/bill/new', data=dict()):
            amount_form = FormWithAmount(obj=self.amount_holder)
        self.assertEqual(6654, amount_form.amount.data,
                         'Not correctly populated')

    @unittest.skipIf(not wtforms_present, 'No wtforms amountfield found')
    def test_internalize_amount_from_form(self):
        """ We can make an internal amount from the form amount field """

        amount_holder = AmountHolder(1254)
        with app.test_request_context('/bill/new', data=dict()):
            amount_form = FormWithAmount(obj=amount_holder)
        amount_form.amount.currency = 'USD'
        self.assertEqual(1254, amount_form.amount.data,
                         'Internal amount returned incorrect')
        self.assertEqual('12,54', amount_form.amount._value(),
                         'External amount wrong')

    @unittest.skipIf(not wtforms_present, 'No wtforms amountfield found')
    def test_internalize_amount_no_precision_from_form(self):
        """ We can make an internal amount from the form amount field """

        amount_holder = AmountHolder(127)
        with app.test_request_context('/bill/new', data=dict()):
            amount_form = FormWithAmountNoPrecision()
        amount_form.amount.data = 1276
        self.assertEqual(1276, amount_form.amount.data,
                         'Internal amount returned incorrect')
        self.assertEqual('1 276', amount_form.amount._value(),
                         'External amount wrong')

    @unittest.skipIf(not wtforms_present, 'No wtforms amountfield found')
    def test_amount_zero(self):
        """ A zero amount in the field returns '0' """

        amount_holder = AmountHolder(0)
        with app.test_request_context('/bill/new', data=dict()):
            amount_form = FormWithAmount(obj=amount_holder)
        self.assertEqual(0, amount_form.amount.data, 'Amount not zero')
        self.assertEqual('0,00', amount_form.amount._value(),
                         'Amount external not correct')

    @unittest.skipIf(not wtforms_present, 'No wtforms amountfield found')
    def test_amount_zero_no_precision(self):
        """ An amount with precision 0 is formatted properly """

        amount_holder = AmountHolder(17)
        amount_form = FormWithAmountNoPrecision(obj=amount_holder)
        self.assertEqual(17, amount_form.amount.data, 'Amount incorrect')
        self.assertEqual('17', amount_form.amount._value(),
                         'Amount external not correct')

    @unittest.skipIf(not wtforms_present, 'No wtforms amountfield found')
    def test_input_amount_no_precision(self):
        """ If we input an amount no decimal it is processed right """

        fd = ['15']
        amount_form = FormWithAmountNoPrecision(obj=self.amount_holder)
        amount_form = FormWithAmountNoPrecision(formdata=ImmutableMultiDict(
            [('a_field', 'value'), ('amount', '15')]))
        self.assertEqual(15, amount_form.amount.data, 'Amount incorrect')
        self.assertEqual('15', amount_form.amount._value(),
                         'Amount external not correct')

    @unittest.skipIf(not wtforms_present, 'No wtforms amountfield found')
    def test_amount_empty_does_not_show(self):
        """ An empty amount is not shown as zeroes """

        amount_form = FormWithAmount()
        self.assertNotEqual('0,00', amount_form.amount._value(),
                            'Amount is zero, not space')

    @unittest.skipIf(not wtforms_present, 'No wtforms amountfield found')
    def test_amount_invalid_fails(self):
        """ An empty amount is not shown as zeroes """

        holder = AmountHolder('23a55')
        with self.assertRaises(ValueError):
            amount_form = FormWithAmount(obj=holder)
            #print(holder.amount)
            amount_form.amount.process_formdata([holder.amount])


if __name__ == '__main__' :
    unittest.main()

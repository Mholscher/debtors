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

""" This module has the definition for wtforms fields. It is attached to
the monetary package, but it is not required to use monetary. Only if 
you want to use wtforms, this is a handy module to use.
"""

from wtforms import Field
from wtforms.widgets import TextInput
from debtviews.monetary import edited_amount, internal_amount, validate_amount

class AmountField(Field):
    """ This class represents a formfield for amounts 

    The field has a value that is the amount itself. To be able to validate
    the amount, we need the currency. A callback can be supplied to fetch
    the currency. This callback takes no parameters.
    """

    widget = TextInput()

    def __init__(self, label='', validators=[], filters=(), currency=None, 
                 **kwargs):

        self.currency = currency
        if currency is None and hasattr(self, 'get_currency'):
            self.currency = self.get_currency()
        super(AmountField, self).__init__(label, validators, **kwargs)

    def _value(self):
        """ Set the value to the external value """

        if self.raw_data:
            return self.raw_data[0]
        if self.data is None:
            return ''
        return edited_amount(self.data, currency=self.currency)
    def process_formdata(self, valuelist):
        """ Set the data to the value retrieved from the form data """

        if valuelist and valuelist[0]:
            try:
                self.data = self.internal_amount(valuelist[0])
            except ValueError as ve:
                raise
        elif self.data is None:
            self.data = ''

    def internal_amount(self, external_amount):
        """ Convert the data to an internal amount

        This function can be replaced to conform to special wishes. 
        The default is to convert an amount with the currency passed in at
        the time of creation.
        """

        return validate_amount(external_amount, currency=self.currency)


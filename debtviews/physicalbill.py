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

""" This module takes care of converting model entities to view entities.

The models fields are conmverted to something the templating environment can
relate to. In this case Jinja2, it knows how to translate numbers to a string,
so we don't bother replacing those, but dates etc. are translated
into printable data.
"""

from datetime import date
from jinja2 import Environment, PackageLoader
from iso4217 import raw_table as currencytable
from debtviews.monetary import edited_amount
from debtmodels.debtbilling import Bills

rtfenvironment = Environment(
    loader=PackageLoader('debtors', 'templates'),
    block_start_string='<%', block_end_string='%>',
    variable_start_string='<<', variable_end_string='>>',
    trim_blocks=True, lstrip_blocks=True,
    autoescape=False)

def rtf(to_encode):
    """ This routine transcripts unicode strings to be usable in
    rtf (rich text format) files.
    
    According to the documentation rtf supports unicode, but not so nice. You 
    can enter codepoints in decimal (e.g. \\u233 is é), and after that you have
    to insert a replacement character. The replacement character is simply
    the question mark.
    """
    
    result = ""
    if not to_encode:
        return to_encode
    for letter in to_encode:
        i = ord(letter)
        if i < 128:
            result = result + letter
        else:
            result = result + "\\u" + str(i) + '?'
    return result


class BillDictView(dict):
    """ This class edits the information of a bill into a dictionary

    The dictionary is the input for the view (MVC view) when we 
    want to create 'physical' billing artefact.

    As billing artefacts want string representations, we gather the 
    conversions to string in this class.
    """

    def __init__(self, bill_id=None):

        self.bill = Bills.get_bill_by_id(bill_id)
        self.client = self.bill.client
        self["bill"] = self._create_bill_dict()
        self["client"] = self._create_client_dict()
        self["date"] = rtf(date.today().strftime("%d %B %Y"))

    def _create_bill_dict(self):
        """ Create the dictionary view of the bill """

        bill_dict = {"bill_id" : self.bill.bill_id,
                     "date_sale" : rtf(self.bill.date_sale.strftime("%d-%m-%Y")),
                     "billing_ccy" : currencytable[self.bill.billing_ccy]["CcyNm"]}
        bill_dict["lines"] = []
        self.total = 0
        for line in self.bill.lines:
            bill_dict["lines"].append(self._create_line_dict(line))
            self.total += line.number_of * line.unit_price
        bill_dict["total"] = edited_amount(self.total, 
                                           currency=self.bill.billing_ccy)
        return bill_dict

    def _create_client_dict(self):
        """ Create the dictionary view of the client """

        client_dict = {"initials" : rtf(self.client.initials),
                       "surname" : rtf(self.client.surname) }
        address = self.client.postal_address()
        if address:
            if address.po_box:
                client_dict["po_box"] = address.po_box
            else:
                client_dict["street"] = address.street
                client_dict["house_number"] = address.house_number
            client_dict["postcode"] = address.postcode
            client_dict["town_or_village"] = address.town_or_village
        return client_dict

    def _create_line_dict(self, line):
        """ We create the line dictionary for one bill line """

        line_dict = {"id" : line.line_id,
                     "short_desc" : rtf(line.short_desc),
                     "number_of" : line.number_of,
                     "unit_price" : edited_amount(line.unit_price,
                                            currency=self.bill.billing_ccy),
                     "total" : edited_amount(line.number_of * line.unit_price,
                                    currency=self.bill.billing_ccy)}
        if line.long_desc:
            line_dict["long_desc"] = rtf(line.long_desc)
        if line.measured_in:
            line_dict["measured_in"] = rtf(str(line.measured_in))
        return line_dict

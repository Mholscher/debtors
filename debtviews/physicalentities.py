#    Copyright 2021 Menno Hölscher
#
#    This file is part of Debtors.

#    Debtors is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    Debtors is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with Debtors.  If not, see <http://www.gnu.org/licenses/>.
""" This module contains shared entities to produce documents (letters and
invoices) for sending to clients. 
"""

from iso4217 import raw_table as currencytable
from debtviews.outputenvironments import (rtfenvironment, htmlenvironment,
                                          rtf)
from debtviews.monetary import edited_amount


class GeneralCorrespondence():
    """ The class that creates shared dictionaries for correspondence """

    def _create_bill_dict(self, bill):
        """ Create the dictionary view of the bill """

        bill_dict = {"bill_id": bill.bill_id,
                     "date_sale":
                         rtf(bill.date_sale.strftime("%d-%m-%Y")),
                     "billing_ccy":
                         currencytable[bill.billing_ccy]["CcyNm"]}
        bill_dict["lines"] = []
        self.total = 0
        for line in bill.lines:
            bill_dict["lines"].append(self._create_line_dict(line))
            self.total += line.number_of * line.unit_price
        bill_dict["total"] = edited_amount(self.total,
                                           currency=bill.billing_ccy)
        return bill_dict

    def _create_line_dict(self, line):
        """ We create the line dictionary for one bill line """

        line_dict = {"id": line.line_id,
                     "short_desc": rtf(line.short_desc),
                     "number_of": line.number_of,
                     "unit_price": edited_amount(line.unit_price,
                                        currency=self.bill.billing_ccy),
                     "total": edited_amount(line.number_of * line.unit_price,
                                            currency=self.bill.billing_ccy)}
        if line.long_desc:
            line_dict["long_desc"] = rtf(line.long_desc)
        if line.measured_in:
            line_dict["measured_in"] = rtf(str(line.measured_in))
        return line_dict

    def _create_client_dict(self, client):
        """ Create the dictionary view of the client """

        client_dict = {"initials": rtf(client.initials),
                       "surname": rtf(client.surname)}
        address = client.postal_address()
        if address:
            if address.po_box:
                client_dict["po_box"] = address.po_box
            else:
                client_dict["street"] = address.street
                client_dict["house_number"] = address.house_number
            client_dict["postcode"] = address.postcode
            client_dict["town_or_village"] = address.town_or_village
        email = client.preferred_mail()
        if email:
            client_dict['email'] = email
        return client_dict

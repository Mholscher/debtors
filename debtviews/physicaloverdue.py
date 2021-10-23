#    Copyright 2021 Menno Hölscher
#
#    This file is part of Debtors.

#    Debtors is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    Debtors is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with Debtors.  If not, see <http://www.gnu.org/licenses/>.

""" This module holds the out processing parts of the overdue processors.

As a reminder: a set of overdue processors is delivered with Debtors. They
are not the "end-all" with respect to overdue processing, just examples of
a way to process overdue and its output. 
"""

from datetime import date
from iso4217 import raw_table as currencytable
from debtviews.monetary import edited_amount
from debtmodels.debtbilling import Bills
from debtviews.outputenvironments import (rtfenvironment, htmlenvironment,
                                          rtf)


class OverdueDictView(dict):
    """ Overdue data for letter production.

    When creating an overdue letter, all data will be assembled in an instance
    of this dictionary. The data consists of:

        :bill data: The data of the bill triggering overdue processing
        :other bills: a list structure with the data of other bills to appear on the letter
        :payments: a list with received payments which have not been fully assigned
        :client: Data for the client that should pay the bill

    """

    def __init__(self, bill_id):

        self.bill = Bills.query.filter_by(bill_id=bill_id).first()
        self.client = self.bill.client
        self["bill"] = self._create_bill_dict()
        self["morebills"] = self._create_bill_list()
        self["client"] = self._create_client_dict()
        self["payments"] = self._create_payment_list()

    def _create_bill_dict(self):
        """ Create the "bill part" of the dictionary """

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
        email = self.client.preferred_mail()
        if email:
            client_dict['email'] = email
        return client_dict

    def _create_payment_list(self):
        """ Create a list of payments from the client not fully assigned """

        payment_list = self.bill.client.payments
        payment_list_dict = []
        for payment in payment_list:
            payment_dict = self._create_payment_dict(payment)
            payment_list_dict.append(payment_dict)
        return payment_list_dict

    def _create_payment_dict(self, payment):
        """ Create a dictionary from  payment """

        payment_dict = {"id" : payment.id,
                        "payment_ccy" : currencytable[payment.payment_ccy]["CcyNm"],
                        "payment_amount" :
                            edited_amount(payment.payment_amount)}
        payment_dict["debcred"] = payment.debcred
        payment_dict["value_date"] =\
            rtf(payment.value_date.strftime("%d-%m-%Y"))
        return payment_dict

    def _create_bill_list(self):
        """ Create the list with the other debt

        All the clients debt will appear on the client letter. This function 
        returns the list of bills in debt that are not the bill that 
        triggered sending of the letter.
        """

        return [self._create_other_bill_dict(bill)
                for bill in self.client.bills if bill != self.bill]

    def _create_other_bill_dict(self, bill):
        """ Returns a bill dictionary for a bill """

        bill_dict = {"bill_id" : bill.bill_id,
                     "date_sale" : rtf(bill.date_sale.strftime("%d-%m-%Y")),
                     "billing_ccy" : currencytable[bill.billing_ccy]["CcyNm"]}
        bill_dict["lines"] = []
        total = 0
        for line in bill.lines:
            bill_dict["lines"].append(self._create_line_dict(line))
            total += line.number_of * line.unit_price
        bill_dict["total"] = edited_amount(total, 
                                           currency=bill.billing_ccy)
        return bill_dict



class PaperLetter():
    """ This models a paper interface, created from a rtf template """

    def __init__(self, template_name=None, bill=None):

        self.template = rtfenvironment.get_template(template_name)
        bill_dict = OverdueDictView(bill.bill_id)
        self.text = self.template.render(bill_dict)

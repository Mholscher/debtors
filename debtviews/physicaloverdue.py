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

""" This module holds the out processing parts of the overdue processors.

As a reminder: a set of overdue processors is delivered with Debtors. They
are not the "end-all" with respect to overdue processing, just examples of
a way to process overdue and its output.
"""

from datetime import date
from email.message import EmailMessage
from iso4217 import raw_table as currencytable
from debtviews.monetary import edited_amount
from debtmodels.debtbilling import Bills
from debtviews.outputenvironments import (rtfenvironment, htmlenvironment,
                                          rtf)
from debtviews.physicalentities import GeneralCorrespondence


class OverdueDictView(dict, GeneralCorrespondence):
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
        self["bill"] = self._create_bill_dict(self.bill)
        self["morebills"] = self._create_bill_list()
        self["client"] = self._create_client_dict(self.client)
        self["payments"] = self._create_payment_list()
        self["date"] = rtf(date.today().strftime("%d %B %Y")) 

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

        payment_dict = {"id": payment.id,
                        "payment_ccy":
                            currencytable[payment.payment_ccy]["CcyNm"],
                        "payment_amount":
                            edited_amount(payment.payment_amount,
                                          currency=payment.payment_ccy)}
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
                for bill in self.client.bills if bill != self.bill
                and bill.status == Bills.ISSUED]

    def _create_other_bill_dict(self, bill):
        """ Returns a bill dictionary for a bill """

        bill_dict = {"bill_id": bill.bill_id,
                     "date_sale": rtf(bill.date_sale.strftime("%d-%m-%Y")),
                     "billing_ccy": currencytable[bill.billing_ccy]["CcyNm"]}
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

class HTMLMailFirstOverdue(object):
    """ This class creates a HTML mail for bills overdue.

    The overdue mail can be stored as text on the file system and be sent
    immediately to an SMTP server to be sent to the client.
    TODO Create the link to the SMTP server
    """

    def __init__(self, bill_id):

        self.bill_id = bill_id
        overdue_dict = OverdueDictView(bill_id)
        first_mail_template = htmlenvironment.get_template('mailfom.txt')
        self.text = first_mail_template.render(overdue_dict)
        html_template = htmlenvironment.get_template('mailfom.html')
        self.html = html_template.render(overdue_dict)
        self.multipart_message = EmailMessage()
        self.multipart_message['From'] = 'billing@debtorscompany.com'
        self.multipart_message['To'] = overdue_dict['client']['email']
        self.multipart_message['Subject'] = 'Your bill '\
            + str(overdue_dict['bill']['bill_id'])
        self.multipart_message.set_content(self.html)
        self.multipart_message.replace_header('Content-type',
                                              'text/html ; charset = "UTF-8"')
        self.html_message = EmailMessage()
        self.html_message.set_content(self.text)
        self.multipart_message.add_alternative(self.text)

    def write_file(self):
        """ Writes the text of the bill to a file """

        with open("output/mailfom" + str(self.bill_id), 'w') as f:
            f.write(self.multipart_message.as_string())

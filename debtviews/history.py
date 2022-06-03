#    Copyright 2015 Menno Hölscher
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

""" This file holds the views for history requests.

History is a transaction that makes it possible to inquire upon
historical events for a client. It shows bills, payments and the
things that "happened" to these.
"""

from datetime import date, datetime
from flask import render_template, abort
from flask.views import MethodView
from debtviews.monetary import edited_amount
from clientviews.forms import ClientSearchForm
from clientmodels.clients import (Clients, NoClientFoundError,
                                  NoPostalAddressError)
from debtors import config
from debtmodels.debtbilling import Bills
from debtmodels.overdue import OverdueSteps

def _get_bill_date(bill_or_payment):

    if hasattr(bill_or_payment, "bill_id"):
        if not bill_or_payment.date_bill:
            return bill_or_payment.date_sale
        return bill_or_payment.date_bill
    return bill_or_payment.value_date

class History(dict):

    def __init__(self, client):

        self.client = client
        self["client"] = self._client_data()
        postal_address = self._postal_address()
        if postal_address:
            self["address"] = postal_address
        mails = self._mail_addresses()
        if mails:
            self["mail_addresses"] = mails
        accounts = self._bank_accounts()
        if accounts:
            self["bank_accounts"] = accounts
        bills_payments = self._bills_and_payments()
        if bills_payments:
            self["bills_payments"] = bills_payments

    def _client_data(self):
        """ Fill the client data in the dictionary (self) """

        client_dict = dict()
        client = self.client
        client_dict["id"] = client.id
        client_dict["initials"] = client.initials
        client_dict["surname"] = client.surname
        if client.first_name:
            client_dict["first_name"] = client.first_name
        if client.birthdate:
            client_dict["birthdate"] = client.birthdate
        if client.sex:
            client_dict["sex"] = client.sex
        return client_dict

    def _postal_address(self):
        """ Fill address data in the dictionary (self) """

        address_dict = dict()
        try:
            address = self.client.postal_address()
        except NoPostalAddressError:
            return None
        if address.street:
            address_dict["street"] = address.street
            address_dict["house_number"] = address.house_number
        else:
            address_dict["po_box"] = address.po_box
        address_dict["postcode"] = address.postcode
        address_dict["town_or_village"] = address.town_or_village
        address_dict["country_code"] = address.country_code
        return address_dict

    def _mail_addresses(self):
        """ Fill mail addresses in the dictionary """

        addresses = [ mail.mail_address for mail in self.client.emails]
        addresses_list = []
        for address in addresses:
            addresses_list.append({ "mail_address" : address })
        return addresses_list

    def _bank_accounts(self):
        """ Fill bank accounts in dictionary """

        accounts = self.client.accounts
        accounts_list = []
        for account in accounts:
            account_dict = {"iban" : account.iban}
            if account.bic:
                account_dict["bic"] = account.bic
            if account.client_name:
                account_dict["client_name"] = account.client_name
            accounts_list.append(account_dict)
        return accounts_list

    def _bills_and_payments(self):
        """ Fill and order bills and payments """

        bill_payment_list = []
        bill_payments = []
        bill_payments.extend(self.client.payments)
        bill_payments.extend(self.client.bills)
        #for payment in self.client.payments:
            #if type(payment.value_date) == datetime:
                #raise TypeError("Payment " + str(payment.id))
        #for bill in self.client.bills:
            #if type(bill.date_bill) == datetime or type(bill.date_sale) == datetime:
                #raise TypeError("Bill " + bill.bill_id)
        bill_payments = sorted(bill_payments, key=_get_bill_date, reverse=True)
        for bill_or_payment in bill_payments:
            if hasattr(bill_or_payment, "bill_id"):
                bill_payment_list.append(self._make_bill_dict(bill_or_payment))
            else:
                bill_payment_list.append(self._make_payment_dict(bill_or_payment))
        return bill_payment_list

    def _make_bill_dict(self, bill):
        """ Make a dictionary for a bill """

        bill_dict = {"bill_id" : bill.bill_id }
        bill_dict["status"] = Bills.STATUS_NAME[bill.status]
        if bill.date_bill:
            bill_dict["date_bill"] =\
                bill.date_bill.strftime(config["DATE_FORMAT"])
        else:
            bill_dict["date_bill"] =\
                bill.date_sale.strftime(config["DATE_FORMAT"])
        bill_dict["status"] = bill.status
        bill_dict["currency"] = bill.billing_ccy
        bill_dict["total"] = edited_amount(bill.total(),
                                currency=bill.billing_ccy)
        if bill.assignments:
            bill_dict["payment_id"] =\
                bill.assignments[0].from_amount.id
            bill_dict["payment_date"] =\
                bill.assignments[0].from_amount.\
                    value_date.strftime(config["DATE_FORMAT"])
        actions = []
        for action in bill.overdue_actions:
            overdue_action = { "id" : action.id }
            step = OverdueSteps.get_by_id(action.step_id)
            overdue_action["name"] = step.step_name
            overdue_action["date_action"] =\
                action.date_action.strftime(config["DATE_FORMAT"])
            actions.append(overdue_action)
        if actions:
            bill_dict["overdue_actions"] = actions
        return bill_dict

    def _make_payment_dict(self, payment):
        """ Make a dictionary for a payment """

        payment_dict = {"id" : payment.id }
        payment_dict["value_date"] =\
            payment.value_date.strftime(config["DATE_FORMAT"])
        payment_dict["payment_ccy"] = payment.payment_ccy
        payment_dict["payment_amount"] = edited_amount(
                                payment.payment_amount,
                                currency=payment.payment_ccy)
        payment_dict["debcred"] = payment.debcred
        if (hasattr(payment, "from_amt")
            and payment.from_amt):
            list_from_amounts = payment.list_assigned_from()
            from_payments = []
            for payment in list_from_amounts:
                orig_payment = {"from_payment" : payment.id}
                orig_payment["from_ccy"] = payment.payment_ccy
                orig_payment["from_amount"] = edited_amount(
                    payment.payment_amount,
                    currency=payment.payment_ccy)
                from_payments.append(orig_payment)
            if from_payments:
                payment_dict["from_payments"] = from_payments
        return payment_dict



class HistoryView(MethodView):
    """ Show the history of this client.

    This view has the client history. It contains:

        * general client data (like name, mail address and postal address
        * the bills created for the client
        * the payments received and attached from this client

    the bills and payments are in a list in reversed date order.
    """

    def get(self, client_id):
        """ Get the information for the client number requested """

        try:
            client = Clients.get_by_id(client_id)
        except NoClientFoundError as ncfe:
            abort(400, str(ncfe))
        client_search_form = ClientSearchForm()
        client_history = History(client)
        return render_template("historyclient.html", client=client_history,
                               search_form=client_search_form)

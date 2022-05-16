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
from debtmodels.debtbilling import Bills

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
        self["address"] = self._postal_address()
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
        address = self.client.postal_address()
        if address.street:
            address_dict["street"] = address.street
            address_dict["house_number"] = address.house_number
        else:
            address_dict["po_box"] = address.po_box
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
        for payment in self.client.payments:
            if type(payment.value_date) == datetime:
                raise TypeError("Payment " + payment.id)
        for bill in self.client.bills:
            if type(bill.date_bill) == datetime or type(bill.date_sale) == datetime:
                raise TypeError("Bill " + bill.bill_id)
        bill_payments = sorted(bill_payments, key=_get_bill_date, reverse=True)
        for bill_or_payment in bill_payments:
            if hasattr(bill_or_payment, "bill_id"):
                bill_dict = {"bill_id" : bill_or_payment.bill_id }
                bill_dict["status"] = Bills.STATUS_NAME[bill_or_payment.status]
                if bill_or_payment.date_bill:
                    bill_dict["date_bill"] = bill_or_payment.date_bill
                else:
                    bill_dict["date_bill"] = bill_or_payment.date_sale
                bill_dict["status"] = bill_or_payment.status
                bill_payment_list.append(bill_dict)
                if bill_or_payment.assignments:
                    bill_dict["payment_id"] =\
                        bill_or_payment.assignments[0].from_amount.id
                    bill_dict["payment_date"] =\
                        bill_or_payment.assignments[0].from_amount.value_date 
            else:
                payment_dict = {"id" : bill_or_payment.id }
                payment_dict["value_date"] = bill_or_payment.value_date
                payment_dict["payment_ccy"] = bill_or_payment.payment_ccy
                payment_dict["payment_amount"] = bill_or_payment.payment_amount
                payment_dict["debcred"] = bill_or_payment.debcred
                bill_payment_list.append(payment_dict)
                if (hasattr(bill_or_payment, "from_amt")
                    and bill_or_payment.from_amt):
                    list_from_amounts = bill_or_payment.list_assigned_from()
                    from_payments = []
                    for payment in list_from_amounts:
                        orig_payment = {"from_payment" : payment.id}
                        orig_payment["from_ccy"] = payment.payment_ccy
                        orig_payment["from_amount"] = payment.payment_amount
                        from_payments.append(orig_payment)
                    if from_payments:
                        payment_dict["from_payments"] = from_payments
        return bill_payment_list

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

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

""" This module contains the methodviews to be used with the client demo 
system that is supplied with the debtors system.

Using the views in the module, one can enter clients and update the 
clients themselves and the dependents like addresses an bank accounts.
"""

from flask import render_template, abort, redirect, url_for, flash, request
from flask.views import MethodView
from clientmodels.clients import Clients, Addresses, NoClientFoundError,\
    EMail, NoAddressFoundError, BankAccounts, NoAccountFoundError, db
from clientviews.forms import ClientForm, ClientMailForm, ClientAddressForm,\
    AddressDeleteForm, ClientSearchForm, ClientBankAccountForm,\
        AccountDeleteForm
from clientviews.mixins import PaginatorMixin


class ClientView(MethodView):
    """ The ClientView contains the controllers for the client system 
    on the client level. Some dependents are also created and/or maintained
    here.
    """

    def get(self, id=None):
        """ Get client data based on the sequence number of the client
        record.
        """

        if id:
            try:
                client = Clients.get_by_id(int(id))
            except NoClientFoundError as ncf:
                abort(404, str(ncf))
        else:
            client = None

        search_form = ClientSearchForm()
        client_form = ClientForm(obj=client)

        return render_template('client.html', form=client_form,
                               search_form=search_form)

    def post(self, id=None):
        """ Process new posted client data.

        Expects a new client, or an existing client with new data
        """

        if id:
            try:
                client = Clients.get_by_id(int(id))
            except NoClientFoundError as ncf:
                abort(404, str(ncf))
        else:
            client = Clients()
                
        client_form = ClientForm()

        if client_form.validate_on_submit():
            client.surname = client_form.surname.data
            client.birthdate = client_form.birthdate.data
            client.initials = client_form.initials.data
            client.first_name = client_form.first_name.data
            client.sex = client_form.sex.data

            if id is None:
                client.add()
            db.session.commit()

            if client_form.addmore.data:
                return redirect(url_for('.create_client'))
            else:
                return redirect(url_for('index'))

        for error_key, error_value in client_form.errors.items():
            for message in error_value:
                flash('Field ' + error_key + ': ' + str(message))
        search_form = ClientSearchForm()
        return render_template('client.html', form=client_form,
                               search_form=search_form)


class ClientViewingList(list, PaginatorMixin):
    """ We create a list that can be used for viewing a list of clients,
    with some associated data
    
    It stores the base client data (as in the Clients class) together
    wit a list of mail addresses (EMail class) and the postal address
    of the client. It assembles the data to be used by e.g. the 
    ClientListView
    """

    def __init__(self, list_creator, page=1, page_length=4):

        PaginatorMixin.__init__(self, list_creator, page=page, page_length=page_length)
    

class ClientListView(MethodView):
    """ This view shows a list of clients.
    
    If you request a list without parameters, it will show you the newest
    clients in the list, in descending order of change date. When you add 
    a search parameter, it will show clients whose surname contains the 
    search parameter.
    """

    def get(self):
        """ Get a list of clients from the database """

        search_form = ClientSearchForm()
        search_for = request.args.get('search_for')

        page = int(request.args.get('page', default=1))
        client_paginator = ClientViewingList(Clients.client_list)
        if search_for:
            client_list = client_paginator.get_page(page,
                                                    search_for=search_for)
        else:
            client_list = client_paginator.get_page(page)
        
        if search_for:
            search_form.search_for.data = search_for

        return render_template('clientlist.html',
                        client_list=client_list,
                        search_form=search_form)


class MailView(MethodView):
    """ Add a new mail address to a client """

    def get(self, id):
        """ Return a page to enter a mail address for a client  """

        client = get_client_by_id(self.id)

        client_mail_form = ClientMailForm()

        return render_template('clientmail.html', form=client_mail_form,
                               client=client)

    def post(self, id):
        """ Processs adding a new mail address for a client """

        client = get_client_by_id(self, id)

        client_mail_form = ClientMailForm()

        bool_preferred = client_mail_form.preferred.data
        if bool_preferred:
            preferred = 1
        else:
            preferred = 0
        mail = EMail(mail_address=client_mail_form.mail_address.data,
                     preferred=preferred)
        client.emails.append(mail)

        db.session.commit()
        return redirect(url_for('.clients', id=client.id))


class AddressView(MethodView):
    """ Class used for adding postal/residential addresses for a client """

    def get(self, id=None, address_id=None):
        """ Return a page to add an address to the client """

        client = get_client_by_id(self, id)

        if address_id:
            address = Addresses.get_by_id(address_id)
            client_address_form = ClientAddressForm(obj=address)
        else:
            client_address_form = ClientAddressForm()

        return render_template('clientaddress.html', client=client,
                               form=client_address_form)

    def post(self, id=None):
        """ Add or change an address to or for a client """

        client = get_client_by_id(self, id)
        
        client_address_form = ClientAddressForm()

        if client_address_form.id.data:
            address = Addresses.get_by_id(client_address_form.id.data)
        else:
            address = Addresses()

        if client_address_form.validate_on_submit():
            address.client_id = client.id
            address.street = client_address_form.street.data
            address.house_number = client_address_form.house_number.data
            address.po_box = client_address_form.po_box.data
            address.postcode = client_address_form.postcode.data
            address.town_or_village = client_address_form.town_or_village.data
            address.address_use = client_address_form.address_use.data
            address.country_code = client_address_form.country.data
            if address.id is None:
                address.add()
                client.addrs.append(address)
            db.session.commit()
            return redirect(url_for('.clients', id=id))
        return render_template('clientaddress.html', client=client,
                               form=client_address_form)


class AddressDeleteConfirmationView(MethodView):
    """ Class used for processing confirmations for address deletion """

    def get(self, id=None, address_id=None):
        """ Show the deletion confirmation page  """

        address_delete_form = AddressDeleteForm()

        try:
            address = Addresses.get_by_id(address_id)
        except NoAddressFoundError as nafe:
            abort(404, str(nafe))

        client = address.addressee

        return render_template('confirmaddressdelete.html', client=client,
                               address=address, form=address_delete_form)

    def post(self, id=None, address_id=None):
        """ Process the posted confirmation result """

        address_delete_form = AddressDeleteForm()

        if address_delete_form.delete.data:
            try:
                address = Addresses.get_by_id(address_id)
            except NoAddressFoundError as nafe:
                abort(404, str(nafe))
            address.delete_address()
            db.session.commit()

        return redirect(url_for('.clients', id=id, _method='GET'))


class BankAccountView(MethodView):
    """ Class used for adding and maintaining bank accounts """

    def get(self, id=None, account_id=None):
        """ Get a specific bank account """

        client =  get_client_by_id(self, id)
        if account_id:
            for acc in client.accounts:
                if account_id == acc.id:
                    account = acc
                    break
            bank_account_form = ClientBankAccountForm(obj=account)
        else:
            account=None
            bank_account_form = ClientBankAccountForm()

        return render_template('clientbankaccount.html', client=client,
                               form=bank_account_form, account=account)

    def post(self, id=None, account_id=None):
        """ Add or update an account for a client """

        client =  get_client_by_id(self, id)

        bank_account_form = ClientBankAccountForm()
        
        if bank_account_form.validate_on_submit():
            if account_id:
                account = None
                for acc in client.accounts:
                    if account_id == acc.id:
                        account = acc
                        break
                if not account:
                    abort(404, 'Bank account not found')
            else:
                account = BankAccounts()
            account.client_id = id
            account.iban = bank_account_form.iban.data
            account.bic = bank_account_form.bic.data
            account.client_name = bank_account_form.client_name.data
            if not account_id:
                client.accounts.append(account)
            db.session.commit()
            return redirect(url_for('.clients', id=id))
        return render_template('clientbankaccount.html', client=client,
                               form=bank_account_form, account=account)

class BankAccountDeleteView(MethodView):
    """ Process confirmation of bank account deletion """

    def get(self, id=None, account_id=None):
        """ Show the bank account deletion form """

        account_delete_form = AccountDeleteForm()
        
        try:
            account = BankAccounts.get_by_id(account_id)
        except NoAccountFoundError as nafe:
            abort(404, 'The requested account was not found')

        if account.owner.id != id:
            abort(404, 'The client could not be found')
        
        return render_template('confirmaccountdelete.html',
                               client=account.owner,
                               account=account, form=account_delete_form)

    def post(self, id=None, account_id=None):
        """ Process the posting of the account delete form """

        client = get_client_by_id(self, id)
        
        bank_account_form = ClientBankAccountForm()
        
        if bank_account_form.validate_on_submit():
            if request.form.get("cancel", False):
                return redirect(url_for('.clients', id=id))
            if account_id:
                account = None
                for acc in client.accounts:
                    if account_id == acc.id:
                        account = acc
                        break
                if not account:
                    abort(404, 'Bank account not found')
            else:
                abort(404, 'A bank account is required')
            account.delete()
            db.session.commit()
            return redirect(url_for('.clients', id=id))
        return render_template('confirmaccountdelete.html',
                               client=account.owner,
                               account=account, form=account_delete_form)        


def get_client_by_id(instance, id):
    """ Get the client from the model by the id passed in """

    if id:
        try:
            client = Clients.get_by_id(int(id))
        except NoClientFoundError as ncf:
            abort(404, str(ncf))
    else:
        abort(404, 'A client is required')

    return client

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
    EMail, db
from clientviews.forms import ClientForm, ClientMailForm
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
        
        client_form = ClientForm(obj=client)

        return render_template('client.html', form=client_form)

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
                return redirect(url_for('create_client'))
            else:
                return redirect(url_for('index'))

        for error_key, error_value in client_form.errors.items():
            for message in error_value:
                flash('Field ' + error_key + ': ' + str(message))
        return render_template('client.html', form=client_form)


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

        page = int(request.args.get('page', default=1))
        client_paginator = ClientViewingList(Clients.client_list)
        return render_template('clientlist.html',
                        client_list=client_paginator.get_page(page))


class MailView(MethodView):
    """ Add a new mail address to a client """

    def get(self, id):
        """ Return a page to enter a mail address for a client  """

        if id is None:
            return 'A client is required', 404
        try:
            client = Clients.get_by_id(id)
        except NoClientFoundError as ncfe:
            abort(404, str(ncfe))
        
        client_mail_form = ClientMailForm()
        
        return render_template('clientmail.html', form=client_mail_form,
                               client=client)

    def post(self, id):
        """ Processs adding a new mail address for a client """

        if id:
            try:
                client = Clients.get_by_id(int(id))
            except NoClientFoundError as ncf:
                abort(404, str(ncf))
        else:
            abort(404, 'A client is required')
                
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
        return redirect(url_for('clients', id=client.id))

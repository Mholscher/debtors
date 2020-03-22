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

""" This module contains the central part of the blueprint for the client
    administration part of the debtors system. Its goal is to separate the
    parts of the clients system as much as I can from the actual application
    using it. """

from flask import Blueprint

client_pages = Blueprint('client', __name__, url_prefix='/client')

from clientviews.clients import ClientView, ClientListView, MailView,\
    AddressView, AddressDeleteConfirmationView, BankAccountView,\
        BankAccountDeleteView

client_pages.add_url_rule('/<int:id>',
 view_func=ClientView.as_view('clients'))
client_pages.add_url_rule('/new',
                          view_func=ClientView.as_view('create_client'))
client_pages.add_url_rule('/list',
                          view_func=ClientListView.as_view('list_clients'))
client_pages.add_url_rule('/<int:id>/mail/new',
                          view_func=MailView.as_view('add_mail'))
client_pages.add_url_rule('/<int:id>/address/new',
                          view_func=AddressView.as_view('add_address'))
client_pages.add_url_rule('/<int:id>/address/<int:address_id>/confirm',
                          view_func=AddressDeleteConfirmationView.as_view('confirm_delete_address'))
client_pages.add_url_rule('/<int:id>/address/<int:address_id>',
                          view_func=AddressView.as_view('change_address'))
client_pages.add_url_rule('/<int:id>/account/new',
                          view_func=BankAccountView.as_view('add_account'))
client_pages.add_url_rule('/<int:id>/account/<int:account_id>',
                          view_func=BankAccountView.as_view('change_accounts'))
client_pages.add_url_rule('/<int:id>/account/<int:account_id>/confirm',
                          view_func=BankAccountDeleteView.as_view('delete_account'))

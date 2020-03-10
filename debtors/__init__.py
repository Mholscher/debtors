#    Copyright 2015 Menno Hölscher
#
#    This file is part of debtors.

#    debtors is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    debtors is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with debtors.  If not, see <http://www.gnu.org/licenses/>.

import logging
import configparser
from flask import Flask, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

app = Flask('debtors')
app.config.from_pyfile('localdebtors.cfg')
db = SQLAlchemy(app, {"session_options" : "READ_UNCOMMITTED"})
CSRFProtect(app)

#logging.basicConfig(filename='debtors.log', level=logging.INFO)
#logging.debug('Debug logging')

import debtmodels.debtbilling 
import clientmodels.clients
from . import views
client_pages = Blueprint('client', __name__)
app.register_blueprint(client_pages)
from clientviews.clients import ClientView, ClientListView, MailView,\
    AddressView, AddressDeleteConfirmationView
app.add_url_rule('/client/<int:id>', view_func=ClientView.as_view('clients'))
app.add_url_rule('/client/new', view_func=ClientView.as_view('create_client'))
app.add_url_rule('/client/list', 
                 view_func=ClientListView.as_view('list_clients'))
app.add_url_rule('/client/<int:id>/mail/new', view_func=MailView.as_view('add_mail'))
app.add_url_rule('/client/<int:id>/address/new', view_func=AddressView.as_view('add_address'))
app.add_url_rule('/client/<int:id>/address/<int:address_id>/confirm', view_func=AddressDeleteConfirmationView.as_view('confirm_delete_address'))
app.add_url_rule('/client/<int:id>/address/<int:address_id>', view_func=AddressView.as_view('change_address'))


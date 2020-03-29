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

""" This module contains a Blueprint for the api access to the debtors system.

Systems outside debtors itself can communicate to the system by sending json\
formatted messages to it. These messages are handled by the views in 
this module.

It also has the url_rules to add to the rule map of wekzeug, so incoming
messages can be dispatched.
"""

from flask import Blueprint
from debtviews.bills import ClientBillsView

debtapi = Blueprint('debtapi', __name__, url_prefix='/api/10')

debtapi.add_url_rule('/client/<int:client_number>/bills',
                     view_func=ClientBillsView.as_view('client_bills'))

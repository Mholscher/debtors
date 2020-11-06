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

Systems outside debtors itself can communicate to the system by sending json
formatted messages to it. These messages are handled by the views in 
this module.

It also has the url_rules to add to the rule map of werkzeug, so incoming
messages can be dispatched.
"""

from flask import Blueprint, jsonify
#from debtviews.billsapi import ClientBillsView, BillCreateView, BillView
import debtviews.billsapi as view_bill
from debtmodels.debtbilling import InvalidDataError

debtapi = Blueprint('debtapi', __name__, url_prefix='/api/10')

debtapi.add_url_rule('/client/<int:client_number>/bills',
                     view_func=view_bill.ClientBillsView.as_view('api_client_bills'))
debtapi.add_url_rule('/bill/<bill_id>',
                     view_func=view_bill.BillView.as_view('api_bill'))
debtapi.add_url_rule('/bill/new',
                     view_func=view_bill.BillCreateView.as_view('api_new_bill'))

@debtapi.errorhandler(InvalidDataError)
def handle_invalid_data(ide):
    """ Handle the case invalid data was received from another system. 

    InvalidDataError is the error all validation errors are inheriting
    from. Also errors like getting a bill_id that does not exist in the
    database inherit from this error. The system that has delivered the
    faulty data is notified that debtors could not process its message.
    """

    response_dict = ide.to_dict()
    response_dict['status'] = 'Bad Request'
    response = jsonify(response_dict)
    response.status_code = 400
    return response

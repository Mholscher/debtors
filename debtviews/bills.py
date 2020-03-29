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

from flask import jsonify
from flask.views import MethodView
from clientmodels.clients import Clients

class ClientBillsView(MethodView):
    """ A view that enables listings of outstanding bills for a client """

    def get(self, client_number=None):
        """ Get the list of outstanding bills for a client """

        client = Clients.get_by_id(client_number)
        return jsonify(BillListDict(client=client))


class BillDict(dict):
    """ This class is used to convert a bill to a dictionary
    
    The list format of the output of a bill makes it hard to directly
    convert it to something we can return to the API. This dictionary
    solves that issue.
    """

    def __init__(self, bill):

        self['bill-id'] = bill.bill_id
        self['date-sale'] = bill.date_sale
        self['date-billed'] = bill.date_bill
        self['bill-replaced'] = bill.prev_bill
        self['status'] = bill.STATUS_NAME[bill.status]


class BillListDict(dict):
    """ This class is used to convert a list of bills
    
    The list is a list of bills for one client. We convert the list
    from the model to a (nested) dictionary. This makes it easy
    to use it in the views
    """

    def __init__(self, client=None, bill_list=None):

        if client is not None:
            bill_list = client.bills
        elif bill_list:
            client = bill_list[0].client
        else:
            raise TypeError('One of client or bill list must be filled')

        self['client'] = client.id
        self['name'] =  client.initials + ' ' + client.surname
        self['bills'] = [BillDict(bill) for bill in client.bills] 

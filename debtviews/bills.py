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

""" This module holds the web interface for bills.

Bills may be delivered to debtors by external systems, but can also be 
created and changed by users through eb transactions. This module has the views 
to do so.
"""
from flask import render_template, redirect, url_for, request
from flask.views import MethodView
from debtmodels.debtbilling import Bills, db
from clientmodels.clients import Clients, NoClientFoundError
from debtviews.forms import BillCreateForm, BillChangeForm

class BillView(MethodView):
    """ Code to access bills on the web """

    def get(self, bill_id=None):
        """ Get the empty page to create a bill or a bill by id """

        if bill_id:
            bill = Bills.get_bill_by_id(bill_id)
            bill_form = BillChangeForm(obj=bill)
        else:
            bill = None
            bill_form = BillCreateForm()

        return render_template('bill.html', form=bill_form)

    def post(self, bill_id=None):
        """ Use the request form data to add/change a bill """

        if bill_id:
            bill = Bills.get_bill_by_id(bill_id)
            bill_form = BillChangeForm(obj=bill)
        else:
            bill_form = BillCreateForm()

        if bill_form.validate_on_submit():
            if bill_form.client_id.data:
                client_id = bill_form.client_id.data
                if client_id:
                    client = Clients.get_by_id(client_id)
            if bill_form.bill_replaced.data:
                prev_bill = bill_form.bill_replaced.data
            else:
                prev_bill = None
            if bill_form.billing_ccy.data:
                billing_ccy = bill_form.billing_ccy.data
            if bill_form.date_sale.data:
                date_sale = bill_form.date_sale.data
            if bill_id:
                bill = Bills.get_bill_by_id(bill_id)
                bill.date_sale = date_sale
                bill.billing_ccy=billing_ccy
                client = bill.client
            else:
                bill = Bills(billing_ccy=billing_ccy,
                             date_sale=date_sale,
                             prev_bill=prev_bill)
                bill.client = client
            db.session.commit()

            if type(bill_form) == BillCreateForm and bill_form.add_more.data:
                return redirect(url_for('bill_create'))
            else:
                return redirect(url_for('client.clients', id=client_id))

        return render_template('bill.html', form=bill_form)
            

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
created and changed by users through web transactions. This module has the views 
to do so.
"""
from flask import render_template, redirect, url_for, request, flash
from flask.views import MethodView
from debtmodels.debtbilling import Bills, BillLines, db
from clientmodels.clients import Clients, NoClientFoundError
from debtviews.forms import BillCreateForm, BillChangeForm


query = db.session.query


def create_bill_line(bill, line_dict):
    """ Create a line from the form in a bill
    
    The bill contains a bill in process. The line is a part of a bill
    form that we transform into a bill line and add to the bill.
    """

    if line_dict['line_id']:
        line = BillLines.get_by_id(line_dict['line_id'])
    else:
        line = BillLines()

    
    line.short_desc = line_dict['short_desc']
    line.long_desc = line_dict['long_desc']
    line.number_of = line_dict['number_of']
    line.measured_in = line_dict['measured_in']
    line.unit_price = line_dict['unit_price']
    
    bill.lines.append(line)


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
        
        for i in range(3):
            bill_form.lines.append_entry()
        
        return render_template('bill.html', form=bill_form, bill=bill)

    def post(self, bill_id=None):
        """ Use the request form data to add a bill """

        if bill_id:
            bill = Bills.get_bill_by_id(bill_id)
            bill_form = BillChangeForm(obj=bill)
        else:
            bill = None
            bill_form = BillCreateForm()

        while bill_form.lines.__len__() > 0\
            and not any(bill_form.lines.data[bill_form.lines.__len__() - 1].values()) :
            bill_form.lines.pop_entry()

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
                billing_ccy = bill_form.billing_ccy.data.upper()
            if bill_form.date_sale.data:
                date_sale = bill_form.date_sale.data
            if bill_id:
                bill = query(Bills).filter_by(bill_id = bill_id).first()
            else:
                bill = Bills(billing_ccy=billing_ccy,
                            date_sale=date_sale,
                            prev_bill=prev_bill)
            bill.client = client

            for line in bill_form.lines.data:
                create_bill_line(bill, line)

            db.session.commit()

            if type(bill_form) == BillCreateForm and bill_form.add_more.data:
                return redirect(url_for('bill_create'))
            else:
                return redirect(url_for('client.clients', id=client_id))

        flash('Validation error encountered')
        return render_template('bill.html', form=bill_form, bill=bill)
            

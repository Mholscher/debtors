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

""" This is the views module of the debtors app. It does not contain
the code for views (with the exception of the root view), but contains
the url_rules pointing to the different views in the debtviews module.
"""

from debtors import app
from flask import redirect, url_for, render_template
from debtviews.bills import BillView, ClientDebtView, BillDetailView
from debtviews.forms import  FormForAmount


@app.route('/')
def index():
    """This is the index page of the application. It shows
    a list of accounts
    """
    return redirect(url_for('client.list_clients')) 

app.add_url_rule('/bill/new', view_func=BillView.as_view('bill_create'))
app.add_url_rule('/bill/<int:bill_id>', view_func=BillView.as_view('bill_update'))
app.add_url_rule('/debt/<int:client_id>',\
    view_func=ClientDebtView.as_view('client_debt'))
app.add_url_rule('/bill/<int:bill_id>/details',\
    view_func=BillDetailView.as_view('bill_detail'))

@app.route('/testamount/<amount>', methods=['GET', 'POST'])
def amount_route(amount=3):

    amount_form = FormForAmount(obj=[amount])
    if amount_form.validate_on_submit():
        print('Amount : ', str(amount_form.amount.data))
        import pdb; pdb.set_trace()
        return redirect(url_for("amount_route", amount=str(amount_form.amount.data)))
    amount_form.amount.data = amount
    return render_template('amountpage.html', form=amount_form)

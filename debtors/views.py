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

from debtors import app, InvalidDataError
from flask import redirect, url_for, render_template, abort
from debtviews.bills import (BillView, ClientDebtView, BillDetailView,
                             DebtorSignalView)
from debtviews.payments import (PaymentView, PaymentUpdateView,
    PaymentAssignView, PaymentAssignToBill, PaymentAssignToPayment,
    PaymentReverseView, PaymentAssignReverseView)
from debtviews.history import HistoryView
from debtviews.forms import  FormForAmount


@app.route('/')
def index():
    """This is the index page of the application. It shows
    a list of clients
    """
    return redirect(url_for('client.list_clients')) 

app.add_url_rule('/bill/new', view_func=BillView.as_view('bill_create'))
app.add_url_rule('/bill/<int:bill_id>', view_func=BillView.as_view('bill_update'))
app.add_url_rule('/debt/<int:client_id>',
    view_func=ClientDebtView.as_view('client_debt'))
app.add_url_rule('/history/<int:client_id>',
    view_func=HistoryView.as_view('client_history'))
app.add_url_rule('/bill/<int:bill_id>/details',
    view_func=BillDetailView.as_view('bill_detail'))
app.add_url_rule('/payment/new',
    view_func=PaymentView.as_view('payment_create'))
app.add_url_rule('/payment/<int:payment_id>',
    view_func=PaymentView.as_view('payment_update'))
app.add_url_rule('/payment/attach',
    view_func=PaymentUpdateView.as_view('payment_attach'))
app.add_url_rule('/payment/assign/<int:payment_id>',
    view_func=PaymentAssignView.as_view('payment_assign'))
app.add_url_rule('/assignment/<int:payment_id>/reverse',
    view_func=PaymentAssignReverseView.as_view('assign_reverse'))
app.add_url_rule('/payment/assign/<int:payment_id>/bill/<int:bill_id>',
    view_func=PaymentAssignToBill.as_view('payment_assign_bill'))
app.add_url_rule('/payment/assign/<int:from_id>/payment/<int:to_id>',
    view_func=PaymentAssignToPayment.as_view('payment_to_payment'))
app.add_url_rule('/payment/reverse/<int:payment_id>',
    view_func=PaymentReverseView.as_view('payment_reverse'))
app.add_url_rule('/signal/<int:signal_id>',
                 view_func=DebtorSignalView.as_view('signal_update'))


@app.route('/testamount/<amount>', methods=['GET', 'POST'])
def amount_route(amount=3):

    amount_form = FormForAmount(obj=[amount])
    if amount_form.validate_on_submit():
        print('Amount : ', str(amount_form.amount.data))
        import pdb; pdb.set_trace()
        return redirect(url_for("amount_route", amount=str(amount_form.amount.data)))
    amount_form.amount.data = amount
    return render_template('amountpage.html', form=amount_form)

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

""" This module holds the web interface for payments.

Payments may be delivered to debtors by reading electronic statements, but
can also be created and changed by users through web transactions. This
module has the views to do the latter.
"""

from flask import render_template, redirect, url_for, request, flash, abort
from flask.views import MethodView
from debtmodels.payments import IncomingAmounts, IncomingAmountNotFoundError
from debtviews.forms import PaymentForm, PaymentCreateForm
from clientviews.forms import ClientSearchForm


class PaymentView(MethodView):
    """ This class shows the data of one payment on the web. """

    def get(self, payment_id=None):
        """ Get the payment with id equal payment_id """

        client_search_form = ClientSearchForm()

        if payment_id:
            try:
                payment = IncomingAmounts.get_payment_by_id(payment_id)
            except IncomingAmountNotFoundError as ianfe:
                abort(404, str(ianfe))
            payment_form = PaymentForm(obj=payment)
        else:
            payment = IncomingAmounts()
            payment_form = PaymentCreateForm()

        return render_template('payment.html', form=payment_form,
                               payment=payment, client=payment.client, 
                               search_form=client_search_form)


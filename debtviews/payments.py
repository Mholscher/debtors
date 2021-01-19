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
from clientmodels.clients import Clients
from debtors import db
from debtmodels.payments import IncomingAmounts, IncomingAmountNotFoundError
from debtviews.forms import PaymentForm, PaymentCreateForm, ClientAttachForm
from debtviews.wtformsmonetary import AmountField
from clientviews.forms import ClientSearchForm


class PaymentView(MethodView):
    """ This class shows the data of one payment on the web. """

    def get(self, payment_id=None):
        """ Get the payment with id equal payment_id """

        client_search_form = ClientSearchForm()

        payment_update_form = ClientAttachForm()

        if payment_id:
            payment_update_form.payment_id.data = payment_id
            try:
                payment = IncomingAmounts.get_payment_by_id(payment_id)
            except IncomingAmountNotFoundError as ianfe:
                abort(404, str(ianfe))
            payment_form = PaymentForm(obj=payment)
            if payment.client:
                payment_update_form.client_id.data = payment.client.id
        else:
            payment = IncomingAmounts()
            payment_form = PaymentCreateForm()

        return render_template('payment.html', form=payment_form,
                               form2=payment_update_form,
                               payment=payment, client=payment.client, 
                               search_form=client_search_form)

    def post(self, payment_id=None):
        """ Add or update a payment with the user input """

        AmountField.get_currency = self._get_currency
        payment_form = PaymentCreateForm()
        payment_update_form = ClientAttachForm()
        payment_id = payment_form.id.data
        if payment_form.validate_on_submit():
            payment_ccy = payment_form.payment_ccy.data
            payment_amount = payment_form.payment_amount.data
            payment_debcred = payment_form.debcred.data
            payment_value_date = payment_form.value_date.data
            payment_our_ref = payment_form.our_ref.data
            if not payment_id:
                payment = IncomingAmounts(payment_ccy = payment_ccy,
                                        payment_amount= payment_amount,
                                        debcred = payment_debcred,
                                        value_date = payment_value_date,
                                        our_ref = payment_our_ref)
                payment.add()
                del AmountField.get_currency
                db.session.commit()
                payment_id = payment.id
                return redirect(url_for('payment_update',
                                        payment_id=payment_id))

        client_search_form = ClientSearchForm()
        payment = IncomingAmounts()
        del AmountField.get_currency
        flash("Validation error(s) encountered")

        return render_template('payment.html', form=payment_form,
                               form2=payment_update_form,
                               payment=payment, client=payment.client, 
                               search_form=client_search_form)

    def _get_currency(field):
        """ Get the currency of this payment for validating amounts """

        return request.form.get('payment_ccy').upper()


class PaymentUpdateView(MethodView):
    """ Update an existing payment from the web """

    def post(self):
        """ Attach a client to the payment """

        update_form = ClientAttachForm()
        payment_id = update_form.payment_id.data
        if not payment_id:
            flash('No payment to attach client to')
            return redirect(url_for('.payment_create'))
        payment = IncomingAmounts.query.filter_by(id=payment_id).first()
        if payment.assigned():
            flash('Cannot attach to client when money assigned')
            return redirect(url_for('.payment_update', payment_id=payment_id))
        client_id = update_form.client_id.data
        client = Clients.query.filter_by(id=client_id).first()
        if client:
            payment.client = client
        else:
            flash('No client {} to attach'.format(client_id))
            return redirect(url_for('.payment_update', payment_id=payment_id))
        db.session.commit()

        return redirect(url_for('.payment_update', payment_id=payment_id))


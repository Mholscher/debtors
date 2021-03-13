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

from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, abort
from flask.views import MethodView
from clientmodels.clients import Clients
from debtors import db
from debtviews.monetary import edited_amount
from debtmodels.payments import IncomingAmounts, IncomingAmountNotFoundError
from debtmodels.debtbilling import Bills, BillNotFoundError
from debtmodels.accounting import AccountingTemplate
from debtviews.forms import (PaymentForm, PaymentCreateForm, ClientAttachForm,
    FindClientForm)
from debtviews.wtformsmonetary import AmountField
from clientviews.forms import ClientSearchForm


class PaymentDict(dict):
    """ Create backing for use of payments without form

    When using a form all this is taken care of by the form. Without
    form we do it ourselves.
    """

    def __init__(self, payment):

        if not payment:
            raise IncomingAmountNotFoundError("No payment for conversion")

        self["id"] = payment.id
        self["payment_ccy"] = payment.payment_ccy
        self["payment_amount"] = edited_amount(payment.payment_amount,
                                               currency=payment.payment_ccy)
        self["debcred"] = IncomingAmounts.DEBCRED[payment.debcred]
        self["value_date"] = payment.value_date.strftime("%d-%m-%Y")
        self["our_ref"] = payment.our_ref
        self["bank_ref"] = payment.bank_ref
        self["client_ref"] = payment.client_ref
        self["client_name"] = payment.client_name
        self["creditor_iban"] = payment.creditor_iban

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
        client_id = update_form.client_id.data
        client = Clients.query.filter_by(id=client_id).first()
        if client:
            try:
                payment.change_client(client)
            except ValueError as ve:
                flash(str(ve))
                return redirect(url_for('.payment_update',
                                        payment_id=payment_id))
        else:
            flash('No client {} to attach'.format(client_id))
            return redirect(url_for('.payment_update', payment_id=payment_id))
        db.session.commit()

        return redirect(url_for('.payment_update', payment_id=payment_id))

class PaymentAssignView(MethodView):
    """ A paymentmay be assigned to a bill

    The operator may search for bills in a few ways. Once the 
    bill to be paid is found, it can be paid.
    """

    def get(self, payment_id):
        """ Get the payment with id payment_id """

        try:
            payment = IncomingAmounts.get_payment_by_id(payment_id)
        except ValueError as ve:
            abort(404, str(ve))
        payment = PaymentDict(payment)
        client_search_form = FindClientForm()

        name=request.args.get("find_name", None)
        client_id=request.args.get("find_number", None)
        account_nr=request.args.get("find_bank_account", None)
        search_values = (name, client_id, account_nr)
        search_results = []

        if any(search_values):
            search_results =\
                IncomingAmounts.get_bill_targets(name=name,
                                             client_id=client_id,
                                             account_nr=account_nr)
        for bill in search_results:
            bill.billing_amount = edited_amount(bill.total(),
                                                currency=bill.billing_ccy)
        return render_template('paymentassign.html', payment=payment,
                               search_results=search_results,
                               search_form=client_search_form)


class PaymentAssignToBill(MethodView):
    """ Assign a payment to a bill """

    def post(self, payment_id, bill_id):
        """ Assign the payment for payment_id to the bill for bill_id """

        payment = IncomingAmounts.get_payment_by_id(payment_id)
        if not payment:
            raise IncomingAmountNotFoundError("No payment for {}"
                                              .format(payment_id))
        bill = Bills.get_bill_by_id(bill_id)
        if not bill:
            raise BillNotFoundError("No bill for {}".format(bill_id))
        payment.assign_to_bill(bill)
        db.session.commit()
        return redirect(url_for("payment_assign", payment_id=payment_id))


class PaymentAccounting(AccountingTemplate):
    """ Create accounting for a payment

    The accounting is created as a dictionary, ready to be shipped as a 
    JSON formatted file.
    
    This class assumes that GLedger is being used. Subclass or replace to
    use a different GL system.
    TODO Where and when do the accounting?
    """

    def journal_entries(self, journal_dict, payment):
        """ Create postings for a payment
        
        The journal_dict passed in is the dictionary that will be
        transformed into a JSON message for the accounting software.
        We need to add the postings and come up with a (unique)
        external key to identify the journal.
        """

        journal_dict["extkey"] = "payment" + str(payment.id)
        if payment.payment_amount == 0:
            raise ValueError("Can not do accounting for zero amount")
        posting_list = []
        posting_debt = {"account" : "debt", "currency" : 
                             payment.payment_ccy,
                             "amount" : str(payment.payment_amount),
                             "debitcredit" : "Cr",
                             "valuedate" : payment.value_date.strftime("%Y-%m-%d")}
        posting_list.append(posting_debt)
        posting_receipt = {"account" : "receipts", "currency" : 
                             payment.payment_ccy,
                             "amount" : str(payment.payment_amount),
                             "debitcredit" : "Db",
                             "valuedate" : payment.value_date.strftime("%Y-%m-%d")}
        posting_list.append(posting_receipt)
        journal_dict["postings"] = posting_list
        return journal_dict


class AssignmentAccounting(AccountingTemplate):
    """ Create posting for assignment of an amount to a bill"""

    def journal_entries(self, journal_dict, assignment):
        """ Create the postings

    The journal_dict passed in will be filled with the accounting for
    assignment and the journal key set.
    """

        journal_dict["extkey"] = "assign" + str(assignment.id)
        posting_list = []
        posting_debt = {"account" : "income", "currency" : 
                             assignment.ccy,
                             "amount" : str(assignment.amount_assigned),
                             "debitcredit" : "Cr",
                             "valuedate" : datetime.now().strftime("%Y-%m-%d")}
        posting_list.append(posting_debt)
        posting_receipt = {"account" : "receipts", "currency" : 
                             assignment.ccy,
                             "amount" : str(assignment.amount_assigned),
                             "debitcredit" : "Cr",
                             "valuedate" : datetime.now().strftime("%Y-%m-%d")}
        posting_list.append(posting_receipt)
        journal_dict["postings"] = posting_list
        return journal_dict

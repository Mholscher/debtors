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
from debtmodels.payments import (IncomingAmounts, IncomingAmountNotFoundError,
                                 AssignedAmounts)
from debtmodels.debtbilling import Bills, BillNotFoundError
from debtmodels.accounting import AccountingTemplate
from debtviews.forms import (PaymentForm, PaymentCreateForm, ClientAttachForm,
    FindClientForm, FindPaymentByRef, OtherPaymentForm)
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
        self["assigned"] = payment.assigned()

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
    """ A payment may be assigned to a bill or a payment

    The operator may search for bills in a few ways. Once the 
    bill to be paid is found, it can be paid.

    If the payment is to be assigned to another payment, the
    user can look up the payment through the references given
    by ourselves or by the bank.
    """

    def get(self, payment_id):
        """ Get the payment and show assignment  choices """

        try:
            payment = IncomingAmounts.get_payment_by_id(payment_id)
        except ValueError as ve:
            abort(404, str(ve))
        if payment.fully_assigned:
            flash("This payment has been fully assigned")
        payment = PaymentDict(payment)
        client_search_form = FindClientForm()
        payment_form = FindPaymentByRef()

        # process input search arguments for finding bill(s)

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

        if name:
            client_search_form.find_name.data = name
        if client_id:
            client_search_form.find_number.data = client_id
        if account_nr:
            client_search_form.find_bank_account.data = account_nr

        # process input search arguments for "other" payments

        our_ref = request.args.get("find_our_ref", None)
        bank_ref = request.args.get("find_bank_ref", None)

        payments_temp = payments_found = []
        to_payment_forms = []

        if our_ref or bank_ref:
            payments_temp =\
                IncomingAmounts.get_target_payments(our_ref=our_ref,
                                                    bank_ref=bank_ref)

        if our_ref:
            payment_form.find_our_ref.data = our_ref
        if bank_ref:
            payment_form.find_bank_ref.data = bank_ref

        for target_payment in payments_temp:
            target_payment = PaymentDict(target_payment)
            to_payment_form = OtherPaymentForm(obj=target_payment)
            target_payment.to_payment_form = to_payment_form
            payments_found.append(target_payment)

        return render_template('paymentassign.html', payment=payment,
                               search_results=search_results,
                               search_form=client_search_form,
                               payments_found=payments_found,
                               payment_form=payment_form)


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


class PaymentAssignToPayment(MethodView):
    """ Assign a payment to a bill """

    def post(self, from_id, to_id):
        """ Assign the payment with payment_id to another payment """

        other_ccy = request.args.get("other_ccy", None)
        other_amount = request.args.get("other_amount", None)

        from_amount = db.session.query(IncomingAmounts).\
            filter_by(id=from_id).first()
        to_amount = db.session.query(IncomingAmounts).\
            filter_by(id=to_id).first()

        if other_ccy and other_ccy != to_amount.payment_ccy:
            abort(400, "Invalid currency")

        if other_amount and not other_ccy:
            abort(400, "Currency for target amount is required")

        if other_amount:
            from_amount.assign_to_amount(to_amount,
                                         other_amount=int(other_amount),
                                         other_ccy=other_ccy)
        else:
            from_amount.assign_to_amount(to_amount)
        db.session.commit()
        return redirect(url_for("payment_assign", payment_id=from_id))


class PaymentAssignReverseView(MethodView):
    """ A payment was assigned and assignment(s) need to be reversed 

    It is immaterial what the payment was assigned to, each assignment
    (whether it was to a bill or another payment) will be reversed.
    """

    def get(self, payment_id=None):
        """ Gather assignments for payment and show these to the user.

        The user can select reversible assignments to process
        """

        try:
            payment = IncomingAmounts.get_payment_by_id(payment_id)
        except IncomingAmountNotFoundError as iafe:
            abort(404, str(iafe))
        payment_dict = PaymentDict(payment)

        assignments = payment.list_assignments()

        for assignment in assignments:
            assignment.amount = edited_amount(assignment.amount_assigned,
                                              currency=assignment.ccy)

        return render_template("assignmentreverse.html", payment=payment_dict,
                               assignment_list=assignments)

    def post(self, payment_id=None):
        """ Reverse a list of assignments for a payment """

        payment = IncomingAmounts.get_payment_by_id(payment_id)

        assignments_selected = request.form

        for id, assignment_id in assignments_selected.items():
            if id.startswith("assign"):
                assigned_amount = None
                for assignment in payment.used_in:
                    if str(assignment.id) == assignment_id:
                        assigned_amount = assignment
                        break
                else:
                    abort(404, "Assignment not found")

                if assigned_amount:
                    assigned_amount.reverse_assignment()

        payment_dict = PaymentDict(payment)

        db.session.commit()

        assignments = payment.list_assignments()

        return render_template("assignmentreverse.html", payment=payment_dict,
                               assignment_list=assignments)


class PaymentReverseView(MethodView):
    """ A reversal of a previous payment must be processed manually """

    def get(self, payment_id=None):
        """ Get a reversal to be manually reversed """

        try:
            payment_reversal = IncomingAmounts.get_payment_by_id(payment_id)
        except IncomingAmountNotFoundError as iafe:
            abort(404, str(iafe))

        if not payment_reversal.rvslind:
            flash(f"Warning: Payment {payment_id} is not a reversal")

        name = request.args.get("find_name", None)
        client_number = request.args.get("find_number", None)
        #account = request.args.get("find_bank_account", None)

        search_results = []
        client_search_form = FindClientForm()
        if name:
            client_search_form.find_name.data = name
        if client_number:
            client_search_form.find_number.data = client_number
        #if account:
        #    client_search_form.find_bank_account.data = account
        search_values = (name, client_number)

        payments_found = []

        if not any(search_values):
            reversible = IncomingAmounts.find_reversible_payments(
                payment_reversal)
            payments_found = [PaymentDict(to_convert) for to_convert
                              in  reversible]
        else:
            if client_number:
                # the user entered a client number
                try:
                    client_found = Clients.get_by_id(client_number)
                except ValueError as ve:
                    client_found = None
                if client_found:
                    payments_found = client_found.payments
            elif name:
                # the user entered (part of) a name
                payments_found = IncomingAmounts.get_payments_by_name(name,
                                     amount=payment_reversal.payment_amount,
                                     ccy=payment_reversal.payment_ccy)
 
        payment_form = FindPaymentByRef()

        return render_template("paymentreverse.html",
                               payment=payment_reversal,
                               search_results=search_results,
                               search_form=client_search_form,
                               payments_found=payments_found,
                               payment_form=payment_form)


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


class PaymentReversalAccounting(AccountingTemplate):
    ''' Create postings for the reversal from the bank for a payment.

    The accounting is created as a dictionary, ready to be shipped as a 
    JSON formatted file.

    This class assumes that GLedger is being used. Subclass or replace to
    use a different GL system.
'''

    def journal_entries(self, journal_dict, reversal):
        """ Create the postings for a payment reversal """

        journal_dict["extkey"] = "paymentreversal" + str(reversal.id)
        if reversal.payment_amount == 0:
            raise ValueError("Can not do accounting for zero amount")
        posting_list = []
        posting_debt = {"account" : "debt", "currency" : 
                             reversal.payment_ccy,
                             "amount" : str(reversal.payment_amount),
                             "debitcredit" : "Cr",
                             "valuedate" : reversal.value_date.strftime("%Y-%m-%d")}
        posting_list.append(posting_debt)
        posting_receipt = {"account" : "receipts", "currency" : 
                             reversal.payment_ccy,
                             "amount" : str(reversal.payment_amount),
                             "debitcredit" : "Db",
                             "valuedate" : reversal.value_date.strftime("%Y-%m-%d")}
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
        if assignment.bill:
            posting_debt = {"account" : "income", "currency" : 
                             assignment.ccy,
                             "amount" : str(assignment.amount_assigned),
                             "debitcredit" : "Cr",
                             "valuedate" : datetime.now().strftime("%Y-%m-%d")}
        elif assignment.to_amount:
            posting_debt = {"account" : "receipts", "currency" : 
                             assignment.ccy,
                             "amount" : str(assignment.amount_assigned),
                             "debitcredit" : "Db",
                             "valuedate" : datetime.now().strftime("%Y-%m-%d")}
        else:
            raise ValueError("Assignment to unknown target")
        posting_list.append(posting_debt)
        if (assignment.to_amount
            and assignment.ccy != assignment.to_amount.payment_ccy):
            posting_ccy_from = {"account" : "convertccy", "currency" : 
                             assignment.ccy,
                             "amount" : str(assignment.amount_assigned),
                             "debitcredit" : "Db",
                             "valuedate" : datetime.now().strftime("%Y-%m-%d")}
            posting_ccy_to = {"account" : "convertccy", "currency" : 
                             assignment.to_amount.payment_ccy,
                             "amount" : str(assignment.to_amount.payment_amount),
                             "debitcredit" : "Cr",
                             "valuedate" : datetime.now().strftime("%Y-%m-%d")}
            posting_list.append(posting_ccy_to)
            posting_list.append(posting_ccy_from)
        posting_receipt = {"account" : "receipts", "currency" : 
                             assignment.ccy,
                             "amount" : str(assignment.amount_assigned),
                             "debitcredit" : "Cr",
                             "valuedate" : datetime.now().strftime("%Y-%m-%d")}
        posting_list.append(posting_receipt)
        journal_dict["postings"] = posting_list
        return journal_dict

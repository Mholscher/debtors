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
from flask import render_template, redirect, url_for, request, flash, abort
from flask.views import MethodView
from debtors import config
from debtmodels.debtbilling import (Bills, BillLines, db, BillNotFoundError,
                                    DebtorSignal)
from debtmodels.payments import (IncomingAmounts)
from clientmodels.clients import Clients, NoClientFoundError
from clientviews.forms import ClientSearchForm
from debtviews.forms import BillCreateForm, BillChangeForm, DebtorSignalForm
from debtviews.monetary import edited_amount
from debtviews.wtformsmonetary import AmountField


query = db.session.query

def get_currency(field):
    """ The drop-in for currency retrieval by the AmountField """

    return request.form.get('billing_ccy').upper()


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

        client_search_form = ClientSearchForm()
        if bill_id:
            try:
                bill = Bills.get_bill_by_id(bill_id)
            except BillNotFoundError as bnfe:
                abort(404, str(bnfe))
            bill_form = BillChangeForm(obj=bill)
        else:
            bill = None
            bill_form = BillCreateForm()

        for i in range(3):
            bill_form.lines.append_entry()

        for line in bill_form.lines.entries:
            if bill:
                line.unit_price.currency = bill.billing_ccy
            line.edited_amount = edited_amount

        if bill:
            signals = DebtorSignal.signals_for(bill)
            for signal in signals:
                signal.date_start = signal.date_start.strftime(
                    config["DATE_FORMAT"])
                if signal.date_end:
                    signal.date_end = signal.date_end.strftime(
                        config["DATE_FORMAT"])
        else:
            signals = []

        return render_template('bill.html', form=bill_form, bill=bill,
                               debtor_signals=signals,
                               search_form = client_search_form)

    def post(self, bill_id=None):
        """ Use the request form data to add a bill """

        if request.form.get('billing_ccy'):
            AmountField.get_currency = get_currency
        if bill_id:
            bill = Bills.get_bill_by_id(bill_id)
            bill_form = BillChangeForm(obj=bill)
        else:
            bill = None
            bill_form = BillCreateForm()

        if hasattr(AmountField, 'get_currency'):
            del AmountField.get_currency

        while (bill_form.lines.__len__() > 0
            and not any(bill_form.lines.data[bill_form.lines.__len__() - 1].values())) :
            bill_form.lines.pop_entry()

        for line in bill_form.lines:
            line.edited_amount = edited_amount

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
            else:
                billing_ccy = None
            if bill_form.date_sale.data:
                date_sale = bill_form.date_sale.data

            if bill_id:
                bill.prev_bill = prev_bill
                bill.date_sale = date_sale
                bill.billing_ccy = billing_ccy
            else:
                bill = Bills(billing_ccy=billing_ccy,
                            date_sale=date_sale,
                            prev_bill=prev_bill)
            bill.client = client

            for line in bill_form.lines.data:
                create_bill_line(bill, line)

            for line in bill.lines:
                line.edited_amount = edited_amount

            db.session.commit()

            if type(bill_form) == BillCreateForm and bill_form.add_more.data:
                return redirect(url_for('bill_create'))
            else:
                return redirect(url_for('client.clients', id=client_id))

        client_search_form = ClientSearchForm()
        flash('Validation error encountered')

        if bill:
            signals = DebtorSignal.signals_for(bill)
        else:
            signals = []

        return render_template('bill.html', form=bill_form, bill=bill,
                               debtor_signals=signals,
                               search_form=client_search_form)


class ClientDebtView(MethodView):
    """ This class is used to show all debt for a client.
    
    All debt means all bills that have not yet been paid, whether or not
    the client has been notified.
    """

    def get(self, client_id=None):
        """ Create the list of client debt 

        It lists debt, payments and the balance per currency
        """

        client_search_form = ClientSearchForm()
        if client_id is None:
            raise NoClientFoundError('Client id is required')
        client = Clients.get_by_id(client_id)
        bills = Bills.get_outstanding_bills(client)

        ccy_list = { bill.billing_ccy for bill in bills }
        ccy_totals = dict()
        for ccy in ccy_list:
            total = sum([bill.total() if bill.billing_ccy == ccy else 0
                for bill in bills])
            ccy_totals[ccy] = total
        bills = {'bill_list': bills}
        payments = IncomingAmounts.client_unassigned_payments(client)
        bills["payment_list"] = payments
        for payment in payments:
            if payment[1] in ccy_totals:
                ccy_totals[payment[1]] = ccy_totals[payment[1]] - payment[3]
            else:
                ccy_totals[payment[1]] = 0 - payment[3]
        if bills['bill_list']:
            bills.update(ccy_totals)

        bills['edit_amount'] = edited_amount
        #print(bills)

        return render_template('debtforclient.html', client=client, 
                               bills=bills, search_form=client_search_form)


class BillDetailView(MethodView):
    """ Show the details of a bill.
    
    The bill may be in any state. The only thing you can do here is
    enquire upon it. To change the bill, other transactions are available.
    """

    def get(self, bill_id=None):
        """ Create the data for showing bill details """

        client_search_form = ClientSearchForm()
        if bill_id is None:
            abort(404, 'A bill id is required')
        bill = Bills.get_bill_by_id(bill_id)
        bill.date_sale_form = bill.date_sale.strftime(config["SHORT_DATE"])
        if bill.date_bill:
            bill.date_bill_form = bill.date_bill.strftime(config["SHORT_DATE"])
        for line in bill.lines:
            line.amount_edit = edited_amount
        return render_template('billdetail.html', bill=bill,
                               search_form=client_search_form)

class DebtorSignalView(MethodView):
    """ View and end a debtor signal for a client.

    Debtor signals are created for bills, but applied at the client level.
    When a bill remains unpaid to long, the client is signalled as a dubious
    debtor. This signal can be removed here.
    """
    def get(self, signal_id=None):
        """ Show the data for a selected signal """

        client_search_form = ClientSearchForm()
        signal = DebtorSignal.get_by_id(signal_id)
        signal_form = DebtorSignalForm(obj=signal)
        return render_template("signal.html", signal_form=signal_form,
                               search_form=client_search_form,
                               signal=signal)

    def post(self, signal_id=None):
        """ Post an amendment to an existing signal 

        Only the start and end date are amendable.
        """

        client_search_form = ClientSearchForm()
        signal = DebtorSignal.get_by_id(signal_id)
        signal_form = DebtorSignalForm()
        if signal_form.validate_on_submit():
            if signal_form.date_start.data\
                and (signal_form.date_start.data != signal.date_start):
                signal.date_start = signal_form.date_start.data
            if signal_form.date_end.data\
                and (signal_form.date_end.data != signal.date_end):
                signal.date_end = signal_form.date_end.data
            db.session.commit()
            return redirect(url_for("signal_update", signal_id=signal.id))

        flash("Validation error encountered")
        return render_template("signal.html", signal_form=signal_form,
                               search_form=client_search_form,
                               signal=signal)


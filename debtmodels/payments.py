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

""" This module holds the model classes for the processing of incoming 
payments.

Incoming payments are identified for the payor and the bill that the
payment must be applied to. No partial application (a payment may be
insufficient to pay all of a bill) will be performed. However, if a
payment is larger than the debt, the debt will be paid and the rest
of the amount retained for further processing.
"""

from datetime import datetime
from debtors import db
from sqlalchemy import event
from sqlalchemy.orm import Session
from debtors import InvalidDataError
from debtmodels.debtbilling import Bills
from clientmodels.clients import Clients


class IncomingAmountNotFoundError(InvalidDataError):
    """ An amount requested by id was not found """

    pass


class IncomingAmounts(db.Model):
    """ Incoming amounts are all stored in this table.
    
    After these have been stored, the assigning process takes these amounts
    and assigns them to a debt or a payment reversal.
    
    The fields have the following meaning:

        :file_timestamp: The date time the paymetn was processed
        :payment_ccy: The currency of the payment
        :payment_amount: The amount in the smallest unit (cents for $ and €)
        :debcred: To be able to process reversal we need to know debit or credit
        :client_id: After the client has been found, (s)he is coupled to the             amount; this is the assignming process.
        :value_date: The date that the amount was added to our bank balkance
        :our_ref: If a reference that we produced is on the payment, this is it
        :bank_ref: The reference from the clients bank
        :client_ref: The clients reference if (s)he has added one
        :client_name: The name on the statement or document that documents the payment
        :creditor_iban: The IBAN the payment was made from
        """

    __tablename__ = 'payments'
    id = db.Column(db.Integer, db.Sequence('payment_seq'),
                   primary_key=True)
    file_timestamp = db.Column(db.DateTime, nullable=False,
                               default=datetime.now)
    payment_ccy = db.Column(db.String(3), nullable=False)
    payment_amount = db.Column(db.Integer, default=0)
    debcred = db.Column(db.String(2), default='Cr')
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'),
                          index=True, nullable=True)
    value_date = db.Column(db.DateTime, default=datetime.now,
                               nullable=True)
    our_ref = db.Column(db.String(35))
    bank_ref = db.Column(db.String(35))
    client_ref = db.Column(db.String(35))
    client_name = db.Column(db.String(30))
    fully_assigned = db.Column(db.Boolean(), default=False)
    creditor_iban = db.Column(db.String(40), nullable=True, index=True)
    client = db.relationship('Clients', backref='payments')
    amount_queued = db.relationship('AmountQueued', uselist=False,
                                    backref='incoming_amount',
                                    cascade='all, delete')


    def add(self):
        """ Add this amount to the session. """

        db.session.add(self)

    @staticmethod
    def get_payment_by_id(payment_id):
        """ Get an Incoming amount for id payment_id """

        payment = db.session.query(IncomingAmounts).filter_by(id=payment_id).\
            first()
        if payment:
            return payment
        raise IncomingAmountNotFoundError('No payment for id {}'.format(payment_id))

    def find_client_to_attach(self):
        """ We try to find the client that made the payment """

        try:
            client = Clients.get_client_by_iban(self.creditor_iban)
        except ValueError:
            return None
        return client

    def find_assignment_targets(self):
        """ Finds a target for assignments """

        bills_with_account = Bills.bills_for_IBAN(self.creditor_iban)
        usable_bills = [bill for bill in bills_with_account 
                        if bill.total() <= self.payment_amount
                        and bill.billing_ccy == self.payment_ccy]
        if self.client_ref:
            bills_having_id = Bills.bills_having_id(self.client_ref)
            usable_bills.extend([bill for bill in bills_having_id 
                            if bill.total() <= self.payment_amount
                            and bill.billing_ccy == self.payment_ccy
                            and bill not in usable_bills])
        usable_bills.sort(key=lambda bill: bill.total(), reverse=True)
        return usable_bills

    def assign_amount(self):
        """ Assign this amount to an outstanding bill """

        client = self.find_client_to_attach()
        if client:
            self.client = client
        usable_bills = self.find_assignment_targets()
        assigned_until_now = 0
        for bill in usable_bills:
            if bill.total() <= self.payment_amount - assigned_until_now:
                assignment =\
                    AssignedAmounts(amount_id=self.id,
                                   ccy=self.payment_ccy,
                                   amount_assigned=bill.total())
                assignment.bill = bill
                assigned_until_now += assignment.amount_assigned
                bill.status = Bills.PAID
                if self.payment_amount == assigned_until_now:
                    self.fully_assigned = True
                assignment.add()

class IncomingAmountsList(list):
    ''' A list of incoming amounts to be processed  '''

    def store_all(self):
        """ Store all entries on the database """

        db.session.commit()


class AmountQueued(db.Model):
    """ Amounts incoming waiting to be assigned

    An amount that comes in needs to be assigned to a debt. This happens 
    in an asynchronous way, so as to not slow other transactions down.
    This is a queued amount.

        :id: The generated sequence number
        :amount_id: The id of the queued IncomingAmount

    """

    __tablename__ = 'amountq'
    id = db.Column(db.Integer, db.Sequence('amtq_seq'),
                   primary_key=True)
    amount_id = db.Column(db.Integer, db.ForeignKey('payments.id'))

    def add(self):
        '''
        Add the amount to the database
        '''

        db.session.add(self)

    @staticmethod
    def is_queued(amount_requested):
        """ Is the amount amount_requested queued? """

        aq = db.session.query(AmountQueued).\
            filter_by(amount_id=amount_requested).first()
        return aq is not None


class AssignedAmounts(db.Model):
    """ These are the amounts that are assigned to a bill or payment
    
    When (part of) an amount is used to pay a bill, an assigned amount is
    created for the amount used and the source. Assigned amounts are only
    created if a bill can be paid in full; we do not assign amounts to
    partially pay a bill.

    Payments may also be assigned to another payment. Se the documentation for an example.

        :id: The generated sequence number
        :amount_id: The id of the incoming amount that is assigned from
        :ccy: The amount of the assigned ccy
        :amount_assigned: How much of the incoming amount is assigned here
        :bill_id: If assigned to a bill (the standard action) the bill assigned to
        :amount_id_to: If assigned to another incoming amount, the id of the amount to which we assigned it
        :amount_to: The amount (in new ccy if applicable) on the new amount

    """

    __table_name__ = 'assignedamts'
    id = db.Column(db.Integer, db.Sequence('assgn_seq'),
                   primary_key=True)
    amount_id = db.Column(db.Integer, db.ForeignKey('payments.id'))
    ccy = db.Column(db.String(3), nullable=False)
    amount_assigned = db.Column(db.Integer, default=0)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.bill_id'),
                        nullable=True)
    amount_id_to = db.Column(db.Integer, db.ForeignKey('payments.id'),
                            nullable=True)
    amount_to = db.Column(db.Integer, default=0)
    bill = db.relationship('Bills', backref='assignments')
    from_amount = db.relationship('IncomingAmounts',uselist=False, 
                                    foreign_keys=[amount_id],
                                    backref='used_in')
    to_amount = db.relationship('IncomingAmounts', 
                                foreign_keys=[amount_id_to],
                                backref='from_amt')

    def add(self):
        """ Add self to session """

        db.session.add(self)

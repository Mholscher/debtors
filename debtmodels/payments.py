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


class IncomingAmounts(db.Model):
    """ Incoming amounts are all stored in this table.
    
    After these have been stored, the assigning process takes these amounts
    and assigns them to a debt or a payment reversal.
    
    The fields have the following meaning:

        :file_timestamp: The date time the paymetn was processed
        :payment_ccy: The currency of the payment
        :payment_amount: The amount in the smallest unit (cents for $ and €)
        :client_id: After the client has been found, (s)he is coupled to the             amount; this is the assignming process.
        :value_date: The date that the amount was added to our bank balkance
        :our_ref: If a reference that we produced is on the payment, this is it
        :bank_ref: The reference from the clients bank
        :client_ref: The clients reference if (s)he has added one
        :client_name: The name on the statement or document that documents the payment
        :creditor_IBAN: The IBAN the payment was made from
        """

    __tablename__ = 'payments'
    id = db.Column(db.Integer, db.Sequence('payment_seq'),
                   primary_key=True)
    file_timestamp = db.Column(db.DateTime, nullable=False,
                               default=datetime.now)
    payment_ccy = db.Column(db.String(3), nullable=False)
    payment_amount = db.Column(db.Integer, default=0)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'),
                          index=True, nullable=True)
    value_date = db.Column(db.DateTime, default=datetime.now,
                               nullable=True)
    our_ref = db.Column(db.String(35))
    bank_ref = db.Column(db.String(35))
    client_ref = db.Column(db.String(35))
    client_name = db.Column(db.String(30))
    creditor_IBAN = db.Column(db.String(40), nullable=True, index=True)
    client = db.relationship('Clients', backref='payments')

    def add(self):
        """ Add this amount to the session. """

        db.session.add(self)


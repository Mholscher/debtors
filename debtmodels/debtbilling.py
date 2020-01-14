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

""" This module contains the database interface items for the debt processing: 

    *   the receipt and storing of preprocessed information for new bills
    *   the alteration of bills due to payment and changes to bills
    *   the changes to bills after payment of the monies.

"""

from debtors import db


class Bills(db.Model):
    """ Bill models the bill send to the client.
    
    The bill is created either by another system sending a bill request, or through the user entering billing data. Changes through the bill are from inside the debtors system when a bill is paid, or it is replaced by another one.

        :bill_id: The primary key, goes up from 1
        :client_id: The client number the bill will be sent to. This si a foreign key into the client database
        :billing_ccy: The currency the bill is issued in.
        :date_sale: The date the system creating the bill request (the message triggering creation of the database record) wants to see on the bill as the date of the sale/contract/..
        :date_bill: The date the billing program created and sent the bill
        :prev_bill: If a bill is incorrect, a new one is sent. This is the number that this bill is replacing (so found on the new bill)
        :status: What can we do with this bill? E.g. a paid bill cannot be resent

    """

    __tablename__ = 'bill'
    bill_id = db.Column(db.Integer, db.Sequence('bill_sequence'),
                        primary_key=True)
    client_id = db.Column(db.Integer)
    billing_ccy = db.Column(db.String(3), default='EUR')
    date_sale = db.Column(db.DateTime, nullable=False)
    date_bill = db.Column(db.DateTime, nullable=True, default=None)
    prev_bill = db.Column(db.Integer, db.ForeignKey('bill.bill_id'),
                          nullable=True)
    status = db.Column(db.String(8), default='new')
    
    def add(self):
        """ Add the bill to the session """

        db.session.add(self)

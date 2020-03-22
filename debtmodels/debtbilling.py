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

from sqlalchemy.orm import validates
from debtors import db


class BillNotFoundError(ValueError):
    """ A bill requested by id was not found"""

    pass


class BillStatusInvalidError(ValueError):
    """ A passed in bill status is not valid """

    pass


class NoSaleDateError(ValueError):
    """ A sale date is required but not supplied """

    pass


class ReplacedBillError(ValueError):
    """ A bill which will be replaced does not exist """

    pass


class ShortDescRequiredError(ValueError):
    """ A bill line is required to have a short description """

    pass

class UnitPriceRequiredError(ValueError):
    """ On a bill line a unit price is required """

    pass


class Bills(db.Model):
    """ Bill models the bill sent to the client.
    
    The bill is created either by another system sending a bill request, or through the user entering billing data. Changes through the bill are from inside the debtors system when a bill is paid, or it is replaced by another one.

        :bill_id: The primary key, goes up from 1
        :client_id: The client number the bill will be sent to. This si a foreign key into the client database
        :billing_ccy: The currency the bill is issued in.
        :date_sale: The date the system creating the bill request (the message triggering creation of the database record) wants to see on the bill as the date of the sale/contract/..
        :date_bill: The date the billing program created and sent the bill
        :prev_bill: If a bill is incorrect, a new one is sent. This is the number that this bill is replacing (so found on the new bill)
        :status: What can we do with this bill? E.g. a paid bill cannot be resent

    """

    NEW = 'new'
    ISSUED = 'issued'
    PAID = 'paid'
    STATUS_NAME = { 'new' : 'New', 'issued' : 'Billed, unpaid',
                           'paid' : 'Fully paid' }

    __tablename__ = 'bill'
    bill_id = db.Column(db.Integer, db.Sequence('bill_sequence'),
                        primary_key=True)
    client_id = db.Column(db.Integer)
    billing_ccy = db.Column(db.String(3), default='EUR')
    date_sale = db.Column(db.DateTime, nullable=False)
    date_bill = db.Column(db.DateTime, nullable=True, default=None)
    prev_bill = db.Column(db.Integer, db.ForeignKey('bill.bill_id'),
                          nullable=True)
    status = db.Column(db.String(8), server_default='new')
    lines = db.relationship('BillLines', backref='bill')
    
    def add(self):
        """ Add the bill to the session """

        db.session.add(self)

    @validates('date_sale')
    def validate_date_sale(self, key, date_sale):
        """ A sale_date is required """

        if not date_sale:
            raise NoSaleDateError('A date of sale is required')
        return date_sale

    @validates('prev_bill')
    def validate_previous_bill(self, key, prev_bill):
        """ Checks a previous bill exists """

        if not prev_bill:
            return prev_bill
        try:
            old = Bills.get_bill_by_id(prev_bill)
        except BillNotFoundError:
            raise ReplacedBillError('The bill {0} to replace does not exist'.format(prev_bill))
        return prev_bill

    @validates('status')
    def validate_bill_status(self, key, status):
        """ Checks a status passed has a valid value """

        if not status in Bills.STATUS_NAME:
            raise BillStatusInvalidError('Status {} is invalid'.format(status))
        return status

    def total(self):
        """ Return the total bill amount """

        total = 0
        for line in self.lines:
            total += line.total()
        return total

    @staticmethod
    def get_bill_by_id(id_requested):
        """Get a bill by reading it by bill_id  """

        bill = db.session.query(Bills).filter_by(bill_id=id_requested).first()
        if not bill:
            raise BillNotFoundError(
                'Bill with id {0} was not found'.format(id_requested))
        return bill


class BillLines(db.Model):
    """ A line on the bill.
    
    The lines explain to the client what she is paying for.
    Each line is e.g. for a product purchased, or a period
    of a subscription.

        :bill_id: The link to the bill this line belongs to
        :line_id: The key to this line
        :short_desc: A short description of what is billed though the line
        :long_desc: A description of what is billed though the line
        :number_items: The number of items or measures
        :measure: Name of the measure used; empty is units
        :unit_price: The price of one unit (or measure)

    """

    __tablename__ = 'billlines'
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.bill_id'),
                        nullable=False)
    line_id = db.Column(db.Integer, db.Sequence('line_sequence'),
                        primary_key=True)
    short_desc = db.Column(db.String(10), nullable=False)
    long_desc = db.Column(db.String(40))
    number_of = db.Column(db.Integer, server_default='1')
    measured_in = db.Column(db.String(10), nullable=True) 
    unit_price = db.Column(db.Integer, nullable=False)

    def add(self):
        """ Add this line to the session """

        db.session.add(self)

    @validates('short_desc')
    def validate_short_desc(self, key, short_desc):
        """ A short description is required """

        if short_desc:
            return short_desc
        raise ShortDescRequiredError('A short description is required')

    @validates('unit_price')
    def validate_unit_price(self, key, unit_price):
        """ A unit price is required """

        if unit_price:
            return unit_price
        raise UnitPriceRequiredError('A unit price is required')

    def total(self):
        """ Calculate a total amount billed on this line """

        return self.number_of * self.unit_price

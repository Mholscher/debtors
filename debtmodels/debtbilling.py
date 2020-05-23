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

from dateutil.parser import parse
from sqlalchemy import event
from sqlalchemy.orm import validates, Session
from iso4217 import raw_table  # This is the currency table
from clientmodels.clients import Clients, db


class InvalidDataError(ValueError):
    """ The data passed in is invalid """

    def to_dict(self):
        """ Return a dictionary with interesting info """

        return {"message" : str(self) }


class BillNotFoundError(ValueError):
    """ A bill requested by id was not found"""

    pass


class BillLineNotFoundError(ValueError):
    """ A bill line requested by id was not found"""

    pass


class BillStatusInvalidError(InvalidDataError):
    """ A passed in bill status is not valid """

    pass


class InvalidBillingCcyError(InvalidDataError):
    """ A passed in billing  currency is not valid """

    pass

class NoSaleDateError(InvalidDataError):
    """ A sale date is required but not supplied """

    pass


class ReplacedBillError(InvalidDataError):
    """ A bill which will be replaced does not exist """

    pass


class ShortDescRequiredError(InvalidDataError):
    """ A bill line is required to have a short description """

    pass

class UnitPriceRequiredError(InvalidDataError):
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
    REPLACED = 'replaced'
    STATUS_NAME = { 'new' : 'New', 'issued' : 'Billed, unpaid',
                    'paid' : 'Fully paid', 'replaced' : 'Bill replaced' }

    __tablename__ = 'bill'
    bill_id = db.Column(db.Integer, db.Sequence('bill_sequence'),
                        primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), index=True)
    bankaccount_id = db.Column(db.Integer, db.ForeignKey('bankaccounts.id'),
                             index=True, nullable=True)
    billing_ccy = db.Column(db.String(3), default='EUR')
    date_sale = db.Column(db.Date, nullable=False)
    date_bill = db.Column(db.Date, nullable=True, default=None)
    prev_bill = db.Column(db.Integer, db.ForeignKey('bill.bill_id'),
                          nullable=True)
    status = db.Column(db.String(8), server_default='new')
    lines = db.relationship('BillLines', backref='bill',
                            cascade='all, delete')
    client = db.relationship('Clients', backref='bills')
    bank_account = db.relationship('BankAccounts', backref='used_in_bills')
    
    def add(self):
        """ Add the bill to the session """

        db.session.add(self)

    @validates('billing_ccy')
    def validate_billing_ccy(self, key, billing_ccy):
        """ Validate the currency against iso 4217 table """

        if not billing_ccy in raw_table.keys():
            raise InvalidBillingCcyError(
                'The currency {} is invalid'.format(billing_ccy))
        return billing_ccy

    @validates('date_sale')
    def validate_date_sale(self, key, date_sale):
        """ A sale_date is required """

        if not date_sale:
            raise NoSaleDateError('A date of sale is required')
        return date_sale

    @validates('prev_bill')
    def validate_previous_bill(self, key, prev_bill):
        """ Checks a previous bill exists """

        return self.check_prev_bill(prev_bill)

    @validates('status')
    def validate_bill_status(self, key, status):
        """ Checks a status passed has a valid value """

        if not status in Bills.STATUS_NAME:
            raise BillStatusInvalidError('Status {} is invalid'.format(status))
        return status

    def set_replaced(self):
        """ Set this bill's status to replaced """

        self.status = self.REPLACED
        return self

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

    @staticmethod
    def check_prev_bill(prev_bill):
        """ Check if a bill id passed in prev_bill exists """

        if not prev_bill:
            return prev_bill
        try:
            old = Bills.get_bill_by_id(prev_bill)
        except BillNotFoundError:
            raise ReplacedBillError('The bill {0} to replace does not exist'.format(prev_bill))
        return prev_bill

    @staticmethod
    def get_bills_with_status(client, statuses):
        """ Return a list of bills for a client with passed in status """

        return [bill for bill in client.bills if bill.status in statuses]

    @staticmethod
    def get_outstanding_bills(client):
        """ Return a list of outstanding bills for client """

        return Bills.get_bills_with_status(client, [Bills.NEW, Bills.ISSUED])

    def set_bill_status_replaced(self, session):
        """ Set the bill status of the bill with id bill_id to replaced

        This is used when the new bill is created """

        if not self.prev_bill:
            return
        old = Bills.get_bill_by_id(self.prev_bill)
        if old:
            old.set_replaced()
            return
        raise BillNotFoundError(f"The bill with id {bill_id} was not found")

    @classmethod
    def create_from_dict(cls, bill_dict):
        """ Create a bill and bill lines from a dictionary

        The dictionary is modeled after the message an external system
        may send to debtors. The bill may need to default some of the
        items, as will bill lines. The result is a bill that is returned.
        """

        client = Clients.get_by_id(int(bill_dict['client'])) 
        try:
            bill = cls(date_sale=parse(bill_dict["date-sale"]))
        except KeyError as ke:
            raise NoSaleDateError("date-sale missing")
        bill.client = client
        if bill_dict.get('currency'):
            bill.billing_ccy = bill_dict['currency']
        if bill_dict.get('bill-replaced'):
            bill.prev_bill = bill_dict['bill-replaced']
        for bill_line in bill_dict["bill-lines"]:
            BillLines.create_line_from_dict(bill, bill_line)
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

    @staticmethod
    def get_by_id(line_id):
        """ Get a line by id """

        line = db.session.query(BillLines).filter_by(line_id = line_id).first()
        if line:
            return line
        raise BillLineNotFoundError("No line found for id")
        

    @classmethod
    def create_line_from_dict(cls, bill, line_dict):
        """ This creates a bill line from a dictionary for a bill
        
        The bill is a Bills instance, used to attach the created line to.
        The line_dict is defining a line for the bill
        """

        line = cls()
        if line_dict.get("short-desc"):
            line.short_desc = line_dict.get("short-desc")
        if line_dict.get("long-desc"):
            line.long_desc = line_dict.get("long-desc")
        line.unit = line_dict["unit"]
        if line_dict.get("unit-desc"):
            line.unit_desc = line_dict["unit-desc"]
        if line_dict.get("unit-price"):
            line.unit_price = line_dict["unit-price"]
        bill.lines.append(line)


@event.listens_for(Session, "before_flush")
def before_flush(session, flush_context, instances):
    """ This is the place to do cross item edits and changes.

    All items are ready to be persisted and need no more
    updates.
    """

    for instance in session.dirty | session.new:
        if isinstance(instance, Bills):
            instance.set_bill_status_replaced(session)

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

from datetime import date
from dateutil.parser import parse
from sqlalchemy import event
from sqlalchemy.orm import validates, Session
from iso4217 import raw_table  # This is the currency table
from clientmodels.clients import Clients, BankAccounts
from debtors import InvalidDataError, db


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
    """ A bill cannot be replaced or does not exist """

    pass


class ShortDescRequiredError(InvalidDataError):
    """ A bill line is required to have a short description """

    pass


class UnitPriceRequiredError(InvalidDataError):
    """ On a bill line a unit price is required """

    pass


class NoClientInPreferenceError(ValueError):
    """ A preference must be for a client """

    pass


class InvalidMediumError(ValueError):
    """ Invalid value in a bill medium """

    pass


class ShortNameSearchStringError(ValueError):
    """ The search string for a client name search was too short """

    pass


class ClientHasSignalError(InvalidDataError):
    """ The client has a debtors signal (dubious debtor) """

    pass


class SignalNotFoundError(ValueError):
    """ There is no signal for the id supplied  """

    pass


class EndBeforeStartError(ValueError):
    """ The start date is after the end date  """

    pass


class Bills(db.Model):
    """ Bill models the bill sent to the client.

    The bill is created either by another system sending a bill request,
    or through the user entering billing data. Changes through the bill
    are from inside the debtors system when a bill is paid, or it is
    replaced by another one.

        :bill_id: The primary key, goes up from 1
        :client_id: The client number the bill will be sent to. This is
            a foreign key into the client database
        :billing_ccy: The currency the bill is issued in.
        :date_sale: The date the system creating the bill request
            (the message triggering creation of the database record)
            wants to see on the bill as the date of the sale/contract/..
        :date_bill: The date the billing program created and sent the bill
        :prev_bill: If a bill is incorrect, a new one is sent. This is
            the number that this bill is replacing (so found on the new bill)
        :status: What can we do with this bill? E.g. a paid bill cannot
            be resent

    """

    NEW = 'new'
    ISSUED = 'issued'
    PAID = 'paid'
    REPLACED = 'replaced'
    DUBIOUS = 'dubious'
    STATUS_NAME = {'new': 'New', 'issued': 'Billed, unpaid',
                   'paid': 'Fully paid', 'replaced': 'Bill replaced',
                   'dubious': 'Debtor dubious'}

    __tablename__ = 'bill'
    bill_id = db.Column(db.Integer,  db.Sequence('bill_sequence'),
                        primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), index=True)
    billing_ccy = db.Column(db.String(3), default='EUR')
    date_sale = db.Column(db.Date, nullable=False)
    date_bill = db.Column(db.Date, nullable=True, default=None)
    prev_bill = db.Column(db.Integer, db.ForeignKey('bill.bill_id'),
                          nullable=True)
    status = db.Column(db.String(8), server_default='new')
    lines = db.relationship('BillLines', backref='bill',
                            cascade='all, delete')
    client = db.relationship('Clients', backref='bills')
    __table_args__ = (db.Index('bystatus', 'status'),)

    def __init__(self, **kwargs):

        if "client_id" in kwargs:
            client = Clients.get_by_id(kwargs["client_id"])
            if DebtorSignal.client_has_signal(client):
                raise ClientHasSignalError("Client has signal")
        elif "client" in kwargs:
            if DebtorSignal.client_has_signal(kwargs["client"]):
                raise ClientHasSignalError("Client has signal")
        super().__init__(**kwargs)

    def add(self):
        """ Add the bill to the session """

        db.session.add(self)

    @validates('billing_ccy')
    def validate_billing_ccy(self, key, billing_ccy):
        """ Validate the currency against iso 4217 table """

        if billing_ccy not in raw_table.keys():
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

        if status not in Bills.STATUS_NAME:
            raise BillStatusInvalidError('Status {} is invalid'.format(status))
        return status

    def set_replaced(self):
        """ Set this bill's status to replaced """

        self.status = self.REPLACED
        return self

    def update_for_bill_production(self):
        """ A physical bill was produced for this bill """

        self.status = self.ISSUED

    def debtor_becomes_dubious(self):
        """ The debtor has become dubious, bill needs to be marked """

        self.status = self.DUBIOUS

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
        """ Check if a bill id passed in prev_bill exists
        and has a valid status.
        """

        if not prev_bill:
            return prev_bill
        try:
            old = Bills.get_bill_by_id(prev_bill)
        except BillNotFoundError:
            raise ReplacedBillError('The bill {0} to replace does not exist'.
                                    format(prev_bill))
        if old.status not in {Bills.NEW, Bills.ISSUED}:
            msg = ('Bill to replace {0} has invalid status {1}'
                .format(prev_bill, old.status))
            raise ReplacedBillError(msg)
        return prev_bill

    @staticmethod
    def get_bills_with_status(client, statuses):
        """ Return a list of bills for a client with passed in status """

        return [bill for bill in client.bills if bill.status in statuses]

    @staticmethod
    def get_outstanding_bills(client):
        """ Return a list of outstanding bills for client """

        return Bills.get_bills_with_status(client, [Bills.NEW, Bills.ISSUED])

    @staticmethod
    def bills_for_IBAN(IBAN):
        """ Get a list of bills with the IBAN passed in """

        accounts = (db.session.query(BankAccounts).filter_by(iban=IBAN).
            all())
        clients = [account.owner for account in accounts]
        return [bill for client in clients for bill in client.bills
                if bill.status == Bills.ISSUED]

    @staticmethod
    def bills_for_clients_name_like(search_string):

        if len(search_string) < 3:
            raise ShortNameSearchStringError("Search string must be > 2 characters")
        client_list = Clients.client_list(search_for=search_string)
        bill_list = []
        for client in client_list:
            bill_list.extend(Bills.get_outstanding_bills(client))
        return bill_list

    @staticmethod
    def bills_having_id(reference):
        """ Collect bills having an id which is in the reference """

        if not reference:
            raise ValueError('A reference is required')
        word_list = reference.split()
        search_for = None
        for word in word_list:
            if word.isnumeric():
                search_for = int(word)
                break
        if not search_for:
            return []
        bills = Bills.query.filter_by(bill_id=search_for)
        bills = bills.filter(Bills.status.in_([Bills.ISSUED, Bills.NEW])).all()
        return bills

    def set_bill_status_replaced(self, session):
        """ Set the bill status of the bill with id bill_id to replaced

        This is used when the new bill is created """

        if not self.prev_bill:
            return
        old = Bills.get_bill_by_id(self.prev_bill)
        if old:
            old.set_replaced()
            return
        raise BillNotFoundError(f"The bill with id {self.prev_bill} was not found")

    def bill_is_paid(self):
        """A bill is paid.

        Currently no side effects, so just set to paid.
        """

        self.status = self.PAID

    def assignment_reversal(self):
        """ The bill was paid previously, but the assignment of the monies
        needs to be revered
        """
        self.status = self.ISSUED

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
        except KeyError:
            raise NoSaleDateError("date-sale missing")
        bill.client = client
        if bill_dict.get('currency'):
            bill.billing_ccy = bill_dict['currency']
        if bill_dict.get('bill-replaced'):
            bill.prev_bill = bill_dict['bill-replaced']
        for bill_line in bill_dict["bill-lines"]:
            BillLines.create_line_from_dict(bill, bill_line)
        if bill_dict.get("debtor-preferences", None):
            DebtorPreferences.create_from_dict(bill_dict["debtor-preferences"],
                                               bill.client)
        return bill

    @classmethod
    def debt_for_period(cls, start_debt_period, end_debt_period):
        """ Return the debt for a period 

        The start and end of period are passed in as dates. The start
        date is not included, the end date is. If start or end date is
        None, that means unbounded, any start date or end date.
        """

        bills = db.session.query(cls)
        bills = bills.filter(cls.status == Bills.ISSUED)
        if start_debt_period:
            bills = bills.filter(cls.date_bill >= start_debt_period)
        if end_debt_period:
            bills = bills.filter(cls.date_bill < end_debt_period)
        bills = bills.all()
        amount_bill_total = dict()
        for bill in bills:
            if bill.billing_ccy in amount_bill_total:
                amount_bill_total[bill.billing_ccy] += bill.total()
            else:
                amount_bill_total[bill.billing_ccy] = bill.total()
        return amount_bill_total



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

        line = db.session.query(BillLines).filter_by(line_id=line_id).first()
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


class DebtorSignal(db.Model):

    __tablename__ = "debtsignals"
    id = db.Column(db.Integer, db.Sequence("signal_seq"),
                   primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), index=True)
    date_start = db.Column(db.Date, nullable=False)
    date_end = db.Column(db.Date, nullable=True, server_default=None)
    client = db.relationship('Clients', uselist=False, backref='signals')

    def add(self):
        """ Add this signal to the session """

        db.session.add(self)

    @validates("date_end")
    def validate_date_end(self, key, date_end):
        """ Validate the end date """

        if date_end is None:
            return date_end
        if self.date_start:
            if date_end < self.date_start:
                raise EndBeforeStartError("End date must be on or after start date")
        return date_end

    @classmethod
    def client_has_signal(cls, client):
        """ Does the client passed have a signal? 

        the routine returns the signal or none for no signal found.
        """

        return db.session.query(cls).filter_by(client=client).first()

    @classmethod
    def signals_for(cls, bill, as_of=date.today()):
        """ This routine returns signals for as_of date

        It returns a list of signals with client, start and end dates of 
        the signal.
        """

        client_signals = db.session.query(cls).filter_by(client=bill.client).all()
        client_signals = [signal for signal in client_signals
                           if not signal.date_end or signal.date_end >= date.today()]
        return client_signals

    @staticmethod
    def get_by_id(signal_id):
        """ Get the signal for signal_id """

        signal = db.session.query(DebtorSignal).filter_by(id=signal_id).first()
        if signal:
            return signal
        raise SignalNotFoundError(f"No error with id {signal_id}")


class DebtorPreferences(db.Model):
    """ This class holds the preferences of the client for the debtors
    transactions.

        :bill medium: What kind of bill (mail, paper etc.) is to be sent
        :letter medium: What kind of letters (e-mail, paper) is preferred

    """

    __tablename__ = 'debtprefs'

    PREF_MAIL = 'mail'
    PREF_POSTAL = 'post'
    PREF_DEBIT = 'dd'
    BILL_MEDIA = {PREF_MAIL, PREF_POSTAL, PREF_DEBIT}
    LETTER_MEDIA = {PREF_MAIL, PREF_POSTAL}

    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'),
                          nullable=False, primary_key=True)
    bill_medium = db.Column(db.String(5), default='mail')
    letter_medium = db.Column(db.String(5), server_default='post')
    client = db.relationship('Clients', backref='debtor_prefs')

    @validates('bill_medium')
    def validate_bill_medium(self, key, bill_medium):

        if bill_medium is None:
            return bill_medium
        if bill_medium in self.BILL_MEDIA:
            return bill_medium
        raise InvalidMediumError('{} is not a valid bill medium'
                                 .format(bill_medium))

    @validates('letter_medium')
    def validate_letter_medium(self, key, letter_medium):

        if letter_medium is None:
            return letter_medium
        if letter_medium in self.BILL_MEDIA:
            return letter_medium
        raise InvalidMediumError('{} is not a valid letter medium'
                                 .format(letter_medium))

    def check_media(self, session):
        """ Check if the chosen media for the client are available.

        If a medium is not available, default to postal.
        """

        if not self.client:
            raise NoClientInPreferenceError('A preference must be set for a client')

        if not self.client.preferred_mail():
            if self.bill_medium == self.PREF_MAIL:
                self.bill_medium = self.PREF_POSTAL
            if self.letter_medium == self.PREF_MAIL:
                self.letter_medium = self.PREF_POSTAL

    @staticmethod
    def create_from_dict(preference_dict, client):
        """ Create preferences from a dictionary """

        prefs = client.debtor_prefs
        if prefs:
            prefs.bill_medium = preference_dict["bill-medium"]
            prefs.letter_medium = preference_dict["letter-medium"]
            return
        prefs = DebtorPreferences(client=client,
                                bill_medium=preference_dict["bill-medium"],
                                letter_medium=preference_dict["letter-medium"]
                                )

    def add(self):
        """ Add these preferences to the session """

        db.session.add(self)


@event.listens_for(Session, "before_flush")
def before_flush(session, flush_context, instances):
    """ This is the place to do cross item edits and changes.

    All items are ready to be persisted and need no more
    updates.
    """

    for instance in session.dirty | session.new:
        if isinstance(instance, Bills):
            instance.set_bill_status_replaced(session)
        if isinstance(instance, DebtorPreferences):
            instance.check_media(session)

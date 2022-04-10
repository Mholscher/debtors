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

Incoming payments are identified for the payer and the bill that the
payment must be applied to. No partial application (a payment may be
insufficient to pay all of a bill) will be performed. However, if a
payment is larger than the debt, the debt will be paid and the rest
of the amount retained for further processing.
"""

from datetime import datetime
from debtors import db
from sqlalchemy.orm import validates
from iso4217 import raw_table  # This is the currency table
from debtors import InvalidDataError
from debtmodels.debtbilling import Bills
from clientmodels.clients import Clients


class IncomingAmountNotFoundError(InvalidDataError):
    """ An amount requested by id was not found """

    pass


class IncomingAmountInvalidCcyError(InvalidDataError):
    """ Validation of amount currency failed """

    pass


class InvalidDebitCreditError(InvalidDataError):
    """ Validation of debit/credit indicator failed """

    pass


class ReferenceToLongError(InvalidDataError):
    """ A reference is too long """

    pass


class CanNotAttachIfMoneyAssignedError(InvalidDataError):
    """ We cannot attach another client if money has been assigned """

    pass


class CanOnlyAssignBillAmount(ValueError):
    """ A bill can only be assigned the exact bill amount """

    pass


class CanOnlyAssignToBillInSameCcy(ValueError):
    """ Trying to assign to a bill in currency not equal to payment """

    pass


class NoSupportedArgumentError(ValueError):
    """ No actual parameter found that is supported """

    pass


class CannotAssignZeroAmountToAmount(ValueError):
    """ A zero amount cannot be assigned """

    pass


class AToAmountIsRequiredError(ValueError):
    """ To assign to a foreign currency, we need the amount in foreign 
    currency """

    pass


class AmountInOtherCcyRequiredError(ValueError):
    """ Assigning to an amount in other currency needs the amount in 
    that currency """

    pass


class CanOnlyReverseEqualAmountError(ValueError):

    pass


class CanNotReverseToAssignedAmount(ValueError):
    """ Amount we want to reverse is assigned """

    pass

class ReverseRequiredOppositeDebcred(ValueError):
    """ Trying to reverse an amount with an amount having same debit/credit """

    pass


class IncomingAmountIsNotAReversal(ValueError):
    """ An incoming amount which was requested as a reversal is not a
    reversal """

    pass


class AssignmentOfReversalNotPossible(ValueError):
    """ We cannot (yet) reverse assignment of a reversal """

    pass


class AssignedAmountNotFound(ValueError):
    """ An assigned amount was requested that does not exist """

    pass


def validate_currency(currency):
    """ Validate the currency on ISO 2417 """

    currency = currency.upper()
    return currency if currency in raw_table.keys() else None


class IncomingAmounts(db.Model):
    """ Incoming amounts are all stored in this table.

    After these have been stored, the assigning process takes these amounts
    and assigns them to a debt or a payment reversal.

    The fields have the following meaning:

        :file_timestamp: The date time the paymetn was processed
        :payment_ccy: The currency of the payment
        :payment_amount: The amount in the smallest unit (cents for $ and €)
        :debcred: To be able to process reversal we need to know debit
            or credit
        :client_id: After the client has been found, (s)he is coupled to
            the amount; this is the assignming process.
        :value_date: The date that the amount was added to our bank balkance
        :our_ref: If a reference that we produced is on the payment, this is it
        :bank_ref: The reference from the clients bank
        :client_ref: The clients reference if (s)he has added one
        :client_name: The name on the statement or document that documents
            the payment
        :creditor_iban: The IBAN the payment was made from
        """

    CREDIT = "Cr"
    DEBIT = "Db"
    DEBCRED = {CREDIT: "Credit", DEBIT: "Debit"}
    __tablename__ = 'payments'
    id = db.Column(db.Integer, db.Sequence('payment_seq'),
                   primary_key=True)
    file_timestamp = db.Column(db.DateTime, nullable=False,
                               default=datetime.now)
    payment_ccy = db.Column(db.String(3), nullable=False)
    payment_amount = db.Column(db.Integer, default=0)
    debcred = db.Column(db.String(2), default='Cr')
    rvslind = db.Column(db.Boolean, default=False)
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
    client = db.relationship(Clients, backref='payments')
    amount_queued = db.relationship('AmountQueued', uselist=False,
                                    backref='incoming_amount',
                                    cascade='all, delete')

    @validates("payment_ccy")
    def validate_ccy(self, key, currency):
        """ Validate the currency entered """

        currency = currency.upper()
        if validate_currency(currency):
            return currency

        raise IncomingAmountInvalidCcyError(
            'The currency {} is invalid'.format(currency))

    @validates("debcred")
    def validatedebcred(self, key, debcred):
        """ Validate the values in the debit/credit indicator  """

        if debcred not in {"Cr", "Db"}:
            raise InvalidDebitCreditError("{} is invalid".format(debcred))

        return debcred

    def validate_maxlen(self, reference):
        """ A reference may not be longer than 35 positions """

        if len(reference) > 35:
            raise ReferenceToLongError("The reference is too long")
        return reference

    @validates("our_ref")
    def validate_our_reference(self, key, our_ref):
        """ Validate our reference """

        if not our_ref:
            return our_ref
        return self.validate_maxlen(our_ref)

    def add(self):
        """ Add this amount to the session. """

        db.session.add(self)

    @staticmethod
    def get_payment_by_id(payment_id):
        """ Get an Incoming amount for id payment_id """

        payment = (db.session.query(IncomingAmounts).filter_by(id=payment_id).
            first())
        if payment:
            return payment
        raise IncomingAmountNotFoundError('No payment for id {}'
                                          .format(payment_id))

    def find_client_to_attach(self):
        """ We try to find the client that made the payment """

        try:
            client = Clients.get_client_by_iban(self.creditor_iban)
        except ValueError:
            return None
        return client

    def find_assignment_targets(self):
        """ Finds a target for assignments """

        if not self.client:
            self.client = self.find_client_to_attach()

        if self.client:
            bills_for_client = Bills.get_outstanding_bills(self.client)
            usable_bills = [bill for bill in bills_for_client
                            if bill.total() <= self.payment_amount
                            and bill.billing_ccy == self.payment_ccy]
        else:
            usable_bills = []

        if self.client_ref:
            bills_having_id = Bills.bills_having_id(self.client_ref)
            usable_bills.extend([bill for bill in bills_having_id
                                if bill.total() <= self.payment_amount
                                and bill.billing_ccy == self.payment_ccy
                                and bill not in usable_bills])
        usable_bills.sort(key=lambda bill: bill.total(), reverse=True)
        return usable_bills

    def assign_amount(self):
        """ Assign this amount to an outstanding bill 

        This routine scripts finding assignment candidates, 
        attaching a client to the payment and executing as many
        assignments as we can from this payment.
        """

        client = self.find_client_to_attach()
        if client:
            self.client = client
        usable_bills = self.find_assignment_targets()
        assigned_until_now = 0
        for bill in usable_bills:
            to_assign = bill.total()
            if to_assign <= self.payment_amount - assigned_until_now:
                self.assign_to_bill(bill, amount=to_assign)
                assigned_until_now += to_assign
                if self.payment_amount == assigned_until_now:
                    self.fully_assigned = True
                    break

    def list_assignments(self):
        """ Return assignments that have not been reversed """

        return [x for x in self.used_in if not x.reversed]

    def assigned(self):
        """ Total up the amount assigned to this payment """

        assigned_total = 0
        for assigned_amount in self.used_in:
            assigned_total += assigned_amount.amount_assigned
        return assigned_total

    def change_client(self, new_client):
        """ Change the client the payment is assigned to

            :new_client: The client this amount will be assigned to

        """

        if self.assigned():
            raise CanNotAttachIfMoneyAssignedError("Cannot attach\
                to payment with assigned amount")
        self.client = new_client
        self.assign_amount()

    def assign_to_bill(self, bill, *, amount=None):
        """ Create an assignment for this amount to bill

            :bill: Assign the amount to this bill
            :amount: If the full payment is not to be assigned to this bill,
                the amount that callee thinks need to be assigned.

        """

        if amount is None:
            assignment_amount = self.payment_amount
        else:
            assignment_amount = amount

        if self.payment_ccy != bill.billing_ccy:
            raise CanOnlyAssignToBillInSameCcy("Currency of bill is {}"
                                               .format(bill.billing_ccy))

        if assignment_amount < bill.total():
            raise CanOnlyAssignBillAmount("Amount to be assigned must be more than or equal billed amount")
        assignment_amount = bill.total()

        assigned_amount = AssignedAmounts(ccy=self.payment_ccy,
                                          amount_assigned =
                                            assignment_amount)
        assigned_amount.bill = bill
        bill.bill_is_paid()
        assigned_amount.from_amount = self
        return assigned_amount

    def assign_to_amount(self, to_amount, other_ccy=None, other_amount=None):
        """ Assign this amount to another amount

        The amounts are checked, the assignment is placed in the
        assignments table and the amount assigned to is updated

            :to_amount: The amount we want to assign the current amount to
            :other_ccy: The currency of the amount assigned to, only use if it is
                different from the currency of this amount
            :other_amount: the amount in the other currency. Only fill if there is
                a currency difference

        """

        if self.payment_amount == 0 or self.fully_assigned:
            raise CannotAssignZeroAmountToAmount("Amount must be > 0")

        if self.payment_ccy != to_amount.payment_ccy and not other_amount:
            raise AmountInOtherCcyRequiredError("Amount in other currency required")

        assigned_amount = AssignedAmounts(ccy=self.payment_ccy,
                               amount_assigned=self.payment_amount
                               - self.assigned())
        assigned_amount.from_amount = self
        assigned_amount.to_amount = to_amount

        if other_ccy:
            if other_amount:
                to_amount.payment_amount += other_amount
            else:
                raise AToAmountIsRequiredError("Amount in {} missing".format(other_ccy))
        else:
            to_amount.payment_amount += assigned_amount.amount_assigned
        self.fully_assigned = True

        return assigned_amount

    def assign_reversal_to_payment(self, to_amount):
        """ Assign this payment to another payment that will be reversed 

        This payment will be assigned as if it is a normal payment, although
        it is a debit. The to_amount will be assigned to and no longer
        available for use to pay a bill.
        """

        if self.payment_ccy != to_amount.payment_ccy:
            raise CanOnlyAssignToBillInSameCcy("Reversal must be same currency as original")
        if self.payment_amount != to_amount.payment_amount:
            raise CanOnlyReverseEqualAmountError("Reversal must be same amount as original")
        if to_amount.assigned():
            raise CanNotReverseToAssignedAmount("Amount reversed was assigned")
        if self.debcred == to_amount.debcred:
            raise ReverseRequiredOppositeDebcred("Can only reverse opposites")

        assigned_amount = AssignedAmounts(ccy=self.payment_ccy,
                               amount_assigned=self.payment_amount)
        assigned_amount.from_amount = self
        assigned_amount.to_amount = to_amount
        self.fully_assigned = True

        to_assignment = AssignedAmounts(ccy=to_amount.payment_ccy,
                                        amount_assigned=
                                        to_amount.payment_amount)
        to_assignment.from_amount = to_amount
        to_assignment.to_amount = self
        to_amount.fully_assigned = True
        return assigned_amount

    def reverse_assignment(self, assigned_amount):
        """ The assignment of this amount in assigned_amount is to be reversed

        All action done by assigning need to be reversed

            :assigned_amount: The assignment that is reversed

        """

        if self.rvslind:
            raise AssignmentOfReversalNotPossible("Cannot reverse assignment of a reversal")
        assigned_amount.reverse_assignment()

    def reverse_assignment_for(self, amount):
        """ An assignment is reversed, this amounts payment amount will be
        lowered

            :amount: The amount by which the amount available (payment_amount)
                needs to be lowered

        """

        self.payment_amount -= amount

    @staticmethod
    def get_bill_targets(name=None, client_id=None, account_nr=None):
        """ Get bills targeted in assignment by client or bank account

        A user can assign a payment to any bill. This routine returns bills
        from input:

            :name: (part of) the name of a client
            :number: the client number of a client
            :bank account: a bank account number of a client

        """

        if client_id:
            try:
                client = Clients.get_by_id(client_id)
                return Bills.get_outstanding_bills(client)
            except ValueError as ve:
                return []
        if name:
            return Bills.bills_for_clients_name_like(name)
        if account_nr:
            return Bills.bills_for_IBAN(account_nr)
        raise NoSupportedArgumentError("Pass client name, number or bank account")

    @staticmethod
    def find_reversible_payments(debit_amount):
        """ Find a list of payments that can be reversed.

        When a debit amount is input (either through the browser or CAMT53,
        we try to find a list of reversible payments.
        """

        payment_list = db.session.query(IncomingAmounts).\
            filter_by(creditor_iban=debit_amount.creditor_iban,
                      payment_amount=debit_amount.payment_amount,
                      payment_ccy=debit_amount.payment_ccy,
                      debcred="Cr").all()
        return payment_list

    @staticmethod
    def find_reversible_by_clients(client_list):
        """ We get a list of clients and return reversible payments

        The payments are retrieved from the clients by following 
        the links on the client records, but defined in this class 
        (i.e. IncomingAmounts) 
        """

        payment_list = []
        for client in client_list:
            payment_list.extend(client.payments)
        return payment_list

    @staticmethod
    def get_payments_by_name(name_fragment, amount=None, ccy=None):
        """ Return payments where the bank supplied (part of) this name 
        for the payer and optionally the amount and currency.
        """

        amount_list = db.session.query(IncomingAmounts).\
            filter(IncomingAmounts.client_name.like("%" + name_fragment
                                                            + "%"))
        if amount:
            amount_list = amount_list.filter(IncomingAmounts.payment_amount
                                                ==amount)
        if ccy:
            amount_list = amount_list.filter(IncomingAmounts.payment_ccy
                                                ==ccy)
        return amount_list.all()

    def reverse_if_one_target(self):
        """ If there is only one target found for reversing, do it

        This function is executed on the reversal!
        """

        target_list = IncomingAmounts.find_reversible_payments(self)
        target_list = [target for target in target_list 
                       if not target.assigned()]
        if len(target_list) == 1:
            return self.assign_reversal_to_payment(target_list[0])

    def get_target_payments(our_ref=None, bank_ref=None):
        """ Get a list of payments with a given (part of) reference """

        if our_ref is None and bank_ref is  None:
            raise NoSupportedArgumentError("(Part of) a reference is required")
        q = IncomingAmounts.query
        if our_ref:
            q = q.filter(IncomingAmounts.our_ref.like("%"+our_ref+"%"))
        if bank_ref:
            q = q.filter(IncomingAmounts.bank_ref.like("%"+bank_ref+"%"))
        q = q.all()
        return q

    @staticmethod
    def client_unassigned_payments(client):
        """ Return unassigned payments for a client. 

        Return a list of unassigned payments, taking into account
        partial assignment (to other payments).

        For each payment we return

            :id: The payment number
            :payment_ccy: The currency of the payment
            :payment_amount: the original amount paid
            :unassigned_amount: the amount not yet assigned
            """

        payments = []
        for payment in client.payments:
            payment_data = (payment.id,
                            payment.payment_ccy,
                            payment.payment_amount,
                            payment.payment_amount - payment.assigned())
            if payment_data[3]:
                payments.append(payment_data)
        return payments


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

        aq = (db.session.query(AmountQueued).
            filter_by(amount_id=amount_requested).first())
        return aq is not None


class AssignedAmounts(db.Model):
    """ These are the amounts that are assigned to a bill or payment

    When (part of) an amount is used to pay a bill, an assigned amount is
    created for the amount used and the source. Assigned amounts are only
    created if a bill can be paid in full; we do not assign amounts to
    partially pay a bill.

    Payments may also be assigned to another payment. Se the documentation
    for an example.

        :id: The generated sequence number
        :amount_id: The id of the incoming amount that is assigned from
        :ccy: The amount of the assigned ccy
        :amount_assigned: How much of the incoming amount is assigned here
        :bill_id: If assigned to a bill (the standard action) the id of the
            bill assigned to
        :bill: If assigned to a bill the bill that is assigned to
        :amount_id_to: If assigned to another incoming amount, the id of the
            amount to which we assigned it
        :reversed: This assignment was reversed and has been promoted to history
        :to_amount: The amount (in new ccy if applicable) on the new amount
        :from_amount: The incoming amount (payment) that is assigned in this

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
    reversed = db.Column(db.Boolean, nullable=True, default=False)
    bill = db.relationship('Bills', backref='assignments')
    from_amount = db.relationship('IncomingAmounts', uselist=False,
                                  foreign_keys=[amount_id],
                                  backref='used_in')
    to_amount = db.relationship('IncomingAmounts',
                                foreign_keys=[amount_id_to],
                                backref='from_amt')

    def add(self):
        """ Add self to session """

        db.session.add(self)

    def reverse_assignment(self):
        """ This assignment is to be reversed 

        The assignment will be deleted and all steps taken when assigning
        will need to be wiped out.
        """

        if self.bill:
            self.bill.assignment_reversal()
        if self.to_amount:
            self.to_amount.reverse_assignment_for(self.amount_assigned)
        self.from_amount.fully_assigned = False
        self.reversed = True

    @staticmethod
    def get_by_id(assignment_id=None):
        """ Get the assignment with id assignment_id  """

        assignment = db.session.query(AssignedAmounts).\
            filter_by(id=assignment_id).first()

        if assignment:
            return assignment

        raise AssignedAmountNotFound("An assigned amount requested was not found")

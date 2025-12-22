#    Copyright 2021 Menno Hölscher
#
#    This file is part of Debtors.

#    Debtors is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    Debtors is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with Debtors.  If not, see <http://www.gnu.org/licenses/>.

""" This module holds the generic code for overdue processing.

Overdue processing has a bit which handles the scheduling and storage of
items pertaining to the scheduling. That is this module. There is also
a module holding the so-called processors, that implement example steps of
overdue processing.
"""

from datetime import date, timedelta, datetime
from debtors import db
from sqlalchemy.orm import (validates, load_only, aliased, mapped_column)
from debtors import app
from debtmodels.debtbilling import Bills
from debtmodels.payments import IncomingAmounts

config = app.config

class DuplicateStepIdError(ValueError):
    """ A step with the same id already exists """

    pass


class NoStepWithIdError(ValueError):
    """ A step with the given id does not exist """

    pass


class StepMustHaveNameError(ValueError):
    """ A step must have a (non-empty) name """

    pass


class DuplicateStepNameError(ValueError):
    """ A step name must be unique """

    pass


class BillStatusWrongError(ValueError):
    """ A bill must have an unpaid/unissued status to be in overdue """

    pass


class ProcessorAlreadyExistsError(BaseException):
    """ Just create one instance of a processor """

    pass


class OverdueSteps(db.Model):
    """ This class holds the information to identify an overdue steps

    The overdue processing has different steps, that are triggered by the
    time since the later of due date and bill date. The processor in each
    step points to a processor routine that implements the step.

        :id: The number of the step. These will be executed in ascending order.
        :number_of_days: The number of days after which this step will be done
        :step_name: The user facing name of this step (e.g. debtor becomes
            dubious)
        :processor: the key to the processor responsible for executing the step

    """

    VALID_OVERDUE_STATUSES = [Bills.ISSUED]

    __tablename__ = "overduesteps"

    id = db.Column(db.Integer, primary_key=True)
    number_of_days = db.Column(db.Integer, default=30, nullable=False)
    # number_of_days = mapped_column(db.Integer, default=30, nullable=False)
    step_name = db.Column(db.String(30), nullable=False)
    processor = db.Column(db.String(30), nullable=True)
    in_actions = db.relationship("OverdueActions", back_populates="step")

    def add(self):
        """ Add step to the table """

        db.session.add(self)

    @validates("id")
    def validate_id(self, key, for_id):
        """ Make sure at this moment the id is unique """

        try:
            self.get_by_id(for_id)
            raise DuplicateStepIdError( f"A step with {for_id} already exists")
        except NoStepWithIdError:
            pass
        return for_id

    @validates("step_name")
    def validate_step_name(self, key, name):
        """ A step name is required """

        if not name or name == "":
            raise StepMustHaveNameError("A step name is required")
        for step in self.__class__.get_days_list():
            if step.step_name == name and step.id != self.id:
                raise DuplicateStepNameError(
                    f"A step with {name} already exists")
        return name

    @staticmethod
    def get_by_id(step_id):
        """ Get the step with id step_id """

        other_step = db.session.query(OverdueSteps).filter_by(id=step_id).\
            first()
        if not other_step:
            raise NoStepWithIdError(
                f"The step with id {step_id} does not exist")
        return other_step

    @staticmethod
    def get_by_processor(processor):
        """ Get a step by name """

        return db.session.query(OverdueSteps).filter_by(processor=processor)\
            .first()

    @staticmethod
    def get_by_name(name):
        """ Get a step by name """

        return db.session.query(OverdueSteps).filter_by(step_name=name).first()

    @classmethod
    def get_days_list(cls):
        """ Get a list of days and steps ordered by number of days """

        return db.session.query(OverdueSteps).\
            options(load_only(cls.number_of_days, cls.id)).\
            order_by(cls.number_of_days.desc()).all()

    @classmethod
    def get_date_list(cls, from_date=date.today()):
        """ Get a list of dates and steps ordered by date """

        days_list = cls.get_days_list()
        result = []
        for each in days_list:
            overdue_entry = (from_date - timedelta(days=each.number_of_days),
                             each.step_name, each.processor)
            result.append(overdue_entry)
        return result


class OverdueActions(db.Model):
    """ This class models the history of overdue actions

    It jots down per bill what actions are taken and at what date

        :id: The sequence number of the action
        :bill_id: The bill on which this action is taken
        :step_id: The id of the overdue action step
        :date_action: The date the action was taken
        :bill: The bill this action is executed for
        :step: The action executed

    """
    __tablename__ = "overdueactions"

    id = db.Column(db.Integer, db.Sequence("ovdaction-sequence"),
                   primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bill.bill_id"),
                        nullable=False)
    step_id = db.Column(db.Integer, db.ForeignKey("overduesteps.id"),
                        nullable=False)
    date_action = db.Column(db.DateTime, nullable=False,
                            default=datetime.now)
    bill = db.relationship("Bills", backref="overdue_actions")
    step = db.relationship("OverdueSteps", uselist=False, back_populates="in_actions")

    def add(self):
        """ Add this action to the session """

        db.session.add(self)

    @classmethod
    def get_action_list(cls, bill):
        """ Return the executed actions for bill

        This returns only actions for an unpaid bill. The history for bills
        that are paid or dubious are uninteresting.
        """

        if bill.status != Bills.ISSUED:
            return []
        actions = [action for action in bill.overdue_actions]
        return actions

    @classmethod
    def last_action(cls, bill):
        """ Get the last action performed from the table """

        actions_bill = cls.query.filter_by(bill=bill).\
            order_by(cls.step_id.desc()).all()
        if actions_bill:
            return actions_bill[0]
        return None

    @classmethod
    def get_by_action(cls, action_type):
        """ Get all action of the type action_type """

        step = OverdueSteps.get_by_processor(action_type)
        return cls.query.filter_by(step_id=step.id).all()

    @classmethod
    def get_all_last_action(cls, processor):
        """ Get last actions with processor equal processor """

        action_alias = aliased(OverdueActions)
        step = OverdueSteps.get_by_processor(processor)
        sq = action_alias.query.filter(OverdueActions.bill_id==action_alias.bill_id,
                                       OverdueActions.id<action_alias.id)
        q = cls.query
        q= q.filter_by(step_id=step.id)
        q = q.filter(~sq.exists())
        return q.all()


class OverdueProcessor(object):
    """ Abstract ancestor for overdue processors

    A processor inheriting from this class will be usable in the overdue
    processes defined in this module. Any specific behaviours are of
    course the responsibility of the subclass.

    Each processor need a key which is equal to the OverdueSteps.processor.
    """

    all_processors = dict()

    def __init__(self):

        try:
            self.all_processors[self.processor_key]
            raise ProcessorAlreadyExistsError(
                "Create only one processor per type")
        except KeyError:
            pass
        self.all_processors[self.processor_key] = self
        temp_data = OverdueSteps.get_by_processor(self.processor_key)
        self.processor_data = [date.today() -
                               timedelta(days=temp_data.number_of_days),
                               temp_data.step_name,
                               temp_data.processor,
                               temp_data.number_of_days]

    def execute(self, bill=None, processor_data=None):
        """This method executes the code needed for this step.

        Processors only need to create a _execute method, doing the
        parts that are unique tot that step
        """

        if not processor_data:
            processor_data = self.processor_data
        if bill.status not in OverdueSteps.VALID_OVERDUE_STATUSES:
            raise BillStatusWrongError(f"Bill status {bill.status} incorrect")
        if bill.date_bill > processor_data[0]:
            return
        current_step = OverdueSteps.get_by_processor(self.processor_key)
        step_done = OverdueActions.query.filter_by(bill=bill).\
            filter_by(step=current_step).first()
        if step_done:
            return
        step_history = OverdueActions.query.filter_by(bill=bill).\
            order_by(OverdueActions.step_id.desc()).all()
        if step_history:
            first_day = (step_history[0].date_action +
                         timedelta(days=self.processor_data[3]) -
                         timedelta(days=step_history[0].step.number_of_days))
            if first_day > datetime.today():
                return
        if self._bill_amount_bagatelle(bill):
            return
        outstanding_bills = bill.get_outstanding_bills(bill.client)
        for each_bill in outstanding_bills:
            if each_bill != bill:
                self.add_step_to(each_bill)

        self._execute(bill=bill)
        result = self.add_step_to(bill)
        return result

    def _execute(self, bill=None):
        """ This method executes the private parts of the step.

        Every processor should implement this method.
        """

        raise NotImplementedError("A subclass should implement this method")

    def add_step_to(self, bill):
        """ This method creates the history record for executing the step

        The history record is for the bill passed in, every bill processed
        needs to be processed through this.
        """

        current_step = OverdueSteps.get_by_processor(self.processor_key)
        current_action = OverdueActions(bill=bill, step=current_step)
        current_action.add()
        return current_action

    def _bill_amount_bagatelle(self, bill):
        """ Run bagatelle process; return false if no bagatelle.

        If it is a bagatelle, try to pay the bill. If that works, no
        more processing required.
        """

        bagatelle_key = "BAGATELLE_" + bill.billing_ccy
        if not config.get(bagatelle_key):
            return False
        all_outstanding = bill.get_outstanding_bills(bill.client)
        total = sum([a_bill.total() if a_bill.billing_ccy == bill.billing_ccy
                     else 0 for a_bill in all_outstanding])
        if config[bagatelle_key] > total:
            if self._bagatelle_paid_bill(bill):
                # No more processing required
                return False
            return True
        return False

    def _bagatelle_paid_bill(self, bill):
        """ Try to pay the bill. """

        bill_amount = bill.billing_ccy, bill.total()
        payments = [payment for payment in bill.client.payments
                    if payment.assigned() < payment.payment_amount]
        total = 0
        for payment in payments:
            total += payment.payment_amount
        incoming_amount = IncomingAmounts(payment_ccy = bill_amount[0],
                                          payment_amount = bill_amount[1]
                                                            - total,
                                          debcred = "Cr",
                                          our_ref = "Bagatelle " 
                                          + str(bill.bill_id),
                                          client = bill.client)
        incoming_amount.add()
        if total:
            summary_amount = IncomingAmounts(payment_ccy = bill_amount[0],
                                          payment_amount = 0,
                                          debcred = "Cr",
                                          our_ref = "Bagatelle " 
                                          + str(bill.bill_id),
                                          client = bill.client)
            for payment in payments:
                if payment.payment_amount:
                    payment.assign_to_amount(summary_amount)
            incoming_amount.assign_to_amount(summary_amount)
            summary_amount.assign_to_bill(bill)
        else:
            incoming_amount.assign_to_bill(bill)
        return False

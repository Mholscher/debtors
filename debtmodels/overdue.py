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
from sqlalchemy.orm import validates, load_only
from debtmodels.debtbilling import Bills


class DuplicateStepIdError(ValueError):
    """ A step with the same id already exists """

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
    step_name = db.Column(db.String(30), nullable=False)
    processor = db.Column(db.String(30), nullable=True)

    def add(self):
        """ Add step to the table """

        db.session.add(self)

    @validates("id")
    def validate_id(self, key, for_id):
        """ Make sure at this moment the id is unique """

        self.get_by_id(for_id)
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
        if other_step:
            raise DuplicateStepIdError(
                f"The step with id {step_id} already exists")
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
            options(load_only("number_of_days", "id")).\
            order_by(cls.number_of_days.desc()).all()

    @classmethod
    def get_date_list(cls, from_date=date.today):
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
    step = db.relationship("OverdueSteps")

    def add(self):
        """ Add this action to the session """

        db.session.add(self)


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

    def execute(self, bill=None, processor_data=None):
        """ This method executes the private parts of the step and what each
        step needs to do.

        Processors only need to create a _execute method, doing the
        parts that are unique tot that step
        """

        if not processor_data:
            raise ValueError("No processor data available!")
        if bill.status not in OverdueSteps.VALID_OVERDUE_STATUSES:
            raise BillStatusWrongError(f"Bill status {bill.status} incorrect")
        if bill.date_bill > processor_data[0]:
            return
        self._execute(bill=bill)
        result = self.add_step_to(bill)
        return result

    def _execute(self, bill=None):
        """ This method executes the code needed for this step.

        Every processor should implement this method.
        """

        raise NotImplementedError("A subclass should implement this method")

    def add_step_to(self, bill):
        """ This method creates the history record for executing the step """

        current_step = OverdueSteps.get_by_processor(self.processor_key)
        current_action = OverdueActions(bill=bill, step=current_step)
        current_action.add()
        return current_action

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
a module holding the so-called processors, that implement the steps of
overdue processing.
"""

from debtors import db
from sqlalchemy.orm import validates
from debtmodels.debtbilling import Bills
from debtmodels.payments import IncomingAmounts


class DuplicateStepIdError(ValueError):
    """ A step with the same id already exists """

    pass


class StepMustHaveNameError(ValueError):
    """ A step must have a (non-empty) name """

    pass


class DuplicateStepNameError(ValueError):
    """ A step name must be unique """

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
        for step in self.get_by_name(name):
            if not step.id == self.id:
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
    def get_by_name(name):
        """ Get a steps by name """

        return db.session.query(OverdueSteps).filter_by(step_name=name).all()


class OverdueProcessor(object):

    all_processors = dict()

    def __init__(self):

        try:
            self.all_processors[self.processor_key]
            raise ProcessorAlreadyExistsError(
                "Create only one processor per type")
        except KeyError:
            pass
        self.all_processors[self.processor_key] = self

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

import unittest
from datetime import datetime, date
from dateutil import parser
from dateutil.tz import tzoffset
from debtors import app, db

from debtmodels.payments import IncomingAmounts, AmountQueued, AssignedAmounts
from debtmodels.debtbilling import Bills, BillLines
from debtmodels.overdue import OverdueSteps, OverdueProcessor
from debtviews.payments import (PaymentAccounting, AssignmentAccounting,
                                PaymentReversalAccounting,
                                AssignmentReversalAccounting)
from debttests.helpers import (delete_test_clients, add_addresses,
    create_clients, spread_created_at, create_bills, add_lines_to_bills,
    delete_test_bills, add_debtor_preferences, delete_amountq,
    delete_test_prefs)

class TestCreateOverdueRule(unittest.TestCase):

    def setUp(self):

        self.st01 = OverdueSteps(id=100, number_of_days=30, 
                                step_name="Baby step",
                                processor="babyproc")
        self.st01.add()
        db.session.flush()

    def tearDown(self):

        db.session.rollback()


    def test_create_simple_rule(self):
        """ Create a step in the database """

        st02 = db.session.query(OverdueSteps).first()
        self.assertEqual(st02.number_of_days, 30, 
                        "Wrong number of days in step")

    def test_duplicate_not_allowed(self):
        """ Two steps cannot have the same id """

        with self.assertRaises(ValueError):
            st03 = OverdueSteps(id=100, number_of_days=70, 
                                step_name="Baby leap")
            st03.add()
            db.session.flush()

    def test_error_on_empty_step_name(self):
        """ A step name cannot be empty """

        with self.assertRaises(ValueError):
            st04 = OverdueSteps(id=200, number_of_days=120, 
                                step_name=None)
            st04.add()
            db.session.flush()
        with self.assertRaises(ValueError):
            st05 = OverdueSteps(id=200, number_of_days=120, 
                                step_name="")
            st05.add()
            db.session.flush()

    def test_step_name_duplicate_fails(self):
        """ A step name must be unique """

        with self.assertRaises(ValueError):
            st06 = OverdueSteps(id=150, number_of_days=120, 
                                step_name="Baby step")
            st06.add()
            db.session.flush()

    def test_cannot_change_name_to_existing(self):
        """ We cannot change the name of a step to an existing name """

        st07 = OverdueSteps(id=150, number_of_days=120, 
                            step_name="Lesser step")
        st07.add()
        db.session.flush()

        with self.assertRaises(ValueError):
            st07.step_name="Baby step"


class TestOverdueStep_functions(unittest.TestCase):

    def setUp(self):

        self.st08 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="Baby step",
                                processor="babyproc")
        self.st08.add()
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_overdue_days_list(self):
        """ Get overdue dates and id of step """

        steps = OverdueSteps.get_days_list()
        self.assertEqual(steps[0].id, 100, "First step not correct in list")

    def test_days_list(self):
        """ Order of days list is correct """

        st09 =OverdueSteps(id=50, number_of_days=35,
                           step_name="Second",
                           processor="second")
        st09.add()
        db.session.flush()
        steps = OverdueSteps.get_days_list()
        self.assertEqual(steps[1].id, 100, "First step not correct in list")
        self.assertEqual(steps[0].id, 50, "Second step not correct in list")
        self.assertEqual(steps[0].processor, "second", "processor not there")

    def test_date_list_from_given_date(self):
        """ Create a date list for checking where we are in overdue """

        st10 =OverdueSteps(id=50, number_of_days=35,
                           step_name="Second",
                           processor="second")
        st10.add()
        db.session.flush()
        steps = OverdueSteps.get_date_list(from_date=date(2021, 10, 2))
        self.assertEqual(steps[1][0], date(2021, 10, 27),
                         "Date not correct")
        self.assertEqual(steps[0][0], date(2021, 11, 6),
                         "Date not correct")
        self.assertEqual(steps[0][2], "second", "processor not correct")


if __name__ == '__main__' :
    unittest.main()

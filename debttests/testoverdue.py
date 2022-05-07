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
from debtmodels.overdue import (OverdueSteps, OverdueProcessor, OverdueActions,
                                BillStatusWrongError)
from debtviews.payments import (PaymentAccounting, AssignmentAccounting,
                                PaymentReversalAccounting,
                                AssignmentReversalAccounting)
from debttests.helpers import (create_clients, add_addresses,
                               create_bills, add_lines_to_bills,
                               delete_test_bills, delete_test_prefs,
                               delete_test_clients, create_payments_for_overdue,
                               delete_test_payments, delete_overdue_actions)
from debtviews.overdue_processors import (FirstLetterProcessor,
                                          SecondLetterProcessor)

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


class TestOverdueStepFunctions(unittest.TestCase):

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
        self.assertEqual(steps[1][0], date(2021, 9, 7),
                         "Date not correct")
        self.assertEqual(steps[0][0], date(2021, 8, 28),
                         "Date not correct")
        self.assertEqual(steps[0][2], "second", "processor not correct")


class TestOverdueActions(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st11 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st11.add()
        self.st12 = OverdueSteps(id=120, number_of_days=25, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st12.add()
        db.session.flush()
        self.flp06 = FirstLetterProcessor()
        self.slp09 = SecondLetterProcessor()

    def tearDown(self):

        db.session.rollback()
        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.commit()

    def test_overdue_step_create_action(self):
        """ Executing an overdue step creates history record """

        dates_list = OverdueSteps.get_date_list()
        for proc_data in dates_list:
            if proc_data[2] == self.flp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp06, "No key {self.flp06.processor_key} found")
        self.flp06.execute(bill=self.bll4, processor_data=current_processor_data)
        oa01 = db.session.query(OverdueActions).first()
        self.assertTrue(oa01, "No action created")

    def test_no_action_until_date(self):
        """ If the date is not yet reached, take no action  """

        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 3, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.flp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp06, "No key {self.flp06.processor_key} found")
        self.flp06.execute(bill=self.bll4, processor_data=current_processor_data)
        oa01 = db.session.query(OverdueActions).first()
        self.assertFalse(oa01, "Action created early")

    def test_empty_dates_list_fails(self):
        """ No processors defined fails """

        current_processor_data = tuple()
        with self.assertRaises(ValueError):
            self.flp06.execute(bill=self.bll4,
                               processor_data=current_processor_data)

    def test_only_overdue_for_issued_bill(self):
        """ Only for issued bills overdue action is taken """

        dates_list = OverdueSteps.get_date_list()
        for proc_data in dates_list:
            if proc_data[2] == self.flp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp06, "No key {self.flp06.processor_key} found")
        with self.assertRaises(BillStatusWrongError):
            self.flp06.execute(bill=self.bll2,
                               processor_data=current_processor_data)

    def test_overdue_step_executed_once(self):
        """ Any overdue step is only executed once for a bill """

        dates_list = OverdueSteps.get_date_list()
        for proc_data in dates_list:
            if proc_data[2] == self.flp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp06, "No key {self.flp06.processor_key} found")
        self.flp06.execute(bill=self.bll4,
                           processor_data=current_processor_data)
        self.flp06.execute(bill=self.bll4,
                           processor_data=current_processor_data)
        first_steps = db.session.query(OverdueActions).\
            filter_by(bill_id=self.bll4.bill_id).\
            filter_by(step_id=100).\
            all()
        self.assertEqual(len(first_steps), 1, "First step not executed once")

    def test_retrieve_last_overdue_action(self):
        """ Retrieve the last executed overdue action """

        self.assertFalse(OverdueActions.last_action(self.bll4), 
                         "A step was returned where no action taken")
        dates_list = OverdueSteps.get_date_list()
        for proc_data in dates_list:
            if proc_data[2] == self.flp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp06, "No key {self.flp06.processor_key} found")
        self.flp06.execute(bill=self.bll4,
                           processor_data=current_processor_data)
        step_flp = OverdueSteps.query.filter_by(id=100).\
            first()
        self.assertTrue(step_flp, "No first letter from db")
        self.assertEqual(OverdueActions.last_action(self.bll4).step_id,
                         step_flp.id, "Last action not First Letter")
        for proc_data in dates_list:
            if proc_data[2] == self.slp09.processor_key:
                current_processor_data = proc_data
                break
        self.slp09.execute(bill=self.bll4,
                           processor_data=current_processor_data)
        step_slp = OverdueSteps.query.filter_by(id=120).\
            first()
        self.assertEqual(OverdueActions.last_action(self.bll4).step_id,
                         step_slp.id, "Last action not Second Letter")

    def test_no_action_returns_none(self):
        """ Asking for last action on no action bill returns None """

        self.assertFalse(OverdueActions.last_action(self.bll4),
                         "An action is returned")

    def test_action_on_other_bill(self):
        """ Overdue action will create action for other bill """

        self.bll24 = Bills(date_sale=date(year=2020, month=1, day=8),
                              date_bill=date(year=2020, month=1, day=9),
                              billing_ccy='JPY',
                              status='issued')
        self.clt1.bills.append(self.bll24)
        self.bills.append(self.bll24)
        bill_line = BillLines(short_desc='sh34',
                        long_desc='A pencil sharpener',
                        number_of=2,
                        measured_in='Pcs',
                        unit_price=254)
        self.bll24.lines.append(bill_line)
        db.session.flush()
        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 4, 8))
        for proc_data in dates_list:
            if proc_data[2] == self.flp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp06, "No key {self.flp06.processor_key} found")
        self.flp06.execute(bill=self.bll24,
                           processor_data=current_processor_data)
        self.assertEqual(OverdueActions.last_action(self.bll8).step_id, 100,
                    "Last action not first letter for other bill")


class TestOverdueActionsFunctions(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st13 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st13.add()
        self.st14 = OverdueSteps(id=120, number_of_days=35, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st14.add()
        self.flp07 = FirstLetterProcessor()
        self.slp10 = SecondLetterProcessor()
        dates_list = OverdueSteps.get_date_list()
        for proc_data in dates_list:
            if proc_data[2] == self.flp07.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp07, "No key {self.flp07.processor_key} found")
        self.flp07.execute(bill=self.bll4,
                           processor_data=current_processor_data)

        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_overdue_actions(self)
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.commit()

    def test_return_action_list_for_bill(self):
        """ A action list is returned for a bill """

        actions = OverdueActions.get_action_list(self.bll4)
        self.assertEqual(len(actions), 1, "Too little/many actions in list")
        self.assertEqual(actions[0].step_id, 100, "Wrong step returned")

    def test_no_action_is_empty_list(self):
        """ No action performed results in empty list """

        actions = OverdueActions.get_action_list(self.bll8)
        self.assertEqual(len(actions), 0, "List not empty")

    def test_no_list_for_bill_wrong_status(self):
        """ Only actions for bills in debt should be reported """

        # Sneak in an unreportable action
        unreportable = OverdueActions(date_action = date(year=2019, month=12,
                                                         day=8))
        unreportable.bill = self.bll2
        unreportable.step = self.st13
        db.session.flush()
        actions = OverdueActions.get_action_list(self.bll2)
        self.assertFalse(actions, "There are actions reported")


if __name__ == '__main__' :
    unittest.main()

#    Copyright 2022 Menno Hölscher
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

import unittest
from datetime import datetime, date, timedelta
from debttests.helpers import (create_clients, create_bills, add_addresses,
                               add_lines_to_bills,delete_amountq, 
                               delete_test_bills, delete_test_clients,
                               create_payments_for_overdue,
                               create_overdue_actions_for_positions,
                               create_overdue_steps, delete_overdue_steps,
                               delete_test_payments, delete_overdue_actions,
                               create_bills_for_positions)
from debtors import app, db, config
from debtmodels.overdue import (OverdueProcessor, OverdueSteps,
                                OverdueActions)
from debtviews.overdue_processors import (FirstLetterProcessor,
                                          SecondLetterProcessor,
                                          DebtTransferProcessor,
                                          DubiousDebtorProcessor)
from debtviews.positions import (DebtByAge, DebtAgeReport, DebtByStatus,
                                 DebtStatusReport)

class TestDebtPosition(unittest.TestCase):

    def setUp(self):

        self.ctx = app.app_context()
        self.ctx.push()
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        create_bills_for_positions(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        create_overdue_steps(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_amountq(self)
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_clients(self)
        OverdueProcessor.all_processors.clear()
        delete_overdue_steps(self)
        db.session.commit()
        self.ctx.pop()

    def test_position_for_recent(self):
        """ The position is reported for recent debt """

        debt_by_age = DebtByAge()
        self.assertEqual(debt_by_age.recent_debt()[self.bll10.billing_ccy],
                         self.bll10.total() + self.bll15.total(),
                         "Recent debt incorrect")

    def test_position_for_older(self):
        """ The position is reported for older debt """

        debt_by_age = DebtByAge()
        self.assertEqual(debt_by_age.older_debt()[self.bll11.billing_ccy],
                         self.bll11.total(), "Older debt incorrect")

    def test_position_for_worrying(self):
        """ The position is reported for very old debt """

        debt_by_age = DebtByAge()
        self.assertEqual(debt_by_age.worrying_debt()[self.bll12.billing_ccy],
                         self.bll12.total(), "Worrying debt incorrect")

    def test_separate_line_per_ccy(self):
        """ The position is split by currency """

        debt_by_age = DebtByAge()
        recent_debt = debt_by_age.recent_debt()
        self.assertEqual(recent_debt[self.bll10.billing_ccy],
                         self.bll10.total() + self.bll15.total(),
                         "Currency debt incorrect")
        self.assertIn(self.bll13.billing_ccy, recent_debt,
                      "No other currency in debt")

    def test_only_issued_in_position(self):
        """ Only issued bills should be in position """

        debt_by_age = DebtByAge()
        recent_debt = debt_by_age.recent_debt()
        self.assertEqual(recent_debt[self.bll10.billing_ccy],
                         self.bll10.total() + self.bll15.total(),
                         "Currency debt incorrect")

class TestPhysicalReport(unittest.TestCase):

    def setUp(self):

        self.ctx = app.app_context()
        self.ctx.push()
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        create_bills_for_positions(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        create_overdue_steps(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_amountq(self)
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_clients(self)
        OverdueProcessor.all_processors.clear()
        delete_overdue_steps(self)
        db.session.commit()
        self.ctx.pop()

    def test_create_report(self):
        """ A report is created """

        debt_age_report = DebtAgeReport()
        debt_age_report.write_report()
        #print(debt_age_report.text)
        self.assertTrue(debt_age_report.text, "No text produced")

    def test_date_on_report(self):
        """ In the report the currrent date is in the header """

        debt_age_report = DebtAgeReport()
        debt_age_report.write_report()
        #print(debt_age_report.text)
        self.assertIn(date.today().strftime(config["DATE_FORMAT"]),
                      debt_age_report.text,
                      "Date today not in text")

    def test_outfile(self):
        """ Can produce an output file """

        debt_age_report = DebtAgeReport()
        debt_age_report.write_file()
        self.assertTrue(debt_age_report.text, "Create failed")
 

class TestDebtByOverdueStatus(unittest.TestCase):

    def setUp(self):

        self.ctx = app.app_context()
        self.ctx.push()
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        create_bills_for_positions(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        create_overdue_steps(self)
        create_overdue_actions_for_positions(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_amountq(self)
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_clients(self)
        delete_overdue_actions(self)
        OverdueProcessor.all_processors.clear()
        delete_overdue_steps(self)
        db.session.commit()
        self.ctx.pop()

    def test_get_overdue_for_status(self):
        """ Get all bills with a known overdue status """

        all_transfers = OverdueActions.get_by_action("transfer")
        all_transferred_bills = [transfer.bill_id for transfer in all_transfers]
        self.assertIn(self.bll12.bill_id,all_transferred_bills)
        self.assertIn(self.bll11.bill_id,all_transferred_bills)

    def test_create_debt_by_status(self):
        """ Create a debt by status dict """

        debt_by_status = DebtByStatus()
        transferred_debt_EUR = self.bll11.total() + self.bll12.total()
        self.assertEqual(debt_by_status.transferred()["EUR"],
                         transferred_debt_EUR,
                         "Amount transferred Euro incorrect")

    def test_debt_by_status_2_currencies(self):
        """ Two currency amounts are returned correctly """

        action_jpy = OverdueActions(date_action=date(2020, 11, 3))
        action_jpy.step = self.st17
        action_jpy.bill = self.bll13
        action_jpy.add()
        db.session.flush()
        debt_by_status = DebtByStatus()
        transferred_debt_EUR = self.bll11.total() + self.bll12.total()
        self.assertEqual(debt_by_status.transferred()["EUR"],
                         transferred_debt_EUR,
                         "Amount transferred Euro incorrect")
        transferred_debt_JPY = self.bll13.total()
        self.assertEqual(debt_by_status.transferred()["JPY"],
                         transferred_debt_JPY,
                         "Amount transferred Yen incorrect")

    def test_get_overdue_for_secondletter(self):
        """ Get bills having had second letter overdue """

        debt_by_status = DebtByStatus()
        second_debt_EUR = self.bll10.total()
        self.assertEqual(debt_by_status.second_letter()["EUR"],
                         second_debt_EUR,
                         "Amount transferred Euro incorrect")

    def test_only_latest_reported(self):
        """ Only the latest action is reported """

        debt_by_status = DebtByStatus()
        two_days_before = date.today() - timedelta(days=2)
        transfer = OverdueActions(date_action=two_days_before)
        transfer.bill = self.bll10
        transfer.step = self.st17
        transfer.add()
        db.session.flush()
        self.assertNotIn("EUR", debt_by_status.second_letter(),
                        "Transferred bill in second letter")
        transferred_debt_EUR = (self.bll11.total() + self.bll12.total()
                                + self.bll10.total())
        self.assertEqual(debt_by_status.transferred()["EUR"],
                         transferred_debt_EUR,
                         "Transferred bill not in total")

class TestOtherActionsAndTotal(unittest.TestCase):

    def setUp(self):

        self.ctx = app.app_context()
        self.ctx.push()
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        create_bills_for_positions(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        create_overdue_steps(self)
        create_overdue_actions_for_positions(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_amountq(self)
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_clients(self)
        delete_overdue_actions(self)
        OverdueProcessor.all_processors.clear()
        delete_overdue_steps(self)
        db.session.commit()
        self.ctx.pop()

    def test_first_letter(self):
        """ Get bills having had overdue first letter """

        debt_by_status = DebtByStatus()
        first_letter_debt_EUR = self.bll15.total()
        self.assertEqual(debt_by_status.first_letter()["EUR"],
                         first_letter_debt_EUR,
                         "Amount first letter Euro incorrect")

    def test_report_for_all_processors(self):
        """ Make sure report shows all actions """

        debt_by_status = DebtByStatus()
        debt = debt_by_status.first_letter()
        self.assertTrue(debt["EUR"], "No debt for first letter")
        debt = debt_by_status.second_letter()
        self.assertTrue(debt["EUR"], "No debt for second letter")
        debt = debt_by_status.transferred()
        self.assertTrue(debt["EUR"], "No debt for transfers")


class TestPhysicalDebtStatusReport(unittest.TestCase):

    def setUp(self):

        self.ctx = app.app_context()
        self.ctx.push()
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        create_bills_for_positions(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        create_overdue_steps(self)
        create_overdue_actions_for_positions(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_amountq(self)
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_clients(self)
        delete_overdue_actions(self)
        OverdueProcessor.all_processors.clear()
        delete_overdue_steps(self)
        db.session.commit()
        self.ctx.pop()

    def test_create_physical_report(self):
        """ We can create the physical report """

        debt_by_status = DebtStatusReport()
        debt_by_status.write_report()
        #print(debt_by_status.text)
        self.assertTrue(debt_by_status.text, "No text in report")
        self.assertIn( date.today().strftime(config["DATE_FORMAT"]),
                      debt_by_status.text,
                      "Date today not in text")

    def test_outfile(self):
        """ Can produce an output file """

        debt_status_report = DebtStatusReport()
        debt_status_report.write_file()
        self.assertTrue(debt_status_report.text, "Create failed")

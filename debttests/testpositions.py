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
from datetime import datetime, date
from debttests.helpers import (create_clients, create_bills, add_addresses,
                               add_lines_to_bills,delete_amountq, 
                               delete_test_bills, delete_test_clients,
                               create_payments_for_overdue,
                               create_overdue_steps, delete_overdue_steps,
                               delete_test_payments,
                               create_bills_for_positions)
from debtors import app, db, config
from debtmodels.overdue import OverdueProcessor
from debtviews.positions import DebtByAge, DebtAgeReport

class TestDebtPosition(unittest.TestCase):

    def setUp(self):

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

    def test_position_for_recent(self):
        """ The position is reported for recent debt """

        debt_by_age = DebtByAge()
        self.assertEqual(debt_by_age.recent_debt()[self.bll10.billing_ccy],
                         self.bll10.total(), "Recent debt incorrect")

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
                         self.bll10.total(), "Currency debt incorrect")
        self.assertIn(self.bll13.billing_ccy, recent_debt,
                      "No other currency in debt")

    def test_only_issued_in_position(self):
        """ Only issued bills should be in position """

        debt_by_age = DebtByAge()
        recent_debt = debt_by_age.recent_debt()
        self.assertEqual(recent_debt[self.bll10.billing_ccy],
                         self.bll10.total(), "Currency debt incorrect")

class TestPhysicalReport(unittest.TestCase):

    def setUp(self):

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
 

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

import os, os.path
import unittest
from debtors import db
from debttests.helpers import (create_clients, add_addresses,
                               create_bills, add_lines_to_bills,
                               delete_test_bills, delete_test_prefs,
                               delete_test_clients, create_payments_for_overdue,
                               delete_test_payments)
from debtviews.monetary import edited_amount
from debtmodels.overdue import OverdueProcessor, ProcessorAlreadyExistsError
from debtmodels.overdue_processors import FirstLetterProcessor
from debtviews.physicaloverdue import PaperLetter, OverdueDictView


class TestCreateOverdueDict(unittest.TestCase):

    def setUp(self):


        create_clients(self)
        add_addresses(self)
        create_bills(self)
        create_payments_for_overdue(self)
        add_lines_to_bills(self)
        db.session.flush()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_payments(self)
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.commit()

    def test_overdue_has_bill_data(self):
        """ An overdue dictionary should contain data for bill  """

        view = OverdueDictView(bill_id=self.bll4.bill_id)
        self.assertIn("bill", view, 'Bill not in overdue view')

    def test_correct_data_in_bill(self):
        """ Some must have items are in the dictionary """

        view = OverdueDictView(bill_id=self.bll4.bill_id)
        self.assertIn("bill_id", view["bill"], 'Bill id not in overdue view')
        self.assertIn("billing_ccy", view["bill"], 'Currency not in overdue view')
        self.assertEqual("Yen", view["bill"]["billing_ccy"],
                         'Currency incorrect/missing in overdue view')
        self.assertEqual("1.880", view["bill"]["total"],
                         'Bill total incorrect in overdue view')

    def test_overdue_has_client_data(self):
        """ An overdue dictionary should contain client data """

        view = OverdueDictView(bill_id=self.bll4.bill_id)
        self.assertIn("client", view, 'Client not in overdue view')
        self.assertIn("surname", view["client"], "Client surname not in view")
        self.assertIn("town_or_village", view["client"],
                      "Client town not in view")

    def test_overdue_has_payment_list(self):
        """ Overdue data has a list of open payments received """

        view = OverdueDictView(bill_id=self.bll4.bill_id)
        self.assertIn("payments", view, "No payments in overdue view")

    def test_payment_in_payment_list(self):
        """ The payment list has a payment for the client """

        view = OverdueDictView(bill_id=self.bll4.bill_id)
        self.assertEqual(edited_amount(self.ia110.payment_amount),
                         view["payments"][0]["payment_amount"],
                         "Payment not in list")

    def test_currency_converted(self):
        """ The currency must be converted to non-ISO form """

        view = OverdueDictView(bill_id=self.bll4.bill_id)
        self.assertEqual("Yen",
                         view["payments"][0]["payment_ccy"],
                         "Payment currency not correct")

    def test_list_other_bills(self):
        """ There must be a list of other bill than the one triggering """

        view = OverdueDictView(bill_id=self.bll4.bill_id)
        self.assertIn("morebills", view, "No other bills in overdue view")

    def test_other_bill_data(self):
        """ Bills in list have valid data  """

        view = OverdueDictView(bill_id=self.bll4.bill_id)
        other_bills = view["morebills"]
        bill7 = [bill for bill in other_bills
                 if bill["bill_id"] == self.bll7.bill_id][0]
        self.assertEqual("Yen", bill7["billing_ccy"], "Currency not correct")
        self.assertEqual(edited_amount(self.bll7.total(),
                                       currency=self.bll7.billing_ccy),
                                       bill7["total"],
                                       "Amount not correct")
        self.assertEqual(self.bll7.date_sale.strftime("%d-%m-%Y"),
                         bill7["date_sale"], "Due date not correct")


class TestFirstLetterContent(unittest.TestCase):

    def setUp(self):

        self.flp05 = FirstLetterProcessor()
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        db.session.flush()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.commit()

    def test_instantiated_template_in_output(self):
        """ The template is in the output """

        bill = self.bll4
        template = "firstletter.rtf"
        template_text = PaperLetter(template_name=template, bill=bill)
        self.assertIn("Testcompany", template_text.text, "Testcompany not in text")

    def test_data_in_template(self):
        """ The data passed in from the datbase is in the text """

        bill = self.bll4
        template = "firstletter.rtf"
        template_text = PaperLetter(template_name=template, bill=bill)
        self.assertIn(str(self.bll4.bill_id), template_text.text, "Bill id  not in text")


if __name__ == '__main__' :
    unittest.main()

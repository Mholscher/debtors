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
from os.path import exists
from datetime import date, timedelta
from debtors import db
from debttests.helpers import (create_clients, add_addresses,
                               create_bills, add_lines_to_bills,
                               delete_test_bills, delete_test_prefs,
                               delete_test_clients, create_payments_for_overdue,
                               delete_test_payments, delete_overdue_steps)
from debtviews.monetary import edited_amount
from debtmodels.overdue import (OverdueProcessor, ProcessorAlreadyExistsError,
                                OverdueSteps, OverdueActions)
from debtviews.overdue_processors import (FirstLetterProcessor, 
                                           SecondLetterProcessor,
                                           DebtTransferProcessor,
                                           DubiousDebtorProcessor,
                                           DubiousDebtorAccounting)
from debtmodels.debtbilling import Bills, BillLines, DebtorSignal
from debtviews.physicaloverdue import PaperLetter, OverdueDictView


class TestCreateOverdueDict(unittest.TestCase):

    def setUp(self):


        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        db.session.flush()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_payments(self)
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
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
        self.assertEqual(edited_amount(self.ia110.payment_amount,
                                       currency=self.ia110.payment_ccy),
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
        #print(self.bll7.date_bill.strftime("%d %B %Y"), bill7)
        self.assertEqual(self.bll7.date_bill.strftime("%d %B %Y"), 
                         bill7["date_bill"], "Bill date not correct")


class TestCreateFirstLetterProcessor(unittest.TestCase):

    def setUp(self):

        self.st21 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st21.add()
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_overdue_steps(self)
        OverdueProcessor.all_processors.clear()

    def test_create_processor(self):
        """ Create a firstletter processor """

        flp01 = FirstLetterProcessor()
        self.assertIn(flp01.processor_key, flp01.all_processors,
                      "Processor not added to all_processors")

    def test_create_second_processor_fails(self):
        """ Can not create a duplicate processor """

        flp02 = FirstLetterProcessor()
        with self.assertRaises(ProcessorAlreadyExistsError):
            flp03 = FirstLetterProcessor()


class TestFirstLetterProcess(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        self.st11 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st11.add()
        db.session.flush()
        self.flp04 = FirstLetterProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_processor_has_auxiliary_data(self):
        """ A processor must have its data  """

        self.assertEqual(self.flp04.processor_data[2], "firstletter",
                         "No processor name in data")
        self.assertEqual(self.flp04.processor_data[0], date.today() - timedelta(days=25),
                         "No number of days in data")
        self.assertEqual(self.flp04.processor_data[1], "First Letter",
                         "Name not correct in data")

    def test_execute(self):
        """ Execute produces a first letter """

        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 3, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.flp04.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp04, "No key {flp04.processor_key} found")
        self.flp04.execute(self.bll4, processor_data=current_processor_data)
        self.assertTrue(exists("output/fl" + str(self.bll4.bill_id)),
                               "First letter file does not exist")

    def test_mail_if_preference_mail(self):
        """ If letter preference of client is mail, also mail is made """

        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 3, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.flp04.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp04, "No key {flp04.processor_key} found")
        self.flp04.execute(self.bll8, processor_data=current_processor_data)
        self.assertTrue(exists("output/mailfom" + str(self.bll8.bill_id)),
                               "First letter mail does not exist")


class TestFirstLetterContent(unittest.TestCase):

    def setUp(self):

        self.st22 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st22.add()
        db.session.flush()
        self.flp05 = FirstLetterProcessor()
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        db.session.flush()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
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
        self.assertIn("Yen", template_text.text,
                      "Bill currency  not in text")

    def test_other_bill_other_currency(self):
        """ Bill in a different currency shows currency """

        bill = self.bll4
        template = "firstletter.rtf"
        template_text = PaperLetter(template_name=template, bill=bill)
        self.assertIn("Euro", template_text.text,
                      "Differing bill currency  not in text")

    def test_payment_on_doc(self):
        """ An unassigned payment from the bill's client is in the letter """

        bill = self.bll4
        template = "firstletter.rtf"
        template_text = PaperLetter(template_name=template, bill=bill)
        self.assertIn("28", template_text.text,
                      "Payment amount not in text")
        self.assertNotIn(",28", template_text.text,
                      "Payment amount wrongly formatted")

    def test_bill_status_limited_to_issued(self):
        """ Only issued bills appear on a first letter """

        bill = self.bll4
        template = "firstletter.rtf"
        template_text = PaperLetter(template_name=template, bill=bill)
        self.assertNotIn(str(self.bll5.bill_id), template_text.text,
                         "Paid bill in text")

    def test_assigned_payment_not_in_letter(self):
        """ An assigned amount should not be in the letter  """

        self.ia111.assign_to_amount(self.ia112)
        self.assertTrue(self.ia111.fully_assigned, "Open amount on payment")
        bill = self.bll8
        template = "firstletter.rtf"
        template_text = PaperLetter(template_name=template, bill=bill)
        self.assertNotIn(str(self.ia111.id), template_text.text,
                         "Assigned amount in text")


class TestFirstLetterMailContent(unittest.TestCase):

    def setUp(self):

        self.st23 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st12 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st12.add()
        db.session.flush()
        self.flp06 = FirstLetterProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_bill_id_in_mail(self):
        """ The id of a bill needs to be present in the mail """

        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 3, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.flp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp06, "No key {flp06.processor_key} found")
        self.flp06.execute(self.bll8, processor_data=current_processor_data)
        with open("output/mailfom" + str(self.bll8.bill_id), "rt") as e_mail:
            mail_text = e_mail.read()
        self.assertIn(str(self.bll8.bill_id), mail_text,
                      "Open bill not in text")
        self.assertNotIn(str(self.bll1.bill_id), mail_text,
                         "Paid bill in text")

    def test_payment_in_mail(self):
        """ A first letter mail must contain payments """

        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 3, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.flp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp06, "No key {flp06.processor_key} found")
        self.flp06.execute(self.bll8, processor_data=current_processor_data)
        with open("output/mailfom" + str(self.bll8.bill_id), "rt") as e_mail:
            mail_text = e_mail.read()
        self.assertIn(str(self.ia111.id), mail_text,
                      "Payment not found in mail")

    def test_assigned_payment_not_in_mail(self):
        """ An assigned payment should not be in mail """

        self.ia111.assign_to_amount(self.ia112)
        self.assertTrue(self.ia111.fully_assigned, "Open amount on payment")
        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 3, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.flp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.flp06, "No key {flp06.processor_key} found")
        self.flp06.execute(self.bll8, processor_data=current_processor_data)
        with open("output/mailfom" + str(self.bll8.bill_id), "rt") as e_mail:
            mail_text = e_mail.read()
        self.assertNotIn(str(self.ia111.id), mail_text,
                      "Assigned payment found in mail")


class TestCreateSecondLetterProcessor(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        self.st13 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st13.add()
        db.session.flush()
        self.flp07 = FirstLetterProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_create_second_letter_processor_step(self):
        """ Create a second letter processor and add to all processors """

        self.st14 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st14.add()
        db.session.flush()
        slp01 = SecondLetterProcessor()
        self.assertIn(slp01, OverdueProcessor.all_processors.values())
        steps = db.session.query(OverdueSteps).all()
        self.assertIn(self.st13, steps, "First letter processor missing")
        self.assertIn(self.st14, steps, "Second letter processor missing")
        second_letter_step = [step for step in steps if step.id == 110][0]
        self.assertTrue(second_letter_step, 
                        "Invalid id on second letter step")

    def test_processor_order_on_list(self):
        """ The list holds processors in date order, reversed """

        self.st15 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st15.add()
        slp02 = SecondLetterProcessor()
        db.session.flush()
        steps = OverdueSteps.get_days_list()
        self.assertEqual(steps[0], self.st15, "First step not second letter")
        self.assertEqual(steps[1], self.st13, "Second step not first letter")


class TestSecondLetterProcess(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st16 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st16.add()
        self.st17 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st17.add()
        self.st27 = OverdueSteps(id=120, number_of_days=60, 
                                step_name="Debt transfer",
                                processor="transfer")
        self.st27.add()
        db.session.flush()
        self.flp08 = FirstLetterProcessor()
        self.slp03 = SecondLetterProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_execute(self):
        """ Execute produces a second letter """

        self.bll10 = Bills(date_sale=date(year=2020, month=1, day=8),
                              date_bill=date(year=2020, month=1, day=8),
                              billing_ccy='JPY',
                              status='issued')
        self.clt5.bills.append(self.bll10)
        self.bills.append(self.bll10)
        db.session.flush()
        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 3, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.slp03.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.slp03, "No key {slp03.processor_key} found")
        self.slp03.execute(self.bll10, processor_data=current_processor_data)
        self.assertTrue(exists("output/sl" + str(self.bll10.bill_id)),
                               "Second letter file does not exist")


class TestSecondLetterContent(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st18 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st18.add()
        self.st19 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st19.add()
        self.st20 = OverdueSteps(id=120, number_of_days=60, 
                                step_name="Debt transfer",
                                processor="transfer")
        self.st20.add()
        self.bll10 = Bills(date_sale=date(year=2020, month=1, day=8),
                              date_bill=date(year=2020, month=1, day=8),
                              billing_ccy='JPY',
                              status='issued')
        self.clt5.bills.append(self.bll10)
        self.bills.append(self.bll10)
        db.session.flush()
        self.flp09 = FirstLetterProcessor()
        self.slp04 = SecondLetterProcessor()
        self.dtp02 = DebtTransferProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_transfer_date_in_letter(self):
        """ The second overdue letter contains the transfer date """

        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 5, 14))
        for proc_data in dates_list:
            if proc_data[2] == self.slp04.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.slp04, "No key {slp04.processor_key} found")
        self.slp04.execute(self.bll10, processor_data=current_processor_data)
        self.assertTrue(exists("output/sl" + str(self.bll10.bill_id)),
                               "Second letter file does not exist")
        with open("output/sl" + str(self.bll10.bill_id)) as slf:
            letter_text = slf.read()
        transfer_date = \
            (self.bll10.date_bill + timedelta(days=60)).strftime("%d %B %Y")
        self.assertIn(transfer_date, letter_text,
                      "No transfer date in second letter")

    def test_other_data_in_letter(self):
        """ Expected data about bills, payments in letter """

        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 5, 14))
        for proc_data in dates_list:
            if proc_data[2] == self.slp04.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.slp04, "No key {slp04.processor_key} found")
        self.slp04.execute(self.bll10, processor_data=current_processor_data)
        with open("output/sl" + str(self.bll10.bill_id)) as slf:
            letter_text = slf.read()
        self.assertIn(str(self.bll4.bill_id), letter_text,
                      "Not all debt in letter")
        self.assertIn(str(self.bll6.bill_id), letter_text,
                      "Not all debt in letter")
        self.assertNotIn(str(self.bll5.bill_id), letter_text,
                         "Bill not in debt in letter")
        self.assertIn(str(self.ia112.id), letter_text,
                      "Open payment not in letter")


class TestSecondMailContent(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st28 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st28.add()
        self.st29 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st29.add()
        self.st30 = OverdueSteps(id=120, number_of_days=60, 
                                step_name="Debt transfer",
                                processor="transfer")
        self.st30.add()
        self.bll11 = Bills(date_sale=date(year=2020, month=1, day=8),
                              date_bill=date(year=2020, month=1, day=8),
                              billing_ccy='JPY',
                              status='issued')
        self.clt1.bills.append(self.bll11)
        self.bills.append(self.bll11)
        bill_line = BillLines(short_desc='reed',
                        long_desc='A hobo reed for you',
                        number_of=12,
                        measured_in='Pcs',
                        unit_price=234)
        self.bll11.lines.append(bill_line)
        db.session.flush()
        self.flp11 = FirstLetterProcessor()
        self.slp06 = SecondLetterProcessor()
        self.dtp03 = DebtTransferProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_bills_in_mail(self):
        """ The mail needs to show the overdue bill and other bills in debt """

        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 5, 14))
        for proc_data in dates_list:
            if proc_data[2] == self.slp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.slp06, "No key {slp06.processor_key} found")
        self.slp06.execute(self.bll11, processor_data=current_processor_data)
        with open("output/mailsom" + str(self.bll11.bill_id), "rt") as e_mail:
            mail_text = e_mail.read()
        self.assertIn(str(self.bll11.bill_id), mail_text,
                      "Oversue  bill not in text")
        self.assertIn(str(self.bll8.bill_id), mail_text,
                      "Open bill not in text")
        self.assertNotIn(str(self.bll1.bill_id), mail_text,
                         "Paid bill in text")

    def test_payment_in_mail(self):
        """ The overview needs to show any unassigned payments """

        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 5, 14))
        for proc_data in dates_list:
            if proc_data[2] == self.slp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.slp06, "No key {slp06.processor_key} found")
        self.slp06.execute(self.bll11, processor_data=current_processor_data)
        with open("output/mailsom" + str(self.bll11.bill_id), "rt") as e_mail:
            mail_text = e_mail.read()
        self.assertIn(str(self.ia111.id), mail_text,
                      "Payment not found in mail")

    def test_payment_assigned_not_in_mail(self):
        """ The overview needs to show no assigned payments """

        self.ia111.assign_to_amount(self.ia112)
        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 5, 14))
        for proc_data in dates_list:
            if proc_data[2] == self.slp06.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.slp06, "No key {slp06.processor_key} found")
        self.slp06.execute(self.bll11, processor_data=current_processor_data)
        with open("output/mailsom" + str(self.bll11.bill_id), "rt") as e_mail:
            mail_text = e_mail.read()
        self.assertNotIn(str(self.ia111.id), mail_text,
                      "Payment found in mail")


class TestCreateDebtTransferProcessor(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st24 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st24.add()
        self.st25 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st25.add()
        self.st26 = OverdueSteps(id=120, number_of_days=60, 
                                step_name="Debt transfer",
                                processor="transfer")
        self.st26.add()
        db.session.flush()
        self.flp10 = FirstLetterProcessor()
        self.slp05 = SecondLetterProcessor()
        self.dtp01 = DebtTransferProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_get_transfer_date(self):
        """ We can get the transfer date from the transfer processor """

        tf_date = self.dtp01.transfer_date(date(2021, 12,2))
        self.assertEqual(tf_date, (date(2021, 12, 2)
                                   + timedelta(days=60)).strftime("%d %B %Y"),
                         "Incorrect date for transfer")

    def test_debt_transfer_processor_on_list(self):
        """ The debt transfer processor is in the dates list """

        steps = OverdueSteps.get_days_list()
        self.assertEqual(steps[1], self.st25, "Second letter not in place")
        self.assertEqual(steps[2], self.st24, "First letter not in place")
        self.assertEqual(steps[0], self.st26, "Debt transfer not in place")


class TestDebtTransferProcess(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st31 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st31.add()
        self.st32 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st32.add()
        self.st33 = OverdueSteps(id=120, number_of_days=60, 
                                step_name="Debt transfer",
                                processor="transfer")
        self.st33.add()
        db.session.flush()
        self.flp12 = FirstLetterProcessor()
        self.slp07 = SecondLetterProcessor()
        self.dtp04 = DebtTransferProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_process_executed(self):
        """ The debt transfer process is ecxecuted """

        self.bll12 = Bills(date_sale=date(year=2020, month=1, day=8),
                              date_bill=date(year=2020, month=1, day=8),
                              billing_ccy='JPY',
                              status='issued')
        self.clt1.bills.append(self.bll12)
        self.bills.append(self.bll12)
        db.session.flush()
        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 4, 22))
        for proc_data in dates_list:
            if proc_data[2] == self.dtp04.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.dtp04, "No key {self.dtp04.processor_key} found")
        self.dtp04.execute(self.bll12, processor_data=current_processor_data)
        action = db.session.query(OverdueActions).\
            filter_by(step=self.st33).first()
        self.assertEqual(action.bill, self.bll12, "Action not transfer for bill")
        self.assertTrue(exists("output/dtm" + str(self.bll12.bill_id)),
                               "Debt transfer letter file does not exist")
        self.assertTrue(exists("output/maildtm" + str(self.bll12.bill_id)),
                               "Debt transfer mail file does not exist")

    def test_file_output_transfer(self):
        """ A file is made with data of the transfer """

        self.bll13 = Bills(date_sale=date(year=2020, month=1, day=8),
                              date_bill=date(year=2020, month=1, day=8),
                              billing_ccy='JPY',
                              status='issued')
        self.clt1.bills.append(self.bll13)
        self.bills.append(self.bll13)
        db.session.flush()
        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 4, 22))
        for proc_data in dates_list:
            if proc_data[2] == self.dtp04.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.dtp04, "No key {self.dtp04.processor_key} found")
        self.dtp04.execute(self.bll13, processor_data=current_processor_data)
        self.assertTrue(exists("output/trfmsg" + str(self.bll13.bill_id)
                               + ".json"), "No debt transfer data")


class TestTransferMessageContent(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st34 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st34.add()
        self.st35 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st35.add()
        self.st36 = OverdueSteps(id=120, number_of_days=60, 
                                step_name="Debt transfer",
                                processor="transfer")
        self.st36.add()
        db.session.flush()
        self.flp13 = FirstLetterProcessor()
        self.slp08 = SecondLetterProcessor()
        self.dtp05 = DebtTransferProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_data_in_letter(self):
        """ Data like bill id and bill date in letter """

        self.bll14 = Bills(date_sale=date(year=2020, month=1, day=12),
                              date_bill=date(year=2020, month=1, day=13),
                              billing_ccy='JPY',
                              status='issued')
        self.clt1.bills.append(self.bll14)
        self.bills.append(self.bll14)
        bill_line = BillLines(short_desc='Mouthpiece',
                        long_desc='A mouthpiece for trumpet',
                        number_of=2,
                        measured_in='Pcs',
                        unit_price=1234)
        self.bll14.lines.append(bill_line)
        db.session.flush()
        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 8, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.dtp05.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.dtp05, "No key {dtp05.processor_key} found")
        self.dtp05.execute(self.bll14, processor_data=current_processor_data)
        with open("output/dtm" + str(self.bll14.bill_id), "rt") as letter:
            text = letter.read()
        self.assertIn(str(self.bll14.bill_id), text,
                      "Overdue  bill not in text")
        self.assertIn(str(self.bll8.bill_id), text,
                      "Open bill not in text")
        self.assertNotIn(str(self.bll1.bill_id), text,
                         "Paid bill in text")
        self.assertIn('2.468', text, "Amount debt not in text")
        self.assertIn(self.bll14.date_bill.strftime("%d %B %Y"),
                      text, "Amount debt not in text")
        self.assertIn(str(self.bll8.bill_id), text,
                      "Other bill not in letter")
        self.assertIn(str(self.ia111.id), text,
                      "Payment not in letter")

    def test_data_in_mail(self):
        """ Data like bill id and bill date in mail """

        self.bll15 = Bills(date_sale=date(year=2020, month=1, day=12),
                              date_bill=date(year=2020, month=1, day=13),
                              billing_ccy='JPY',
                              status='issued')
        self.clt1.bills.append(self.bll15)
        self.bills.append(self.bll15)
        bill_line = BillLines(short_desc='Mouthpiece',
                        long_desc='A mouthpiece for trumpet',
                        number_of=2,
                        measured_in='Pcs',
                        unit_price=1234)
        self.bll15.lines.append(bill_line)
        db.session.flush()
        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 8, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.dtp05.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.dtp05, "No key {dtp05.processor_key} found")
        self.dtp05.execute(self.bll15, processor_data=current_processor_data)
        with open("output/maildtm" + str(self.bll15.bill_id), "rt") as e_mail:
            text = e_mail.read()
        self.assertIn(str(self.bll15.bill_id), text,
                      "Overdue  bill not in text")
        self.assertIn(str(self.bll8.bill_id), text,
                      "Open bill not in text")
        self.assertNotIn(str(self.bll1.bill_id), text,
                         "Paid bill in text")
        self.assertIn('2.468', text, "Amount debt not in text")
        self.assertIn(self.bll15.date_bill.strftime("%d %B %Y"),
                      text, "Amount debt not in text")
        self.assertIn(str(self.bll8.bill_id), text,
                      "Other bill not in letter")
        self.assertIn(str(self.ia111.id), text,
                      "Payment not in letter")

    def test_json_content(self):
        """ Data like bill id and bill date in json """

        self.bll16 = Bills(date_sale=date(year=2020, month=1, day=10),
                              date_bill=date(year=2020, month=1, day=12),
                              billing_ccy='JPY',
                              status='issued')
        self.clt1.bills.append(self.bll16)
        self.bills.append(self.bll16)
        bill_line = BillLines(short_desc='Mouthpiece',
                        long_desc='A mouthpiece for trombone',
                        number_of=2,
                        measured_in='Pcs',
                        unit_price=1734)
        self.bll16.lines.append(bill_line)
        db.session.flush()
        dates_list = OverdueSteps.get_date_list(from_date=date(2020, 8, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.dtp05.processor_key:
                current_processor_data = proc_data
                break
        self.assertTrue(self.dtp05, "No key {dtp05.processor_key} found")
        self.dtp05.execute(self.bll16, processor_data=current_processor_data)
        with open("output/trfmsg" + str(self.bll16.bill_id) + ".json", "rt") as trfmsg:
            json_text = trfmsg.read()
        self.assertIn(str(self.bll16.bill_id), json_text,
                      "Overdue  bill not in json")
        self.assertIn(str(self.bll8.bill_id), json_text,
                      "Open bill not in json")
        self.assertNotIn(str(self.bll1.bill_id), json_text,
                         "Paid bill in json")
        self.assertIn('3.468', json_text, "Amount debt not in json")
        self.assertIn(self.bll16.date_bill.strftime("%d %B %Y"),
                      json_text, "Bill date not correct in json")
        self.assertIn(str(self.bll8.bill_id), json_text,
                      "Other bill not in json")
        self.assertIn(str(self.ia111.id), json_text,
                      "Payment not in json")

class TestCreateDubiousDebtor(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st37 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st37.add()
        self.st38 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st38.add()
        self.st39 = OverdueSteps(id=120, number_of_days=60, 
                                step_name="Debt transfer",
                                processor="transfer")
        self.st39.add()
        db.session.flush()
        self.flp13 = FirstLetterProcessor()
        self.slp08 = SecondLetterProcessor()
        self.dtp05 = DebtTransferProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_can_create_processor(self):
        """ We can create a dubious debtor processor """

        self.st40 = OverdueSteps(id=130, number_of_days=80, 
                                step_name="Dubious debtor",
                                processor="dubious")
        self.st40.add()
        db.session.flush()
        self.ddp01 = DubiousDebtorProcessor()
        steps = OverdueSteps.get_by_processor("dubious")
        self.assertTrue(steps, "Step not in list")
        self.assertIn("dubious", self.ddp01.all_processors,
                      "Dubious Debtor Processor not in all processors")


class TestDubiousDebtorProcess(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        self.st41 = OverdueSteps(id=100, number_of_days=25, 
                                step_name="First Letter",
                                processor="firstletter")
        self.st41.add()
        self.st42 = OverdueSteps(id=110, number_of_days=40, 
                                step_name="Second Letter",
                                processor="secondletter")
        self.st42.add()
        self.st43 = OverdueSteps(id=120, number_of_days=60, 
                                step_name="Debt transfer",
                                processor="transfer")
        self.st43.add()
        self.st44 = OverdueSteps(id=130, number_of_days=80, 
                                step_name="Dubious debtor",
                                processor="dubious")
        self.st44.add()
        db.session.flush()
        self.flp13 = FirstLetterProcessor()
        self.slp08 = SecondLetterProcessor()
        self.dtp05 = DebtTransferProcessor()
        self.ddp01 = DubiousDebtorProcessor()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        delete_overdue_steps(self)
        db.session.commit()

    def test_create_dubious_signal(self):
        """ A dubious signal is created by the processor """

        bll17 = Bills(date_sale=date(year=2020, month=1, day=10),
                      date_bill=date(year=2020, month=1, day=12),
                      billing_ccy='JPY',
                      status='issued')
        bll17.client = self.clt1
        bll17.add()
        db.session.commit()
        dates_list = OverdueSteps.get_date_list(from_date=date(2021, 8, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.ddp01.processor_key:
                current_processor_data = proc_data
                break

        self.ddp01.execute(bll17, processor_data=current_processor_data)
        sig17 = DebtorSignal.client_has_signal(self.clt1)
        self.assertTrue(sig17, "No signal found")

    def test_bill_set_dubious(self):
        """ The bill that is handled is set to dubious """

        bll18 = Bills(date_sale=date(year=2020, month=2, day=10),
                      date_bill=date(year=2020, month=2, day=12),
                      billing_ccy='JPY',
                      status='issued')
        bll18.client = self.clt1
        bll18.add()
        db.session.commit()
        bll18_id = bll18.bill_id
        dates_list = OverdueSteps.get_date_list(from_date=date(2021, 8, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.ddp01.processor_key:
                current_processor_data = proc_data
                break

        self.ddp01.execute(bll18, processor_data=current_processor_data)
        bll19 = db.session.query(Bills).filter_by(bill_id=bll18_id).first()
        self.assertEqual(bll19.status, Bills.DUBIOUS,
                         "Bill processed not set to dubious status")

    def test_other_bills_set_dubious(self):
        """ Other outstanding bills for client needs to be marked dubious """

        bll20 = Bills(date_sale=date(year=2020, month=2, day=15),
                      date_bill=date(year=2020, month=2, day=16),
                      billing_ccy='JPY',
                      status='issued')
        bll20.client = self.clt1
        bll20.add()
        db.session.commit()
        bll20_id = bll20.bill_id
        dates_list = OverdueSteps.get_date_list(from_date=date(2021, 9, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.ddp01.processor_key:
                current_processor_data = proc_data
                break

        self.ddp01.execute(bll20, processor_data=current_processor_data)
        self.assertEqual(self.bll8.status, Bills.DUBIOUS,
                         "Other bill not set to dubious status")
        self.assertEqual(self.bll1.status, Bills.DUBIOUS,
                         "Other bill not set to dubious status")

    def test_paid_bills_not_harmed(self):
        """ Paid bills should remain paid """

        bll21 = Bills(date_sale=date(year=2020, month=2, day=14),
                      date_bill=date(year=2020, month=2, day=14),
                      billing_ccy='JPY',
                      status='issued')
        bll21.client = self.clt1
        bll21.add()
        db.session.commit()
        bll21_id = bll21.bill_id
        dates_list = OverdueSteps.get_date_list(from_date=date(2021, 9, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.ddp01.processor_key:
                current_processor_data = proc_data
                break

        self.ddp01.execute(bll21, processor_data=current_processor_data)
        self.assertEqual(self.bll2.status, Bills.PAID,
                         "Paid bill touched by dubious debtor")

    def test_accounting_made(self):
        """ Accounting is made when a contract is set to dubious """

        bll22 = Bills(date_sale=date(year=2020, month=1, day=22),
                      date_bill=date(year=2020, month=1, day=23),
                      billing_ccy='JPY',
                      status='issued')
        bll22.client = self.clt1
        bll22.add()
        db.session.commit()
        bll22_id = bll22.bill_id
        dates_list = OverdueSteps.get_date_list(from_date=date(2021, 9, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.ddp01.processor_key:
                current_processor_data = proc_data
                break

        self.ddp01.execute(bll22, processor_data=current_processor_data)
        ddac01 = DubiousDebtorAccounting(bll22)
        post_list = ddac01["journal"]["postings"]
        accounts = [account for posting in post_list for k, account in posting.items() if k == 'account' ]
        self.assertIn("debt", accounts, 'No debt posting')
        self.assertIn("dubious", accounts, "No dubious debt posting")
        post_balance = 0
        for posting in post_list:
            if posting["debitcredit"] == "Cr":
                post_balance += int(posting["amount"])
            if posting["debitcredit"] == "Db":
                post_balance -= int(posting["amount"])
        self.assertEqual(post_balance, 0, "Journal doesn't balance")
        self.assertEqual(ddac01["journal"]["extkey"],
                         "dubious" + str(bll22.bill_id),
                         "Invalid external key")

    def test_other_bill_accounting(self):
        """ Accounting is done for all bills """

        bll23 = Bills(date_sale=date(year=2020, month=1, day=22),
                      date_bill=date(year=2020, month=1, day=23),
                      billing_ccy='JPY',
                      status='issued')
        bll23.client = self.clt1
        bll23.add()
        db.session.commit()
        bll23_id = bll23.bill_id
        dates_list = OverdueSteps.get_date_list(from_date=date(2021, 9, 18))
        for proc_data in dates_list:
            if proc_data[2] == self.ddp01.processor_key:
                current_processor_data = proc_data
                break

        self.ddp01.execute(bll23, processor_data=current_processor_data)
        ddac02 = DubiousDebtorAccounting(self.bll8)
        self.assertEqual(ddac02["journal"]["extkey"],
                         "dubious" + str(self.bll8.bill_id),
                         "Invalid external key")


if __name__ == '__main__' :
    unittest.main()

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

import unittest
from datetime import datetime, date
from dateutil import parser as dt_parse
from xml.sax import ContentHandler, make_parser, parse
from debttests.helpers import (create_clients, create_bills, add_addresses,
                               add_lines_to_bills,delete_amountq, 
                               delete_test_bills, delete_test_clients,
                               create_payments_for_overdue,
                               delete_test_payments)
from debtors import app, db
from debtors.processCAMT import CAMT53Handler
from debtmodels.payments import IncomingAmounts
from debtviews.history import History

class TestClientDataInMessages(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        create_payments_for_overdue(self)
        db.session.flush()
        self.camthandler = CAMT53Handler()
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)

    def tearDown(self):

        db.session.rollback()
        delete_amountq(self)
        delete_test_bills(self)
        delete_test_payments(self)
        delete_test_clients(self)
        db.session.commit()

    def test_client_name_address_in_message(self):
        """ Name and address are in returned data """

        his1 = History(client=self.clt5)
        self.assertEqual(his1["client"]["id"], self.clt5.id,
                         "Client number not correct")
        self.assertEqual(his1["client"]["surname"], 'Aubergine',
                         "Wrong client name {}".format(his1["client"]["surname"]))

    def test_postal_address_in_message(self):
        """ The postal address is in the data """

        his2 = History(client=self.clt5)
        address = self.clt5.postal_address()
        self.assertEqual(his2["address"]["street"], address.street,
                         "address not correct")
        self.assertEqual(his2["address"]["house_number"], 
                         address.house_number,
                         "address not correct")
        self.assertEqual(his2["address"]["town_or_village"],
                         address.town_or_village,
                         "address not correct")

    def test_po_box_address(self):
        """ The postal address is a po box """

        his3 = History(client=self.clt2)
        address = self.clt2.postal_address()
        with self.assertRaises(KeyError):
           street =  his3["address"]["street"]
        self.assertEqual(his3["address"]["po_box"], address.po_box,
                         "postbox not correct")

    def test_mail_address(self):
        """ Test mail address present """

        his4 = History(client=self.clt1)
        self.assertEqual(his4["mail_addresses"][0]["mail_address"],
                    "dingor@prov.com", "Address not in dictionary")

    def test_more_mail_addresses(self):
        """ More mail addresses appear all in output """

        his5 = History(client=self.clt2)
        self.assertEqual(len(his5["mail_addresses"]), 2,
                             "Too many/little addresses: {}".format(len(his5["mail_addresses"])))

    def test_bank_account(self):
        """ Test bank account present """

        his6 = History(client=self.clt1)
        self.assertEqual(his6["bank_accounts"][0]["iban"],
                    self.clt1.accounts[0].iban, "Account not in dictionary")

    def test_more_accounts(self):
        """ More bank accounts get reflected in dictionary """

        his7 = History(client=self.clt3)
        self.assertEqual(len(his7["bank_accounts"]), 2,
                         "Too many/little accounts in dictionary")

    def test_list_bills(self):
        """ All bills must be in the list of bills and payments """

        his8 = History(client=self.clt5)
        bill_list = [bill["bill_id"] for bill in his8["bills_payments"]
            if "bill_id" in bill]
        self.assertIn(self.bll6.bill_id, bill_list, 
                      "Bill not in generated list")
        self.assertEqual(len(bill_list), 3, "Not enough/too many bills")

    def test_newest_bill_first(self):
        """ The bills should be presented from new to old """

        his9 = History(client=self.clt5)
        bill_list = [bill for bill in his9["bills_payments"]]
        date_list = [bill["date_bill"]
                     for bill in bill_list if "date_bill" in bill]
        self.assertTrue(date_list[0] >= date_list[1],
                        "First bills not in order")
        self.assertTrue(date_list[1] >= date_list[2],
                        "Last bills not in order")

    def test_no_bills_for_client(self):
        """ A client having no bills should return no bill """

        his10 = History(client=self.clt2)
        with self.assertRaises(KeyError,
                               msg="Bill found for client having none"):
            bill_list = [bill for bill in his10["bills_payments"]]

    def test_bill_has_status(self):
        """ Each bill comes with a status """

        his11 = History(client=self.clt5)
        bill_list = [bill for bill in his11["bills_payments"]]
        status_list = [bill["status"]
                     for bill in bill_list if "status" in bill]
        self.assertEqual(len(status_list), 3,
                         "Bills without status")

    def test_payment_in_list(self):
        """ Payments want to be in the bills and payments list """

        his12 = History(client=self.clt5)
        bill_payment_list = [bill_payment
                             for bill_payment in his12["bills_payments"]]
        id_list = [payment["id"] for payment in bill_payment_list
                   if "id" in payment]
        self.assertIn(self.ia112.id, id_list,
                      "Payment not in list")
        self.assertEqual(len(id_list), 2, "Too many little payments in list")

    def test_payment_attributes(self):
        """ The (non-key) attributes of a payment are in the list """

        his13 = History(client=self.clt5)
        bill_payment_list = [bill_payment
                             for bill_payment in his13["bills_payments"]]
        payment_list = [payment for payment in bill_payment_list
                   if "id" in payment]
        for payment in payment_list:
            self.assertIn("value_date", payment, "Date not in payment")
            self.assertIn("payment_ccy", payment, "Currency not in payment")
            self.assertIn("payment_amount", payment, "Amount not in payment")
            self.assertIn("debcred", payment, "Debit/credit not in payment")

    def test_bills_payments_are_in_order(self):
        """ The order is maintained for payments and bills interspersed """

        his14 = History(client=self.clt5)
        bill_payment_list = [bill_payment
                             for bill_payment in his14["bills_payments"]]
        self.assertEqual(bill_payment_list[0]["bill_id"], self.bll4.bill_id,
                         "Bill 4 not in 1st position")
        self.assertEqual(bill_payment_list[1]["id"], self.ia112.id,
                         "Payment 112 not in 2nd position")

    def test_paid_bill_assigned_amount(self):
        """ A paid bill has number of paying amount and date """

        payment = self.ia110
        his15 = History(client=self.clt5)
        bill_list = [bill for bill in his15["bills_payments"]
                     if "bill_id" in bill
                     and bill["bill_id"] == self.bll5.bill_id]
        self.assertTrue(bill_list, "Bill list empty")
        self.assertEqual(bill_list[0]["payment_id"], payment.id,
                        "No payment number")

    def test_payment_has_source(self):
        """ A payment has indication where it is from if from a payment """

        payment = self.ia112
        new_payment = IncomingAmounts(payment_ccy=payment.payment_ccy,
                                      payment_amount=0,
                                      value_date=date.today())
        new_payment.client = self.clt5
        payment.assign_to_amount(new_payment)
        db.session.flush()
        his16 = History(client=self.clt5)
        payment_list = [payment for payment in his16["bills_payments"]
                     if "id" in payment
                     and payment["id"] == new_payment.id]
        self.assertTrue(payment_list, "Payment list empty")
        self.assertEqual(payment_list[0]["from_payments"][0]["from_payment"], payment.id,
                        "No payment number")

    def test_payment_has_more_than_1_source(self):
        """ If a payment has 2 sources, both are reported  """

        first_payment = self.ia112
        another_payment = IncomingAmounts(
                                      payment_ccy=first_payment.payment_ccy,
                                      payment_amount=45,
                                      value_date=date.today())
        new_payment = IncomingAmounts(payment_ccy=first_payment.payment_ccy,
                                      payment_amount=0,
                                      value_date=date.today())
        new_payment.client = self.clt5
        another_payment.client = self.clt5
        first_payment.assign_to_amount(new_payment)
        another_payment.assign_to_amount(new_payment)
        db.session.flush()
        his17 = History(client=self.clt5)
        payment_list = [payment for payment in his17["bills_payments"]
                     if "id" in payment
                     and payment["id"] == new_payment.id]
        orig_payments = payment_list[0]["from_payments"]
        for payment in orig_payments:
            self.assertIn(payment["from_payment"],
                          (first_payment.id, another_payment.id),
                          f"Payment missing")

    def test_no_source_payment_returns_nothing(self):
        """ A payment with no source payments doesn't have sources """

        first_payment = self.ia112
        his18 = History(client=self.clt5)
        payment_list = [payment for payment in his18["bills_payments"]
                     if "id" in payment
                     and payment["id"] == first_payment.id]
        for each in payment_list:
            self.assertNotIn("from_payment", each,
                                "Payment in list as source")

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
                               delete_test_bills, delete_test_clients)
from debtors import app, db
from debtors.processCAMT import CAMT53Handler
from debtviews.history import History

class TestClientDataInMessages(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        db.session.flush()
        self.camthandler = CAMT53Handler()
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)

    def tearDown(self):

        db.session.rollback()
        delete_amountq(self)
        delete_test_bills(self)
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

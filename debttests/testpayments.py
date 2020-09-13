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
from datetime import datetime
from dateutil import parser
from debtors import db
from debtmodels.payments import IncomingAmounts
from debttests.helpers import delete_test_clients, add_addresses,\
    create_clients, spread_created_at, create_bills, add_lines_to_bills,\
    delete_test_bills, add_debtor_preferences
from debtors.processCAMT import CAMT53Handler
from xml.sax import ContentHandler, make_parser, parse


class TestCreatePayment(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        #create_bills(self)
        #add_lines_to_bills(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        #delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_create_incoming_amount(self):
        """ We can create an incoming amount """

        ia01 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=1330)
        ia01.add()
        db.session.flush()
        self.assertEqual('EUR', ia01.payment_ccy, 'Failure creating')

    def test_create_with_client(self):
        """ Add a payment with a client """

        ia02 = IncomingAmounts(payment_ccy='USD',
                               payment_amount=13800)
        ia02.client = self.clt1
        db.session.flush()
        self.assertEqual(self.clt1.id, ia02.client_id, 'Not attached')


class TestCAMTEntryHandler(unittest.TestCase):

    def setUp(self):

        self.camthandler = CAMT53Handler()
        self.camthandler.entries = []
        self.camthandler.creation_timestamp =\
            parser.parse(timestr="2014-01-08T02:55:04.378+01:00")
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)

    def tearDown(self):

        self.camthandler = None
        parser = None

    def test_create_unassigned_amount(self):
        """ We can create an unassigned amount in the handler """

        with open('debttests/SEPA credit entry.xml') as sce:
            parse(sce, self.camthandler)
            self.assertTrue(self.camthandler.unassigned_amount,
                            'No unassigned amount parsed')

    def test_unassigned_amount_correct_amount(self):
        """ The amount on the unassigned amount is correct """

        with open('debttests/SEPA credit entry.xml') as sce:
            parse(sce, self.camthandler)
            unassigned = self.camthandler.unassigned_amount
            self.assertEqual(unassigned.payment_amount, 35000, 
                            'Wrong amount parsed')
            self.assertEqual(unassigned.payment_ccy, 'EUR', 
                            'Wrong/no currency parsed')

    def test_value_date(self):
        """ The value date on a unassigned amount is correct """

        with open('debttests/SEPA credit entry.xml') as sce:
            parse(sce, self.camthandler)
            unassigned = self.camthandler.unassigned_amount
            self.assertEqual(unassigned.value_date, 
                             datetime(year=2014, month=1, day=3), 
                            'Wrong valuedate parsed')

    def test_bank_reference(self):
        """ We extract the banks transaction reference """

        with open('debttests/SEPA credit entry.xml') as sce:
            parse(sce, self.camthandler)
            unassigned = self.camthandler.unassigned_amount
            self.assertEqual(unassigned.bank_ref, 
                            '59999208N9', 
                            'Wrong bank reference  parsed')

    def test_user_reference(self):
        """ We extract the paying clients reference """

        with open('debttests/SEPA credit entry.xml') as sce:
            parse(sce, self.camthandler)
            unassigned = self.camthandler.unassigned_amount
            self.assertEqual(unassigned.client_ref, 
                            '0010008346912014', 
                            'Wrong client reference  parsed')

    def test_client_name_IBAN(self):
        """ We extract the clients name """

        with open('debttests/SEPA credit entry.xml') as sce:
            parse(sce, self.camthandler)
            unassigned = self.camthandler.unassigned_amount
            self.assertEqual(unassigned.client_name, 
                            'ING Testrekening', 
                            'Wrong client name  parsed')
            self.assertEqual(unassigned.creditor_IBAN, 
                            'NL20INGB0001234567', 
                            'Wrong IBAN  parsed')

    def test_our_reference(self):
        """ We can extract our reference """

        with open('debttests/SEPA credit entry.xml') as sce:
            parse(sce, self.camthandler)
            unassigned = self.camthandler.unassigned_amount
            self.assertEqual(unassigned.our_ref, 
                            None, 
                            f'Our reference incorrect: {unassigned.our_ref}')


class TestMoreTransactions(unittest.TestCase):

    def setUp(self):
        self.camthandler = CAMT53Handler()
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)
        self.infile = open('debttests/ING transactievoorbeelden.xml', 'r')

    def tearDown(self):

        self.camthandler = None
        parser = None
        self.infile.close()

    def test_multiple_entries(self):
        """ We can parse more than one entry """

        parse(self.infile, self.camthandler)
        self.assertTrue(len(self.camthandler.entries) > 1,
                        'Too little entries found')
        
    def test_file_timestamp(self):
        """ The timestamp of the statement is in the entries """

        parse(self.infile, self.camthandler)
        self.assertEqual(self.camthandler.entries[2].file_timestamp,
                        parser.parse("2014-01-04T01:55:04.378+01:00"),
                        'Wrong/no timestamp')

    def test_nr_of_processed_entries(self):
        """ We process the right no of transactions """

        parse(self.infile, self.camthandler)
        self.assertEqual(len(self.camthandler.entries),
                        9, 'Too many/little entries')

    def test_statement_for_wrong_account(self):
        """ A statement for a wrong account fails """

        self.camthandler.accounts = ['NL21INGB0001234568']
        parse(self.infile, self.camthandler)
        self.assertEqual(len(self.camthandler.entries),
                        0, 'Too many entries')
        

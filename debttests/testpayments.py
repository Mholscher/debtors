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
from dateutil import parser
from dateutil.tz import tzoffset
from debtors import db
from debtmodels.payments import IncomingAmounts, AmountQueued, AssignedAmounts
from debtmodels.debtbilling import Bills, BillLines
from debttests.helpers import delete_test_clients, add_addresses,\
    create_clients, spread_created_at, create_bills, add_lines_to_bills,\
    delete_test_bills, add_debtor_preferences, delete_amountq,\
    delete_test_prefs
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
                            '011111333306999888000000008', 
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
            self.assertEqual(unassigned.creditor_iban, 
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
        delete_amountq(self)
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_multiple_entries(self):
        """ We can parse more than one entry """

        parse(self.infile, self.camthandler)
        self.assertTrue(len(self.camthandler.entries) > 1,
                        'Too little entries found')
        
    def test_file_timestamp(self):
        """ The timestamp of the statement is in the entries """

        parse(self.infile, self.camthandler)
        self.assertEqual(self.camthandler.entries[2].file_timestamp,
                        parser.parse("2014-01-04T01:55:04"),
                        'Wrong/no timestamp')

    def test_nr_of_processed_entries(self):
        """ We process the right no of transactions """

        parse(self.infile, self.camthandler)
        self.assertEqual(len(self.camthandler.entries),
                        6, 'Too many/little entries')

    def test_statement_for_wrong_account(self):
        """ A statement for a wrong account fails """

        self.camthandler.accounts = ['NL21INGB0001234568']
        parse(self.infile, self.camthandler)
        self.assertEqual(len(self.camthandler.entries),
                        0, 'Too many entries')

    def test_transaction_type(self):
        """ Invalid transaction type is refused """

        parse(self.infile, self.camthandler)
        ref_list = [entry.bank_ref for entry in self.camthandler.entries\
                    if entry.bank_ref == '012222333306999888111100002']
        self.assertEqual(len(ref_list),
                        0, 'Entry not ignored')

    def test_debit_credit(self):
        """ Debit and credit are correctly set """

        parse(self.infile, self.camthandler)
        ref_list = [(entry.debcred, entry.bank_ref) for entry in self.camthandler.entries\
                    if entry.bank_ref == '011111333306999888000000008'\
                        or entry.bank_ref == '021514017743280167000000001']
        for entry in ref_list:
            if entry[1] == '011111333306999888000000008':
                self.assertEqual(entry[0], 'Cr',
                                 'Credit entry not booked as credit')
            elif entry[1] == '021514017743280167000000001':
                self.assertEqual(entry[0], 'Db',
                                 'Debit entry not booked as debit')

    def test_store_entries(self):
        """ We can store entries at the end of a statement """

        parse(self.infile, self.camthandler)
        one_amount = db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000008').first()
        self.assertTrue(one_amount, "No entry for bank reference")


class TestAssignAmounts(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
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

    def test_assigning_tried(self):
        """ Adding a payment triggers assigning attempt """

        self.camthandler.entries = []
        self.camthandler.creation_timestamp =\
            parser.parse(timestr="2014-01-08T02:55:04.378+01:00")
        with open('debttests/SEPA credit entry.xml') as sce:
            parse(sce, self.camthandler)
        ce1 = db.session.query(AmountQueued).first()
        self.assertTrue(ce1, 'No first entry in queue')

    def test_is_queued(self):
        """ We can ask if an assigned amount is queued """

        self.camthandler.entries = []
        self.camthandler.creation_timestamp =\
            parser.parse(timestr="2014-01-08T02:55:04.378+01:00")
        with open('debttests/SEPA credit entry.xml') as sce:
            parse(sce, self.camthandler)
        ce1 = db.session.query(IncomingAmounts).first()
        self.assertTrue(AmountQueued.is_queued(ce1.id),
                        "Is queued doesn't answer") 

class TestAssignment(unittest.TestCase):

    def setUp(self):
        
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        db.session.flush()
        self.camthandler = CAMT53Handler()
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)
        self.infile = open('debttests/SEPA transacties test assignment.xml', 'r')

    def tearDown(self):

        db.session.rollback()
        self.camthandler = None
        parser = None
        self.infile.close()
        #delete_amountq(self)
        db.session.flush()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.query(AmountQueued).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_assign_thru_account(self):
        """ We can assign if we know the other account """

        parse(self.infile, self.camthandler)
        ia03 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        ial01 = ia03.find_assignment_target()
        self.assertIn(self.bll4, ial01)

    def test_rule_out_large_debt(self):
        """ A large amount billed is not selected as a target """

        bll5 = Bills(billing_ccy='JPY', date_sale=date(year=2020, month=1,
                                                       day=15),
                     date_bill=date(year=2020, month=1, day=15), 
                     status='issued')
        blll1 = BillLines(short_desc='Large!', number_of=15,
                          unit_price=500)
        bll5.lines.append(blll1)
        bll5.client = self.clt5
        bll5.add()
        db.session.flush()
        parse(self.infile, self.camthandler)
        ia03 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        ial01 = ia03.find_assignment_target()
        self.assertNotIn(bll5, ial01)

    def test_no_other_ccy(self):
        """ An amount received must have the same ccy as the bill """

        bll6 = Bills(billing_ccy='EUR', date_sale=date(year=2020, month=2,
                                                       day=16),
                     date_bill=date(year=2020, month=2, day=16), 
                     status='issued')
        blll2 = BillLines(short_desc='ccy wrong', number_of=5,
                          unit_price=2)
        bll6.lines.append(blll2)
        bll6.client = self.clt5
        bll6.add()
        db.session.flush()
        parse(self.infile, self.camthandler)
        ia04 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        ial02 = ia04.find_assignment_target()
        self.assertNotIn(bll6, ial02)

    def test_order_of_bills(self):
        """ Bills need to be returned in descending order of amount """

        bll7 = Bills(billing_ccy='JPY', date_sale=date(year=2020, month=2,
                                                       day=16),
                     date_bill=date(year=2020, month=2, day=16), 
                     status='issued')
        blll3 = BillLines(short_desc='ccy wrong', number_of=5,
                          unit_price=2)
        bll7.lines.append(blll3)
        bll7.client = self.clt5
        bll7.add()
        db.session.flush()
        parse(self.infile, self.camthandler)
        ia05 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        ial03 = ia05.find_assignment_target()
        self.assertGreater(ial03[0].total(), ial03[1].total(),
                           'Bills not in descending order')

    def test_assign_exact_amount(self):
        """ We can assign the exact amount of a bill """

        parse(self.infile, self.camthandler)
        ia06 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        ia06.assign_amount()
        aa01 = db.session.query(AssignedAmounts).\
            filter_by(from_amount=ia06).first()
        self.assertEqual(aa01.from_amount.id, ia06.id, 'Not assigned')
        self.assertEqual(aa01.bill.status, 'paid', 'Status not set to paid')

    def test_assign_more_bills(self):
        """ We can assign to more bills """

        bll8 = Bills(billing_ccy='JPY', date_sale=date(year=2020, month=2,
                                                       day=16),
                     date_bill=date(year=2020, month=2, day=16), 
                     status='issued')
        blll4 = BillLines(short_desc='sec bill', number_of=5,
                          unit_price=2)
        bll8.lines.append(blll4)
        bll8.client = self.clt5
        bll8.add()
        ia02 = IncomingAmounts(payment_ccy='JPY',
                               creditor_iban= 'NL76INGB0594788005',
                               payment_amount=1890)

        ia02.add()
        db.session.flush()
        ia02.assign_amount()
        db.session.flush()
        aa02 = db.session.query(AssignedAmounts).all()
        self.assertEqual(len(aa02), 2, 'Not assigned to 2 bills')
        self.assertEqual(ia02.client, self.clt5, 'Not attached to client')

    def test_unassigned_is_attached_to_client(self):
        """ If an amount can be attached to a client, do that. """

        parse(self.infile, self.camthandler)
        ia07 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000019').first()
        ia07.assign_amount()
        aa01 = db.session.query(IncomingAmounts).\
            filter_by(id=ia07.id).first()
        self.assertEqual(aa01.client, self.clt2, 'Not attached to client')

    def test_create_incoming_amount_for_reversal(self):
        """ A reversal creates an incoming debit amount """

        ia08 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=12500,
                               debcred='CR',
                               bank_ref='Bankref 11129',
                               creditor_iban='NL08INGB0212952803')
        ia08.client = self.clt2
        db.session.flush()
        parse(self.infile, self.camthandler)
        ia09 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='022221333306999888222200112').first()
        self.assertEqual(ia09.debcred, 'Db', 'No debit entry')

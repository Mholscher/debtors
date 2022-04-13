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
from werkzeug.datastructures import ImmutableMultiDict
from debtviews.monetary import edited_amount
from debtors import app, db
from debtmodels.payments import IncomingAmounts, AmountQueued, AssignedAmounts
from debtmodels.debtbilling import Bills, BillLines
from debtviews.payments import (PaymentAccounting, AssignmentAccounting,
                                PaymentReversalAccounting,
                                AssignmentReversalAccounting)
from debttests.helpers import (delete_test_clients, add_addresses,
    create_clients, spread_created_at, create_bills, add_lines_to_bills,
    delete_test_bills, delete_amountq, delete_test_prefs)
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

    def test_create_payment_currency(self):
        """ An incoming amount has a valid currency """

        ia15 = IncomingAmounts(payment_ccy='jpy',
                               payment_amount=1330)
        ia15.add()
        db.session.flush()
        self.assertEqual('JPY', ia15.payment_ccy, 'Currency not uppercased')

    def test_nonexisting_currency_fails(self):
        """ An incoming amount has a valid currency """

        with self.assertRaises(ValueError):
            ia16 = IncomingAmounts(payment_ccy='CBY',
                                payment_amount=17830)
            ia16.add()
            db.session.flush()

    def test_nonexisting_debcred_fails(self):
        """ An incoming amount has a debit/credit indicator """

        with self.assertRaises(ValueError):
            ia17 = IncomingAmounts(payment_ccy='GBP',
                                payment_amount=17830,
                                debcred='Ag')
            ia17.add()
            db.session.flush()

    def test_reference_too_long(self):
        """ A reference is max 35 positions """

        with self.assertRaises(ValueError):
            ia17 = IncomingAmounts(payment_ccy='EUR',
                                payment_amount=10090,
                                debcred='Cr',
                                our_ref='123456789012345678901234567890123456')
            ia17.add()
            db.session.flush()

    def test_create_with_client(self):
        """ Add a payment with a client """

        ia02 = IncomingAmounts(payment_ccy='USD',
                               payment_amount=13800)
        ia02.client = self.clt1
        db.session.flush()
        self.assertEqual(self.clt1.id, ia02.client_id, 'Not attached')

    def test_get_payment_by_id(self):
        """ We can get a bill by its id """

        ia10 = IncomingAmounts(payment_ccy='USD',
                               payment_amount=48556,
                               creditor_iban= 'NL08INGB0212952803',
                               client_name='F.K. Pieterse')
        ia10.client = self.clt2
        ia10.add()
        db.session.flush()
        ia10_id = ia10.id
        self.assertEqual(IncomingAmounts.get_payment_by_id(ia10_id).id,
                         ia10_id, 'Wrong/no payment retrieved by id')

    def test_attach_client_when_assigned_fails(self):
        """ We cannot assitgn a non-existing client """

        ia18 = IncomingAmounts(payment_ccy='USD',
                               payment_amount=48856,
                               creditor_iban= 'NL08INGB0212952123',
                               client_name='F.K. Giropal')
        ia18.add()
        aa04 = AssignedAmounts(ccy='USD', amount_assigned=3)
        aa04.from_amount = ia18
        db.session.flush()
        with self.assertRaises(ValueError):
            ia18.change_client(self.clt3)


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
        self.parser = None
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

    def test_reversal_indicator_set(self):
        """ We translate the reversal indicator from CAMT053 """

        parse(self.infile, self.camthandler)
        rvsl_list = [(entry.debcred, entry.rvslind) for entry in 
                     self.camthandler.entries if entry.bank_ref ==
                     "021514017743280167000000001"]
        for entry in rvsl_list:
            self.assertEqual(entry[0], "Db", "Entry not debit")
            self.assertEqual(entry[1], True, "Entry no reversal")


class TestAssignAmounts(unittest.TestCase):

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

    def test_attach_client(self):
        """ We can attach a client to a payment """

        incoming_amount = IncomingAmounts(payment_ccy='USD',
                                payment_amount=48876,
                                debcred = 'Cr')
        incoming_amount.client = self.clt4
        db.session.flush()
        self.assertIn(incoming_amount, self.clt4.payments,
                      'Payment not in clients payments')

    def test_assign_to_any_bill(self):
        """ Assign a payment to a bill not for the attached client """

        ia19 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=1000,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 21))
        ia19.client = self.clt3
        ia19.add()
        db.session.flush()
        aa06 = AssignedAmounts(ccy='JPY',
                               amount_assigned=1000)
        aa06.bill = self.bll4
        db.session.flush()
        self.assertIn(aa06, self.bll4.assignments, "Not assigned to bill")

    def test_assign_amount_through_method(self):
        """ Assign a full payment to a bill """

        ia20 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=1880,
                               debcred='Cr',
                               value_date=datetime(2020, 12, 11))
        ia20.client = self.clt3
        ia20.add()
        db.session.flush()
        aa07 = ia20.assign_to_bill(self.bll4)
        self.assertIn(aa07, ia20.used_in, "Not assigned to amount")

    def test_incoming_amount_bill_must_be_same_ccy(self):
        """ A payment must be same currency as bill to assign"""

        ia22 = IncomingAmounts(payment_ccy='USD',
                               payment_amount=890,
                               debcred='Cr',
                               value_date=datetime(2021, 2, 1))
        ia22.client = self.clt4
        ia22.add()
        db.session.flush()
        with self.assertRaises(ValueError):
            aa09 = ia22.assign_to_bill(self.bll4)

    def test_assignment_pays_bill(self):
        """ If we assign "enough" cash to a bill, it is paid """

        ia23 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=1880,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 25))
        ia23.client = self.clt3
        ia23.add()
        db.session.flush()
        aa10 = ia23.assign_to_bill(self.bll4)
        self.assertEqual(self.bll4.status, "paid", "Bill not set paid")

    def test_cannot_assign_less_than_bill_amount(self):
        """ Assigning less than bill amount fails """

        ia24 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=1758,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 25))
        ia24.client = self.clt3
        ia24.add()
        db.session.flush()
        with self.assertRaises(ValueError):
            aa11 = ia24.assign_to_bill(self.bll4)

    def test_can_assign_part_of_payment(self):
        """ Part of a payment can be assigned to pay a bill """

        ia25 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=3760,
                               debcred='Cr',
                               value_date=datetime(2021, 2, 1))
        ia25.client = self.clt3
        ia25.add()
        db.session.flush()
        aa12 = ia25.assign_to_bill(self.bll4, amount=self.bll4.total())
        self.assertEqual(self.bll4.status, Bills.PAID, "Bill not paid")

    def test_list_unassigned(self):
        """ We can list unassigned payments """

        ia110 = IncomingAmounts(payment_ccy='JPY',
                                payment_amount=1855,
                                debcred='Cr',
                                value_date=datetime(2021, 7, 1))
        ia110.client = self.clt4
        ia110.add()
        db.session.flush()
        ial13 = ia110.client_unassigned_payments(self.clt4)
        self.assertEqual(len(ial13), 1, "Too many/little payments in list")
        self.assertEqual(ia110.id, ial13[0][0],
                         "Incoming amount not in list")
        self.assertEqual(ia110.payment_amount, ial13[0][2],
                         "Incoming amount not in list")
        self.assertEqual(ia110.payment_amount, ial13[0][3],
                         "Unassigned amount not in list")

    def  test_assigned_subtracted_from_payment(self):
        """ An assigned amount is subtracted from unassigned """

        ia111 = IncomingAmounts(payment_ccy='EUR',
                                payment_amount=1275,
                                debcred='Cr',
                                value_date=datetime(2021, 7, 12))
        ia111.client = self.clt4
        bll15 = Bills(billing_ccy='EUR',
                                date_sale=datetime(2021, 7, 8),
                                date_bill=datetime(2021, 7, 8),
                                status="issued")
        bill_line = BillLines(short_desc='Shrt', number_of=1,
                          unit_price=875)
        bill_line.bill = bll15
        bll15.client = self.clt4
        bll15.add()
        db.session.flush()
        aa34 = ia111.assign_to_bill(bll15, amount=875)
        db.session.flush()
        ial14 = ia111.client_unassigned_payments(self.clt4)
        self.assertEqual(len(ial14), 1, "Too many/little payments in list")
        self.assertEqual(ial14[0][3], 400,
                         "Incorrect unassigned amount")

    def test_fully_assigned_payment_ignored(self):
        """ Fully assigned payments are not returned """

        ia113 = IncomingAmounts(payment_ccy='EUR',
                                payment_amount=1288,
                                debcred='Cr',
                                value_date=datetime(2021, 8, 3))
        ia113.client = self.clt4
        bll15 = Bills(billing_ccy='EUR',
                                date_sale=datetime(2021, 8, 1),
                                date_bill=datetime(2021, 8, 1),
                                status="issued")
        bill_line = BillLines(short_desc='PPK', number_of=1,
                          unit_price=1288)
        bill_line.bill = bll15
        bll15.client = self.clt4
        bll15.add()
        db.session.flush()
        aa35 = ia113.assign_to_bill(bll15)
        ial15 = ia113.client_unassigned_payments(self.clt4)
        self.assertEqual(len(ial15), 0, "Too many payments in list")


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
        db.session.query(AssignedAmounts).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_assign_thru_account(self):
        """ We can assign if we know the other account """

        parse(self.infile, self.camthandler)
        ia03 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        ial01 = ia03.find_assignment_targets()
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
        ial01 = ia03.find_assignment_targets()
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
        ial02 = ia04.find_assignment_targets()
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
        ial03 = ia05.find_assignment_targets()
        self.assertGreater(ial03[0].total(), ial03[1].total(),
                           'Bills not in descending order')

    def test_assign_exact_amount(self):
        """ We can assign the exact amount of a bill """

        parse(self.infile, self.camthandler)
        ia06 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()

        ia06.assign_amount()
        db.session.commit()

        aa01 = db.session.query(AssignedAmounts).\
            filter_by(from_amount=ia06).first()

        self.assertEqual(aa01.from_amount.id, ia06.id, 'Not assigned')
        self.assertEqual(aa01.bill.status, 'paid', 'Status not set to paid')
        self.assertTrue(ia06.fully_assigned, 'Fully assigned not set')

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

        bll10 = Bills(billing_ccy='JPY', date_sale=date(year=2020, month=2,
                                                       day=14),
                     date_bill=date(year=2020, month=2, day=16), 
                     status='issued')
        blll6 = BillLines(short_desc='35',
                    long_desc='Perfume bottle',
                    number_of=2,
                    measured_in='box',
                    unit_price=116)
        bll10.lines.append(blll6)
        bll10.add()
        bll10.client = self.clt5

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
                               debcred='Cr',
                               bank_ref='Bankref 11129',
                               creditor_iban='NL08INGB0212952803')
        ia08.client = self.clt2
        db.session.flush()
        parse(self.infile, self.camthandler)
        ia09 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='022221333306999888222200112').first()
        self.assertEqual(ia09.debcred, 'Db', 'No debit entry')

    def test_assign_by_client_ref(self):
        """ If the client reference holds the bill id, we assign """

        parse(self.infile, self.camthandler)
        ia10 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000755').first()
        #print("Bill number " + str(self.bll3.bill_id))
        ia10.client_ref = "Bill number " + str(self.bll3.bill_id)
        db.session.flush()
        ial04 = ia10.find_assignment_targets()
        self.assertIn(self.bll3, ial04, 'Bill is not in targets')

    def test_assign_only_unpaid_by_ref(self):
        """ We only return unpaid assignment candidates """

        parse(self.infile, self.camthandler)
        ia11 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000187763').first()
        ia11.client_ref = "Bill number " + str(self.bll2.bill_id)
        db.session.flush()
        ial05 = ia11.find_assignment_targets()
        self.assertNotIn(self.bll2, ial05, 'Bill is in targets')

    def test_attach_client_triggers_assignment(self):
        """ When attaching a new client, assignment is tried """

        ia18 = IncomingAmounts(payment_ccy='USD',
                               payment_amount=48856,
                               creditor_iban= 'NL08INGB0212952123',
                               client_name='F.K. Giropal')
        ia18.add()
        bll9 = Bills(billing_ccy='USD', date_sale=date(year=2020, month=2,
                                                       day=16),
                     date_bill=date(year=2020, month=2, day=16), 
                     status='issued')
        bll9.client = self.clt2
        blll5 = BillLines(short_desc='phi', number_of=2,
                          unit_price=1300)
        bll9.add()
        blll5.bill = bll9
        db.session.flush()
        ia18.change_client(self.clt2)
        db.session.flush()
        aa05 = db.session.query(AssignedAmounts).filter_by(bill=bll9).first()
        self.assertTrue(aa05, 'No assignement took place')

    def test_find_assignment_target_by_client_name(self):
        """ We can find assignment targets by (part of) client name """

        bill_list = IncomingAmounts.get_bill_targets(name="Auber")
        self.assertIn(self.bll4, bill_list, "Expected bill not returned")

    def test_find_bills_but_none_found(self):
        """ If we enter a name and no bill found, we get an empty list """

        bill_list = IncomingAmounts.get_bill_targets(name="Knir")
        self.assertEqual(bill_list, [], "No empty list returned")

    def test_search_string_too_short_fails(self):
        """ Passing a search string that is very short, fails. """

        with self.assertRaises(ValueError):
            bill_list = IncomingAmounts.get_bill_targets(name="Kr")

    def test_find_by_number(self):
        """ We can find bills for a client by client number """

        client_id = self.clt5.id
        bill_list = IncomingAmounts.get_bill_targets(client_id=client_id)
        self.assertTrue(bill_list, "Bill list empty")
        self.assertIn(self.bll4, bill_list, "Expected bill not returned")

    def test_invalid_client_number_returns_empty_list(self):
        """ When requesting an non-existing client number fails """

        bill_list = IncomingAmounts.get_bill_targets(client_id=1)
        self.assertEqual(bill_list, [], "Returned nhot an empty ;ist")

    def test_find_by_bank_account(self):
        """ We can find bills by bank account number  """

        iban = 'NL95INGB0696154021'
        bill_list = IncomingAmounts.get_bill_targets(account_nr=iban)

    def test_pass_no_id_fails(self):
        """ If we pass no parameters, finding bills fails """

        with self.assertRaises(ValueError):
            bill_list = IncomingAmounts.get_bill_targets()

    def test_find_payment_for_reversal(self):
        """ Find the payment that is to be reversed """

        parse(self.infile, self.camthandler)
        ia57 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=56797,
                               debcred="Db",
                               creditor_iban='NL08INGB0212170098')
        ia57.add()
        db.session.flush()
        ial10 = IncomingAmounts.find_reversible_payments(ia57)
        ia61 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref="011111333306999888000000755").first()
        self.assertIn(ia61, ial10, "Reversible item not found")

    def test_list_items_must_be_credit(self):
        """ Only credit items must be returned """

        parse(self.infile, self.camthandler)
        ia60 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=13400,
                               debcred="Db",
                               creditor_iban= 'NL08INGB0212952803')
        ia60.add()
        db.session.flush()
        ial12 = IncomingAmounts.find_reversible_payments(ia60)
        for payment in ial12:
            self.assertEqual(payment.debcred, "Cr", "Debit item in list")
 

    def test_payment_must_have_same_amount(self):
        """ A payment is only reversible if the amount is equal  """

        parse(self.infile, self.camthandler)
        ia58 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=56797,
                               debcred="Db",
                               creditor_iban= 'NL08INGB0212170098')
        ia58.add()
        ia59 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=13100,
                               debcred="Db",
                               creditor_iban= 'NL08INGB0212170098')
        ia59.add()
        db.session.flush()
        ia62 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref="011111333306999888000000755").first()
        ial11 = IncomingAmounts.find_reversible_payments(ia58)
        self.assertIn(ia62, ial11, "Reversible item not found")
        ial12 = IncomingAmounts.find_reversible_payments(ia59)
        self.assertNotIn(ia59, ial12, "The payment was returned wrongly")

    def test_item_must_have_same_currency(self):
        """ To select a payment as candidate, currencies must be the same """

        parse(self.infile, self.camthandler)
        ia63 = IncomingAmounts(payment_ccy='GBP',
                               payment_amount=56797,
                               debcred="Db",
                               creditor_iban= 'NL08INGB0212170098')
        ia63.add()
        db.session.flush()
        ia64 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref="011111333306999888000000755").first()
        ial12 = IncomingAmounts.find_reversible_payments(ia63)
        self.assertNotIn(ia64, ial12, "Reversible item other ccy returned")


class TestAssignToPayment(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        self.ia38 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=4456,
                               creditor_iban= 'NL08INGB0212977892',
                               client_name='T. Sommerzeel',
                               our_ref='Ref TB22',
                               bank_ref='11987')
        self.ia38.add()
        self.ia39 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=0,
                               client_name='T. den Oude',
                               our_ref='Snn34')
        self.ia39.add()
        db.session.flush()
        self.camthandler = CAMT53Handler()
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)
        self.infile = open('debttests/SEPA transacties test assignment.xml', 'r')
        parse(self.infile, self.camthandler)

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
        db.session.query(AssignedAmounts).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_shows_payment(self):
        """ The assignment page shows a payment for a reference """

        ia34 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=88756,
                               creditor_iban= 'NL08INGB0212952188',
                               client_name='F.K. Grondeel',
                               our_ref='ref2286')
        ia34.add()
        db.session.flush()
        ia34_id = ia34.id
        ial06 = IncomingAmounts.get_target_payments(our_ref='2286')
        self.assertIn(ia34, ial06, "Payment not found")

    def test_no_payment_returns_empty_list(self):
        """ A selector that returns no payments, gets an empty list """

        ia35 = IncomingAmounts(payment_ccy='GBP',
                               payment_amount=88735,
                               creditor_iban= 'NL08INGB0212952186',
                               client_name='F.K. Nakkisch',
                               our_ref='ref227789')
        ia35.add()
        db.session.flush()
        ia35_id = ia35.id
        ial07 = IncomingAmounts.get_target_payments(our_ref='2286')
        self.assertFalse(ial07, "Payment found, not there")

    def test_empty_search_criterion_fails(self):
        """ Not passing criterion fails """

        ia36 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=665456,
                               creditor_iban= 'NL08INGB0212952657',
                               client_name='F.J. Waterbak',
                               our_ref='&&9098')
        ia36.add()
        db.session.flush()
        ia36_id = ia36.id
        with self.assertRaises(ValueError):
            ial08 = IncomingAmounts.get_target_payments()

    def test_bank_reference_searchable(self):
        """ We can search for a bank reference """

        ia37 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=866856,
                               creditor_iban= 'NL08INGB0212977654',
                               client_name='T. Immerzeel',
                               our_ref='Some text',
                               bank_ref='referentie text')
        ia37.add()
        db.session.flush()
        ia37_id = ia37.id
        ial09 = IncomingAmounts.get_target_payments(bank_ref='text')
        self.assertIn(ia37, ial09, "Payment not found")

    def test_assign_to_payment(self):
        """ We can assign to a payment """

        aa14 = AssignedAmounts(ccy='EUR',
                               amount_assigned=4456)
        aa14.from_amount = self.ia38
        aa14.to_amount = self.ia39
        db.session.flush()
        self.assertIn(aa14, self.ia39.from_amt, 
                         "Back link not set")
        self.assertIn(aa14, self.ia38.used_in, 
                         "Forward link not set")

    def test_assign_to_payment_method(self):
        """ We can assign to amount through a method """

        aa15 = self.ia38.assign_to_amount(self.ia39)
        db.session.flush()
        aa31 = AssignedAmounts.get_by_id(aa15.id)
        self.assertEqual(aa15.amount_assigned, self.ia38.payment_amount,
                         "No assignment found")
        self.assertTrue(aa31, "Not able to fetch assigned amount")

    def test_cannot_assign_zero_amount(self):
        """ We cannot assign if from amount is zero  """

        with self.assertRaises(ValueError):
            aa16 = self.ia39.assign_to_amount(self.ia38)

    def test_assigning_update_to_amount(self):
        """ Assign to amount is updated with amount """

        aa16 = self.ia38.assign_to_amount(self.ia39)
        self.assertEqual(aa16.amount_assigned, self.ia39.payment_amount,
                         "To amount not correct")
        self.assertTrue(self.ia38.fully_assigned,
                        "From amount not set to assigned")

    def test_assign_remaining_amount_to_other(self):
        """ Assign the remaining of an amount to another """

        aa17 = AssignedAmounts(ccy='EUR',
                               amount_assigned=22)
        aa17.from_amount = self.ia38
        db.session.flush()
        aa18 = self.ia38.assign_to_amount(self.ia39)
        self.assertEqual(self.ia39.payment_amount, 4434,
                         "To amount not correct")
        self.assertEqual(aa18.to_amount, self.ia39, 
                         "Assignment no /incorrect to amount")

    def test_assign_to_amount_other_currency(self):
        """ Assign an amount to an amount in another currency """

        ia40 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=0)
        ia40.add()
        db.session.flush()
        aa19 = self.ia38.assign_to_amount(ia40, other_ccy=ia40.payment_ccy,
                                          other_amount=1365)
        self.assertEqual(ia40.payment_amount, 1365,
                         "Amount not properly converted")
        self.assertEqual(aa19.amount_assigned, self.ia38.payment_amount,
                         "Wrong amount assigned")

    def test_assign_different_ccy_no_amount_fails(self):
        """ Need to pass in "other amount"to assign to different currency """

        ia50 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=0)
        ia50.add()
        db.session.flush()
        with self.assertRaises(ValueError):
            aa23 = self.ia38.assign_to_amount(ia50)


    def test_assign_more_than_remainder_fails(self):
        """ If we assign an unassigned amount of zero, it fails """

        ia48 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        aa22 = AssignedAmounts(ccy='JPY',
                               amount_assigned=1880)
        aa22.from_amount = ia48
        ia49 = IncomingAmounts(payment_ccy="JPY",
                               payment_amount=0)
        ia48.assign_to_amount(ia49)
        db.session.flush()
        with self.assertRaises(ValueError):
            ia48.assign_to_amount(ia49)

    def test_reverse_open_payment(self):
        """ Reverse a payment not yet assigned """

        ia65 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=12500,
                               debcred='Cr',
                               creditor_iban= 'NL08INGB0212952803',
                               client_name='ING Testrekening',
                               our_ref='Some text',
                               bank_ref='Terugboeking betaling')
        ia66 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='022221333306999888222200112').first()
        db.session.flush()
        ia65.assign_reversal_to_payment(ia66)
        self.assertEqual(ia65.fully_assigned, True, "Reversal not assigned")
        self.assertTrue(ia66.fully_assigned, "Reversed item still available")

    def test_reverse_if_one_eligible_target(self):
        """ If one target thatcan be reversed, do it """

        ia67 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=56797,
                               debcred='Db',
                               creditor_iban= 'NL08INGB0212170098',
                               client_name='Aquamarijn',
                               our_ref='Some text',
                               bank_ref='Terugboeking betaling')
        ia67.add()
        ia68 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000755').first()
        db.session.flush()
        ia67.reverse_if_one_target()
        self.assertTrue(ia68.fully_assigned, "Reversed item still available")

    def test_reverse_fails_if_wrong_ccy(self):
        """ Trying to reverse a payment for another currency fails """

        ia69 = IncomingAmounts(payment_ccy='GBP',
                               payment_amount=12500,
                               debcred='Db',
                               creditor_iban= 'NL08INGB0212952803',
                               client_name='ING Testrekening',
                               our_ref='Reverse British Pounds',
                               bank_ref='Terugboeking betaling')
        ia70 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='022221333306999888222200112').first()
        db.session.flush()
        with  self.assertRaises(ValueError):
            ia69.assign_reversal_to_payment(ia70)

    def test_reverse_fails_if_wrong_amount(self):
        """ Trying to reverse a payment for another currency fails """

        ia71 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=12530,
                               debcred='Db',
                               creditor_iban= 'NL08INGB0212952803',
                               client_name='ING Testrekening',
                               our_ref='Reverse British Pounds',
                               bank_ref='Terugboeking betaling')
        ia72 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='022221333306999888222200112').first()
        db.session.flush()
        with  self.assertRaises(ValueError):
            ia71.assign_reversal_to_payment(ia72)

    def test_reverse_fails_if_same_debcred(self):
        """ Trying to reverse a payment with credit amount fails """

        ia76 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=12500,
                               debcred='Db',
                               creditor_iban= 'NL08INGB0212952803',
                               client_name='ING Testrekening',
                               our_ref='Reverse British Pounds',
                               bank_ref='Terugboeking betaling')
        ia77 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='022221333306999888222200112').first()
        db.session.flush()
        with  self.assertRaises(ValueError):
            ia76.assign_reversal_to_payment(ia77)

    def test_reverse_fails_if_assigned(self):
        """ Trying to reverse a payment for another currency fails """

        ia73 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=12500,
                               debcred='Cr',
                               creditor_iban= 'NL08INGB0212952803',
                               client_name='ING Testrekening',
                               our_ref='Reverse British Pounds',
                               bank_ref='Terugboeking betaling')
        ia74 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='022221333306999888222200112').first()
        ia75 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=0,
                               debcred='Cr')
        db.session.flush()
        ia74.assign_to_amount(ia75)
        db.session.flush()
        with  self.assertRaises(ValueError):
            ia73.assign_reversal_to_payment(ia74)


    def test_assign_reversal_cannot_be_reversed(self):
        """ An assignment of a reversal cannot be reversed """

        #ia107 = IncomingAmounts(payment_ccy='EUR',
                               #payment_amount=12500,
                               #debcred='Cr',
                               #creditor_iban= 'NL08INGB0212952803',
                               #client_name='ING Testrekening',
                               #our_ref='Reverse fail',
                               #bank_ref='Terugboeking betaling')
        ia108 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='021514017743280167000000001').first()
        ia109 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=0,
                               debcred='Cr',
                               rvslind=True)
        db.session.flush()
        aa33 = ia108.assign_to_amount(ia109)
        db.session.flush()
        with  self.assertRaises(ValueError):
            ia108.reverse_assignment(aa33)


class TestAssignmentReversal(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        self.ia95 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=4456,
                               creditor_iban= 'NL08INGB0212977892',
                               client_name='T. Sommerzeel',
                               our_ref='Ref TB22',
                               bank_ref='11987')
        self.ia95.add()
        self.ia96 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=0,
                               client_name='T. den Oude',
                               our_ref='Snn34')
        self.ia96.add()
        db.session.flush()
        self.camthandler = CAMT53Handler()
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)
        self.infile = open('debttests/SEPA transacties test assignment.xml', 'r')
        parse(self.infile, self.camthandler)

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
        db.session.query(AssignedAmounts).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_get_reversable_assignments(self):
        """ Get assignments for the payment whose assignment(s) to reverse """

        ia97 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()

        ia97.assign_amount()
        db.session.commit()

        aa24 = db.session.query(AssignedAmounts).\
            filter_by(from_amount=ia97).first()
        self.assertIn(aa24, ia97.used_in, "Assigned amount not in list")

    def test_get_reversable_assignments_through_function(self):
        """ Get assignments for the payment whose assignment(s) to reverse """

        ia98 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()

        ia98.assign_amount()
        db.session.commit()

        al01 = ia98.list_assignments()
        al02 = ia98.used_in

        for assigned in al01:
            self.assertIn(assigned, al02, "Not all returned in db")
        for assigned in al02:
            self.assertIn(assigned, al01, "Not all in returned list")

    def test_return_more_assignments(self):
        """ Return more than one assignment """

        ia99 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=2535,
                               creditor_iban= 'NL08INGB0212977817',
                               client_name='T. Heerziel',
                               our_ref='Ref 2assi',
                               bank_ref='11987')
        ia99.add()
        ia100 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=47)
        ia100.add()
        ia101 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=0)
        ia101.add()
        db.session.flush()
        aa25 = ia99.assign_to_bill(self.bll4)
        aa26 = ia99.assign_to_amount(ia101)
        db.session.flush()
        al03 = ia99.list_assignments()
        self.assertEqual(len(al03), 2, "Too many/little amounts returned")

    def test_reverse_assignment(self):
        """ Reversing assignment logically deletes assignment row """

        ia102 = IncomingAmounts(payment_ccy='JPY',
                                payment_amount=2535,
                                creditor_iban= 'NL08INGB0212977817',
                                client_name='T. Heerziel',
                                our_ref='Ref 2assi',
                                bank_ref='11987')
        ia102.add()
        db.session.flush()
        aa27 = ia102.assign_to_bill(self.bll4)
        db.session.flush()
        self.assertEqual(self.bll4.status, 'paid', "The status is not paid")
        ia102.reverse_assignment(aa27)
        db.session.flush()
        al04 = db.session.query(AssignedAmounts).filter_by(from_amount=ia102).all()
        self.assertTrue(al04[0].reversed, "Assigned amount not reversed")
        self.assertNotEqual(self.bll4.status, 'paid',
                            "The status of the bill is still paid")
        self.assertEqual(self.bll4.total(), 1880, "The bill has wrong debt")

    def test_reverse_assignment_amount(self):
        """ Reverse an assignment to an amount """

        ia103 = IncomingAmounts(payment_ccy='JPY',
                                payment_amount=2535,
                                creditor_iban= 'NL08INGB0212977817',
                                client_name='T. Heerziel',
                                our_ref='Ref 2assi',
                                bank_ref='11987')
        ia103.add()
        ia104 = IncomingAmounts(payment_ccy='JPY',
                                payment_amount=0)
        ia104.add()
        db.session.flush()
        aa28 = ia103.assign_to_amount(ia104)
        db.session.flush()
        ia103.reverse_assignment(aa28)
        al05 = db.session.query(AssignedAmounts).filter_by(from_amount=ia103).all()
        self.assertEqual(ia104.payment_amount, 0, "Amount not zero after reversal")
        self.assertFalse(ia103.fully_assigned, "Fully assigned not reversed")
        self.assertTrue(aa28.reversed, "Assignment not set to reversed")

    def test_reversal_not_in_assignments(self):
        """ After reversal, an assignment does not appear in the list """

        ia103 = IncomingAmounts(payment_ccy='JPY',
                                payment_amount=2535,
                                creditor_iban= 'NL08INGB0212977817',
                                client_name='T. Heerziel',
                                our_ref='Ref 2assi',
                                bank_ref='11987')
        ia103.add()
        ia104 = IncomingAmounts(payment_ccy='JPY',
                                payment_amount=0)
        ia104.add()
        db.session.flush()
        aa28 = ia103.assign_to_amount(ia104)
        db.session.flush()
        ia103.reverse_assignment(aa28)
        al05 = ia103.list_assignments()
        self.assertNotIn(aa28, al05, "Assigned amount in list after reversal")


    def test_reversal_creates_accounting(self):
        """ An assignment reversal leads to accounting """

        ia105 = IncomingAmounts(payment_ccy='JPY',
                                payment_amount=2235,
                                creditor_iban= 'NL08INGB0212977817',
                                client_name='T. Temin',
                                our_ref='Ref 3assi',
                                bank_ref='11989')
        ia105.add()
        ia106 = IncomingAmounts(payment_ccy='JPY',
                                payment_amount=0)
        ia106.add()
        db.session.flush()
        aa32 = ia105.assign_to_amount(ia106)
        db.session.flush()
        ia105.reverse_assignment(aa32)
        ara01 = AssignmentReversalAccounting(aa32)
        self.assertEqual(ara01["journal"]["extkey"][:13], "assignreverse",
                         "Incorrect external key")
        self.assertEqual(len(ara01["journal"]["postings"]), 2, "Wrong number of postings")


class TestAssignmentReversalTransactions(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        self.ia38 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=4456,
                               creditor_iban= 'NL08INGB0212977892',
                               client_name='T. Sommerzeel',
                               our_ref='Ref TB22',
                               bank_ref='11987')
        self.ia38.add()
        self.ia39 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=0,
                               client_name='T. den Oude',
                               our_ref='Snn34')
        self.ia39.add()
        db.session.flush()
        self.camthandler = CAMT53Handler()
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)
        self.infile = open('debttests/SEPA transacties test assignment.xml', 'r')
        parse(self.infile, self.camthandler)
        self.app = app.test_client()
        self.app.testing = True

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
        db.session.query(AssignedAmounts).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_get_one_assignment(self):
        """ Get one assignment if there is only one """

        self.ia38.assign_to_amount(self.ia39)
        ia39_id = self.ia39.id
        ia38_id = self.ia38.id
        db.session.commit()
        rv = self.app.get("/assignment/" + str(ia38_id) + "/reverse")
        self.assertIn(str(ia39_id).encode(), rv.data,
                      "Assigned not shown")

    def test_get_more_assigned(self):
        """ With more assignments, we see all """

        bl01 = Bills(date_sale=date(year=2021, month=6, day=18),
                          date_bill=date(year=2021, month=6, day=19),
                          billing_ccy='EUR',
                          status='issued')
        bl01.add()
        bll13 = BillLines(short_desc='Spoon', unit_price=18, number_of=2)
        bl01.lines.append(bll13)
        bl02 = Bills(date_sale=date(year=2021, month=7, day=8),
                          date_bill=date(year=2021, month=7, day=9),
                          billing_ccy='EUR',
                          status='issued')
        bl02.add()
        bll14 = BillLines(short_desc='Bucket', unit_price=4, number_of=1)
        bl02.lines.append(bll14)
        ia38_id = self.ia38.id
        db.session.flush()
        aa28 = self.ia38.assign_to_bill(bl01)
        aa29 = self.ia38.assign_to_bill(bl02)
        bl01_id = bl01.bill_id
        bl02_id = bl02.bill_id
        db.session.commit()
        aa28_id = aa28.id
        aa29_id = aa29.id
        rv = self.app.get("/assignment/" + str(ia38_id) + "/reverse")
        self.assertIn(str(bl01_id).encode(), rv.data,
                      "First assigned not shown")
        self.assertIn(str(bl02_id).encode(), rv.data,
                      "Second assigned not shown")
        self.assertIn(str(aa28_id).encode(), rv.data,
                      "First assignment id not shown")
        self.assertIn(str(aa29_id).encode(), rv.data,
                      "Second assignment id not shown")

    def test_reverse_assign_non_existing_payment_fails(self):
        """ Reversing assignments for non existing payment fails """

        rv = self.app.get("/assignment/1/reverse")
        self.assertEqual("404 NOT FOUND", rv.status, 
                         "Assignment reverse returns wrong status")
        self.assertIn(b"No payment", rv.data, "Message not correct")

    def test_reverse_assignement(self):
        """ Reverse one assignment """

        self.ia38.assign_to_amount(self.ia39)
        ia39_id = self.ia39.id
        ia38_id = self.ia38.id
        db.session.commit()
        ia38_assignment = self.ia38.used_in[0]
        ad1 = {"assign" +  str(ia38_assignment.id) : str(ia38_assignment.id)}
        rv=self.app.post("/assignment/" + str(ia38_id) + "/reverse",
                         data=ImmutableMultiDict(ad1))
        aa30 = db.session.query(AssignedAmounts).filter_by(id=ia38_assignment.id)\
                    .first()
        self.assertTrue(aa30.reversed, "Assignment still exists")

    def test_post_assignment_reverse_non_existing_fails(self):
        """ Posting an invalid assignment reference fails

        This also works when the assignment number exists, but is for another
        payment. No separate test
        """

        ad1 = {"assign1" : "1"}
        rv=self.app.post("/assignment/" + str(self.ia38.id) + "/reverse",
                         data=ImmutableMultiDict(ad1))
        self.assertIn("404", rv.status, "Non existing assignment not refused")


class TestPaymentAccounting(unittest.TestCase):

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
        parse(self.infile, self.camthandler)


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
        db.session.query(AssignedAmounts).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_create_journal(self):
        """ From a payment a journal can be created """

        ia29 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        pa01 = PaymentAccounting(ia29)
        self.assertTrue(pa01["journal"], "No valid journal created")

    def test_journal_has_id(self):
        """ Generated accounting contains the key """

        ia30 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        pa02 = PaymentAccounting(ia30)
        self.assertEqual(pa02["journal"]["extkey"], "payment" + str(ia30.id),
                         "No valid external key in payment")

    def test_payment_reversal_journal_id(self):
        """ A payment reversal makes accounting with correct id """

        ia94 = db.session.query(IncomingAmounts).filter_by(bank_ref='021514017743280167000000001').first()
        pra01 = PaymentReversalAccounting(ia94)
        self.assertEqual(pra01["journal"]["extkey"], "paymentreversal"
                         + str(ia94.id), "No valid external key in payment")

    def test_no_accounting_for_zero_payment(self):
        """ If the payment amount is zero, refuse accounting """

        ia31 = IncomingAmounts(payment_ccy="USD",
                               payment_amount=0,
                               creditor_iban= 'NL08INGB0212952123',
                               client_name='F.L. Snazzyclient')
        with self.assertRaises(ValueError):
            pa03 = PaymentAccounting(ia31)

    def test_payment_accounting_correct_posts(self):
        """ The correct posting types are created for correct amounts """

        ia32 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000755').first()
        pa04 = PaymentAccounting(ia32)
        postings = pa04["journal"]["postings"]
        accounts = [account for posting in postings for k, account in posting.items() if k == 'account' ]
        self.assertIn("debt", accounts, "No debt posting")
        self.assertIn("receipts", accounts, "No receipt posting")
        self.assertEqual(postings[0]["amount"], str(ia32.payment_amount),
                         "Incorrect amount in posting")
        self.assertEqual(postings[0]["currency"], str(ia32.payment_ccy),
                         "Incorrect currency in posting")

    def test_assign_to_bill_accounting(self):
        """ Make accounting for assigning to a bill """

        ia33 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()

        ia33.assign_amount()
        db.session.commit()

        aa13 = db.session.query(AssignedAmounts).\
            filter_by(from_amount=ia33).first()
        aac01 = AssignmentAccounting(aa13)

        aac01_extkey = aac01["journal"]["extkey"]
        self.assertEqual(aac01_extkey, "assign" + str(aa13.id),
                         "Incorrect journal key")
        postings = aac01["journal"]["postings"]
        accounts = [account for posting in postings for k, account in posting.items() if k == 'account' ]
        self.assertIn("income", accounts, "No debt posting")
        self.assertIn("receipts", accounts, "No receipt posting")

    def test_assign_to_amount_accounting(self):
        """ Make accounting to assign to another amount """

        ia34 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        ia35 = IncomingAmounts(payment_ccy=ia34.payment_ccy,
                               payment_amount=0)
        db.session.flush()
        aa20 = ia34.assign_to_amount(ia35)
        db.session.flush()
        aac02 = AssignmentAccounting(aa20)
        postings = aac02["journal"]["postings"]
        accounts = [account for posting in postings 
                    for k, account in posting.items() if k == 'account' ]
        self.assertIn("receipts", accounts, "No receipt posting")
        self.assertNotIn("income", accounts, "unexpected income posting")
        self.assertEqual(len(postings), 2, "Incorrect number of postings")

    def test_assign_other_currency_accounting(self):
        """ Make accounting for change of currency  """

        ia36 = db.session.query(IncomingAmounts).\
            filter_by(bank_ref='011111333306999888000000008').first()
        ia37 = IncomingAmounts(payment_ccy="EUR",
                               payment_amount=0)
        db.session.flush()
        aa21 = ia36.assign_to_amount(ia37, other_ccy="EUR",
                                     other_amount=17820)
        db.session.flush()
        aac03 = AssignmentAccounting(aa21)
        postings = aac03["journal"]["postings"]
        accounts = [account for posting in postings 
                    for k, account in posting.items() if k == 'account' ]
        self.assertIn("receipts", accounts, "No receipt posting")
        self.assertNotIn("income", accounts, "unexpected income posting")
        self.assertIn("convertccy", accounts, "Conversion postings missing")
        self.assertEqual(len(postings), 4, "Incorrect number of postings")


class TestPaymentTransactions(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        self.ia11 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=1330)
        self.ia11.add()
        db.session.flush()
        self.camthandler = CAMT53Handler()
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)
        self.infile = open('debttests/SEPA transacties test assignment.xml', 'r')
        parse(self.infile, self.camthandler)
        db.session.commit()
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):

        db.session.rollback()
        self.infile.close()
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.query(AmountQueued).delete()
        db.session.query(AssignedAmounts).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_get_payment(self):
        """ We can retrieve a payment """

        ia12 = db.session.query(IncomingAmounts).first()
        rv = self.app.get('/payment/' + str(ia12.id))
        self.assertEqual(rv.status_code, 200, 'Not OK: find payment')

    def test_get_invalid_fails(self):
        """ Get a Not Found when retrieving non-existent payment """

        rv = self.app.get('/payment/1')
        self.assertEqual(rv.status_code, 404, 'Not Found not returned from find payment')

    def test_put_payment(self):
        """ Create a new payment """

        self.app.post('/payment/new', data={'payment_ccy':'EUR',
                                           'payment_amount':'567,99',
                                           'debcred':'Cr',
                                           'value_date':'17-12-2020'})
        ia13 = db.session.query(IncomingAmounts).\
            filter_by(payment_amount=56799).first()
        self.assertEqual(ia13.value_date, parser.parse('17-12-2020'),
                         'Incorrect date')
        self.assertEqual(ia13.payment_ccy, 'EUR', 'Currency incorrect')


    def test_attach_client(self):
        """ Attach a client to a payment """

        ia11_id = self.ia11.id
        clt3_id = self.clt3.id
        rv = self.app.post('/payment/attach', data={'payment_id':
                                                    str(self.ia11.id),
                                                    'client_id':
                                                    str(clt3_id)},
                            follow_redirects=True)
        ia14 = db.session.query(IncomingAmounts).filter_by(id=ia11_id)\
            .first()
        #print(rv.status_code)
        self.assertEqual(ia14.client.id, clt3_id, "Client not attached")

    def test_attach_client_no_payment_fails(self):
        """ When we try attaching a client to no payment, it fails """

        clt3_id = self.clt3.id
        rv = self.app.post('/payment/attach', data={'payment_id':
                                                    None,
                                                    'client_id':
                                                    str(clt3_id)},
                            follow_redirects=True)
        self.assertIn(b'No payment', rv.data, 'Message missing')

    def test_attach_invalid_client_fails(self):
        """ When we try attaching a client to no payment, it fails """

        ia11_id = self.ia11.id
        rv = self.app.post('/payment/attach', data={'payment_id':
                                                    ia11_id,
                                                    'client_id':
                                                    1},
                            follow_redirects=True)
        self.assertIn(b'No client', rv.data, 'Message missing')

    def test_cannot_attach_client_to_assigned(self):
        """ If a payment is assigned to, we cannot change client """

        bll3_id = self.bll3.bill_id
        ia11_id = self.ia11.id
        client_id = self.clt3.id
        aa03 = AssignedAmounts(ccy='EUR', amount_assigned=3)
        aa03.from_amount=self.ia11
        db.session.flush()
        rv = self.app.post('/payment/attach', data={'payment_id':
                                                    ia11_id,
                                                    'client_id':
                                                    client_id},
                            follow_redirects=True)
        self.assertIn(b'Cannot attach', rv.data,
                      'Attached to payment with assigned amount')

    def test_invalid_ccy_error(self):
        """ Specifying an invalid currency gives an error """

        rv = self.app.post('/payment/new', data={'payment_ccy':'CBY',
                                            'payment_amount':'567,99',
                                            'debcred':'Cr',
                                            'value_date':'17-12-2020'})
        self.assertIn(b'The currency', rv.data,  "Error not on screen")

    def test_assign_to_bill(self):
        """ Assign a payment to a bill """

        ia24 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=1880,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 17))
        ia24.client = self.clt3
        ia24.add()
        db.session.flush()
        bll4_id = self.bll4.bill_id
        routestr = "/payment/assign/" + str(ia24.id) + "/bill/" + str(self.bll4.bill_id)
        rv = self.app.post(routestr)
        self.bll4 = db.session.query(Bills).filter_by(bill_id=bll4_id).first()
        self.assertEqual(self.bll4.status, Bills.PAID, "Bill not assigned")

    def test_amount_has_corrcet_precision(self):
        """ The number of decimals after the decimal separator is correct """

        ia117 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=705,
                               debcred='Cr',
                               value_date=datetime(2022, 3, 17))
        ia117.client = self.clt3
        db.session.flush()
        rv = self.app.get("/payment/" + str(ia117.id))
        self.assertEqual(rv.status_code, 200., "Transaction failed")
        self.assertIn(b"705", rv.data, "Amount not in right format") 

    def test_assign_nonexisting_payment_fails(self):
        """ Getting a non-existing payment to assign fails """

        rv = self.app.get('/payment/assign/1')
        self.assertEqual(rv.status_code, 404,
                         'Not Found not returned from find payment')

    def test_assign_shows_debt_select(self):
        """ When reading the assign page, we are shown the client fields """

        ia26 = IncomingAmounts(payment_ccy='USD',
                               payment_amount=19980,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 16))
        ia26.add()
        db.session.flush()
        rv = self.app.get('/payment/assign/' + str(ia26.id))
        self.assertIn(b"By client", rv.data, 'No client search field')
        self.assertIn(b"find_number", rv.data, 'No client search number field')
        self.assertIn(b"find_bank_account", rv.data,
                      'No client search account field')

    def test_find_by_name(self):
        """ Search bills by name """

        ia27 = IncomingAmounts(payment_ccy='USD',
                               payment_amount=19980,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 16))
        ia27.add()
        db.session.flush()
        qrystring = "?find_name=" + "Aubergine"
        rv = self.app.get('/payment/assign/' + str(ia27.id) + qrystring)
        self.assertIn(b'Aubergine', rv.data, 'Name not in response')

    def test_find_by_client_id(self):
        """ Search bills for a client by number """

        ia28 = IncomingAmounts(payment_ccy='USD',
                               payment_amount=19980,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 16))
        ia28.add()
        db.session.flush()
        qrystring = "?find_number=" + str(self.clt5.id)
        rv = self.app.get('/payment/assign/' + str(ia28.id) + qrystring)
        self.assertIn(b'Aubergine', rv.data, 'Name not in response')

    def test_assign_to_bill_via_screen(self):
        """ The assign payment to bill  """

        bll11 = Bills(billing_ccy='EUR',
                      date_sale=parser.parse("2020-12-24"),
                      date_bill=parser.parse("2020-12-28"),
                      status="issued",
                      client=self.clt3)
        blll7 = BillLines(short_desc="ks",
                          long_desc="Korte Steel",
                          unit_price=1200,
                          bill=bll11)
        bll11.add()
        db.session.commit()
        bll11_id = bll11.bill_id
        rv = self.app.post("/payment/assign/" + str(self.ia11.id) +
                           "/bill/" + str(bll11.bill_id),
                           follow_redirects=True)
        bll12 = db.session.query(Bills).filter_by(bill_id=bll11_id).\
            first()
        self.assertTrue(bll12, "No bill with id {}".format(bll11_id))
        self.assertEqual(bll12.status, "paid", "bill not paid")


class TestPaymentAssignToPayment(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        self.ia11 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=1330)
        self.ia11.add()
        db.session.flush()
        self.camthandler = CAMT53Handler()
        self.parser = make_parser()
        self.parser.setContentHandler(self.camthandler)
        self.infile = open('debttests/SEPA transacties test assignment.xml', 'r')
        parse(self.infile, self.camthandler)
        db.session.commit()
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):

        db.session.rollback()
        self.infile.close()
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.query(AmountQueued).delete()
        db.session.query(AssignedAmounts).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_put_selection(self):
        """ Get assignment page with selection by reference of payments """

        ia41 = db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000019').first()
        qrystring="?find_our_ref=&find_bank_ref=000008&search_payment=Find+payment"
        rv = self.app.get("/payment/assign/" + str(ia41.id) +
                          qrystring,
                          follow_redirects=True)
        self.assertIn(b"1.880" , rv.data, "Amount not in response")

    def test_put_selection_by_account(self):
        """ Get assignment page with search of bills by bank account """

        ia42 = db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000019').first()
        bill_list = Bills.bills_for_IBAN('NL76INGB0594788005')        
        qrystring = "?find_name=&find_number=&find_bank_account=NL76INGB0594788005&search_client=Find+client+debt"
        rv = self.app.get("/payment/assign/" + str(ia42.id) +
                          qrystring,
                          follow_redirects=True)
        self.assertIn(b"1.880" , rv.data, "Amount not in response")

    def test_search_string_for_account_returned(self):
        """ If we search for a bill, the search string is returned """

        ia43 = db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000019').first()
        bill_list = Bills.bills_for_IBAN('NL76INGB0594788005')        
        qrystring = "?find_name=&find_number=&find_bank_account=NL76INGB0594788005&search_client=Find+client+debt"
        rv = self.app.get("/payment/assign/" + str(ia43.id) +
                          qrystring,
                          follow_redirects=True)
        self.assertIn(b"NL76INGB0594788005" ,
                      rv.data, "Search string not in response")
        self.assertIn(b"No bill found",
                      rv.data, "No message saying no bill found")

    def test_ref_search_returned(self):
        """ If we search for a reference, the search string is returned """

        ia44 = db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000187763').first()
        qrystring = "?find_our_ref=watty&find_bank_ref=&search_payment=Find+payment"
        rv = self.app.get("/payment/assign/" + str(ia44.id) +
                          qrystring,
                          follow_redirects=True)
        self.assertIn(b"watty" ,
                      rv.data, "Search string not in response")
        self.assertIn(b"No payment found",
                      rv.data, "No message saying nothing found")

    def test_assign_to_same_ccy_amount(self):
        """ Assign an amount to another amount in the same ccy """

        ia45 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=0,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 16))
        ia45.add()
        db.session.commit()
        ia45_id = ia45.id
        ia46 = db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000019').first()
        ia46_id = ia46.id

        rv = self.app.post("/payment/assign/" + str(ia46.id) + "/payment/"
                           + str(ia45.id))

        ia45 = db.session.query(IncomingAmounts).filter_by(id=ia45_id).first()
        ia47 =db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000019').first()
        self.assertEqual(ia47.payment_amount, ia45.payment_amount,
                         "Amount not updated")
        ia46 = db.session.query(IncomingAmounts).filter_by(id=ia46_id).first()
        self.assertTrue(ia46.used_in, "No assignment found")

    def test_assign_to_other_ccy_amount(self):
        """ We can assign to an amount in another currency """

        ia51 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=0,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 16))
        ia51.add()
        db.session.flush()
        ia51_id = ia51.id
        ia52 = db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000019').first()
        ia52_id = ia52.id

        qrystring = "?other_ccy=" + ia51.payment_ccy + "&other_amount=5562"
        rv = self.app.post("/payment/assign/" + str(ia52.id) + "/payment/"
                           + str(ia51.id) + qrystring)

        ia51 = db.session.query(IncomingAmounts).filter_by(id=ia51_id).first()
        ia52 =db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000019').first()
        self.assertEqual(ia51.payment_amount, 5562, "Amount to incorrect")

    def test_wrong_other_ccy_fails(self):
        """ Other currency is incorrect produces a 400 error """

        ia53 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=0,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 16))
        ia53.add()
        db.session.flush()
        ia53_id = ia53.id
        ia54 = db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000019').first()
        ia54_id = ia54.id

        qrystring = "?other_ccy=GBP&other_amount=5562"
        rv = self.app.post("/payment/assign/" + str(ia54.id) + "/payment/"
                           + str(ia53.id) + qrystring)
        self.assertEqual(rv.status_code, 400, "No status 400")

    def test_other_amount_no_ccy_fails(self):
        """ Pass an other amount but no currency fails """

        ia55 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=0,
                               debcred='Cr',
                               value_date=datetime(2021, 1, 16))
        ia55.add()
        db.session.flush()
        ia55_id = ia55.id
        ia56 = db.session.query(IncomingAmounts).filter_by(bank_ref='011111333306999888000000019').first()
        ia56_id = ia56.id

        qrystring = "?other_amount=5562"
        rv = self.app.post("/payment/assign/" + str(ia56.id) + "/payment/"
                           + str(ia55.id) + qrystring)
        self.assertEqual(rv.status_code, 400, "No status 400")


class TestPaymentReversal(unittest.TestCase):

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
        parse(self.infile, self.camthandler)
        db.session.commit()
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):

        db.session.rollback()
        self.infile.close()
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.query(AmountQueued).delete()
        db.session.query(AssignedAmounts).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_can_request_reversal(self):
        """ We can request reversal page with a reversal """

        ia78 = db.session.query(IncomingAmounts).filter_by(bank_ref='021514017743280167000000001').first()
        ia78_id_str = str(ia78.id)
        rv = self.app.get("/payment/reverse/" + ia78_id_str)
        self.assertEqual(rv.status_code, 200, "Get reversal failed")
        self.assertIn(b'ING Testrekening', rv.data,
                      "Client name not shown")

    def test_reversal_no_payment_fails(self):
        """ Trying to reverse a non-existing payment fails """

        rv = self.app.get("/payment/reverse/1")
        self.assertEqual(rv.status_code, 404,
                         "Get reversal id 1 wrong status code")

    def test_reversal_indicator_set(self):
        """ Trying to get reversal when it is a payment fails """

        ia79 = db.session.query(IncomingAmounts).filter_by(bank_ref='022221333306999888222200112').first()
        ia79_id_str = str(ia79.id)
        rv = self.app.get("/payment/reverse/" + ia79_id_str)
        self.assertEqual(rv.status_code, 200, "Get reversal failed")
        self.assertIn(b'not a reversal', rv.data, "Invalid reversal not seen")

    def test_show_search_argument(self):
        """ When transaction is called with argument, it shows """

        ia80 = db.session.query(IncomingAmounts).filter_by(bank_ref='021514017743280167000000001').first()
        ia80_id_str = str(ia80.id)
        rv = self.app.get("/payment/reverse/" + ia80_id_str +
                          "?find_name=Jasper&find_number=218&find_bank_account=1188764")
        self.assertEqual(rv.status_code, 200, "Get reversal failed")
        self.assertIn(b'Jasper', rv.data, "Name not in output")
        self.assertIn(b'218', rv.data, "Number not in output")
        #self.assertIn(b'1188764', rv.data, "Bank account not in output")

    def test_get_shows_perfect_match(self):
        """ If on get we have a perfect match, we show it """

        ia81 = db.session.query(IncomingAmounts).filter_by(bank_ref='021514017743280167000000001').first()
        ia81_id_str = str(ia81.id)
        # setup a "perfect match"
        ia82 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=3000,
                               debcred='Cr',
                               our_ref="To find",
                               creditor_iban="NL20INGB0001234567",
                               value_date=datetime(2014, 1, 3))
        ia82.add()
        db.session.flush()
        rv = self.app.get("/payment/reverse/" + ia81_id_str)
        self.assertIn(b"To find", rv.data, "Reference not on screen")

    def test_conversion_of_target(self):
        """ A payment showing as reversal target, must be edited """

        ia83 = db.session.query(IncomingAmounts).filter_by(bank_ref='021514017743280167000000001').first()
        ia83_id_str = str(ia83.id)
        # setup a "perfect match"
        ia84 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=3000,
                               debcred='Cr',
                               our_ref="Test Conversion",
                               creditor_iban="NL20INGB0001234567",
                               value_date=datetime(2014, 1, 3))
        ia84.add()
        db.session.flush()
        rv = self.app.get("/payment/reverse/" + ia83_id_str)
        self.assertIn(b"30,00", rv.data, "Amount not converted")
        self.assertIn(b"Credit", rv.data, "Debit/credit not converted")

    def test_find_search_client_name(self):
        """ We find a (maybe) reversible by client name """

        ia85 = db.session.query(IncomingAmounts).filter_by(bank_ref='021514017743280167000000001').first()
        ia85_id_str = str(ia85.id)
        ia86 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=3000,
                               debcred='Cr',
                               our_ref="Test Conversion",
                               creditor_iban="NL20INGB0001234567",
                               value_date=datetime(2014, 1, 3),
                               client_name="ING Testrekening")
        ia86.add()
        db.session.commit()
        ia86_id_str = str(ia86.id)
        rv = self.app.get("/payment/reverse/" + ia86_id_str +
                          "?find_name=ING%20Testrekening")
        self.assertIn(ia85_id_str.encode(), rv.data, "Amount not in list")

    def test_amount_for_reversal_must_be_equal(self):
        """ Amounts unequal to reversal amount must be ignored """

        ia87 = db.session.query(IncomingAmounts).filter_by(bank_ref='021514017743280167000000001').first()
        ia87_id_str = str(ia87.id)
        ia88 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=3003,
                               debcred='Cr',
                               our_ref="Test Conversion",
                               creditor_iban="NL20INGB0001234567",
                               value_date=datetime(2014, 1, 3),
                               client_name="ING Testrekening")
        ia88.add()
        db.session.commit()
        ia88_id_str = str(ia88.id)
        ia89 = IncomingAmounts(payment_ccy='GBP',
                               payment_amount=3000,
                               debcred='Cr',
                               our_ref="Test Conversion",
                               creditor_iban="NL20INGB0001234567",
                               value_date=datetime(2014, 1, 3),
                               client_name="ING Testrekening")
        ia89.add()
        db.session.commit()
        ia89_id_str = str(ia89.id)

        rv = self.app.get("/payment/reverse/" + ia87_id_str +
                          "?find_name=ING%20Testrekening")
        self.assertNotIn(ia88_id_str.encode(), rv.data,
                         "Different amount in list")
        self.assertNotIn(ia89_id_str.encode(), rv.data,
                         "Different currency in list")

    def test_find_search_client_number(self):
        """ We can find payments by client number """

        ia90 = db.session.query(IncomingAmounts).filter_by(bank_ref='021514017743280167000000001').first()
        ia90_id_str = str(ia90.id)
        ia91 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=3000,
                               debcred='Cr',
                               our_ref="Test Conversion",
                               creditor_iban="NL20INGB0001234567",
                               value_date=datetime(2014, 1, 3),
                               client_name="Oker")
        ia91.client = self.clt6
        ia91.add()
        db.session.commit()
        ia91_id_str = str(ia91.id)
        rv = self.app.get("/payment/reverse/" + ia90_id_str +
                          "?find_number=" + str(self.clt6.id))
        self.assertIn(ia91_id_str.encode(), rv.data,
                         "Amount not in list")

    def test_payment_to_reversed_cannot_be_assigned(self):
        """ An assigned reversal candidate needs to be marked """

        ia93 = db.session.query(IncomingAmounts).filter_by(bank_ref='021514017743280167000000001').first()
        ia93_id_str = str(ia93.id)
        ia92 = IncomingAmounts(payment_ccy='EUR',
                               payment_amount=3000,
                               debcred='Cr',
                               our_ref="Paid bil reversal",
                               creditor_iban="NL20INGB0001234567",
                               value_date=datetime(2014, 1, 3),
                               client_name="Oker")
        ia92.client = self.clt6
        ia92.add()
        ia92.assign_to_bill(self.bll6)
        db.session.commit()
        rv = self.app.get("/payment/reverse/" + ia93_id_str )
        self.assertIn(b"Assigned", rv.data, "No assignment remark")


class TestPaymentsAndDebt(unittest.TestCase):

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
        parse(self.infile, self.camthandler)
        db.session.commit()
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):

        db.session.rollback()
        self.infile.close()
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.query(AmountQueued).delete()
        db.session.query(AssignedAmounts).delete()
        db.session.query(IncomingAmounts).delete()
        db.session.commit()

    def test_payment_on_screen(self):
        """ An unassigned payment appears on screen """

        ia114 = db.session.query(IncomingAmounts).filter_by(bank_ref=
                                                    '022221333306999888222200112')\
                                                        .first()
        ia114_id_str = str(ia114.id)
        ia114.client = self.clt3
        rv = self.app.get("/debt/" + str(ia114.client.id))
        self.assertEqual(rv.status_code, 200, "Failed transaction")
        self.assertIn(ia114_id_str.encode(), rv.data, "Amount not in output")
        amount = edited_amount(ia114.payment_amount, currency=ia114.payment_ccy)
        self.assertIn(amount.encode(), rv.data, "Amount not correct")

    def test_payment_updates_ccy_debt(self):
        """ A payment diminishes currency debt """

        ia115 = db.session.query(IncomingAmounts).filter_by(bank_ref=
                                                    '022221333306999888222200112')\
                                                        .first()
        ia115_id_str = str(ia115.id)
        ia115.client = self.clt3
        rv = self.app.get("/debt/" + str(ia115.client.id))
        self.assertEqual(rv.status_code, 200, "Failed transaction")
        amount = edited_amount(self.bll3.total() - ia115.payment_amount, currency=ia115.payment_ccy)
        self.assertIn(amount.encode(), rv.data, "Amount not correct")

    def test_payment_other_ccy_reported(self):
        """ A payment in a currency without debt is reported """

        ia116 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=3000,
                               debcred='Cr',
                               our_ref="Other ccy payment",
                               creditor_iban="NL20INGB0001234567",
                               value_date=datetime(2021, 12, 30),
                               client_name="Aquamarijn")
        ia116.client = self.clt3
        db.session.flush()
        rv = self.app.get("/debt/" + str(ia116.client.id))
        self.assertEqual(rv.status_code, 200, "Failed transaction")
        amount = edited_amount( -ia116.payment_amount, currency=ia116.payment_ccy)
        self.assertIn(amount.encode(), rv.data, "Amount not correct")


if __name__ == '__main__' :
    unittest.main()

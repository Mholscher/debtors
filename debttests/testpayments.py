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
from debtors import app, db
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

    def test_attach_client(self):
        """ We can attach a client to a payment """

        incoming_amount = IncomingAmounts(payment_ccy='USD',
                                payment_amount=48876,
                                debcred = 'Cr')
        incoming_amount.client = self.clt4
        db.session.flush()
        self.assertIn(incoming_amount, self.clt4.payments,
                      'Payment not in clients payments')


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
        self.assertEqual(len(aa02), 3, 'Not assigned to 2 bills')
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
        db.session.query(IncomingAmounts).delete()
        db.session.query(AssignedAmounts).delete()
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

    #def test_put_payment(self):
        """ Create a new payment """

        #self.app.put('/payment/new', data={'payment_ccy':'EUR',
                                           #'payment_amount':'567,99',
                                           #'debcred':'Cr',
                                           #'value_date':'17-12-2020'})
        #ia13 = db.session.query(IncomingAmounts).\
            #filter_by(payment_amount=56799).first()
        #self.assertEqual(ia13.value_date, parser.parse('17-12-2020'),
                         #'Incorrect date')
        #self.assertEqual(ia13.payment_ccy, 'EUR', 'Currency incorrect')


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



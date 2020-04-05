#    Copyright 2015 Menno Hölscher
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
from json import dumps
from debtors import app, db
from clientmodels.clients import Clients, Addresses, EMail, BankAccounts
from debtmodels.debtbilling import Bills, BillLines
from debtviews.bills import BillDict, BillListDict
from debttests.helpers import delete_test_clients, add_addresses,\
    create_clients, spread_created_at 
from datetime import datetime, date

class TestCreateBill(unittest.TestCase):

    def setUp(self):

        pass

    def rollback(self):

        db.session.rollback()

    def test_create_bill(self):
        """ We can create a new bill  """

        bill01 = Bills(date_sale=datetime.now(), date_bill=None,
                      prev_bill=None, status=Bills.NEW)
        bill01.add()
        db.session.flush()
        self.assertTrue(bill01.bill_id, 'No bill id found')

    def test_no_sale_date_fails(self):
        """ The date of sale is required """

        with self.assertRaises(ValueError):
            bill02 = Bills(date_sale=None, status=Bills.NEW)
            bill02.add()
            db.session.flush()

    def test_replaced_bill_must_exist(self):
        """ Adding a bill replacing a non-existent bill, fails """

        with self.assertRaises(ValueError):
            bill03 = Bills(date_sale=datetime.now(), date_bill=None,
                            prev_bill=1005, status=Bills.NEW)
            bill03.add()
            db.session.flush()

    def test_billing_ccy_must_exist(self):
        """ The billing currency must be on ISO 4217 """

        with self.assertRaises(ValueError):
            bill09 = Bills(date_sale=datetime.now(), date_bill=None,
                            billing_ccy = 'BAL',
                            prev_bill=None, status=Bills.NEW)
            bill09.add()
            db.session.flush()

    def test_billing_ccy_may_be_none(self):
        """ We can enter none for the billing currency """

        bill10 = Bills(date_sale=datetime.now(), date_bill=None,
                       billing_ccy=None,
                       prev_bill=None, status=Bills.NEW)
        bill10.add()
        db.session.flush()
        self.assertEqual(bill10.billing_ccy, 'EUR', 'No defaulting of currency')

    def test_can_replace_bill(self):
        """ Replacing an existing bill succeeds """

        bill04 = Bills(date_sale=datetime.now(), date_bill=None,
                      status=Bills.NEW)
        bill04.add()
        db.session.flush()
        bill04 = db.session.query(Bills).first()
        bill05 = Bills(date_sale=datetime.now(), date_bill=None,
                      prev_bill=bill04.bill_id, status=Bills.NEW)
        bill05.add()
        db.session.flush()
        self.assertEqual(bill05.prev_bill, bill04.bill_id,
                         'Bill to replace not accepted')


class TestBillFromMessage(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        db.session.flush()
        self.bill_dict =\
            {"client" : str(self.clt1.id),
             "currency" : "USD",
             "date-sale" : "2020-03-29",
             "bill-lines": [{"short-desc" : "Short desc", 
                        "long-desc" : "A longer description",
                        "unit" : 25,
                        "unit-desc" : "kilos",
                        "unit-price" : 1765},
                        {"short-desc" : "Another", 
                        "long-desc" : "Another longer description",
                        "unit" : 1,
                        "unit-price" : 2265}]
             }

    def tearDown(self):

        db.session.rollback()
        delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_create_bill_from_dict(self):
        """ We can create a bill from the dict """

        bill15 = Bills.create_from_dict(self.bill_dict)
        self.assertIn(bill15, self.clt1.bills, 'Bill not added')

    def test_invalid_client_fails(self):
        """ Adding a bill for a non-existing client fails """

        self.bill_dict['client'] = 1
        with self.assertRaises(ValueError):
            bill16 = Bills.create_from_dict(self.bill_dict)

    def test_bill_lines_added(self):
        """ The bill lines are added to the bill """

        bill17 = Bills.create_from_dict(self.bill_dict)
        self.assertEqual(len(bill17.lines), 2, 'Incorrect no of lines')
        

class TestBillFunctions(unittest.TestCase):

    def setUp(self):

        self.bill08 = Bills(date_sale=datetime.now(), date_bill=None,
                            status=Bills.NEW)
        self.bill08.add()
        self.bl09 = BillLines(short_desc='Lumpy', unit_price=18)
        self.bill08.lines.append(self.bl09)
        self.bl10 = BillLines(short_desc='Gravy', unit_price=45,
                              number_of=5)
        self.bill08.lines.append(self.bl10)
        create_clients(self)
        add_addresses(self)
        self.bill08.client = self.clt1
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_bill_total(self):
        """ The bill can return total due on it """

        self.assertEqual(self.bill08.total(), 243, 
                         'Incorrect total bill amount')

    def test_can_set_status(self):
        """ We can set the status of a bill """

        self.bill08.status = Bills.ISSUED
        db.session.flush()
        self.assertEqual(self.bill08.status, Bills.ISSUED, 
                         'Change not accepted')

    def test_set_invalid_status_fails(self):
        """  cannot set a status to an invalid value """

        with self.assertRaises(ValueError):
            self.bill08.status = 'blabber'
            db.session.flush()

    def test_get_all_client_bills(self):
        """ Get all bills for a client """

        bill08_id = self.bill08.bill_id
        bill11 = Bills(date_sale=datetime.now(), date_bill=None,
                       status=Bills.NEW)
        bill11.client = self.clt1
        db.session.flush()

        bill08_new = db.session.query(Bills).filter_by(bill_id=bill08_id).first()
        self.assertEqual(len(bill08_new.client.bills), 2, 'Wrong no. of bills')
        self.assertEqual(len(self.clt2.bills), 0, 'Unexpected bill on client')

    def test_get_only_issued_bills(self):
        """ We can get only bills for one status """

        bill08_id = self.bill08.bill_id
        bill12 = Bills(date_sale=datetime.now(), date_bill=None,
                       status=Bills.ISSUED)
        bill12.client = self.clt1
        db.session.flush()

        list_issued = Bills.get_bills_with_status(self.clt1, [Bills.ISSUED])
        self.assertEqual(len(list_issued), 1, 'Wrong no. of issued bills')

    def test_return_outstanding_bills(self):
        """ We can return a list of outstanding bills for a client """

        bill13 = Bills(date_sale=datetime.now(), date_bill=None,
                       status=Bills.ISSUED)
        bill13.client = self.clt1
        bill14 = Bills(date_sale=datetime.now(), date_bill=None,
                       status=Bills.PAID)
        bill14.client = self.clt1
        db.session.flush()

        list_unpaid = Bills.get_outstanding_bills(self.clt1)
        self.assertIn(bill13, list_unpaid, 'Unpaid bill not in unpaid list')
        self.assertNotIn(bill14, list_unpaid, 'Paid bill  in unpaid list')


class TestConvertToTagged(unittest.TestCase):
    """ Testing conversion from domain model to something the view
    can work with
    """

    def setUp(self):
        
        create_clients(self)
        add_addresses(self)
        create_bills(self)
    
    def tearDown(self):

        db.session.rollback()
        delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_convert_bill(self):
        """ We can convert a bill to a billdict """

        bld1 = BillDict(self.bll1) 
        self.assertEqual(bld1["date-sale"], str(self.bll1.date_sale.date()),
                         'Date sale not set correctly')

    def test_bill_list(self):
        """ We can convert a list of bills with its client data """

        blld1 = BillListDict(bill_list=self.bll1.get_outstanding_bills(self.clt1))
        self.assertEqual(blld1["bills"][0], BillDict(self.bll1),
                         'First bill not the expected one')
        self.assertEqual(blld1["client"], self.bll1.client.id,
                         'Client id incorrect')

    def test_bill_list_from_client(self):
        """ We can convert a list of bills from only a client number """

        blld2 = BillListDict(client=self.clt1)
        self.assertEqual(blld2["bills"][0], BillDict(self.bll1),
                         'First bill not the expected one')
        self.assertEqual(blld2["client"], self.bll1.client.id,
                         'Client id incorrect')

    def test_no_list_or_client(self):
        """ Passing no bill list nor client fails """

        with self.assertRaises(TypeError):
            blld3 = BillListDict()

    def test_empty_list_fails(self):
        """ When we send in an empty list, failure occurs """

        with self.assertRaises(TypeError):
            blld4 = BillListDict(bill_list=[])        


class TestBillTransactions(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        db.session.flush()
        self.bill_dict =\
            {"client" : str(self.clt1.id),
             "currency" : "USD",
             "date-sale" : "2020-03-29",
             "bill-lines": [{"short-desc" : "Short desc", 
                        "long-desc" : "A longer description",
                        "unit" : 25,
                        "unit-desc" : "kilos",
                        "unit-price" : 1765},
                        {"short-desc" : "Another", 
                        "long-desc" : "Another longer description",
                        "unit" : 1,
                        "unit-price" : 2265}]
             }
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):

        db.session.rollback()
        delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_get_outstanding(self):
        """ We can retrieve a json with the debt """

        rv = self.app.get('/api/10/client/' + str(self.clt1.id) + '/bills')
        self.assertIn(str(self.clt1.id).encode(), rv.data, 'ID number bill not found')

    def test_non_existing_client_fails(self):
        """ A request for a list of bills for a nonexisting client fails """

        rv = self.app.get('/api/10/client/1/bills')
        self.assertIn(b'404', rv.data, 'Not found not done')

    def test_empty_list_succeeds(self):
        """ A request for a list of bills for a client with no bill """

        rv = self.app.get('/api/10/client/' + str(self.clt2.id) + '/bills')
        self.assertIn(b'Petrol', rv.data, 'Request for bills not OK')
        self.assertEqual(200, rv.status_code, 'Status not OK')

    def test_add_bill_success(self):
        """ We can add a bill to the database through a transaction """

        rv = self.app.post('/api/10/bill/new', json=self.bill_dict)
        self.assertEqual(rv.status_code, 200, 'Failure')
        self.assertIn(b'bill-id', rv.data, 'No bill id returned')

    def test_missing_date_fails(self):
        """ Sending a json with a missing date-sale causes 400 """

        bill_dict = self.bill_dict.copy()
        del bill_dict['date-sale']
        rv = self.app.post('/api/10/bill/new', json=bill_dict)
        self.assertEqual(400, rv.status_code, 'No 400 status returned')

    def test_prev_bill_not_found(self):
        """ Trying to replace a non-existing bill gives 400 """

        self.bill_dict["bill-replaced"] = 1
        rv = self.app.post('/api/10/bill/new', json=self.bill_dict)
        self.assertEqual(400, rv.status_code, 'No 400 status returned')
        

    def test_get_bill_by_id(self):
        """ We can get a bill by its bill id """

        rv = self.app.get('/api/10/bill/' + str(self.bll2.bill_id))
        bill_date = str(self.bll2.date_bill.date()).encode()
        self.assertIn(bill_date, rv.data, 'Date not returned')


class TestLineCreate(unittest.TestCase):

    def setUp(self):

        self.bill06 = Bills(date_sale=datetime.now(), date_bill=None,
                            status='new')
        self.bill06.add()
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_create_one_line(self):
        """ We can create a line for the bill """

        bl01 = BillLines(bill_id=self.bill06.bill_id, short_desc='short',
                         unit_price=70)
        bl01.add()
        db.session.flush()
        self.assertTrue(bl01.line_id, 'No id for line')
        self.assertEqual(bl01.bill_id, self.bill06.bill_id,
                         'bill id incorrect')

    def test_add_via_bill(self):
        """ We can add a bill line via the lines property """

        bl02 = BillLines(short_desc='short',unit_price=60)
        self.bill06.lines.append(bl02)
        db.session.flush()
        self.assertEqual(bl02.bill_id, self.bill06.bill_id,
                         'Bill id incorrect')

    def test_add_more_lines(self):
        """ We can add more than 1 line """

        bl03 = BillLines(short_desc='a short one',unit_price=17)
        self.bill06.lines.append(bl03)
        bl04 = BillLines(short_desc='a short two',unit_price=47)
        self.bill06.lines.append(bl04)
        self.assertEqual(len(self.bill06.lines), 2, "wrong number of lines")

    def test_short_desc_mandatory(self):
        """ A short description is mandatory """

        with self.assertRaises(ValueError):
            bl05 = BillLines(short_desc=None, long_desc='a long one',
                             unit_price=38)
            self.bill06.lines.append(bl05)

    def test_unit_price_mandatory(self):
        """ The unit price field is mandatory """

        with self.assertRaises(ValueError):
            bl06 = BillLines(short_desc='Shorty', long_desc='a long one',
                             unit_price=None)
            self.bill06.lines.append(bl06)

class TestBillLineFunctions(unittest.TestCase):

    def setUp(self):

        self.bill07 = Bills(date_sale=datetime.now(), date_bill=None,
                            status='new')
        self.bill07.add()
        self.bl07 = BillLines(short_desc='Verkort', unit_price=75)
        self.bill07.lines.append(self.bl07)
        self.bl08 = BillLines(short_desc='Kurz', unit_price=68,
                              number_of=5)
        self.bill07.lines.append(self.bl08)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_line_totals(self):
        """ A line must have a total amount """
        
        totals = []
        for line in self.bill07.lines:
            totals.append(line.total())
        self.assertIn(75, totals, 'Line not correctly calculated')
        self.assertIn(340, totals, 'Line not correctly calculated')

def create_bills(instance):
    """ Create bills for test 'instance' """

    instance.bll1 = Bills(date_sale=datetime.now(), date_bill=None,
                          status='new')
    instance.clt1.bills.append(instance.bll1)
    instance.bll2 = Bills(date_sale=datetime.now(), date_bill=datetime.now(),
                          status='paid')
    instance.clt1.bills.append(instance.bll2)
    instance.bll3 = Bills(date_sale=date(year=2019, month=11, day=18),
                          date_bill=None,
                          status='new')
    instance.clt3.bills.append(instance.bll3)


def delete_test_bills(instance):
    """ Delete all the bills created for a test """

    try:
        for attribute in instance.vars():
            if isinstance(attribute, Bills):
                db.session.delete(attribute)
    except AttributeError:
        pass


if __name__ == '__main__' :
    unittest.main()

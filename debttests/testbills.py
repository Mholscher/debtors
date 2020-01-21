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
from debtors import db
from debtmodels.debtbilling import Bills, BillLines
from datetime import datetime

class TestCreateBill(unittest.TestCase):

    def setUp(self):

        pass

    def rollback(self):

        db.session.rollback()

    def test_create_bill(self):
        """ We can create a new bill  """

        bill01 = Bills(date_sale=datetime.now(), date_bill=None,
                      prev_bill=None, status='new')
        bill01.add()
        db.session.flush()
        self.assertTrue(bill01.bill_id, 'No bill id found')

    def test_no_sale_date_fails(self):
        """ The date of sale is required """

        with self.assertRaises(ValueError):
            bill02 = Bills(date_sale=None, status='new')
            bill02.add()
            db.session.flush()

    def test_replaced_bill_must_exist(self):
        """ Adding a bill replacing a non-existent bill, fails """

        with self.assertRaises(ValueError):
            bill03 = Bills(date_sale=datetime.now(), date_bill=None,
                            prev_bill=1005, status='new')
            bill03.add()
            db.session.flush()

    def test_can_replace_bill(self):
        """ Replacing an existing bill succeeds """

        bill04 = Bills(date_sale=datetime.now(), date_bill=None,
                      status='new')
        bill04.add()
        db.session.flush()
        bill04 = db.session.query(Bills).first()
        bill05 = Bills(date_sale=datetime.now(), date_bill=None,
                      prev_bill=bill04.bill_id, status='new')
        bill05.add()
        db.session.flush()
        self.assertEqual(bill05.prev_bill, bill04.bill_id,
                         'Bill to replace not accepted')


class TestBillFunctions(unittest.TestCase):

    def setUp(self):

        self.bill08 = Bills(date_sale=datetime.now(), date_bill=None,
                            status='new')
        self.bill08.add()
        self.bl09 = BillLines(short_desc='Lumpy', unit_price=18)
        self.bill08.lines.append(self.bl09)
        self.bl10 = BillLines(short_desc='Gravy', unit_price=45,
                              number_of=5)
        self.bill08.lines.append(self.bl10)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_bill_total(self):
        """ The bill can return total due on it """

        self.assertEqual(self.bill08.total(), 243, 
                         'Incorrect total bill amount')


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


if __name__ == '__main__' :
    unittest.main()

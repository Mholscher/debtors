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
from debtmodels.debtbilling import Bills
from datetime import datetime

class TestCreateBill(unittest.TestCase):

    def setUp(self):

        pass

    def rollback(self):

        db.session.rollback()

    def test_create_bill(self):
        """ We can create a new bill  """

        bill01 = Bills(date_sale=datetime.now(), date_bill=None,
                      status='new')
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


if __name__ == '__main__' :
    unittest.main()

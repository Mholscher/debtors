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

if __name__ == '__main__' :
    unittest.main()

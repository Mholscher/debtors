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
from debtors import db
from debttests.helpers import delete_test_clients, add_addresses,\
    create_clients, spread_created_at, create_bills, add_lines_to_bills,\
    delete_test_bills
from debtviews.physicalbill import rtfenvironment, BillDictView

class TestPaperBillCreate(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        db.session.flush()
        self.bill_dict = {"client" : {"initials" : "J.F.M.",
                                     "surname" : "Bredero",
                                     "street" : "Oranjestraat",
                                     "house_number": "57",
                                     "postcode" : "5703 PG",
                                     "town_or_village" : "Turfjedam",
                                     "country" : "Nederland"},
                         "bill" : { "bill_id" : 75,
                                    "date_sale" : "25-05-2020",
                                    "billing_ccy" : "Euro",
                                    "total" : "31,25",
                                    "lines" : [ {"short_desc" : "1875",
                                                 "long_desc" : "Zaagbeschermkap",
                                                 "number_of" : 2,
                                                 "unit_price" : "12,75",
                                                 "total" : "24,50"},
                                                {"short_desc" : "ska-1176",
                                                 "long_desc" : "Mot, in zakken",
                                                 "number_of" : 3,
                                                 "measured_in" : "kilo",
                                                 "unit_price" : "2,25",
                                                 "total" : "6,75"}]}}

    def tearDown(self):

        db.session.rollback()
        delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_create_paper_bill(self):
        """ We can create a paper bill from the bill_dict"""

        bill_template = rtfenvironment.get_template('paperbill.rtf')
        rv = bill_template.render(self.bill_dict)
        self.assertIn('Bredero', rv, 'Client name not in text')
        self.assertIn('Euro', rv, 'Currency name not in text')
        self.assertIn('Zaagbeschermkap', rv, 'Line long decription not in text')
        #with open('bill15', 'w') as f:
            #f.write(rv)

    def test_can_retrieve_bill_data(self):
        """ We can retrieve bill data from the database """

        view = BillDictView(bill_id=self.bll3.bill_id)
        self.assertIn("client", view, 'Client not in view')
        self.assertIn("bill", view, 'Bill not in view')
        self.assertIn("date", view, 'Date not in view')

    def test_bill_has_line(self):
        """ Test bill has a correct bill line """

        view = BillDictView(bill_id=self.bll3.bill_id)
        long_desc = view["bill"]["lines"][0]["long_desc"]
        self.assertEqual("Grease", long_desc, 'Description incorrect')

    def test_amount_edited(self):
        """ An amount in a bill line is edited """

        view = BillDictView(bill_id=self.bll3.bill_id)
        unit_price = view["bill"]["lines"][0]["unit_price"]
        self.assertEqual("128,73", unit_price, 'Amount incorrect')

    def test_print_unicode(self):
        """ We can print unicode non-ascii characters """

        view = BillDictView(bill_id=self.bll3.bill_id)
        bill_template = rtfenvironment.get_template('paperbill.rtf')
        rv = bill_template.render(view)
        self.assertIn('\\u916', rv, 'Delta not found')
        self.assertIn('\\u246', rv, 'ö not found')
        with open('bill16', 'w') as f:
            f.write(rv)


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

from os.path import exists
from datetime import datetime
import unittest
from debtors import db
from debttests.helpers import delete_test_clients, add_addresses,\
    create_clients, spread_created_at, create_bills, add_lines_to_bills,\
    delete_test_bills
from debtmodels.debtbilling import Bills, BillLines
from debtviews.physicalbill import rtfenvironment, BillDictView, PaperBill,\
    HTMLMailBill, BillAccounting, BillReplaceAccounting

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
        #with open('bill16', 'w') as f:
            #f.write(rv)

    def test_invalid_bill_id_fails(self):
        """ When an invalid bill_id is supplied, a graceful failure """

        with self.assertRaises(ValueError):
            view = BillDictView(bill_id=1)



class TestPaperBillProcess(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_create_bill_text(self):
        """ Create a bill from a supplied bill_id """

        bill_doc = PaperBill(self.bll3.bill_id)
        self.assertIn(str(self.bll3.bill_id), bill_doc.text,
                      "Id not in bill text")

    def test_write_bill_to_file(self):
        """ We can write the RTF to a file """

        bill_doc = PaperBill(self.bll3.bill_id)
        bill_doc.write_file()
        self.assertTrue(exists("output/bill" + str(self.bll3.bill_id)),
                               "Output file does not exist")

class TestMailBill(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_can_create_text_document(self):
        """ We can create a text document """

        bill_mail = HTMLMailBill(self.bll4.bill_id)
        self.assertIn('Aubergine', bill_mail.text, 'Client name not correct')
        #with open('output/mail' + str(self.bll4.bill_id), 'w') as f:
            #f.write(bill_mail.text)

    def test_can_create_html_document(self):
        """ We can ceeate a HTML document """

        bill_html = HTMLMailBill(self.bll4.bill_id)
        self.assertIn('Aubergine', bill_html.html, 'Client name not correct')
        #with open('output/htmlmail' + str(self.bll4.bill_id) + '.html', 'w') as f:
            #f.write(bill_html.html)

    #def test_create_email_part_plain(self):
        #""" Create an email message part for the plaintext bit """

        #bill_mail = HTMLMailBill(self.bll4.bill_id)
        #self.assertIn('text/plain', bill_mail.text_message['Content-type'])

    def test_create_email_multipart(self):
        """ Create a multipart message with the text and html """

        bill_mail = HTMLMailBill(self.bll4.bill_id)
        self.assertIn('multipart/alternative',
                      bill_mail.multipart_message['Content-type'])
        #with open('output/mail' + str(self.bll4.bill_id), 'w') as f:
            #f.write(bill_mail.multipart_message.as_string())

    def test_sender_recipient_subject(self):
        """ An email contains sender, recipient and subject """

        bill_mail = HTMLMailBill(self.bll4.bill_id)
        self.assertIn('debtorscompany',
                      bill_mail.multipart_message['From'])
        self.assertIn(self.bll4.client.preferred_mail().mail_address,
                      bill_mail.multipart_message['To'])
        self.assertIn(str(self.bll4.bill_id),
                      bill_mail.multipart_message['Subject'])


class TestCreateAccounting(unittest.TestCase):


    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_create_accounting(self):
        """ We can create an accounting transaction """

        bac1 = BillAccounting(self.bll3)
        posting_list = bac1['journal']['postings']
        accounts = [account for posting in posting_list for k, account in posting.items() if k == 'account' ]
        self.assertIn('sales', accounts, 'No sales posting')
        self.assertIn('debt', accounts, 'No debt posting')
        self.assertEqual(self.bll3.date_sale.strftime("%Y-%m-%d"),
                         posting_list[0]["valuedate"], 'Incorrect date')

    def test_posts_headers(self):
        """ Headers are presesent in the journal """

        bac2 = BillAccounting(self.bll3)
        self.assertIn("function", bac2["journal"], 'No function')
        self.assertEqual(bac2["journal"]["function"], "insert", 'Function incorrect')
        self.assertIn("extkey", bac2["journal"], 'No journal key')
        self.assertEqual(bac2["journal"]["extkey"], "bill" + str(self.bll3.bill_id), 'Journal key incorrect')

    def test_do_not_post_zero(self):
        """ Trying to post a zero debt fails """

        with self.assertRaises(ValueError):
            bac3 = BillAccounting(self.bll5)

    def test_can_return_json(self):
        """ We can return a JSON version of the post  """

        bac4 = BillAccounting(self.bll4)
        bac4_json = bac4.as_json()
        self.assertIn('JPY', bac4_json, 'Currency not in json')
        self.assertIn('sales', bac4_json, 'Account not in json')
        self.assertIn('{"', bac4_json, 'General json problem')


class TestReversalAccounting(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()
        delete_test_bills(self)
        delete_test_clients(self)
        db.session.commit()

    def test_create_accounting_replaced_bill(self):
        """ We create accounting for a replaced bill """

        self.bill01 = Bills(date_sale=datetime.now(), date_bill=None,
                            prev_bill=self.bll3.bill_id, status=Bills.NEW)
        self.bill01.add()
        self.bl01 = BillLines(short_desc='Lumpy', unit_price=18)
        self.bill01.lines.append(self.bl01)
        self.bl02 = BillLines(short_desc='Gravy', unit_price=45,
                              number_of=5)
        self.bill01.lines.append(self.bl02)
        self.bill01.client = self.clt1
        db.session.flush()
        bac5 = BillReplaceAccounting(self.bll3)
        posting_list = bac5['journal']['postings']
        accounts = [(posting['account'], posting['debitcredit'])
                    for posting in posting_list ]
        self.assertIn(('sales', 'Db'), accounts, 'No sales posting/wrong sign')
        self.assertIn(('debt', 'Cr'), accounts, 'No debt posting/wrong sign')
        self.assertEqual('billr' + str(self.bll3.bill_id),
                         bac5['journal']['extkey'], "Wrong extkey")


if __name__ == '__main__':
    unittest.main()

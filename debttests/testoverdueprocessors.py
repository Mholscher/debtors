#    Copyright 2021 Menno Hölscher
#
#    This file is part of Debtors.

#    Debtors is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    Debtors is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with Debtors.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import os
from os.path import exists
from debtors import db
from debttests.helpers import (create_clients, add_addresses,
                               create_bills, add_lines_to_bills,
                               delete_test_bills, delete_test_prefs,
                               delete_test_clients)
from debtmodels.overdue import OverdueProcessor, ProcessorAlreadyExistsError
from debtmodels.overdue_processors import FirstLetterProcessor

class TestCreateFirstLetterProcessor(unittest.TestCase):

    def tearDown(self):

        OverdueProcessor.all_processors.clear()

    def test_create_processor(self):
        """ Create a firstletter processor """

        flp01 = FirstLetterProcessor()
        self.assertIn(flp01.processor_key, flp01.all_processors,
                      "Processor not added to all_processors")

    def test_create_second_processor_fails(self):
        """ Can not create a duplicate processor """

        flp02 = FirstLetterProcessor()
        with self.assertRaises(ProcessorAlreadyExistsError):
            flp03 = FirstLetterProcessor()

class TestFirstLetterProcess(unittest.TestCase):

    def setUp(self):

        self.flp04 = FirstLetterProcessor()
        create_clients(self)
        add_addresses(self)
        create_bills(self)
        add_lines_to_bills(self)
        db.session.flush()

    def tearDown(self):

        OverdueProcessor.all_processors.clear()
        db.session.rollback()
        delete_test_bills(self)
        delete_test_prefs(self)
        delete_test_clients(self)
        db.session.commit()

    def test_execute(self):
        """ Execute produces a first letter """

        self.flp04.execute(self.bll4)
        self.assertTrue(exists("output/fl" + str(self.bll4.bill_id)),
                               "First letter file does not exist")

if __name__ == '__main__' :
    unittest.main()

#    Copyright 2018 Menno Hölscher
#
#    This file is part of Debtors.

#    Debtors is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    Debtors is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with Debtors.  If not, see <http://www.gnu.org/licenses/>.

from debtmodels.overdue import OverdueSteps, OverdueProcessor

class FirstLetterProcessor(OverdueProcessor):

    def __init__(self):

        self.processor_key = "firstletter"
        super().__init__()

    def execute(self, bill=None):
        """ Execute first letter processing for a bill """

        with open("output/fl" + str(bill.bill_id), "wt") as first_letter:
            first_letter.write("First letter for " + str(bill.bill_id))

    def text(self, bill=None):
        """ Return the rendered text for a letter """

        return b""

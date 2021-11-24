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
from debtviews.physicaloverdue import PaperLetter

class FirstLetterProcessor(OverdueProcessor):

    def __init__(self):

        self.processor_key = "firstletter"
        super().__init__()

    def _execute(self, bill=None):
        """ Execute first letter processing for a bill """

        self.first_letter = PaperLetter(template_name="firstletter.rtf",
                                   bill=bill)
        with open("output/fl" + str(bill.bill_id), "wt") as letter_file:
            letter_file.write(self.first_letter.text)

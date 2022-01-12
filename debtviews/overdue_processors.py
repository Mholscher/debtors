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

from datetime import date, timedelta
from debtmodels.overdue import OverdueSteps, OverdueProcessor
from debtviews.physicaloverdue import (PaperLetter, HTMLMailFirstOverdue,
                                       HTMLMailSecondOverdue,
                                       HTMLMailDebtTransfer,
                                       JSONDebtTransfer)

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

        if bill.client.debtor_prefs\
            and bill.client.debtor_prefs[0].letter_medium == "mail":
            self.first_mail = HTMLMailFirstOverdue(bill.bill_id)
            self.first_mail.write_file()

class SecondLetterProcessor(OverdueProcessor):

    def __init__(self):

        self.processor_key = "secondletter"
        super().__init__()

    def _execute(self, bill=None):

        self.second_letter = PaperLetter(template_name="secondletter.rtf",
                                         bill=bill)
        with open("output/sl" + str(bill.bill_id), "wt") as letter_file:
            letter_file.write(self.second_letter.text)

        if bill.client.debtor_prefs\
            and bill.client.debtor_prefs[0].letter_medium == "mail":
            self.second_mail = HTMLMailSecondOverdue(bill.bill_id)
            self.second_mail.write_file()

class DebtTransferProcessor(OverdueProcessor):

    def __init__(self):

        self.processor_key = "transfer"
        super().__init__()

    def _execute(self, bill=None):

        self.transfer_letter = PaperLetter(template_name="transferletter.rtf",
                                         bill=bill)
        with open("output/dtm" + str(bill.bill_id), "wt") as letter_file:
            letter_file.write(self.transfer_letter.text)

        if bill.client.debtor_prefs\
            and bill.client.debtor_prefs[0].letter_medium == "mail":
            self.transfer_mail = HTMLMailDebtTransfer(bill.bill_id)
            self.transfer_mail.write_file()

        self.transfer_message = JSONDebtTransfer(bill_id=bill.bill_id)
        self.transfer_message.write_file()

    def transfer_date(self, date_bill):
        """ Calculate the transfer date for a bill date """

        return (date_bill + 
                timedelta(days=self.processor_data[3])).strftime("%d %B %Y")


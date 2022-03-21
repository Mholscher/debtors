#    Copyright 2018 Menno Hölscher
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

""" This module holds the **example** processors for the overdue processing.

The imported OverdueProcessor holds a template for every processor,. The thing
that the processors here need to implement is the _execute method. It should
do the processing specific to the step. Also here you will find routines that
do subprocesses, like in DubiousDebtorAccounting.
"""

from datetime import date, timedelta, datetime
from debtmodels.overdue import OverdueProcessor
from debtmodels.debtbilling import DebtorSignal
from debtmodels.accounting import AccountingTemplate
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


class DubiousDebtorProcessor(OverdueProcessor):

    def __init__(self):

        self.processor_key = "dubious"
        super().__init__()

    def _execute(self, bill=None):

        # create the debtorssignal
        signal = DebtorSignal(client=bill.client,
                              date_start=date.today())
        signal.add()
        outstanding_bills = bill.get_outstanding_bills(bill.client)
        for other_bill in outstanding_bills:
            other_bill.debtor_becomes_dubious()


class DubiousDebtorAccounting(AccountingTemplate):
    """ Create the accounting lines and external key for dubious

    TODO where is this to be called?
    """

    def journal_entries(self, journal_dict, dubious_bill):
        """ Create the accounting entries for a bill turning dubious. """

        journal_dict["extkey"] = "dubious" + str(dubious_bill.bill_id)
        posting_list = []
        posting_debt = {"account": "debt", "currency":
                        dubious_bill.billing_ccy,
                        "amount": str(dubious_bill.total()),
                        "debitcredit": "Cr",
                        "valuedate": datetime.today().strftime("%Y-%m-%d")}
        posting_list.append(posting_debt)
        posting_dubious = {"account": "dubious", "currency":
                           dubious_bill.billing_ccy,
                           "amount": str(dubious_bill.total()),
                           "debitcredit": "Db",
                           "valuedate": datetime.today().strftime("%Y-%m-%d")}
        posting_list.append(posting_dubious)
        journal_dict["postings"] = posting_list
        return journal_dict


class BagatelleAccounting(AccountingTemplate):
    """ Create accounting for bagatelle processing

    This creates only the accounting that is necessary to fund the
    extra money (the bagatelle) that is necessary to pay the (rest of)
    the bill in debt. The rest will be dealt with in assigning the debt.
    """

    def journal_entries(self, journal_dict, missing_amount):
        """ Create the accounting to be able to fund a missing amount

        The missing amount is a tuple with

            * the currency of the missing amount
            * the number of units in that currency

        """

        return journal_dict

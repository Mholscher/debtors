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

""" Module to hold the contenthandler to process a camt message """

from xml.sax import ContentHandler, make_parser, parse
from dateutil.parser import parse as dt_parse
from debtviews.monetary import internal_amount
from debtmodels.payments import IncomingAmounts, IncomingAmountsList,\
    AmountQueued


class CAMT53Handler(ContentHandler):
    """ Contains all code to handle a CAMT053 message.
    
    The format is described in several places, I used the descriptions 
    of the NVB (Dutch banking association), supported by some ING documents.
    It may be that to take advantage of country specific services, you will 
    need to adjust the code.
    """
    
    PROCESS_FAMILIES = (("RCDT", "DMCT"), ("RCDT", "ESCT"),
                        ("RCDT", "RRTN"), ("RCDT", "STDO"),
                        ("RCDT", "XBCT"), ("IDDT", "BBDD"),
                        ("IDDT", "ESDD"), ("IDDT", "PADD"),
                        ("IDDT", "PMDD"), ("IDDT", "PRDD"),
                        ("IDDT", "UPDD"))

    def start_within_entry(self, name, attrs):
        """ Process startelement for elements that are within an entry

        An entry is to be read as one statement line, with an amount, 
        a description and a value date.
        """

        if name == 'Amt':
            self.unassigned_amount.payment_ccy = attrs['Ccy']
            self.in_amount = True
        elif name == 'ValDt':
            self.in_valuedate = True
        elif name == 'CdtDbtInd':
            self.in_credit_debit = True
        elif name == 'Dt' or name == 'DtTm'\
            and hasattr(self, ".in_valuedate"):
            self.in_date = True
        elif name == 'NtryRef':
            self.in_entry_ref = True
        elif name == 'Ref':
            self.in_ref = True
        elif name == 'RltdPties':
            self.in_creditor = True
        elif name == 'Nm' and hasattr(self, "in_creditor"):
            self.in_client_name = True
        elif name == 'IBAN' and hasattr(self, "in_creditor"):
            self.in_creditor_iban = True
        elif name == "Fmly":
            self.in_family = True
        elif name == "Cd" and hasattr(self, "in_family"):
            self.in_family_code = True
        elif name == "SubFmlyCd" and hasattr(self, "in_family"):
            self.in_sub_family_code = True
        else:
            super().startElement(name, attrs)

    def end_within_entry(self, name):
        """ Process end element for elements that are within an entry 

        An entry is to be read as one statement line, with an amount, 
        a description and a value date.
        """

        if name == 'Amt':
            del(self.in_amount)
        elif name == 'CdtDbtInd':
            del(self.in_credit_debit)
        elif name == 'ValDt':
            del(self.in_valuedate)
        elif name == 'Dt' and hasattr(self, "in_date"):
            del(self.in_date)
        elif name == 'NtryRef':
            del(self.in_entry_ref)
        elif name == 'Ref':
            del(self.in_ref)
        elif name == 'RltdPties':
            del(self.in_creditor)
        elif name == 'Nm' and hasattr(self, "in_creditor"):
            del(self.in_client_name)
        elif name == 'IBAN' and hasattr(self, "in_creditor"):
            del(self.in_creditor_iban)
        elif name == "Cd" and hasattr(self, "in_family_code"):
            del(self.in_family_code)
        elif name == "Fmly" and hasattr(self, "in_family"):
            del(self.in_family)
            del(self.family)
            del(self.process)
        elif name == "SubFmlyCd" and hasattr(self, "in_sub_family_code"):
            del(self.in_sub_family_code)
        else:
            super().endElement(name)

    def startElement(self, name, attrs):
        """ The parser calls this routine for each new element.
        
        If the element is known to the CAMT53Handler, it handles the
        element. The element is recognised by its name.
        """

        if hasattr(self, "ignore_statement"):
            return
        elif name == "Ntry":
            self.in_entry = True
            self.unassigned_amount = IncomingAmounts()
            self.unassigned_amount.file_timestamp = self.creation_timestamp
        elif name == 'Stmt':
            self.in_statement = True
            self.entries = IncomingAmountsList()
        elif name == 'CreDtTm' and hasattr(self, 'in_statement'):
            self.in_create_timestamp = True
        elif name == 'Acct':
            self.in_account = True
        elif name == 'IBAN' and hasattr(self, 'in_account'):
            self.in_our_IBAN = True
        elif hasattr(self, "in_entry"):
            self.start_within_entry(name, attrs)
        else:
            super().startElement(name, attrs)

    def endElement(self, name):
        """ The parser calls this routine each time an element is done parsing
        
        If there is closing logic for the element, it is done.
        """

        if name== 'Ntry' and hasattr(self, "in_entry"):
            if hasattr(self, "ignore_entry"):
                del(self.ignore_entry)
            else:
                self.unassigned_amount.add()
                self.entries.append(self.unassigned_amount)
                # queue this for assignment
                amount_queued = AmountQueued(incoming_amount =\
                    self.unassigned_amount)
                amount_queued.add()
            del(self.in_entry) 
        elif name == 'Stmt':
            if hasattr(self, "ignore_statement"):
                del(self.ignore_statement)
            else:
                self.entries.store_all()
            del(self.in_statement)
        elif name == 'CreDtTm' and hasattr(self, 'in_statement'):
            del(self.in_create_timestamp)
        elif name == 'Acct' and hasattr(self, 'in_account'):
            del(self.in_account)
        elif name == 'IBAN' and hasattr(self, 'in_our_IBAN'):
            del(self.in_our_IBAN)
        elif hasattr(self, "in_entry"):
            self.end_within_entry(name)
        else:
            super().endElement(name)

    def characters(self, content):
        """ Called for each CDATA text in an element
        
        The characters are the value in the xml entry (not to be confused
        with the statement entry ;=)
        """

        if hasattr(self, "ignore_statement"):
            return
        elif hasattr(self, "in_our_IBAN")\
            and hasattr(self, "accounts"):
                if content not in self.accounts:
                    self.ignore_statement = True
        elif hasattr(self, 'in_credit_debit') and self.in_credit_debit:
            if content == 'DBIT':
                self.unassigned_amount.debcred = 'Db'
            else:
                self.unassigned_amount.debcred = 'Cr'
        elif hasattr(self, 'in_amount')\
            and self.in_amount:
            self.unassigned_amount.payment_amount = internal_amount(content)
        elif hasattr(self, 'in_date')\
            and self.in_date:
            self.unassigned_amount.value_date = dt_parse(timestr=content)
        elif hasattr(self, 'in_entry_ref')\
            and self.in_entry_ref:
            self.unassigned_amount.bank_ref = content
        elif hasattr(self, 'in_ref')\
            and self.in_ref:
            self.unassigned_amount.client_ref = content
        elif hasattr(self, 'in_client_name')\
            and self.in_client_name:
            self.unassigned_amount.client_name = content
        elif hasattr(self, 'in_creditor_iban')\
            and self.in_creditor_iban:
            self.unassigned_amount.creditor_iban = content
        elif hasattr(self, 'in_create_timestamp')\
            and hasattr(self, 'in_statement'):
            self.creation_timestamp = dt_parse(timestr=content)
        elif hasattr(self, "in_family_code"):
            self.family = content
        elif hasattr(self, "in_sub_family_code"):
            self.process = (self.family, content)
            if self.process not in self.PROCESS_FAMILIES:
                self.ignore_entry = True
        else:
            super().characters(content)

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

from xml.sax import ContentHandler, make_parser, parse
from dateutil.parser import parse as dt_parse
from debtviews.monetary import internal_amount
from debtmodels.payments import IncomingAmounts

class CAMT53Handler(ContentHandler):

    def startElement(self, name, attrs):
        """ The parser calls this routine for each new element.
        
        If the element is known to the CAMT53Handler, it handles the
        element. The element is recognised by its name.
        """

        if name == "Ntry":
            self.unassigned_amount = IncomingAmounts()
        elif name == 'Amt':
            self.unassigned_amount.payment_ccy = attrs['Ccy']
            self.in_amount = True
        elif name == 'ValDt':
            self.in_valuedate = True
        elif name == 'Dt' or name == 'DtTm'\
            and hasattr(self, ".in_valuedate"):
            self.in_date = True
        elif name == 'AcctSvcrRef':
            self.in_acct_svcr_ref = True
        elif name == 'Ref':
            self.in_ref = True
        elif name == 'RltdPties':
            self.in_creditor = True
        elif name == 'Nm' and hasattr(self, "in_creditor"):
            self.in_client_name = True
        elif name == 'IBAN' and hasattr(self, "in_creditor"):
            self.in_creditor_IBAN = True
        else:
            super().startElement(name, attrs)

    def endElement(self, name):
        """ The parser calls this routine each time an element is done parsing
        
        If there is closing logic for the element, it is done.
        """

        if name == 'Amt':
            del(self.in_amount)
        elif name == 'ValDt':
            del(self.in_valuedate)
        elif name == 'Dt' and hasattr(self, "in_date"):
            del(self.in_date)
        elif name == 'AcctSvcrRef':
            del(self.in_acct_svcr_ref)
        elif name == 'Ref':
            del(self.in_ref)
        elif name == 'RltdPties':
            del(self.in_creditor)
        elif name == 'Nm' and hasattr(self, "in_creditor"):
            del(self.in_client_name)
        elif name == 'IBAN' and hasattr(self, "in_creditor"):
            del(self.in_creditor_IBAN)
        else:
            super().endElement(name)

    def characters(self, content):
        """ Called for each CDATA text in an element """

        if hasattr(self, 'in_amount')\
            and self.in_amount:
            self.unassigned_amount.payment_amount = internal_amount(content)
        elif hasattr(self, 'in_date')\
            and self.in_date:
            self.unassigned_amount.value_date = dt_parse(timestr=content)
        elif hasattr(self, 'in_acct_svcr_ref')\
            and self.in_acct_svcr_ref:
            self.unassigned_amount.bank_ref = content
        elif hasattr(self, 'in_ref')\
            and self.in_ref:
            self.unassigned_amount.client_ref = content
        elif hasattr(self, 'in_client_name')\
            and self.in_client_name:
            self.unassigned_amount.client_name = content
        elif hasattr(self, 'in_creditor_IBAN')\
            and self.in_creditor_IBAN:
            self.unassigned_amount.creditor_IBAN = content
        else:
            super().characters(content)

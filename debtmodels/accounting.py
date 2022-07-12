#    Copyright 2021 Menno Hölscher
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

""" This is the accounting module. It holds the template object that modules
can use to inherit from for doing accounting.
"""

class AccountingTemplate(dict):
    """ Create accounting for an event

    The accounting is created as a dictionary, ready to be shipped as a 
    JSON formatted file.
    
    This class assumes that GLedger is being used. Subclass or replace to
    use a different GL system.
    """

    def __init__(self, event):

        super().__init__()
        self["journal"] = self._create_journal(event)

    def journal_entries(self, journal_dict, event):
        """ Create event dependent items in accounting 

        The method should create the postings and the external key extkey
        to create valid accounting for GLedger.
        """

        raise NotImplementedError("Subclass the template and implement journal_entries")

    def _create_journal(self, event):
        """ Create the journal for a event """

        journal_dict = dict()
        journal_dict["function"] = "insert"

        return self.journal_entries(journal_dict, event)


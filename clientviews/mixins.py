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

""" This module holds a PaginatorMixin for debtors """

class PaginatorMixin():
    """ A paginator voor viewing lists.

    A viewing list is a combination of a list of models
    and this mixin which "knows" how to page the list.
    """
    
    def __init__(self, list_creator, page=1, page_length=None):
        
        self.page = page
        self.page_length = page_length
        self.list_creator = list_creator

    def get_page(self, page_number=1):
        """  We get the data from the list creator for the page
        that was requested.
        """
        
        start_at = (page_number -1) * self.page_length
        list_for = self.page_length
        return self.list_creator(start_at=start_at, list_for=list_for)
        

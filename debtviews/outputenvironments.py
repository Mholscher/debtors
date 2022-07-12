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

""" This module holds the environments for jinja processing.

Originally built for bill production, it was also useful for overdue
processing and split off to its own module.
"""

from jinja2 import Environment, PackageLoader

rtfenvironment = Environment(
    loader=PackageLoader('debtors', 'templates'),
    block_start_string='<%', block_end_string='%>',
    variable_start_string='<<', variable_end_string='>>',
    trim_blocks=True, lstrip_blocks=True,
    autoescape=False)

htmlenvironment = Environment(
    loader=PackageLoader('debtors', 'templates'),
    autoescape=True)

def rtf(to_encode):
    """ This routine transcripts Unicode strings to be usable in
    rtf (rich text format) files.

    rtf supports Unicode, but not so nice. 
    You can enter codepoints in decimal (e.g. \\u233 is é), and after that 
    you have to insert a replacement character. The replacement character is simply the question mark for debtors.
    """

    result = ""
    if not to_encode:
        return to_encode
    for letter in to_encode:
        i = ord(letter)
        if i < 128:
            result = result + letter
        else:
            result = result + "\\u" + str(i) + '?'
    return result


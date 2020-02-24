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

""" In this module we find all the forms (wtforms) descriptions for 
the demo client system.
 """

from datetime import date
from flask_wtf import FlaskForm
from wtforms import HiddenField, StringField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from flask_wtf.csrf import CSRFProtect


class BirthDateBeforeToday(ValueError):
    """ This date validator checks that the date passed is not later
    than today.
    
    It is aimed at checking birth dates, that cannot be later than today.
    """

    message = 'Birth date cannot be after today'
    def __init__(self, message=None):

        if message:
            self.message = message

    def __call__(self, form, field):

        if field.data and field.data > date.today():
            raise ValidationError(self.message)


class ClientForm(FlaskForm):
    """ This form enables entering client data into the system """

    id = HiddenField('id')
    csrf_token = HiddenField('csrf_token')
    surname = StringField('Client surname', validators=[DataRequired(), Length(max=30)])
    initials = StringField('Initials', validators=[Length(max=10)])
    first_name = StringField('First name', validators=[Length(max=20)])
    birthdate = DateField('Birthdate', format='%d-%m-%Y', 
                          validators=[Optional(), BirthDateBeforeToday()])
    sex = StringField('Client sex')
    update = SubmitField('Update client and exit')
    addmore = SubmitField('Update, than add client')

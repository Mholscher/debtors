#    Copyright 2015 Menno Hölscher
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

""" This module contains the model data for the client demonstration system
delivered with debtors.

All models will be in this file, because the model is to be as simple as
can be. After all, it is just for showing what debtors needs.
"""
from datetime import date
from sqlalchemy.orm import validates
from debtors import db


class  NoSurnameError(ValueError):
    """ The surname cannot be empty """

    pass


class BirthDateError(ValueError):
    """ A birthdate cannot be in the future """

    pass


class InvalidSexError(ValueError):
    """ Sex maybe M (Male), F (Female) or space (unknown) """

    pass


class Clients(db.Model):
    """ Clients models the central part of a client

    The data that is central to the client (person or company) is held
    in this table. Data that can be multiple *(like addresses and
    bank accounts) will be held in separate tables.
    """
    
    __tablename__ = 'clients'
    id = db.Column(db.Integer, db.Sequence('client_sequence'), primary_key=True)
    surname = db.Column(db.String(30), index=True, nullable=False)
    first_name = db.Column(db.String(20))
    initials = db.Column(db.String(10))
    birthdate = db.Column(db.Date)
    sex = db.Column(db.String(1), server_default=' ')

    @validates('surname')
    def validate_surname(self, key, surname):
        """ A surname cannot be empty """

        if surname:
            return surname
        raise NoSurnameError('The surname of a client is mandatory')

    @validates('birthdate')
    def validate_birthdate(self, key, birthdate):
        """ A birthdate will be in the past """

        if birthdate > date.today():
            raise BirthDateError('Birthdate cannot be after today')
        return birthdate

    @validates('sex')
    def validate_sex_code(self, key, sex):
        """ Sex maybe M (Male), F (Female) or space (unknown) """

        if sex in {'M', 'F', ' '}:
            return sex
        raise InvalidSexError('{} is not a valid sex code'.format(sex))

    def add(self):
        """ Add this client to the session """

        db.session.add(self)
        return self

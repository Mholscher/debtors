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
from sqlalchemy import event
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


class NoPostalAddressError(Exception):
    """ No postal address was found """

    pass


class NoVillageError(ValueError):
    """ A town must have a town or village """

    pass


class NotAValidAddressType(ValueError):
    """ An address must have a valid type """

    pass


VALID_ADDRESS_TYPES = {'P', 'R', ' '}
POSTAL_ADDRESS = 'P'
RESIDENTIAL_ADDRESS = 'R'
GENERAL_ADDRESS = ' '


class Clients(db.Model):
    """ Clients models the central part of a client

    The data that is central to the client (person or company) is held
    in this table. Data that can be multiple (like addresses and
    bank accounts) will be held in separate tables.
    """
    
    __tablename__ = 'clients'
    id = db.Column(db.Integer, db.Sequence('client_sequence'), primary_key=True)
    surname = db.Column(db.String(30), index=True, nullable=False)
    first_name = db.Column(db.String(20))
    initials = db.Column(db.String(10))
    birthdate = db.Column(db.Date)
    sex = db.Column(db.String(1), server_default=' ')
    addrs = db.relationship('Addresses', backref='adressee')

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

    def postal_address(self):
        """ Return the correct postal address for this client.
        
        The algo is: return the address of type 'P', if none there ,
        return one of type ' ' (General). Neither one available,
        fail.
        """

        return Addresses.postal_address_for_client(self)


class Addresses(db.Model):
    """ Address records for a client. 
    
    These are the snail-mail addresses that we keep for the clients
    plus (if required) their residential address. These addresses
    are distinguished by a code, where space equals a 
    "general" address, residential and postal.filter
    """

    __tablename__ = 'addresses'
    id = db.Column(db.Integer, db.Sequence('address_seq'), primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'),
                          nullable=False)
    street = db.Column(db.String(25))
    house_number = db.Column(db.String(12))
    po_box = db.Column(db.String(12))
    town_or_village = db.Column(db.String(25))
    postcode = db.Column(db.String(10))
    country_code = db.Column(db.String(3), nullable=False)
    address_use = db.Column(db.String(1), nullable=False, default=' ')

    def add(self):
        """ Add 6this address to the session """

        db.session.add(self)
        return self

    @validates('street')
    def validate_street(self, key, street):
        """ Validate street """

        if street and self.po_box:
            raise ValueError('Fill either a street or po box')
        return street

    @validates('house_number')
    def validate_house_number(self, key, house_number):
        """ Validate house_number """

        if house_number and self.po_box:
            raise ValueError('Fill either a house_number or po box')
        return house_number

    @validates('po_box')
    def validate_po_box(self, key, po_box):
        """ Validate po_box """

        if po_box and (self.street or self.house_number):
            raise ValueError('Fill either a po_box or po box')
        return po_box

    @validates('town_or_village')
    def validate_town(self, key, town_or_village):
        """ An address must have a town or village """

        if town_or_village:
            return town_or_village
        raise NoVillageError('An address must have a town or village')

    @validates('address_use')
    def validate_address_use(self, key, address_use):
        """ Validate address useful
        
            :Rule 1: Only valid values
            :Rule 2: A po_box address must be postal

        """

        if not address_use:
            address_use = ' '
        #Rule 1
        if not address_use in VALID_ADDRESS_TYPES:
            raise NotAValidAddressType('{} is not a valid type'.format(address_use))
        #Rule 2
        if self.po_box and not self.street:
            address_use = POSTAL_ADDRESS
        return address_use

    @staticmethod
    def postal_address_for_client(client):
        """ Return *one* postal address for a client """

        postal_addresses = [x for x in client.addrs if x.address_use == 'P']
        if postal_addresses:
            return postal_addresses[0]
        general_addresses = [x for x in client.addrs 
                             if x.address_use in {' ', None}]
        if general_addresses:
            return general_addresses[0]
        raise NoPostalAddressError(f'A postal addres could not be found: {client.surname}')
        
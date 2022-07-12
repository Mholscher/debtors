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
from datetime import date, datetime
from sqlalchemy import event, text
from sqlalchemy.orm import validates, Session
from debtors import db

query = db.session.query

class  NoSurnameError(ValueError):
    """ The surname cannot be empty """

    pass


class BirthDateError(ValueError):
    """ A birthdate cannot be in the future """

    pass


class InvalidSexError(ValueError):
    """ Sex maybe M (Male), F (Female) or space (unknown) """

    pass

class NoClientFoundError(ValueError):
    """ A request did not find a client """

    pass


class NoAddressFoundError(Exception):
    """ No postal address was found """

    pass


class NoPostalAddressError(Exception):
    """ No postal address was found """

    pass


class NoResidentialAddressError(Exception):
    """ No residetial address was found """

    pass


class NoVillageError(ValueError):
    """ A town must have a town or village """

    pass


class NotAValidAddressType(ValueError):
    """ An address must have a valid type """

    pass


class InvalidIBANError(ValueError):
    """ An IBAN failed the check for a valid checksum """

    pass


class NoAccountFoundError(ValueError):
    """ No account found for the requested id or IBAN """

    pass


class DuplicateMailError(Exception):
    """ A mail address must be unique for a client """

    pass

class TooManyPreferredMailsError(Exception):
    """ Only one mail address can be preferred """

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
    updated_at = db.Column(db.DateTime, onupdate=datetime.now,
                           default=datetime.now)
    addrs = db.relationship('Addresses', backref='addressee',
                            cascade='all, delete')
    emails = db.relationship('EMail', backref='to',
                            cascade='all, delete')
    accounts = db.relationship('BankAccounts', backref='owner',
                            cascade='all, delete')

    @validates('surname')
    def validate_surname(self, key, surname):
        """ A surname cannot be empty """

        if surname:
            return surname
        raise NoSurnameError('The surname of a client is mandatory')

    @validates('birthdate')
    def validate_birthdate(self, key, birthdate):
        """ A birthdate will be in the past """

        if not birthdate:
            return birthdate
        if birthdate > date.today():
            raise BirthDateError('Birthdate cannot be after today')
        return birthdate

    @validates('sex')
    def validate_sex_code(self, key, sex):
        """ Sex maybe M (Male), F (Female) or space (unknown) """

        if not sex:
            sex = ' '
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

    def residential_address(self):
        """ Return the correct residential address for the client """

        return Addresses.residential_addres_for_client(self)

    def preferred_mail(self):
        """ Return the preferred mail address for the client """

        return EMail.preferred_mail_for_client(self)

    @staticmethod
    def get_by_id(requested_id):
        """ Get the client with the supplied id """

        client = query(Clients).filter(Clients.id == requested_id).first()
        if client:
            return client
        raise NoClientFoundError('No client with id {}'.format(requested_id))

    @staticmethod
    def get_client_by_iban(iban):
        """ Get a client by IBAN

        If more than one client exists with this IBAN (Compte Jointe)
        we return an error, also when the IBAN does not occur in the
        database.
        """

        try:
            return BankAccounts.get_account_by_iban(iban).owner
        except NoAccountFoundError as naf:
            raise NoClientFoundError(str(naf)) from naf

    @staticmethod
    def get_clients_by_name(surname):
        """ Get a list of clients with the surname supplied """

        return query(Clients).filter(Clients.surname == surname).all()

    @staticmethod
    def client_list(start_at=0, list_for=None, search_for=None):
        """ Return a list of clients """

        client_list = query(Clients).order_by(Clients.updated_at.desc())
        if search_for:
            client_list =client_list.\
                filter(Clients.surname.like('%' + search_for + '%'))
        if start_at:
            client_list = client_list.offset(start_at)
        if list_for:
            client_list = client_list.limit(list_for)
        return client_list.all()


class Addresses(db.Model):
    """ Address records for a client. 
    
    These are the snail-mail addresses that we keep for the clients
    plus (if required) their residential address. These addresses
    are distinguished by a code, where space equals a 
    "general" address, residential and postal.
    """

    __tablename__ = 'addresses'
    id = db.Column(db.Integer, db.Sequence('address_seq'), primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id',
                                                    ondelete='CASCADE'),
                          nullable=False)
    street = db.Column(db.String(25))
    house_number = db.Column(db.String(12))
    po_box = db.Column(db.String(12))
    town_or_village = db.Column(db.String(25))
    postcode = db.Column(db.String(10))
    country_code = db.Column(db.String(3), nullable=False)
    address_use = db.Column(db.String(1), nullable=False, default=' ')

    def add(self):
        """ Add this address to the session """

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
            raise ValueError('Fill either a po_box or house number')
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

    @staticmethod
    def residential_addres_for_client(client):
        """ Return one residential address for a client.

        If the client has at least one address marked residential, return
        that. Otherwise return one general address.
        If no residential or general address is available,
        fail.
        """

        residential_addresses = [x for x in client.addrs\
            if x.address_use == RESIDENTIAL_ADDRESS]
        if residential_addresses:
            return residential_addresses[0]
        residential_addresses = [x for x in client.addrs\
            if x.address_use == GENERAL_ADDRESS]
        if residential_addresses:
            return residential_addresses[0]
        raise NoResidentialAddressError(f'No residential address found: {client.surname}')

    @staticmethod
    def get_by_id(id=None):
        """ Return an address by id """

        address = db.session.query(Addresses).filter_by(id = id).first()
        if address is None:
            raise NoAddressFoundError(f'No address for id {id}')
        return address

    def delete_address(self):
        """ Delete this address form the database """

        db.session.delete(self)


class EMail(db.Model):
    """ Electronic mail addresses for a client

    It is just an electronic mail address for the client, plus an
    indicator telling if an address is preferred to contact the client.
    """

    __tablename__ = 'email'
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id',
                                                    ondelete='CASCADE'),
                          nullable=False)
    mail_address = db.Column(db.String(65), primary_key=True, nullable=False,
                             index=True)
    preferred = db.Column(db.Integer, server_default=text("0"))

    def add(self):
        """ Add this address to the session """

        db.session.add(self)

    @staticmethod
    def preferred_mail_for_client(client):
        """ Return the preferred mail address for client """

        mail_address = [x.mail_address for x in client.emails if x.preferred]
        if mail_address:
            return mail_address[0]
        return client.emails[0].mail_address if client.emails else None

    def check_duplicates(self, session):
        """ The check searches for duplicates of this mail address.

        It can only be executed after all changes in a transaction
        are completed, i.e. typically in the before_flush event.
        N.B. The passing of the session is a hack; you can get it also
        as the global session, but this makes the importance of the 
        session for the process clearer.
        """

        for email in self.to.emails:
            if email.mail_address == self.mail_address\
                and email != self\
                and not email in session.deleted:
                    raise DuplicateMailError('Can not have equal addresses for client')

    def check_preferred(self, session):
        """ Check that at most one address is preferred """

        count = 0
        for email in self.to.emails:
            if email.preferred:
                count += 1
        if count > 1:
            raise TooManyPreferredMailsError('Only one preferred mail address allowed')

    def check_before_flushing(self, session):
        """ Do all before flushing checks """

        self.check_duplicates(session)
        self.check_preferred(session)


class BankAccounts(db.Model):
    """ Bank accounts for a client
    
    Each account is identified for the outside world by a IBAN.
    Other account numbers are not supported. The bank account use
    is for billing and receipt processing. No balances or so
    are being maintained.
    """

    __tablename__ = 'bankaccounts'
    id = db.Column(db.Integer, db.Sequence('bankacc-seq'), primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id',
                                                    ondelete='CASCADE'),
                          nullable=False)
    iban = db.Column(db.String(40), nullable=True, index=True)
    bic = db.Column(db.String(10), nullable=True)
    client_name = db.Column(db.String(60))

    """ Translate table for IBAN checks; mind you: ASCII/Unicode specific! """
    iban_trans = {x : str(x - 87) for x in range(97, 123)}

    def add(self):
        """ Add this account to the database session """

        db.session.add(self)

    @validates("iban")
    def validate_iban(self, key, iban):
        """ Validate an IBAN using the 97-test."""

        if iban is None or iban == '':
            raise InvalidIBANError('An IBAN is required')
        check_digit = int(iban[2:4])
        if check_digit < 2 or check_digit > 98:
            raise InvalidIBANError('Check digit invalid')
        recomposed = (iban[4:len(iban)] + iban[0:4]).lower()
        recomposed = recomposed.translate(self.iban_trans)
        if int(recomposed) % 97 == 1:
            return iban
        raise InvalidIBANError('IBAN failed checksum test')

    def delete(self):
        """ Delete this account from the session """

        db.session.delete(self)

    def check_account_name(self, session):
        """ Check that the account name is not empty. If it is empty,
        default to the initials and name of the client.

        This should be done just before flushing, when everything is
        filled.
        """

        if self.client_name is None or self.client_name == '':
            self.client_name = self.owner.initials + ' ' + self.owner.surname

    def check_before_flushing(self, session):

        self.check_account_name(session)

    @staticmethod
    def get_account_by_iban(iban):
        """ Get the data of an account based on a supplied iban """

        accounts = query(BankAccounts).filter(BankAccounts.iban == iban).all()
        if len(accounts) == 0:
            raise NoAccountFoundError('No account for {}'.format(iban))
        if len(accounts) > 1:
            raise MoreThanOnAccountError('More than 1 account for {}'.format(iban))
        return accounts[0]

    @staticmethod
    def get_by_id(id):
        """ Get a bank account by its id """

        account = query(BankAccounts).filter(BankAccounts.id == id).first()
        if account is None:
            raise NoAccountFoundError('No account for this id')
        return account

@event.listens_for(Session, "before_flush")
def before_flush(session, flush_context, instances):
    """ This is the place to do cross item edits.

    All items are ready to be persisted and need no more
    updates.
    """

    for instance in session.dirty | session.new:
        if isinstance(instance, EMail) or isinstance(instance, BankAccounts):
            instance.check_before_flushing(session)

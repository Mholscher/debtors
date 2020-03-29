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

""" The test helpers are functions which are used in different test sources.

Placing these in one helper .py file helps re-use and prevents writing similar
code more than once.
"""

from datetime import datetime, date
from clientmodels.clients import Clients, Addresses, NoPostalAddressError,\
    POSTAL_ADDRESS, RESIDENTIAL_ADDRESS, GENERAL_ADDRESS, EMail,\
        DuplicateMailError, TooManyPreferredMailsError, BankAccounts,\
        NoResidentialAddressError, NoClientFoundError
from debtors import db


def create_clients(instance):
    """ Create clients for the test 'instance' """

    if not hasattr(instance, 'client_list'):
        instance.client_list = []
    instance.clt1 = Clients(surname='Karmozijn',
                            initials='K.T.Y.',
                            first_name='Karel')
    instance.clt1.add()
    instance.client_list.append(instance.clt1.surname)
    instance.clt2 = Clients(surname='Petrol',
                            initials='C.R.',
                            birthdate=date(1988, 3, 12),
                            sex='F')
    instance.clt2.add()
    instance.client_list.append(instance.clt2.surname)
    instance.clt3 = Clients(surname='Aquamarijn',
                            initials='P.J.',
                            first_name='Peter',
                            birthdate=date(1998, 3, 17),
                            sex='M')
    instance.clt3.add()
    instance.client_list.append(instance.clt3.surname)
    instance.clt4 = Clients(surname='Turkoois',
                            initials='G.',
                            first_name='Gerrit',
                            birthdate=date(1982, 1, 17),
                            sex='M')
    instance.clt4.add()
    instance.client_list.append(instance.clt4.surname)
    instance.clt5 = Clients(surname='Aubergine',
                            initials='A.R.',
                            first_name='Antoinette',
                            birthdate=date(1981, 11, 14),
                            sex='F')
    instance.clt5.add()
    instance.client_list.append(instance.clt5.surname)
    instance.clt6 = Clients(surname='Oker',
                            initials='D.R.',
                            first_name='Drella',
                            birthdate=date(1968, 12, 12),
                            sex='M')
    instance.clt6.add()
    instance.client_list.append(instance.clt6.surname)

def spread_created_at(instance):
    """ This routine is used on the production of create_clients """

    instance.clt1.updated_at = datetime(2018, 11, 3, hour=12, minute=17)
    instance.clt2.updated_at = datetime(2016, 9, 14, hour=12, minute=7)
    instance.clt3.updated_at = datetime(2018, 11, 3, hour=13, minute=7)
    instance.clt4.updated_at = datetime(2014, 2, 2, hour=2, minute=37)
    instance.clt5.updated_at = datetime(2017, 10, 1, hour=14, minute=55)
    instance.clt6.updated_at = datetime(2011, 1, 2, hour=0, minute=25)

def add_addresses(instance):
    """ This routine adds addresses to clients. """

    instance.adr20 = Addresses(street='Wilhelminastraat',
                            town_or_village='Meddo',
                            house_number='12',
                            postcode='8822 DH', country_code='NLD',
                            address_use=GENERAL_ADDRESS)
    instance.clt1.addrs.append(instance.adr20)
    instance.adr21 = Addresses(street='Vrijheidsplein',
                            town_or_village='Enschede',
                            house_number='78',
                            postcode='7821 HJ', country_code='NLD',
                            address_use=RESIDENTIAL_ADDRESS)
    instance.clt2.addrs.append(instance.adr21)
    instance.adr22 = Addresses(po_box ='12',
                            town_or_village='Hengelo',
                            postcode='2822 AJ', country_code='NLD',
                            address_use=POSTAL_ADDRESS)
    instance.clt2.addrs.append(instance.adr22)
    instance.adr23 = Addresses(street='Beukenlaan',
                            town_or_village='Zeist',
                            house_number='52',
                            postcode='3812 DG', country_code='NLD',
                            address_use=GENERAL_ADDRESS)
    instance.clt4.addrs.append(instance.adr23)
    instance.adr24 = Addresses(street='Zeugnisstraße',
                            town_or_village='Neuenrath',
                            house_number='34',
                            postcode='6798', country_code='DEU',
                            address_use=GENERAL_ADDRESS)
    instance.clt4.addrs.append(instance.adr24)
    instance.adr25 = Addresses(street='Stationsplein',
                            town_or_village='Dinxperlo',
                            house_number='123',
                            postcode='8815 JJ', country_code='NLD',
                            address_use=GENERAL_ADDRESS)
    instance.clt5.addrs.append(instance.adr25)
    instance.clt6.addrs.append(instance.adr23)
    # Mail addresses
    instance.mad01 = EMail(mail_address='dingor@prov.com')
    instance.clt1.emails.append(instance.mad01)
    instance.mad02 = EMail(mail_address='nogor@oprov.com')
    instance.clt2.emails.append(instance.mad02)
    instance.mad03 = EMail(mail_address='snipper12@gierton.org')
    instance.clt2.emails.append(instance.mad03)
    instance.mad04 = EMail(mail_address='bozeboer@tractie.nl')
    instance.clt4.emails.append(instance.mad04)
    instance.mad05 = EMail(mail_address='klap.noot@prov.com')
    instance.clt5.emails.append(instance.mad05)
    instance.mad06 = EMail(mail_address='snodeplanner@bedrijf.co.uk')
    instance.clt6.emails.append(instance.mad06)
    # Bank accounts
    instance.ba1 = BankAccounts(iban='NL45INGB0162029659',
                                client_name='F. Wanders')
    instance.clt1.accounts.append(instance.ba1)
    instance.ba2 = BankAccounts(iban='NL08INGB0212952803',
                                client_name=None)
    instance.clt2.accounts.append(instance.ba2)
    instance.ba3 = BankAccounts(iban='NL94INGB0264350197',
                                client_name=None)
    instance.clt3.accounts.append(instance.ba3)
    instance.ba4 = BankAccounts(iban='NL76INGB0395563003',
                                client_name='Peter Aquamarijn')
    instance.clt3.accounts.append(instance.ba4)
    instance.ba5 = BankAccounts(iban='NL76INGB0594788005',
                                client_name=None)
    instance.clt5.accounts.append(instance.ba5)
    instance.ba6 = BankAccounts(iban='NL95INGB0696154021',
                                client_name=None)
    instance.clt6.accounts.append(instance.ba6)

def delete_test_clients(instance):
    """ Delete clients and dependants added in create_clients """

    client_list =\
        db.session.query(Clients).filter(Clients.surname.in_(instance.client_list)).all()
    for client in client_list:
        db.session.delete(client)



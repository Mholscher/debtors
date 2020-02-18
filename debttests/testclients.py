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
import unittest
from debtors import db
from datetime import date, timedelta
from clientmodels.clients import Clients, Addresses, NoPostalAddressError,\
    POSTAL_ADDRESS, RESIDENTIAL_ADDRESS, GENERAL_ADDRESS, EMail,\
        DuplicateMailError, TooManyPreferredMailsError, BankAccounts,\
        NoResidentialAddressError


class TestCreateClient(unittest.TestCase):

    def setUp(self):

        pass

    def tearDown(self):

        db.session.rollback()

    def test_create_client(self):
        """ We can create a client """

        clt01 = Clients(surname='Janzen', first_name='Piet',
                        initials='J.P.I', birthdate=date(2002, 1, 23),
                        sex='M')
        db.session.add(clt01)
        db.session.flush()
        self.assertTrue(clt01.id, 'Creating failed')

    def test_no_surname_fails(self):
        """ If surname is none,fail  """

        with self.assertRaises(ValueError):
            clt02 = Clients(surname=None, first_name='Piet',
                        initials='J.P.I', birthdate=date(2002, 1, 23),
                        sex='M')
            clt02.add()
            db.session.flush()

    def test_birth_date_in_past(self):
        """ A birthdate cannot be in the future  """

        today_plus = date.today() + timedelta(days=4)
        with self.assertRaises(ValueError):
            clt02 = Clients(surname='Veldhuis', first_name='Mees',
                        initials='M.H.', birthdate=today_plus,
                        sex='M')
            clt02.add()
            db.session.flush()

    def test_sex_m_f_or_u(self):
        """ Sex can only be m, f or unknown (=empty) """

        clt03 = Clients(surname='Velde, v.d.', first_name='Ab',
                        birthdate=date(1981, 10, 4), sex='M')
        clt04 = Clients(surname='Velde, v.d.', first_name='Caroline',
                        birthdate=date(1982, 1, 14), sex='F')
        clt05 = Clients(surname='Velde, v.d.', first_name='Noah',
                        birthdate=date(2001, 8, 1), sex=' ')
        clt03.add()
        clt04.add()
        clt05.add()
        self.assertEqual(clt03.sex, 'M', 'Wrong sex for Ab')
        self.assertEqual(clt04.sex, 'F', 'Wrong sex for Caroline')
        self.assertEqual(clt05.sex, ' ', 'Wrong sex for Noah')
        with self.assertRaises(ValueError):
            clt06 = Clients(surname='Velde, v.d.', first_name='Sien',
                            birthdate=date(2004, 7, 1), sex='T')
            clt06.add()
            db.session.flush()


class TestAddressCreate(unittest.TestCase):

    def setUp(self):

        self.clt07 = Clients(surname='Gershuis', first_name='Simon',
                        initials='S.N.', birthdate=date(1981, 10, 4),
                        sex='M')
        self.clt07.add()
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_create_address(self):
        """ We can create an address """

        adr01 = Addresses(street='Wall Street', house_number='5',
                        town_or_village='New York', postcode='320Y',
                        country_code='USA', client_id=self.clt07.id)
        adr01.add()
        self.assertEqual(self.clt07.addrs[0], adr01, 'Not added to addresses')

    def test_add_address_to_client(self):
        """ We add an address through the client """

        adr02 = Addresses(street='High Street', house_number='76',
                        town_or_village='Aberdeen', postcode='320Y 123',
                        country_code='GBR')
        self.clt07.addrs.append(adr02)
        db.session.flush()
        self.assertEqual(adr02.client_id, self.clt07.id, 'Foreign key incorrect')

    def test_address_no_client_fails(self):
        """ Cannot add an address without client """

        adr03 = Addresses(street='Peterplatz', house_number='12',
                        town_or_village='Neu Schwanden', postcode='14600',
                        country_code='DEU')
        
        with self.assertRaises(Exception):
            adr03.add()
            db.session.flush()

    def test_po_box_or_street(self):
        """ Either a street address or po box is filled """

        with self.assertRaises(ValueError):
            adr04 = Addresses(street='Schlossplatz', house_number='21',
                              town_or_village='Weinsteg', postcode='146',
                              country_code='DEU', po_box='34')
            self.clt07.addrs.append(adr04)
            db.session.flush()
 
    def test_po_box_street_2(self):
        """ Either a house number or po box is filled """

        with self.assertRaises(ValueError):
            adr05 = Addresses(house_number='21',
                              town_or_village='Weinsteg', postcode='146',
                              country_code='DEU', po_box='34')
            self.clt07.addrs.append(adr05)
            db.session.flush()

    def test_po_box_only_postal(self):
        """ A po_box is always postal """

        adr13 = Addresses(po_box='134',town_or_village='Neu Schwanden',
                          postcode='14600', address_use=' ',
                          country_code='DEU')
        self.clt07.addrs.append(adr13)
        db.session.flush()
        adr13 = db.session.query(Addresses).filter(Addresses.id == adr13.id).\
            one()
        self.assertEqual(adr13.address_use, POSTAL_ADDRESS, 
                         'Postbox in non postal address')

    def test_address_must_have_town(self):
        """ An address should have a town, always """
        
        with self.assertRaises(Exception):
            adr06 = Addresses(street='Back Street', house_number='11',
                              town_or_village=None, postcode='3WY DF6',
                              country_code='GBR')
            self.clt07.addrs.append(adr06)
            db.session.flush()

    def test_invalid_address_use_fails(self):
        """ We should not have invalid address use """

        with self.assertRaises(ValueError):
            adr13 = Addresses(po_box='134',town_or_village='Tesken',
                          postcode='100', address_use='T',
                          country_code='DEU')
            self.clt07.addrs.append(adr13)
            db.session.flush()


class TestAddressUse(unittest.TestCase):

    def setUp(self):

        self.clt08 = Clients(surname='Dalsberg', first_name='Philip',
                        initials='P.N.', birthdate=date(1967, 2, 1),
                        sex='M')
        self.clt08.add()
        self.adr07 = Addresses(po_box='44', town_or_village='Naaldwijk',
                               postcode='1454 DP', country_code='NLD',
                               address_use=POSTAL_ADDRESS)
        self.clt08.addrs.append(self.adr07)
        self.adr08 = Addresses(street='Wolkersplein', house_number='44',
                               town_or_village='Naaldwijk',
                               postcode='1454 GH', country_code='NLD',
                               address_use=RESIDENTIAL_ADDRESS)
        self.clt08.addrs.append(self.adr08)
        self.clt09 = Clients(surname='Notenberg', first_name='Anna',
                        initials='A,M.', birthdate=date(1972, 8, 11),
                        sex='F')
        self.clt09.add()
        self.adr09 = Addresses(street='Kerkstraat', house_number='5',
                               town_or_village='Zeddam',
                               postcode='4545 HN', country_code='NLD',
                               address_use=GENERAL_ADDRESS)
        self.clt09.addrs.append(self.adr09)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_client_returns_postal_address(self):
        """ When requested, the postal address is returned """

        adr10 = self.clt08.postal_address()
        self.assertEqual(adr10, self.adr07, 'Incorrect address returned')

    def test_general_address_preferred(self):
        """ If there is only a general addres, it is postal """

        adr11 = self.clt09.postal_address()
        self.assertEqual(adr11, self.adr09, 'General address not returned')

    def test_prefer_postal(self):
        """ From a general and postal address, postal is preferred """

        adr12 = Addresses(street='Hermansweg', house_number='41',
                            town_or_village='Naaldwijk',
                            postcode='1454 GJ', country_code='NLD',
                            address_use=GENERAL_ADDRESS)
        self.clt08.addrs.append(adr12)
        adr10 = self.clt08.postal_address()
        self.assertEqual(adr10, self.adr07, 'Incorrect address returned')

    def test_no_postal_address(self):
        """ No postal address for a client fails  """

        adr12 = db.session.query(Addresses).\
            filter(Addresses.id == self.adr09.id).one()
        adr12.address_use = RESIDENTIAL_ADDRESS
        db.session.flush()
        with self.assertRaises(NoPostalAddressError):
            adr12 = self.clt09.postal_address()

    def test_no_residential_address(self):
        """ No residential address fails when getting residential address """

        clt13 = Clients(surname='Kansom', initials='G.J.',
                        sex='M')
        adr18 = Addresses(po_box='12', town_or_village='Ootmarsum',
                         address_use=POSTAL_ADDRESS)
        clt13.addrs.append(adr18)
        db.session.flush()
        with self.assertRaises(NoResidentialAddressError):
            adr19 = clt13.residential_address()
        


class TestMailAddress(unittest.TestCase):

    def setUp(self):

        self.clt10 = Clients(surname='Snavelaar', first_name='Karel',
                        initials='K.T.', birthdate=date(1971, 4, 5),
                        sex='M')
        self.clt10.add()
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_add_mail_address(self):
        """ We can add a first mail address """

        mad01 = EMail(mail_address='ksnavelaar@gmail.com')
        self.clt10.emails.append(mad01)
        db.session.flush()
        self.assertEqual(self.clt10.emails[0].mail_address,
                         'ksnavelaar@gmail.com', 
                         'Email not added')
    def test_add_more_than_one(self):
        """ We can add more than one mail address """

        mad02 = EMail(mail_address='ksnavelaar@gmail.com')
        self.clt10.emails.append(mad02)
        mad03 = EMail(mail_address='praatgraag@ziggo.nl')
        self.clt10.emails.append(mad03)        
        db.session.flush()
        self.assertEqual(len(self.clt10.emails), 2, 'No 2 emails for client')

    def test_cannot_add_mail_twice(self):
        """ We cannot add the same mail address twice """

        with self.assertRaises(DuplicateMailError):
            mad04 = EMail(mail_address='schnitzel@gmail.com')
            self.clt10.emails.append(mad04)
            mad05 = EMail(mail_address='schnitzel@gmail.com')
            self.clt10.emails.append(mad05)        
            db.session.flush()

    def test_delete_duplicate(self):
        """ We can add a mail address after we deleted a duplicate """

        mad06 = EMail(mail_address='saucijs@gmail.com')
        self.clt10.emails.append(mad06)
        db.session.flush()
        db.session.delete(mad06)
        mad07 = EMail(mail_address='saucijs@gmail.com')
        self.clt10.emails.append(mad07)        
        db.session.flush()
        self.assertEqual(self.clt10.emails[0], mad06, 'Wrong mail address on client')

    def test_can_set_preferred(self):
        """ We can set a preferred mail address """

        mad10 = EMail(mail_address='bigmouth@gmail.com', preferred=1)
        self.clt10.emails.append(mad10)
        db.session.flush()
        self.assertTrue(self.clt10.emails[0].preferred, 'Email address not preferred')

    def test_client_knows_preferred(self):
        """ We can find the preferred mail address for a client """

        mad11 = EMail(mail_address='nondescrip@gmail.com', preferred=1)
        self.clt10.emails.append(mad11)
        mad12 = EMail(mail_address='verydescrip@gmail.com')
        self.clt10.emails.append(mad12)
        db.session.flush()
        self.assertEqual(self.clt10.preferred_mail(), mad11,
                         'Client did not return preferred address')

    def test_no_preferred_any_will_do(self):
        """ No preferred address for client, than any will do """

        mad13 = EMail(mail_address='any1@gmail.com', preferred=1)
        self.clt10.emails.append(mad13)
        mad14 = EMail(mail_address='any2@gmail.com')
        self.clt10.emails.append(mad14)
        db.session.flush()
        self.assertIn(self.clt10.preferred_mail(), {mad13, mad14},
                      'Invalid/no mail returned')
        

    def test_cannot_set_preferred_twice(self):
        """ We should not be able to set preferred on 2 addresses """

        with self.assertRaises(TooManyPreferredMailsError):
            mad08 = EMail(mail_address='bigmouth@gmail.com', preferred=1)
            self.clt10.emails.append(mad08)
            mad09 = EMail(mail_address='maggie@gmail.com', preferred=1)
            self.clt10.emails.append(mad09)        
            db.session.flush()


class TestBankAccounts(unittest.TestCase):

    def setUp(self):

        self.clt11 = Clients(surname='Gijzen', first_name='Fien',
                        initials='F.', birthdate=date(1941, 4, 16),
                        sex='F')
        self.clt11.add()
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_can_create_account(self):
        """ We can create a new bankaccount """

        ba01 = BankAccounts(iban='NL82INGB0001789067', 
                            client_name='Mevr. F. Gijzen')
        self.clt11.accounts.append(ba01)
        db.session.flush()
        self.assertEqual(self.clt11.accounts[0].client_name,
                         'Mevr. F. Gijzen', 'Name account owner incorrect')

    def test_name_defaults(self):
        """ No name specified? Default is initials + surname """

        ba02 = BankAccounts(iban='NL82INGB0001789067') 
        self.clt11.accounts.append(ba02)
        db.session.flush()
        self.assertEqual(self.clt11.accounts[0].client_name, 
                         (self.clt11.initials + ' ' + self.clt11.surname),
                         'Name default not set correctly')

    def test_reject_failed_checksum(self):
        """ An account number with invalid checksum is rejected """

        with self.assertRaises(ValueError):
            ba03 = BankAccounts(iban='NL02ABNA0123456780',
                                client_name='W. Vanderman')
            self.clt11.accounts.append(ba03)
            db.session.flush()

    def test_reject_on_control(self):
        """ An account number with invalid control digits is rejected """

        with self.assertRaises(ValueError):
            ba04 = BankAccounts(iban='NL01ABNA0123456789',
                                client_name='W. Vanderman')
            self.clt11.accounts.append(ba04)
            db.session.flush()
        with self.assertRaises(ValueError):
            ba05 = BankAccounts(iban='NL99ABNA0123456789',
                                client_name='W. Vanderman')
            self.clt11.accounts.append(ba05)
            db.session.flush()

    def test_iban_mandatory(self):
        """ The IBAN is mandatory """

        with self.assertRaises(ValueError):
            ba06 = BankAccounts(iban=None,
                                client_name='W. Vanderman')
            self.clt11.accounts.append(ba06)
            db.session.flush()


class TestDebtorInterface(unittest.TestCase):

    def setUp(self):

        self.clt12 = Clients(surname='Jansen', first_name='Tycho',
                        initials='T.M.', birthdate=date(1971, 2, 23),
                        sex='M')
        self.clt12.add()
        self.adr14 = Addresses(po_box='42', town_or_village='Den Haag',
                               postcode='2754 DP', country_code='NLD',
                               address_use=POSTAL_ADDRESS)
        self.clt12.addrs.append(self.adr14)
        self.adr15 = Addresses(street='Willemsstraat',
                               town_or_village='Naaldwijk',
                               house_number='77',
                               postcode='2822 GH', country_code='NLD',
                               address_use=RESIDENTIAL_ADDRESS)
        self.clt12.addrs.append(self.adr15)
        self.mad15 = EMail(mail_address='tyhoj@aprovider.com')
        self.clt12.emails.append(self.mad15)
        self.mad16 = EMail(mail_address='tyhoj@otherprovider.com',
                           preferred=True)
        self.clt12.emails.append(self.mad16)
        self.ba07 = BankAccounts(iban='GB33BUKB20201555555555', 
                            client_name='Tycho Jansen')
        self.clt12.accounts.append(self.ba07)
        self.ba08 = BankAccounts(iban='NL83INSI0807135747', 
                            client_name='T.M. Jansen')
        self.clt12.accounts.append(self.ba08)        
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_get_postal_address(self):
        """ We get the correct postal address """

        adr16 = self.clt12.postal_address()
        self.assertEqual(adr16, self.adr14, 'Wrong postal address')

    def test_get_residential_address(self):
        """ We can get the residential address """

        adr17 = self.clt12.residential_address()
        self.assertEqual(adr17, self.adr15, 'Wrong residential address')

    def test_get_bank_account_list(self):
        """ We can get a list of bank accounts for a client """

        account_list = self.clt12.accounts
        self.assertEqual(len(account_list), 2, f'Wrong no. of accounts: {len(account_list)}') 
        self.assertIn(self.ba08, account_list, 'Account missing')

    def test_get_acccount_data_by_iban(self):
        """  We can get account data by IBAN """

        ba09 = BankAccounts.get_account_by_iban(self.ba08.iban)
        self.assertEqual(ba09.client_name, self.ba08.client_name,
                         'Wrong account data returned')

    def test_get_client_by_iban(self):
        """ Get a client from IBAN """

        clt14 = Clients.get_client_by_iban(self.ba08.iban)
        self.assertEqual(clt14, self.clt12, 'Wrong client returned')

    def test_get_client_by_name(self):
        """ Get a client by surname """

        clt_list01 = Clients.get_clients_by_name(self.clt12.surname)
        self.assertEqual(clt_list01[0].surname, self.clt12.surname, 
                         'Client returned with wrong surname')

    def test_more_clients_same_name(self):
        """ More clients with the same surname are returned """

        clt15 = Clients(surname='Jansen', first_name='Arne',
                        sex='M')
        clt15.add()
        db.session.flush()
        clt_list02 = Clients.get_clients_by_name(self.clt12.surname)
        self.assertEqual(len(clt_list02), 2, 'Not the correct no. of Clients returned')


if __name__ == '__main__' :
    unittest.main()

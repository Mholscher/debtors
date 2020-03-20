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
from debtors import db, app
from datetime import date, timedelta, datetime
from clientmodels.clients import Clients, Addresses, NoPostalAddressError,\
    POSTAL_ADDRESS, RESIDENTIAL_ADDRESS, GENERAL_ADDRESS, EMail,\
        DuplicateMailError, TooManyPreferredMailsError, BankAccounts,\
        NoResidentialAddressError, NoClientFoundError
from clientviews.clients import ClientViewingList


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


class TestClientFunctions(unittest.TestCase):

    def setUp(self):

        self.clt16 = Clients(surname='Zwaluwen', first_name='Job',
                        initials='J.N.', birthdate=date(1984, 11, 2),
                        sex='M')
        self.clt16.add()
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_get_by_id(self):
        """ Get a client by its id """

        clt17 = Clients.get_by_id(self.clt16.id)
        self.assertEqual(clt17.id, self.clt16.id, 'Get client with wrong id')

    def test_invalid_client_id_fails(self):
        """ An invalid id fails """

        with self.assertRaises(ValueError):
            clt18 = Clients.get_by_id(1)

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

    def test_delete_address(self):
        """ We can delete an address """

        adr14 = Addresses(street='Rue des Promesses', house_number='1',
                              town_or_village='La Vilette', postcode='54765',
                              country_code='FRA')
        self.clt07.addrs.append(adr14)
        db.session.flush()
        self.assertIn(adr14, self.clt07.addrs, 'Failed to add address')
        adr14.delete_address()
        db.session.flush()
        self.assertNotIn(adr14, db.session.deleted, 'Address not deleted')


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


class TestAddressFunctions(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        add_addresses(self)
        db.session.flush()
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):

        db.session.rollback()

    def test_add_address(self):
        """ We can add an address to a client having an address """

        id = self.clt1.id
        address_dict = dict(street='Oude Gangsteeg', house_number='42',
                           postcode='4234 KK', town_or_village='Meppel',
                           country='NLD', address_use=GENERAL_ADDRESS)
        rv = self.app.post('/client/' + str(self.clt1.id) + '/address/new',
                           data=address_dict, follow_redirects=True)
        self.clt1 = Clients.query.filter(Clients.id == id).first()
        self.assertEqual(len(self.clt1.addrs), 2, 'Address too many/missing')
        delete_test_clients(self)
        db.session.commit()

    def test_get_delete_address_confirmation(self):
        """ We can request the confirmation screenh for a delete """

        rv = self.app.get('/client/' + str(self.clt4.id) + '/address/'\
            + str(self.adr23.id) + '/confirm')
        self.assertIn(b'Beukenlaan', rv.data, 'Address not returned')
        self.assertIn(b'delete', rv.data, 'Button name missing')

    def test_post_delete_address_confirmation(self):
        """ When we confirm a deletion, it is done """

        adr23_id = self.adr23.id
        adr24_id = self.adr24.id
        rv = self.app.post('/client/' + str(self.clt4.id) + '/address/'\
            + str(self.adr23.id) + '/confirm', data={"delete" : True},
            follow_redirects=True)
        address_list = db.session.query(Addresses).all()
        id_set = set()
        for address in address_list:
            id_set.add(address.id)
        self.assertNotIn(adr23_id, id_set, 'Not deleted')
        self.assertIn(adr24_id, id_set, 'This should be here!')
        delete_test_clients(self)
        db.session.commit()


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

    def test_add_mail_thru_interface(self):
        """ We can add a mail address thru the transaction """

        self.app = app.test_client()
        self.app.testing = True
        rv = self.app.post('client/' + str(self.clt10.id) + '/mail/new',
                           data={'mail_address' : 'kronos23@wxs.nl',
                                 'preferred' : False }, follow_redirects=True)
        addrs = db.session.query(EMail).filter(EMail.mail_address=='kronos23@wxs.nl').all()
        self.assertEqual(len(addrs), 1, 'Address not added/too many')
        db.session.query(EMail).filter(EMail.client_id == self.clt10.id).delete()
        db.session.query(Addresses).filter(Addresses.client_id == self.clt10.id).delete()
        db.session.query(Clients).filter(Clients.id == self.clt10.id).delete()
        db.session.commit()


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


class TestBankAccountsFunctions(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        db.session.flush()
        spread_created_at(self)
        add_addresses(self)
        db.session.flush()
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):

        db.session.rollback()
        delete_test_clients(self)
        db.session.commit()

    def test_get_bankaccount(self):
        """ Get a bank account for a client """

        rv = self.app.get('/client/'+ str(self.clt3.id) + '/account/'\
            + str(self.ba4.id))
        self.assertIn(self.ba4.client_name.encode(), rv.data, 'Name not in output')

    def test_show_empty_account_page(self):
        """ Show the account page for adding an account """

        rv = self.app.get('/client/'+ str(self.clt3.id) + '/account/new')
        self.assertIn(b'Bank', rv.data, 'Bank not in output')

    def test_add_bank_account(self):
        """ Add a bank account to a client """

        clt4_id = self.clt4.id
        rv = self.app.post('/client/'+ str(self.clt4.id) + '/account/new',
                           data = dict(client_id=str(self.clt4.id),
                                       id=None,
                                       iban='NL02DEUT0946769532',
                                       bic=None,
                                       client_name='Gerrit Turkoois'))
        clt4 = db.session.query(Clients).filter_by(id=clt4_id).first()
        self.assertEqual(len(clt4.accounts), 1, 'Incorrect no. of accounts')

    def test_account_not_for_client(self):
        """ We cannot update an account passing an incorrect client """

        rv = self.app.post('/client/'+ str(self.clt4.id) + '/account/'
                           + str(self.ba1.id),
                           data = dict(client_id=str(self.clt4.id),
                                       id=None,
                                       iban='NL26BKMG0794396038',
                                       bic=None,
                                       client_name='G. Turkoois'))
        self.assertIn(b'Not Found', rv.data, 'No not found')

    def test_change_owner_name(self):
        """ We can change the owner name on the account """

        ba5_id = self.ba5.id
        rv = self.app.post('/client/'+ str(self.clt5.id) + '/account/'
                           + str(self.ba5.id),
                           data = dict(client_id=str(self.clt5.id),
                                       id=self.clt5.id,
                                       iban='NL76INGB0594788005',
                                       bic=None,
                                       client_name='Antoinette Aubergine'),
                           follow_redirects=True)
        clt5_new = db.session.query(BankAccounts).filter_by(id=ba5_id).first()
        self.assertIn('Antoinette', clt5_new.client_name,
                      'Antoinette not in owner name')

    def test_show_account_delete(self):
        """ We show the delete confirmation page for accounts """

        iban_nr = self.ba5.iban
        rv = self.app.get('/client/' + str(self.clt5.id) + '/account/'
                           + str(self.ba5.id) + '/delete')
        self.assertIn(iban_nr.encode(), rv.data, 'IBAN not in page content')

    def test_request_wrong_account(self):
        """ We get an errror if the account and owner diverge """

        rv = self.app.get('/client/' + str(self.clt5.id) + '/account/'
                          + str(self.ba1.id) + '/delete')
        self.assertIn(b'404', rv.data, '404 not returned')

    def test_request_non_existing_account(self):
        """ An error is returned on deletion of a non-existing account  """

        rv = self.app.get('/client/' + str(self.clt5.id) + 
                          '/account/1/delete')
        self.assertIn(b'404', rv.data, '404 not returned')

    def test_post_delete_confirmation(self):
        """ Post the delete confirmation for a bank account """

        ba5_id = self.ba5.id
        clt5_id = self.clt5.id
        rv=self.app.post('client/' + str(self.clt5.id) + '/account/'
                         + str(self.ba5.id) + '/delete', 
                         data=dict(client_id=self.clt5.id, delete=True),
                         follow_redirects=True)
        clt5_new = db.session.query(Clients).filter_by(id=clt5_id).first()
        self.assertTrue(clt5_new, 'Read client unsuccessful')
        account_ids = []
        for account in clt5_new.accounts:
            account_ids.append(account.id)
        self.assertNotIn(ba5_id, account_ids, 'Account not deleted')

    def test_post_invalid_account(self):
        """ We cannot confirm deleting the wrong account """

        rv=self.app.post('client/' + str(self.clt5.id) + '/account/'
                         + str(self.ba3.id) + '/delete', 
                         data=dict(client_id=self.clt5.id, delete=True),
                         follow_redirects=True)
        self.assertIn(b'404', rv.data, 'Deleting account not refused')

    def test_deleting_non_existing_account(self):
        """ Deleting a non-existing account is met with 404 """

        rv=self.app.post('client/' + str(self.clt5.id)
                         + '/account/1/delete', 
                         data=dict(client_id=self.clt5.id, delete=True),
                         follow_redirects=True)
        self.assertIn(b'404', rv.data,
                      'Deleting non-existing account not refused')


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


class TestClientTransactions(unittest.TestCase):

    def setUp(self):

        self.app = app.test_client()
        self.app.testing = True

    def rollback():

        pass

    def test_get_client(self):
        """ We can get a client """

        clt19 = Clients(surname='Zomervreugd', first_name='Fedor',
                        birthdate=date(1988, 11,3))
        clt19.add()
        db.session.flush()
        rv = self.app.get('/client/' + str(clt19.id))
        self.assertIn(clt19.surname.encode(), rv.data, 'Name not in response')

    def test_fail_get_client(self):
        """ Get a client that doesn't exist bows out gracefully """

        rv = self.app.get('/client/56')
        self.assertIn(b'Not Found', rv.data, 'Client exists')

    def test_client_create_start(self):
        """ We can use /client/new to start creating a client """

        rv = self.app.get('/client/new')
        self.assertIn(b'Client surname', rv.data, 'Incorrect data returned')

    def test_post_new_client(self):
        """ We can post data for a new client """

        data=dict(surname='Kansenkapper',
                    initials='K.L.P.',
                    first_name='Kees',
                    birthdate='08-12-2001',
                    sex='M')
        rv = self.app.post('client/new', data=data, follow_redirects=True)
        client_list = Clients.get_clients_by_name('Kansenkapper')
        self.assertTrue(client_list[0].id, 'Client did not get id')
        for each in client_list:
            db.session.delete(each)
        db.session.commit()

    def test_update_client(self):
        """ We update an existing client """

        rv = self.app.post('/client/new', data=dict(surname='Klapperboom',
                                                   first_name='Jan',
                                                   initials="J.G.H.",
                                                   birthdate='05-07-1986',
                                                   sex='M'),
                           follow_redirects=True)
        client_list = Clients.get_clients_by_name('Klapperboom')
        id = client_list[0].id
        rv = self.app.post('/client/' + str(id), 
                           data=dict(
                                        surname='Klapperboom',
                                        first_name='Jan',
                                        initials='J.G.H.',
                                        birthdate='05-07-1985',
                                        sex='M'),
                           follow_redirects=True)
        client = Clients.get_by_id(int(id))
        self.assertEqual(client.birthdate, date(1985, 7, 5),
                         'Birth date not updated')
        client_list = Clients.get_clients_by_name('Klapperboom')
        for each in client_list:
            db.session.delete(each)
        db.session.commit()

class TestClientList(unittest.TestCase):

    def setUp(self):

        create_clients(self)
        db.session.flush()
        spread_created_at(self)
        add_addresses(self)
        db.session.flush()

    def tearDown(self):

        db.session.rollback()

    def test_get_list_from_model(self):
        """ We can get a list of clients from the model """

        client_list = Clients.client_list()
        self.assertEqual(len(client_list), 6, 'Wrong number of clients')

    def test_client_list_is_ordered(self):
        """ The client list is ordered """

        client_list = Clients.client_list()
        self.assertEqual(client_list[0].surname, self.clt3.surname,
                         'List starts with wrong client')
        self.assertEqual(client_list[5].surname, self.clt6.surname,
                         'List ends with wrong client')

    def test_we_can_limit_client_list(self):
        """ We can limit the list to say, client 2 until 4 """

        client_list = Clients.client_list(start_at=2, list_for=3)
        self.assertEqual(client_list[0], self.clt5, 'List does not start at 2nd')
        self.assertEqual(client_list[-1], self.clt4, 'List does not end at 5th')

    def test_get_list_beyond_end(self):
        """ Requesting a list beyond the end of the table, returns empty list 
        """

        client_list = Clients.client_list(start_at=8)
        self.assertEqual(len(client_list), 0, 'List has clients')

    def test_get_more_than_left_truncates(self):
        """ If we ask for more than remaining, the list is truncated """

        client_list = Clients.client_list(start_at=3, list_for=5)
        self.assertEqual(len(client_list), 3, 'List has wrong no. of clients')

    def test_can_create_list_view(self):
        """ We create a view over a client list """

        client_paginator = ClientViewingList(Clients.client_list,
                                            page=1, page_length=4)
        client_list_view = client_paginator.get_page()
        self.assertEqual(len(client_list_view), 4,
                         'Wrong number of clients in view')

    def test_can_get_other_page(self):
        """ We can get the second page """

        client_paginator = ClientViewingList(Clients.client_list,
                                            page=1, page_length=4)
        client_list_view = client_paginator.get_page(page_number=2)
        self.assertEqual(len(client_list_view), 2,
                         'Wrong number of clients in view')

    def test_get_mail_adresses(self):
        """ Mail addresses are reachable from list elements """

        client_list = Clients.client_list()
        selected_client = client_list[client_list.index(self.clt2)]
        self.assertEqual(len(selected_client.emails), 2,
                         'Too little/many mail addresses')

    def test_get_adresses(self):
        """ Traditional addresses are reachable from list elements """

        client_list = Clients.client_list()
        selected_client = client_list[client_list.index(self.clt2)]
        self.assertEqual(len(selected_client.addrs), 2,
                         'Too little/many mail addresses')

    def test_list_for_search_string(self):
        """ We can get a list of clients for a search string on surname """

        search_for = 'kar'
        client_list = Clients.client_list(search_for=search_for)
        self.assertEqual(len(client_list), 1, 'Too many/no clients in list')
        self.assertEqual(client_list[0].id, self.clt1.id, 'Its the wrong client')

    def test_more_clients_in_list(self):
        """ We get more clients if they conform to search """

        clt20 = Clients(surname='Boldootkar',
                                initials='S.T.I.N.K.',
                                first_name='Simon')
        clt20.add()
        db.session.flush()
        search_for = 'kar'
        client_list = Clients.client_list(search_for=search_for)
        self.assertEqual(len(client_list), 2, 'Too many/too little clients in list')

    def test_list_with_search_and_page(self):
        """ We can combine search string and page """

        search_for = 'kar'
        client_paginator = ClientViewingList(Clients.client_list,
                                            page=1, page_length=4)
        client_list_view = client_paginator.get_page(page_number=2,
                                                    search_for=search_for)
        self.assertEqual(len(client_list_view), 0, 'Clients in list')        


class TestClientListFunctions(unittest.TestCase):
    

    def setUp(self):

        create_clients(self)
        db.session.flush()
        spread_created_at(self)
        add_addresses(self)
        db.session.flush()
        self.app = app.test_client()
        self.app.testing = True

    def tearDown(self):

        db.session.rollback()

    def test_get_first_page(self):
        """ We can get the first page of the client list """

        rv = self.app.get('/client/list')
        self.assertIn(b'Karmozijn', rv.data, 'Expected Karmozijn, not found')

    def test_get_2nd_page(self):
        """ We can get the second page of the list """

        rv = self.app.get('/client/list?page=2')
        self.assertIn(b'Turkoois', rv.data, 'Expected Turkoois, not found')

    def test_email_present(self):
        """ We return the email addresses of a client """

        rv = self.app.get('/client/list?page=1')
        self.assertIn(b'nogor', rv.data, 'Expected "nogor", not found')
        self.assertIn(b'snipper12', rv.data, 'Expected "snipper12", not found')

    def test_traditional_address(self):
        """ We return postal and residential addresses for clients """

        rv = self.app.get('/client/list?page=1')
        self.assertIn(b'Vrijheidsplein', rv.data, 
                      'Expected "Vrijheidsplein", not found')
        self.assertIn(b'Hengelo', rv.data, 'Expected "Hengelo", not found')  
    

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
    # This routine is used on the production of create_clients

    instance.clt1.updated_at = datetime(2018, 11, 3, hour=12, minute=17)
    instance.clt2.updated_at = datetime(2016, 9, 14, hour=12, minute=7)
    instance.clt3.updated_at = datetime(2018, 11, 3, hour=13, minute=7)
    instance.clt4.updated_at = datetime(2014, 2, 2, hour=2, minute=37)
    instance.clt5.updated_at = datetime(2017, 10, 1, hour=14, minute=55)
    instance.clt6.updated_at = datetime(2011, 1, 2, hour=0, minute=25)

def add_addresses(instance):
    # This routine is used on the production of create_clients

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


if __name__ == '__main__' :
    unittest.main()

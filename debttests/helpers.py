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

from datetime import datetime, date, timedelta
from debtors import db
from clientmodels.clients import Clients, Addresses, NoPostalAddressError,\
    POSTAL_ADDRESS, RESIDENTIAL_ADDRESS, GENERAL_ADDRESS, EMail,\
        DuplicateMailError, TooManyPreferredMailsError, BankAccounts,\
        NoResidentialAddressError, NoClientFoundError
from debtmodels.overdue import (OverdueSteps, OverdueActions)
from debtmodels.debtbilling import (Bills, BillLines, DebtorPreferences,
                                    DebtorSignal)
from debtmodels.payments import (AmountQueued, IncomingAmounts,
                                 AssignedAmounts)
from debtviews.overdue_processors import (FirstLetterProcessor,
                                          SecondLetterProcessor,
                                          DebtTransferProcessor,
                                          DubiousDebtorProcessor)


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
    instance.clt3 = Clients(surname='Aq\u00f6amarijn\u0394',
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
    instance.clt2.addrs.append(instance.adr23)
    instance.adr26 = Addresses(street='Generaal Spoorlaan',
                            town_or_village='Driebergen',
                            house_number='16',
                            postcode='3865 AE', country_code='NLD',
                            address_use=GENERAL_ADDRESS)
    instance.clt3.addrs.append(instance.adr26)
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
    add_debtor_preferences(instance)

def delete_test_clients(instance):
    """ Delete clients and dependants added in create_clients """

    db.session.query(DebtorPreferences).delete()
    client_list =\
        db.session.query(Clients).filter(Clients.surname.in_(instance.client_list)).all()
    for client in client_list:
        db.session.delete(client)

def create_bills(instance):
    """ Create bills for test 'instance' """

    instance.bills = []
    instance.bll1 = Bills(date_sale=date.today(), date_bill=None,
                          status='new')
    instance.clt1.bills.append(instance.bll1)
    instance.bills.append(instance.bll1)
    instance.bll2 = Bills(date_sale=date.today(),
                          date_bill=date.today(),
                          billing_ccy = 'EUR',
                          status='paid')
    instance.clt1.bills.append(instance.bll2)
    instance.bills.append(instance.bll2)
    instance.bll3 = Bills(date_sale=date(year=2019, month=11, day=18),
                          billing_ccy='EUR',
                          date_bill=None,
                          status='new')
    instance.clt3.bills.append(instance.bll3)
    instance.bills.append(instance.bll3)
    instance.bll4 = Bills(date_sale=date(year=2022, month=2, day=18),
                          date_bill=date(year=2022, month=2, day=18),
                          billing_ccy='JPY',
                          status='issued')
    instance.clt5.bills.append(instance.bll4)
    instance.bills.append(instance.bll4)
    instance.bll5 = Bills(date_sale=date(year=2020, month=3, day=2),
                          date_bill=None,
                          billing_ccy='JPY',
                          status='new')
    instance.clt5.bills.append(instance.bll5)
    instance.bills.append(instance.bll5)
    instance.bll6 = Bills(date_sale=date(year=2020, month=3, day=18),
                          date_bill=date(year=2020, month=3, day=19),
                          billing_ccy='EUR',
                          status='issued')
    instance.clt5.bills.append(instance.bll6)
    instance.bills.append(instance.bll6)
    instance.bll8 = Bills(date_sale=date(year=2020, month=2, day=18),
                          date_bill=date(year=2020, month=2, day=18),
                          billing_ccy = 'EUR',
                          status='issued')
    instance.clt1.bills.append(instance.bll8)
    instance.bills.append(instance.bll8)

def create_bills_overdue(instance):
    """ Add some bills required for testing overdue """

    instance.bll7 = Bills(date_sale=date(year=2020, month=3, day=23),
                          date_bill=date(year=2020, month=3, day=25),
                          billing_ccy='JPY',
                          status='issued')
    instance.clt5.bills.append(instance.bll7)
    instance.bills.append(instance.bll7)
    instance.bll9 = Bills(date_sale=date(year=2020, month=1, day=23),
                          date_bill=date(year=2020, month=1, day=25),
                          billing_ccy='GBP',
                          status='issued')
    instance.clt6.bills.append(instance.bll9)
    bill_line = BillLines(short_desc='S5',
                        long_desc='Snap head',
                        number_of=1,
                        unit_price=115)
    instance.bll9.lines.append(bill_line)

def create_bills_for_positions(instance):
    """ Add bills to test for age of position """

    young_date = date.today() - timedelta(days=10)
    instance.bll10 = Bills(date_sale=young_date,
                          date_bill=young_date,
                          billing_ccy = 'EUR',
                          status='issued')
    instance.clt1.bills.append(instance.bll10)
    instance.bills.append(instance.bll10)
    bill_line = BillLines(short_desc='Sk009',
                        long_desc='A very fine product',
                        number_of=10,
                        unit_price=105)
    instance.bll10.lines.append(bill_line)
    older_date = date.today() - timedelta(days=45)
    instance.bll11 = Bills(date_sale=older_date,
                          date_bill=older_date,
                          billing_ccy = 'EUR',
                          status='issued')
    instance.clt1.bills.append(instance.bll11)
    instance.bills.append(instance.bll11)
    bill_line = BillLines(short_desc='Sk011',
                        long_desc='Another fine mess',
                        number_of=8,
                        unit_price=75)
    instance.bll11.lines.append(bill_line)
    worrying_date = date.today() - timedelta(days=72)
    instance.bll12 = Bills(date_sale=worrying_date,
                          date_bill=worrying_date,
                          billing_ccy = 'EUR',
                          status='issued')
    instance.clt1.bills.append(instance.bll12)
    instance.bills.append(instance.bll12)
    bill_line = BillLines(short_desc='Sk11998',
                        long_desc='Me worry? Noooo',
                        number_of=2,
                        unit_price=750)
    instance.bll12.lines.append(bill_line)
    instance.bll13 = Bills(date_sale=young_date,
                          date_bill=young_date,
                          billing_ccy = 'JPY',
                          status='issued')
    instance.clt1.bills.append(instance.bll13)
    instance.bills.append(instance.bll13)
    bill_line = BillLines(short_desc='Wampoo',
                        long_desc='Japanese debt',
                        number_of=4,
                        unit_price=550)
    instance.bll13.lines.append(bill_line)
    instance.bll14 = Bills(date_sale=young_date,
                          date_bill=young_date,
                          billing_ccy = 'EUR',
                          status='new')
    instance.clt1.bills.append(instance.bll14)
    instance.bills.append(instance.bll14)
    bill_line = BillLines(short_desc='Sk98',
                        long_desc='Not in position',
                        number_of=1,
                        unit_price=850)
    instance.bll14.lines.append(bill_line)
    instance.bll15 = Bills(date_sale=young_date,
                          date_bill=young_date,
                          billing_ccy = 'EUR',
                          status='issued')
    instance.clt2.bills.append(instance.bll15)
    instance.bills.append(instance.bll15)
    bill_line = BillLines(short_desc='fl15',
                         long_desc='Needs 1 letter',
                         number_of=8,
                         unit_price=178)
    instance.bll15.lines.append(bill_line)

def create_overdue_actions_for_positions(instance):
    """ Create overdue actions for the overdue by status report """

    two_days_before = datetime.today() - timedelta(days=2)
    transferred = OverdueActions(date_action=two_days_before)
    transferred.bill = instance.bll12
    transferred.step = instance.st17
    transferred = OverdueActions(date_action=two_days_before)
    transferred.bill = instance.bll11
    transferred.step = instance.st17
    secondletter = OverdueActions(date_action=two_days_before)
    secondletter.bill = instance.bll10
    secondletter.step = instance.st16
    firstletter = OverdueActions(date_action=two_days_before)
    firstletter.bill = instance.bll15
    firstletter.step = instance.st15


def create_payments_for_overdue(instance):
    """ Add received payments to a client having an overdue bill """

    instance.ia110 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=28,
                               creditor_iban= 'NL08INGB0212977892',
                               client_name='T. Gebraltas',
                               value_date=date(2021, 2, 13),
                               our_ref='Ref Undef',
                               bank_ref='320098')
    instance.ia110.change_client(instance.bll4.client)

    instance.ia111 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=144,
                               creditor_iban= 'NL08INGB0212955892',
                               client_name='T. Funderthun',
                               our_ref='Ref 8',
                               bank_ref='320155')
    instance.ia111.change_client(instance.clt1)

    instance.ia112 = IncomingAmounts(payment_ccy='JPY',
                               payment_amount=8,
                               value_date=date(2022, 1, 8),
                               our_ref='Ref Undef')
    instance.ia112.change_client(instance.bll4.client)

def add_lines_to_bills(instance):
    """ Add lines to the bills in the instance

    The instance bills are in instance.bills 
    """

    bill = instance.bll1
    bill_line = BillLines(short_desc='S1',
                        long_desc='A longer description one',
                        number_of=15,
                        unit_price=115)
    bill.lines.append(bill_line)
    bill_line = BillLines(short_desc='S2',
                        long_desc='A longer description two',
                        number_of=12,
                        measured_in='Kilo',
                        unit_price=234)
    bill.lines.append(bill_line)
    bill = instance.bll2
    bill_line = BillLines(short_desc='1276',
                        long_desc='Outside business place',
                        number_of=1,
                        measured_in='unit',
                        unit_price=128734)
    bill.lines.append(bill_line)
    bill = instance.bll3
    bill_line = BillLines(short_desc='h0',
                        long_desc='Grease',
                        number_of=2,
                        measured_in='tin',
                        unit_price=12873)
    bill.lines.append(bill_line)
    bill_line = BillLines(short_desc='h1',
                        long_desc='Tin solder',
                        number_of=15,
                        measured_in='bottles',
                        unit_price=1212)
    bill.lines.append(bill_line)
    bill_line = BillLines(short_desc='h2',
                        long_desc='Screw, flat head',
                        number_of=5,
                        measured_in='boxes',
                        unit_price=2199)
    bill.lines.append(bill_line)
    bill_line = BillLines(short_desc='h3',
                        long_desc='Screw, round head',
                        number_of=1,
                        measured_in='box',
                        unit_price=1876)
    bill.lines.append(bill_line)
    bill = instance.bll4
    bill_line = BillLines(short_desc='765',
                        long_desc='Nine inch nails',
                        number_of=5,
                        measured_in='box',
                        unit_price=376)
    bill.lines.append(bill_line)
    bill = instance.bll6
    bill_line = BillLines(short_desc='Sh75',
                        long_desc='Paper bags',
                        number_of=4,
                        measured_in='pcs',
                        unit_price=566)
    bill.lines.append(bill_line)
    if hasattr(instance, "bll7"):
        bill = instance.bll7
        bill_line = BillLines(short_desc='Fi5',
                            long_desc='Milk cartons',
                            number_of=34,
                            measured_in='pcs',
                            unit_price=660)
        bill.lines.append(bill_line)

def add_debtor_preferences(instance):
    """ Add preferences to some of the clients """

    instance.clt1.debtor_prefs.append(DebtorPreferences(bill_medium='mail',
                                                   letter_medium='mail'))
    instance.clt3.debtor_prefs.append(DebtorPreferences(bill_medium='mail',
                                                   letter_medium='post'))

def create_debtor_signals(instance):
    """ Create debtor signals """

    instance.sig12 = DebtorSignal(client=instance.bll8.client,
                                    date_start=date.today() - timedelta(days=4),
                                    date_end=None)
    instance.sig13 = DebtorSignal(client=instance.bll8.client,
                                    date_start=date.today() - timedelta(days=6),
                                    date_end=date.today() - timedelta(days=2))

def create_overdue_steps(instance):
    """ Create steps for all steps defined in overdue_processors """

    instance.st15 = OverdueSteps(id=100, number_of_days=25, 
                                 step_name="First Letter",
                                 processor="firstletter")
    instance.st15.add()
    instance.st16 = OverdueSteps(id=120, number_of_days=40, 
                                 step_name="Second Letter",
                                 processor="secondletter")
    instance.st16.add()
    instance.st17 = OverdueSteps(id=140, number_of_days=55, 
                                 step_name="Debt transfer",
                                 processor="transfer")
    instance.st17.add()
    instance.st18 = OverdueSteps(id=160, number_of_days=80, 
                                 step_name="Debt dubious",
                                 processor="dubious")
    instance.st18.add()
    # Create processors
    instance.flp14 = FirstLetterProcessor()
    instance.slp09 = SecondLetterProcessor()
    instance.dtp06 = DebtTransferProcessor()
    instance.ddp02 = DubiousDebtorProcessor()

def delete_amountq(instance):
    """ Empty the amounts queue for assignment """

    amounts = db.session.query(AmountQueued).all()
    for amount in amounts:
        db.session.delete(amount)

def delete_test_bills(instance):
    """ Delete all the bills created for a test """

    bills = db.session.query(Bills).all()
    for bill in bills:
        db.session.delete(bill)

def delete_test_payments(instance):
    """ Delete all payments created for a test """

    assignments = db.session.query(AssignedAmounts).all()
    for assigned_amount in assignments:
        db.session.delete(assigned_amount)
    payments = db.session.query(IncomingAmounts).all()
    for payment in payments:
        db.session.delete(payment)

def delete_test_prefs(instance):
    """ Delete all preferences created for a test """

    prefs = db.session.query(DebtorPreferences).all()
    for pref in prefs:
        db.session.delete(pref)

def delete_debtor_signals(instance):
    """ Delete all signals """

    signals = db.session.query(DebtorSignal).all()
    for signal in signals:
        db.session.delete(signal)

def delete_overdue_steps(instance):
    """ Delete all overdue steps """

    steps = db.session.query(OverdueSteps).all()
    for step in steps:
        db.session.delete(step)

def delete_overdue_actions(instance):
    """ Delete all overdue actions """

    actions = OverdueActions.query.all()
    for action in actions:
        db.session.delete(action)

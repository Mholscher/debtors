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

""" This module holds the form necessary to create and change bills

The manual changes to and creation of bills needs forms. This module
holds these forms.
"""

from flask_wtf import FlaskForm
from wtforms import HiddenField, StringField, DateField, SubmitField,\
    IntegerField, SelectField, FieldList, FormField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from debtmodels.debtbilling import Bills, ReplacedBillError
from debtmodels.payments import validate_currency, IncomingAmounts as Amounts
# For testing only!
from debtviews.wtformsmonetary import AmountField


class PrevBillMustExist(ValueError):
    """ WTForms validator for existence of a previous bill

    If we want to replace an existing bill, the number passed in for
    that previous bill must denote an existing bill.
    """

    message = 'No bill to replace'

    def __init__(self, message=None):

        if message:
            self.message = message

    def __call__(self, form, field):

        try:
            Bills.check_prev_bill(field.data)
        except ReplacedBillError as rbe:
            raise ValidationError(str(rbe))


class RequiredIfAny(ValueError):
    """ WTForms validator for a required field

    It replaces a DataRequired validator, where we can only see the
    field is required if this same field is filled. Here a field can be empty
    if none of the other fields are filled. However, if one other field (any)
    is filled, this field becomes required.
    """

    message = 'This field is required'

    def __init__(self, message=None):

        if message:
            self.message = message

    def __call__(self, form, field):

        if not field.data:
            raise ValidationError(self.message)


class PaymentCcyValid(ValueError):
    """ WTForms validator for existence of a payment currency

    If a payment is entered through the new payment page, we needs
    to make sure the currency is an existing one, e.g. for editing
    amounts.
    """

    message = 'The currency {} is invalid'

    def __init__(self, message=None):

        if message:
            self.message = message

    def __call__(self, form, field):

        if not validate_currency(field.data):
            raise ValidationError(self.message.format(field.data))


class EndDateValid(ValueError):
    """ WTForms validator for end date of a signal """

    message = 'End date must be on or after start date'

    def __init__(self, message=None):

        if message:
            self.message = message

    def __call__(self, form, field):

        if field.data is None:
            return
        if field.data < form.date_start.data:
            raise ValidationError(self.message.format(field.data))



class BillLineForm(FlaskForm):
    """ This class holds data for a line in the bill """

    line_id = HiddenField('Line id')
    bill_id = HiddenField('Bill id')
    short_desc = StringField('Short description',
                             validators=[RequiredIfAny(),
                                         Length(min=1, max=10)])
    long_desc = StringField('Description', validators=[Length(max=40)])
    number_of = IntegerField('Number of units', validators=[RequiredIfAny()])
    measured_in = StringField('Measured in')
    unit_price = AmountField('Unit price', validators=[RequiredIfAny()])


class BillForm(FlaskForm):
    """ This holds parts of the form for creating and changing bills """

    bill_id = HiddenField('bill id')
    csrf_token = HiddenField('csrf_token')
    billing_ccy = StringField('Billing currency', validators=[Length(max=3)])
    bill_replaced = IntegerField('Bill to be replaced',
                                 validators=[Optional(), PrevBillMustExist()])
    lines = FieldList(FormField(BillLineForm))


class BillCreateForm(BillForm):
    """ This is the form for creating a new bill """

    client_id = StringField('Client number')
    date_sale = DateField('Date of sale', format='%d-%m-%Y',
                          validators=[DataRequired()])
    add_1 = SubmitField('Update & exit')
    add_more = SubmitField('Update & new')


class BillChangeForm(BillForm):
    """ This is the form for changing an existing bill """

    client_id = StringField('Client number', validators=[Optional()])
    date_sale = DateField('Date of sale', format='%d-%m-%Y')
    update = SubmitField('Update')


class FormForAmount(FlaskForm):

    amount = AmountField()
    submitting = SubmitField('Submit')


class PaymentForm(FlaskForm):
    """ This is the form for showing payment data """

    local_choices = [(k, v) for k, v in Amounts.DEBCRED.items()]
    id = HiddenField('Payment sequence')
    csrf_token = HiddenField('csrf_token')
    payment_ccy = StringField('Currency', validators=[Length(max=3),
                                                      PaymentCcyValid()])
    payment_amount = AmountField('Amount paid')
    debcred = SelectField('Debit/credit', choices=local_choices,
                          validators=[Length(max=2)])
    value_date = DateField('Paid at', format='%d-%m-%Y')
    our_ref = StringField('Our reference', validators=[Length(max=35)])
    bank_ref = StringField('Bank reference', validators=[Length(max=35)])
    creditor_iban = StringField('Creditors IBAN', validators=[Length(max=35)])
    client_name = StringField('Client name (from bank)')


class PaymentCreateForm(PaymentForm):
    """ The part of the form for creating a payment """

    submit = SubmitField('Create payment')


class ClientAttachForm(FlaskForm):
    """ The form to attach a client to a payment """

    payment_id = HiddenField('Payment sequence')
    client_id = StringField('Client number')
    attach = SubmitField('Attach client')


class FindClientForm(FlaskForm):
    """ Form for finding clients through different predicates """

    find_name = StringField('By client: Name')
    find_number = StringField('Number')
    find_bank_account = StringField('Bankaccount')
    search_client = SubmitField('Find client debt')


class FindPaymentByRef(FlaskForm):
    """ The form to find payments to assign to """

    find_our_ref = StringField("Our reference")
    find_bank_ref = StringField("Bank reference")
    search_payment = SubmitField("Find payment")


class OtherPaymentForm(FlaskForm):
    id = HiddenField("Other payment id")
    payment_amount = AmountField("Other currency amount")
    add_to_payment = SubmitField("Add here")


class DebtorSignalForm(FlaskForm):
    id = HiddenField("Signal id")
    date_start = DateField("Start date", format="%d-%m-%Y",
                           validators=[DataRequired()])
    date_end = DateField("End date", format="%d-%m-%Y",
                         validators=[EndDateValid()])
    change_signal = SubmitField("Update signal")


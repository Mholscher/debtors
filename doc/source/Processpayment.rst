Process payments
================

Payments from bank statements
-----------------------------

If payments are being made into our bank account, these appear on our daily statement. It is assumed that statements are digitally coming in, detailing payments. The example implementation is for CAMT.053 formatted statements. Check the documentation of your preferred bank to see what it supports.

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| an amount id           | the debtors system | n/a       | n/a      |              
+------------------------+--------------------+-----------+----------+
| a client id            | the debtors system | optional  | None     |              
+------------------------+--------------------+-----------+----------+
| statement date         | the bank statement | mandatory | n/a      |              
+------------------------+--------------------+-----------+----------+
| our reference          | the bank statement | optional  | None     |              
+------------------------+--------------------+-----------+----------+
| bank reference         | the bank statement | mandatory | n/a      |              
+------------------------+--------------------+-----------+----------+
| client reference       | the bank statement | optional  | n/a      |              
+------------------------+--------------------+-----------+----------+
| a client name          | the bank statement | optional  | None     |              
+------------------------+--------------------+-----------+----------+
| amount currency        | the bank statement | mandatory | n/a      |              
+------------------------+--------------------+-----------+----------+
| amount received        | the bank statement | mandatory | n/a      |              
+------------------------+--------------------+-----------+----------+
| debit/credit indicator | the bank statement | mandatory | credit   |              
+------------------------+--------------------+-----------+----------+

The payments from the statement are assigned to a debt by finding out:

    :our reference: The reference to a bill will be mentioned on the statement, enabling the program to directly find the bill. This may be the bill id
    :the account of the client: if the account the payment is made from is known to us, we may know whose bill to assign to. Then we assign the amount to the oldest bill

If no bill is found to assign to, we keep the amount at the client level, or at the unassigned level. If we only know the client who paid or the amount is not enough to pay the bill or the client overpaid, the amount paid or the overpaid amount is kept as an amount at the client level.

If the amount received is in a different currency from the bill, the system will not assign the amount to a bill. See :ref:`multicurrency`

The debit/credit indicator is used to be able to process reversals.

To see a paid amount, go to <host>/payment/<payment-id>

.. _manualpaymentinput:

Payments from user inputs
-------------------------

Payments done by other means than bank payment may be input to the system through manual user input. The input data is as follows:

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| an amount id           | the debtors system | n/a       | n/a      |
+------------------------+--------------------+-----------+----------+
| a client id            | user input         | optional  | None     |
+------------------------+--------------------+-----------+----------+
| entry date             | user input         | mandatory | today    |
+------------------------+--------------------+-----------+----------+
| our reference          | user input         | mandatory | None     |
+------------------------+--------------------+-----------+----------+
| their reference        | user input         | optional  | None     |
+------------------------+--------------------+-----------+----------+
| a client name          | user input         | optional  | None     |
+------------------------+--------------------+-----------+----------+
| amount currency        | user input         | mandatory | n/a      |
+------------------------+--------------------+-----------+----------+
| amount received        | user input         | mandatory | n/a      |
+------------------------+--------------------+-----------+----------+
| debit/credit indicator | user input         | mandatory | credit   |              
+------------------------+--------------------+-----------+----------+

The role of our reference is to point the user to any document that details the source of the data. If e.g. the amount is paid in cash, you refer to a copy of the receipt by its number.

Assigning the money to a debt is performed like for payments from the daily statement.

Assigned amounts
----------------

When (part of) an amount is used to pay a bill, an assigned amount is created for the amount used and the source. Assigned amounts are only created if a bill can be paid in full; we do not assign amounts to partially pay a bill.

If an assignment is to another "payment" which is manually input, we can assign to part of an amount. The new amount constructed may be coming from more than one source. It would be limiting to not allow that.

*   a client pays 34 Euro to a bill for 44 Euro

*   after a while he pays the missing 10 Euro

*   we create an amount of 44 Euro from the 2 amounts, which makes it possible to pay the bill

When a bill can be paid in full, but the amount was greater than the amount due on the bill, a remainder of the payment is still usable to assign to another bill or even bills. This looks as follows:

*   an amount of EUR 3400,- was received from the client

*   EUR 1500,- was used to pay bill 15, so bill 15 is set paid, an assigned amount for EUR 1500,- created. When inquiring, an outstanding amount of EUR 1900,- (3400 - 1500) is showing on the receipt.

*   if a bill of EUR 800,- is then written for the client, this bill is set paid, an assigned amount for EUR 800,- created. When inquiring, an available amount of EUR 1100,- (3400 - 1500 - 800) is shown on the receipt.

Amounts are assigned in date and time order. So a client will not be put through the debt process after missing one payment. This has the following exception: A client gets a bill for JPY 540 and after that for JPY 100. Client pays the JPY 100 bill, but that is insufficient for paying the first bill. The second one though will be paid, because the money is enough.

The fields on the assigned amount are:

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| assignment id          | the debtors system | n/a       | n/a      |
+------------------------+--------------------+-----------+----------+
| incoming amount id     | the debtors system | mandatory | n/a      |
+------------------------+--------------------+-----------+----------+
| amount currency        | amount currency    | mandatory | n/a      |
+------------------------+--------------------+-----------+----------+
| amount assigned        | the paid debt on   | mandatory | n/a      |
|                        | the bill or the    |           |          |
|                        | amount transferred |           |          |
+------------------------+--------------------+-----------+----------+
| bill id                | the debtors system | optional  | None     |
|                        | or user input      |           |          |
+------------------------+--------------------+-----------+----------+
| reversed               | user input         | optional  | False    |
+------------------------+--------------------+-----------+----------+
| amount id of the new   | user input         | optional  | None     |
| amount                 |                    |           |          |
+------------------------+--------------------+-----------+----------+
| amount in new currency | amount currency    | mandatory | n/a      |
+------------------------+--------------------+-----------+----------+

Some comments on fields:

    :amount currency: The currency of the original incoming amount. Must be the currency from the amount with "incoming amount id".
    :amount assigned: The amount "split off" from the original amount. Can also be the full amount. 
    :amount id of the new amount: the amount that is the target of a split off
    :amount in new currency: links to the new amount. This is either the full new amount, or a part of it. If part, there must be another part to supply the rest.

Payments may also be assigned to another payment. For an example of how to use this, see :ref:`multicurrency`.

Assigned amounts are only visible in the payments that are assigned by the amount.

Attach a payment to (another) client
------------------------------------

When the system cannot assign to a bill automatically, but is aware of the client that paid the amount, it will attach that payment to the client. We can also do that manually. On the payment screen, enter the client number in the appropriate field and click attach. From then on, the amount will be shown in the client debt screen.

If a client is already attached, attaching a new one will replace the previous attachment.

Assigning amounts to a bill manually
------------------------------------

When the system has not assigned an amount to a bill, we can do that manually. The system will find bills that may be (part of) what the money should be assigned to. The user can choose the bill(s) to assign to, and the system will assign money to the bills.

Rules for finding the bills:

* The bill amount must be smaller than the unassigned amount
* Bill currency must be the same as the incoming payment currency
* The operator can select a client whose bills are used when looking for unpaid bills
* If the client is not  known, look if the name on the payment is "like" the name of a client

One or more of the bills may be selected, however, the total of all bill amounts may of course not exceed the unassigned amount on the payment.

.. _reversal:

Assigning reversals
-------------------

Upon receiving a debit from the bank for an account, we need to assign this also. The process of assigning however is different from credits. 

*    In case it corrects a payment that has not been assigned, we assign the original credit to the debit.
*   When the original payment was assigned to a bill we need to "unpay" the bill, i.e. the assignment needs to be reversed, using the received debit amount.
*   Amounts assigned to another amount can be reversed the same away as assignments to bills. However, when the resulting amount was assigned, that assignment must first be manually reversed, because it may have more consequences.

Processing is equal for debits received through the electronic statements and manually input debits.

Accounting items will be simply reversing the accounting done for posting for credit changes.

Assigning reversals manually
----------------------------

If we want to process debits manually, we have to give the operator the opportunity to find any credits that would be reasonable. Upon showing the page, one or more credits are shown with the following properties:

*   the account of the reversal and the candidate original are equal
*   the amounts of the reversal and the candidate are equal
*   the reversal and the candidate have the same value date

If no candidates having these properties are found, the list remains empty.

The operator can search for candidates by entering search arguments. When they enter a client number or surname:

*   all candidates must be from accounts having said customer or customers (in case of a surname) attached.
*   all candidates must have the exact same currency and amount as the reversal, but a different debit/credit indicator

When they enter an account number:

*   all candidates must be for that account number
*   all candidates must have the exact same currency and amount as the reversal, but a different debit/credit indicator

Any of the shown candidates will be selectable as the entry to reverse. However, any entry that is assigned to another amount may need to be reversed first (see :ref:`reversal`).

Reversing assignment
--------------------

If an amount is assigned to a bill or another amount, it may be assigned in error, or a reversal for the amount may be received. To be able to process these we can reverse an assignment.

The assignment(s) are accessed via the original payment, whose assignment(s) are to be reversed. Accessing the reversal will show all assignments of this amount and those that should be reversed, can be selected.

When the selection is submitted, assignments are reversed by removing the assignments, This entails:

*   removing the assignment proper from the database (by logical delete)
*   reversing any accounting done for assignment
*   if assignment was to a bill, the bill status will be set to issued (from paid)
*   if assignment was to an amount, the amount will be deducted from the available amount for assignment on the amount assigned to

Reversal from assignments to amount can only be done if the amount assigned to is not itself assigned. If it is, this assignment needs to be reversed first.

Reversal assignment has very specific limitations. I have chosen not to reverse assignments of payment reversals.

.. _multicurrency:

Payments in a different currency from the bill
----------------------------------------------

As the debtors system does not have currency rates, it is not possible to convert amounts between currencies. So, if an amount is reported by the bank in a different currency than the amount on the bill, we cannot directly use that amount to pay the bill.

We will make use of the manual input facility mentioned in :ref:`manualpaymentinput`. The amount of the original input can be assigned to the newly created user payment. This will assign all of the money on the original payment and make the new amount available for assigning to the bill. If part of the payment has already been assigned to a bill, this assigning to another amount will be for the remainder, obviously.

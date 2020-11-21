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

    :our reference: The reference to a bill will be mentioned on the statement, enabling the program to directly find the bill. This may be the bill id or the payment
    :the account of the client: if the account the payment is made from is known to us, we may know whose bill to assign to. Then we assign the amount to the oldest bill
    :the name of the client: if we have an exact match with the name of the client, we assign the amount to the oldest bill in the administration

If no bill is found to assign to, we keep the amount at the client level, or at the unassigned level. If we only know the client who paid or the amount is not enough to pay the bill or the client overpaid, the amount paid or the overpaid amount is kept as an amount at the client level.

If the amount received is in a different currency from the bill, the system will not assign the amount to a bill. See :ref:`multicurrency`

The debit/credit indicator is used to be able to process reversals.

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
| debit/credit indicator | the bank statement | mandatory | credit   |              
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

.. _multicurrency:

Payments in a different currency from the bill
----------------------------------------------

As the debtors system does not have currency rates, it is not possible to convert amounts between currencies. So, if an amount is reported by the bank in a different currency than the amount on the bill, we cannot directly use that amount to pay the bill.

We will make use of the manual input facility mentioned in :ref:`manualpaymentinput`. The amount of the original input can be assigned to the newly created user payment. This will assign all of the money on the original payment and make the new amount available for assigning to the bill. 

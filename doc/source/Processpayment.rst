Process payments
================

Payments from bank statements
-----------------------------

If payments are being made into our bank account, these appear on our daily statement. It is assumed that statements are coming in, detailing payments. 

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
| a client name          | the bank statement | optional  | None     |              
+------------------------+--------------------+-----------+----------+
| amount received        | the bank statement | mandatory | n/a      |              
+------------------------+--------------------+-----------+----------+
| bill paid id           | the debtors system | optional  | None     |              
+------------------------+--------------------+-----------+----------+

The payments from the statement are assigned to a debt by finding out:

    :our reference: The reference to a bill will be mentioned on the statement, enabling the program to directly find the bill.
    :the account of the client: if the account the payment is made from is known to us, we may know whose bill to assign to. Then we assign the amount to the oldest bill
    :the name of the client: if we have an exact match with the name of the client, we assign the amount to the oldest bill in the administration

If no bill is found to assign to, we keep the amount at the client level, or at the unassigned level. The unassigned amounts are not part of the debtors systems responsibility. 

If we only know the client who paid or the amount is not enough to pay the bill or the client overpaid, the amount paid or the overpaid amount is kept as an amount at the client level.

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
| amount received        | user input         | mandatory | n/a      |              
+------------------------+--------------------+-----------+----------+

The role of our reference is to point the user to any document that details the source of the data. If e.g. the amount is paid in cash, you refer to a copy of the receipt by its number.

Assigning the money to a debt is performed like for payments from the daily statement.

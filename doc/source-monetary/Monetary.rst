The monetary library
====================

The uses of the library
-----------------------

The monetary library is meant for the development of systems that have a monetary component. The scope is amount conversions, incorporating formatting according to the locale of the running program and formatting of amounts according to the rules of the currency.

Amount editing
--------------

Amounts are supposed to be stored as integers in the smallest unit available. So for Euro amounts, the amount is stored in cents, for Yen in yen. The number of decimal places (precision, both terms are used in the documentation) is gotten from the ISO table 4217.

Amounts are formatted according to the rules of the locale. If your machine is running in the locale en-US, the decimal position is the decimal point and the amount has space as its thousand separator.

There is code to check amount input as strings. In the end, the amount is cleared from special characters "brute force" and parsed to an integer. A sign is left on the amount, though if it is in a unexpected place conversion will fail. Expected places are at the start and the end of the amount.

Integration of WTForms: AmountField
-----------------------------------

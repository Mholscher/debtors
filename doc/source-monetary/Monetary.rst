The monetary library
====================

The uses of the library
-----------------------

The monetary library is meant for the development of systems that have a monetary component. The scope is amount conversions, incorporating formatting according to the locale of the running program and formatting of amounts according to the rules of the currency.

.. _AmountEditing:

Amount editing
--------------

Amounts are supposed to be stored as integers in the smallest unit available. So for Euro amounts, the amount is stored in cents, for Yen in yen. The number of decimal places (precision, both terms are used in the documentation) is gotten from the ISO table 4217.

Amounts are formatted according to the rules of the locale. If your machine is running in the locale en-US, the decimal position is the decimal point and the amount has space as its thousand separator.

There is code to check amount input as strings. In the end, the amount is cleared from special characters "brute force" and parsed to an integer. A sign is left on the amount, though if it is in a unexpected place conversion will fail. Expected places are at the start and the end of the amount.

Integration of WTForms: AmountField
-----------------------------------

If you are using WTForms to process web input from forms, the package comes with an AmountField that enables you to put amounts on the web page and validate those. The field is fully compliant with WTForms, where a StringField can be used, the AmountField can be used. Formatting is done by the routines mentioned in :ref:`AmountEditing`.

The formatting of the decimal separator depends on the currency. E.g. Euro and US Dollar have two decimal positions, Yen has none. We can pass the currency in the following ways:

  + when instantiating the field, pass the currency in in the currency field        ("currency='EUR'")

  + after the instance is created, set the instance variable currency to the value desired

  + before instantiating, set the get_currency method of the class to a function that accepts the field (as self) and returns the currency. If present, the field will call the method when it needs/could use the currency. Remove the function after instantiating the amount field(s)

The preferred ways are the first two. The function is a hack that carries risks. 

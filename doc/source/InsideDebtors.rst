Inside debtors
==============

Some technical information may be required to understand Debtors workings. In this chapter we describe some capita from the design and its background.

.. _physicalbill:

The physical bill
-----------------

In the description we refer to the physical bill production as an example. It is not a complete system, with documents that can be used "out of the box". This is because companies will be having their own rules and styling of these documents.

However, part of the code is reusable. The physicalbill module in debtviews has code to convert the model entities into usable human-readable data. This is re-usable, as whatever the medium (paper, mail), we need the conversion of numbers, amounts etc., into something a human can understand.

To check the use of the module and as an example, a template to create an RTF document is supplied (paperbill.rtf) and a HTML mail message (printbase.html, mailbill.html and mailbill.txt).

Overriding a preference
-----------------------

A postal address is assumed to be present always. So, if a preference of mail is set for a client bill or letter and the client has no known mail address, a postal letter is created.

Sending the mail bill
---------------------

I have left out the code to send the bill. Any SMTP sending code should work.

Document storage
----------------

Printing letters is not done by the system itself, it produces RTF documents. These documents are saved in the output directory of debtors. This is currently hardcoded, but can be changed easily (of course). To print these, you need a document processing program that can print RTF documents, it has been tested with LibreOffice (works) and Calligra (fails, it misinterprets some RTF commands).

The bank statement
------------------

Process payments is restricted to the processing of individual transactions from the statement. If you want to reconcile the bank account balance in your organization with the data from the bank, use another application.

Only incoming payments are processed. If you need to process outgoing payments, another system is called for.

Debtors does not supply code to process MT940 style statements. If you want to process those, replace or extend some of the incoming amounts code.

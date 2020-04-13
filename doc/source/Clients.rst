.. _democlientsystem:

The client subsystem
====================

Why this is part of debtors
---------------------------

The debtors system needs a client system to keep information on clients, their addresses and their bank accounts. Normally a company has such a system in place and will not be interested in having another one. This system does not want to replace existing systems, it is meant to be able to show and test all debtors functions. 

Its public interface to the debtors system may also give you an idea how client systems (other than this one) can interface to debtors. If you build a facade modeling the interface of this system, changes to debtors will of course be minimized.

Overview
--------

Clients are added to the system by a web application. The input will come from adding clients, adding addresses for this client and adding one or more bank accounts owned by the client. Later we can add bank accounts and addresses, invalidate addresses (e.g. on moving house) and we can remove bank accounts.

Upon death of the client we will not do anything. For a system detailing the minimum actions needed to keep debtors running, this is not essential.

Creating clients
----------------

The client is created on line through a web page. The client data input is as follows:

    :surname: Surname of the client. Maiden names are not separated out in the administration
    :first name: First name of the client; this is optional
    :initials: Initials ; also optional
    :birth date: birth date of the client. Optional, and of course irrelevant for corporations.
    :client sex: Sex of the client, for use in letters and mails

A client id is supplied by the client system.

The client can have one or more addresses. These come in flavors, a mail address (snail mail) and electronic mail. These  differ substantially and will be input through different (parts of the) web page(s). A mail address is input as follows:

    :street: Street name for the address
    :house_number: A house number in the street
    :po_box: A postbox number. If a postbox number is given, no street and house number are allowed.
    :town_village: The city, town or village of the address
    :postcode: The postcode
    :country: The country of residence
    :address_use: The usage of the address, general, postal, residence

An electronic mail address is utterly simple:

    :email: Electronic mail address for internet use. This address is checked to have valid syntax ("format")
    :preferred: Is this the client his preferred mail address?

The client can have one or more bank accounts. 

    :account_number: The bank account number
    :bic: Business Identifier Code of the bank where the account is held
    :name: The name that is on the bank account


Storing client information
--------------------------

The database contains the following data for the client:

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| client id              | the client system  | n/a       | n/a      |              
+------------------------+--------------------+-----------+----------+
| Surname                | input data         | Mandatory | No       |              
+------------------------+--------------------+-----------+----------+
| First name             | input data         | Optional  | No       |              
+------------------------+--------------------+-----------+----------+
| Initials               | input data         | Optional  | No       |              
+------------------------+--------------------+-----------+----------+
| Birth date             | input data         | Optional  | None     |              
+------------------------+--------------------+-----------+----------+
| Client sex             | input data         | Optional  | None     |              
+------------------------+--------------------+-----------+----------+

The database contains the following data for the clients addresses:

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| client id              | the client system  | Mandatory | n/a      |              
+------------------------+--------------------+-----------+----------+
| id                     | the client system  | n/a       | n/a      |              
+------------------------+--------------------+-----------+----------+
| street                 | input data         | Optional  | No       |              
+------------------------+--------------------+-----------+----------+
| house number           | input data         | Optional  | n/a      |              
+------------------------+--------------------+-----------+----------+
| po box                 | input data         | Optional  | n/a      |              
+------------------------+--------------------+-----------+----------+
| town or village        | input data         | Mandatory | No       |              
+------------------------+--------------------+-----------+----------+
| post code              | input data         | Optional  | n/a      |              
+------------------------+--------------------+-----------+----------+
| Country code           | input data         | Optional  | From     |              
|                        |                    |           | config   |
+------------------------+--------------------+-----------+----------+
| address use            | input data         | Optional  | General  |              
+------------------------+--------------------+-----------+----------+

The following remarks apply:

    :id: Address ids are starting from 0 for each client. There is no check for problems with concurrency
    :street, house number, po box: Either po box, or street and house number must be filled
    :post code: No checks on post code are done, these need be supplied by country code
    :address use: General, postal or residence. General is empty.

The database contains the following data for email addresses:

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| client id              | the client system  | Mandatory | n/a      |             
+------------------------+--------------------+-----------+----------+
| mail address           | input data         | Mandatory | No       |              
+------------------------+--------------------+-----------+----------+
| preferred              | input data         | Optional  | None     |              
+------------------------+--------------------+-----------+----------+

The database contains the following data for bank accounts:

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| client id              | the client system  | Mandatory | n/a      |              
+------------------------+--------------------+-----------+----------+
| id                     | the client system  | n/a       | n/a      |              
+------------------------+--------------------+-----------+----------+
| account number(IBAN)   | input data         | Mandatory | No       |              
+------------------------+--------------------+-----------+----------+
| bank id (BIC)          | input data         | Optional  | No       |              
+------------------------+--------------------+-----------+----------+
| Name                   | input data         | Mandatory | Client   |              
|                        |                    |           | name and |              
|                        |                    |           | initials |              
+------------------------+--------------------+-----------+----------+


The API for the debtors system
------------------------------

The client system needs to be able to supply the debtors system with information the billing and overdue processes need. The interface supplied are:

    :the client address: Address information for a client
    :client bank accounts: Deliver bank account information
    :bank account info: Deliver data for one (specified) bank account
    :selected clients: Select client information by name
    :find client by account: return client information for a given account number

All these interfaces are purely for GETting information from the client system. It will not be possible to do changes through  the interfaces.


The debtors interfaces
======================

The technical descriptions
--------------------------

For communications from other systems the debtor system has interfaces that these systems can use. This part of the document details how these systems can interface with the debtors system, in as far as lay-outs and conversation sequences are concerned.

Getting a list of outstanding bills
-----------------------------------

An external system can request a list of outstanding bills for a client. The list is requested as a HTTP message to

    /api/10/client/<client number>/bills

where <client number> is the client number of the client you want the bills for. There is no payload, the method is "GET".

Debtors answers with a message that has the following form::

    {"client" : "25",
    "name" : "J.J.L. Jansen",
    "bills" : [{"bill-id" : "733",
                "date-sale" : "2020-05-09",
                "date-billed" : "2020-05-09",
                "bill-replaced" : "16",
                "status" : "Billed, unpaid"},
               {"bill-id" : "749",
                "date-sale" : "2020-06-03",
                "date-billed" : "2020-06-04",
                "status" : "Billed, unpaid"}]}

The meaning of the fields is as follows:

    client
        The client number of the client requested. This is passed back as a string, because a client number may contain non-numeric parts.

    name
        The clients name. This is an edited form of the name. The demo client system will return a string composed of the initials and the surname of the client.

    bills
        a list of bills for the client. Only outstanding bills are listed.

    bill-id
        the internal number of the bill as known in the billing system. Can be used to collect more information on the bills

    date-sale
        The date of the transaction (sale) that was the origin of the debt that is referred to.

    date-billed
        The date the client was notified of this bill. This is important for the debt follow up.

    status
        A status of the bill. It is a shortcut which enables us to say something about the status of a bill (billed, paid etc.) without having to calculate the status each time it is retrieved.

The answer is a success message (the list) or an error message (:ref:`errormessages`).

.. _requestbill:

Submitting a bill request
-------------------------

Through the API other systems can submit bill requests to debtors. The url is

    /api/10/bill/new

The content of the payload is as follows::

    {"client" : "25",
     "currency" : "USD",
     "date-sale" : "2020-03-29:",
     "bill-replaced": "6",
     "bill-lines": [{"short-desc" : "Short description", 
                     "long-desc" : "A longer description",
                     "unit" : 25,
                     "unit-desc" : "kilos",
                     "unit-price" : 1765},
                     {"short-desc" : "Another description", 
                     "long-desc" : "Another longer description",
                     "unit" : 1,
                     "unit-price" : 2265}],
     "debtor-preferences" : {"bill-medium" : "mail",
                             "letter-medium" : "post"}
     }

The meaning of the fields is as follows:

    client
        The client id of the client that will be billed

    currency
        The currency that the bill will be in. It is the error code as found in ISO 4217

    date-sale
        The date the transaction was completed that created the debt

    bill-replaced
        If the current bill request should replace a previous bill, this is added; the bill with the bill_id from this item is invalidated by debtors. This item is optional, it will not be present on most bills

    bill-lines
        The individual lines detailing what is billed here and how the amount is made up

    short-desc
        The short description of the line. This is mandatory, it contains data that is sufficient for the recipient of the bill to understand what is billed.

    long-desc
        An optional explanation/precision of the bill line

    unit
        The number of units billed. This is an amount greater than zero

    unit-desc
        An optional field describing what the number in unit is. It is optional, default is units.

    unit-price
        The price per unit. The total for the line is unit * unit-price

    debtor-preferences
        The preferences of the client for the debtor system, currently how the debtor is contacted for the communication detailed below

    bill-medium
        The way the client receives bills. It can be mail for e-mail and post for postal

    letter medium
        The way the client receives bills. It can be mail for e-mail and post for postal


The debtor system will answer a success message (:ref:`successmessage`). This successmessage wil have the format::

    {"status" : "OK", "bill-id" : 725 }


.. _successmessage:

Confirm a successful transaction
--------------------------------

Confirming a succesful transaction is done by a success message. This message has the following format::

    {"status" : "OK", "bill-id" : 725  } 

The variant message is dependent on the transaction, it will usually contain an "interesting" key for the external system. E.g. after adding a bill request it will hold the bill_id.

.. _errormessages:

Error messages
--------------

Errors are returned as HTTP errors with a payload explaining the error, when an explication is available. E.g. a 500 error will usually not have any more "interesting" error info available, but a 404 will usually have that, we can return a message explaining what resource was not found.

A  message payload is as follows::

    {"message" : "The client was not found" , "client-number" : "25" }

The second item in the payload will be different depending on the resource that was required. Also if the missing resource is one the requested resource depends upon, it may be different. E.g. if we ask for a bill and we cannot retrieve the client, there will be a client number.

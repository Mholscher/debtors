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

The answer is a success message or an error message (:ref:`errormessages`).



.. _errormessages:

Error messages
--------------

Errors are returned as HTTP errors with a payload explaining the error, when an explication is available. E.g. a 500 error will usually not have any more "interesting" error info available, but a 404 will usually, because we can return a message explaining what resource was not found.

A  message payload is as follows::

    {"message" : "The client was not found" , "client-number" : "25" }

The second item in the payload will be different depending on the resource that was required. Also if the missing resource is one the requested resource depends upon, it may be different. E.g. if we ask for a bill and we cannot retrieve the client, there will be a client number.

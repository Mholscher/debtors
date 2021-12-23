Overdue processing
==================

The concept of overdue processing steps
---------------------------------------

To organize the overdue processing, we define steps in the overall overdue process. These steps are related to the time the payment is overdue. In this document we name the steps after documents that are produced, the system is more flexible than that.

The steps in the overdue process are defined in the database, so you are not limited to the steps here.

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| the overdue step id    | user input         | No        | None     |
+------------------------+--------------------+-----------+----------+
| after number of days   | user input         | No        | 30       |
+------------------------+--------------------+-----------+----------+
| step name              | user input         | No        | None     |
+------------------------+--------------------+-----------+----------+
| processor              | user input         | Yes       | None     |
+------------------------+--------------------+-----------+----------+

Steps are identified by a number. The number must be chosen by the user. It enables the user optimal freedom when choosing step numbers. In the example table  we use the numbers to order the step the same as the ordering of the steps in time.

The processor gets the bill that triggered overdue processing. It is responsible for checking if there are circumstances that prevent processing (e.g. the user has made an agreement with the client to postpone overdue processing) and doing overdue processing.

The list of available processor examples is:

    :firstletter: The first reminder of unpaid debt is sent
    :secondletter: The second reminder is sent
    :transfer: The debt is transferred to a debt collecting agency
    :dubiousdebt: The debt is from now on considered dubious. It is made dormant and the sum in debt posted as a loss due to non-payment.

In :ref:`overdue_processing` we state that the oldest debt is leading in debt processing, so one of the "circumstances" mentioned earlier is the existence of older debt.

The processor being empty triggers the default processor, which in the example process does nothing. You can define a process where a default exists if you have a use for it.

The history of overdue processing
---------------------------------

To be able to determine the step last executed (:ref:`last_step`) and to inform the user of what steps have been executed, we keep a history of all steps for a bill. The history consists of:

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| the id of this step    | the debtors system | Mandatory | n/a      |
+------------------------+--------------------+-----------+----------+
| step name              | the debtors system | Mandatory | n/a      |
+------------------------+--------------------+-----------+----------+
| bill processed         | the debtors system | Mandatory | n/a      |
+------------------------+--------------------+-----------+----------+
| triggering bill        | the debtors system | Optional  | n/a      |
+------------------------+--------------------+-----------+----------+
| date and time of       | the debtors system | Mandatory | n/a      |
| completion             |                    |           |          |
+------------------------+--------------------+-----------+----------+

If the content of a step is aimed at producing a document (e.g. a notification of late payment), reprinting the letter does not create a new history entry. Redoing the process should do that.

If a second overdue letter contains a debt for which a first overdue letter was not yet produced, the first overdue letter is supposed to be sent. See the graphic in :ref:`overdue_processing`. A record is than written for the processing of this bill.The triggering bill is used for the case described here to hold the bill that, well, triggered the processing of this step.

.. _last_step:

The last step: what was it?
------------------------------

For a bill overdue the last step taken for that bill is the record where "bill processed" is the bill under consideration and the "date and time of completion" is the latest for the bill.

The "after number of days" is not considered when determining if a step has been done. Suppose the second step should be taken after 60 days, if it appears in a later step before that 60 days, it is still considered to have been through second step, even if it is only 40 days overdue.

First overdue letter
--------------------

The processor will be creating a notice of overdue.

Second overdue letter
---------------------

The processor will be creating a notice of overdue. This will contain a notice of pending transfer to the debt collecting agency.

Notification of transfer
------------------------

The processor will transfer debt to the debt collecting agency. The client is notified in a letter that the agency will from now on contact the client about the debt and likewise the client should address any enquiries on the debt to the agency, not to the supplier.

All debt is transferred, not only the bill that triggered this action.

If for one or more of the bills in debt there is a block (see :ref:`debt_blocked`), the transfer is not done.

The content of the transfer is not known, because it is dependent on the agency contracted. We will create a small text file to show it has been processed.

Debtor becomes dubious
----------------------

There is no outgoing communication is this step. The bill is marked as dubious and accounting is made to reduce the debt and increase the dubious debtors account for the amount not received.

The client is marked as a debtor risk.

.. _debt_blocked:

Pausing and resuming overdue processing
---------------------------------------

Overdue processing can be be paused and resumed. A process that is paused has a block which shows:

+------------------------+--------------------+-----------+----------+
| Field name             |Source              | Optional? | Default  |
+========================+====================+===========+==========+
| the id the bill        | user input         | Mandatory | n/a      |
+------------------------+--------------------+-----------+----------+
| start date of the      | user input         | Mandatory | Today    |
| block                  |                    |           |          |
+------------------------+--------------------+-----------+----------+
| end date of the        | user input         | Optional  | None     |
| block                  |                    |           |          |
+------------------------+--------------------+-----------+----------+

If other debt of the client is processed, any bill for which there is a block is ignored.

The end date of the block can be entered when creating it, or at any later date.At the end date, overdue processing is resumed immediately. If a block has no end date, it will be extended indefinitely.

Bagatelle processing
--------------------

It is not efficient to process small debts. Debt processing costs money. So if a debt is small, no overdue processing is done if there is no other debt. The amount below which no debt processing is done, is kept as a configuration item.

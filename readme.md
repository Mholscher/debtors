# Debtors : Debt management software #

## Installing Debtors ##

Install Debtors from Github. There currently is no way to install it e.g. using pypi.

## How Debtors is developed ##

Debtors is developed on openSuse Linux, using Python 3.6 and MariaDB 10.2 to implement its database. To interface with the database I used SQLAlchemy, taking care to not use MariaDB specific constructs. It should run with all database backends SQLAlchemy supports, but no guarantees :=)

## A requirement to use all functions ##

The accounting is done with the GLedger package of my Github user. If you want to change that, see the source for the accounting interface.


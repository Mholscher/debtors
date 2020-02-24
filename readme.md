# Debtors : Debt management software #

## Installing Debtors ##

Install Debtors from Github. There currently is no way to install it e.g. using pypi.

## How Debtors is developed ##

Debtors is developed on openSuse Linux, using Python 3.6 and MariaDB 10.2 to implement its database. To interface with the database I used SQLAlchemy, taking care to not use MariaDB specific constructs. It should run with all database backends SQLAlchemy supports, but no guarantees :=)

## The environment, and why runserver? ##

The server in development can be started by running

python -m runserver

in the project directory. It will start the development server for development. If, contrary to the recommendation, you want to run it as a production server, remove the first 2 lines from the runserver.py script.

I choose this way to run the project as I could not get "flask run" to run the server in the way I like. If you can, good on you. It's not like I didn't try to do it the proper way...

## A requirement to use all functions ##

The accounting is done with the GLedger package of my Github user. If you want to change that, see the source for the accounting interface.


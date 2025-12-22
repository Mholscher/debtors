#    Copyright 2015-2020 Menno Hölscher
#
#    This file is part of debtors.

#    debtors is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    debtors is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with debtors.  If not, see <http://www.gnu.org/licenses/>.

import logging
import configparser
import locale as locale_module
from flask import Flask
from sqlalchemy.orm import declarative_base
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect


Base = declarative_base()

app = Flask('debtors')
app.config.from_pyfile('localdebtors.cfg')
config = app.config
db = SQLAlchemy(model_class=Base)
db.init_app(app)
CSRFProtect(app)
locale_module.setlocale(locale_module.LC_ALL, '')
locale = locale_module.localeconv()
DECIMAL_CHAR = locale['decimal_point']

#logging.basicConfig(filename='debtors.log', level=logging.INFO)
#logging.debug('Debug logging')

class InvalidDataError(ValueError):
    """ The data passed in is invalid """

    def to_dict(self):
        """ Return a dictionary with interesting info """

        return {"message" : str(self) }
 
from clients.clientbp import client_pages
app.register_blueprint(client_pages)
from debtors.debtapibp import debtapi
app.register_blueprint(debtapi)
import clientmodels.clients
import debtmodels.debtbilling
import debtmodels.payments
import debtmodels.overdue
from . import views

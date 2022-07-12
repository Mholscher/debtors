#    Copyright 2022 Menno Hölscher
#
#    This file is part of debtors.

#    debtors is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    debtors is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with debtors.  If not, see <http://www.gnu.org/licenses/>.

""" This file holds the views for position requests.

Positions present totals of debt and unassigned incoming amounts in totals.
Each viewpoint will enable decision makers to check the debt position, but
organized to different viewpoints, e.g. the debt by age.
"""

from datetime import date, timedelta, datetime
from flask import render_template, abort
from flask.views import MethodView
from debtors import config
from debtmodels.debtbilling import Bills
from debtviews.monetary import edited_amount
from debtviews.outputenvironments import rtfenvironment


class DebtByAge(object):

    """ Debt ordered by age """

    AGE_RECENT_DEBT = 30
    AGE_OLDER_DEBT = 60
    AGE_WORRYING = 90
    AGE_TOO_OLD = 360

    def recent_debt(self):
        """ Return debt recently invoiced """

        young_debt_period = (date.today()
                             - timedelta(days=self.AGE_RECENT_DEBT))
        return Bills.debt_for_period(young_debt_period, None)

    def older_debt(self):
        """ Return debt not very long overdue """

        young_debt_period = (date.today()
                             - timedelta(days=self.AGE_RECENT_DEBT))
        older_debt_period = (date.today()
                             - timedelta(days=self.AGE_OLDER_DEBT))
        return Bills.debt_for_period(older_debt_period, young_debt_period)

    def worrying_debt(self):
        """ Return debt unpaid for a long period. """

        older_debt_period = (date.today()
                             - timedelta(days=self.AGE_OLDER_DEBT))
        worrying_debt_period = (date.today()
                                - timedelta(days=self.AGE_WORRYING))
        return Bills.debt_for_period(worrying_debt_period,
                                     older_debt_period)


class DebtAgeReport():
    """ The age report for debt.

    It creates a report for different ages of debt 
    """

    def __init__(self):

        self.template = rtfenvironment.get_template("debtagereport.rtf")

    def write_report(self):
        """ This creates the data and renders the report template """

        debt_by_age = DebtByAge()
        report_data = dict()
        report_data["date_report"] = date.today().strftime(config["DATE_FORMAT"])
        report_data["time_report"] = datetime.today().strftime("%H:%M")
        recent_debt = debt_by_age.recent_debt()
        debt_by_ccy = []
        for k, v in recent_debt.items():
            ccy_debt = {"ccy": k, "amount": edited_amount(v, currency=k)}
            debt_by_ccy.append(ccy_debt)
        report_data["recent_debt"] = debt_by_ccy
        older_debt = debt_by_age.older_debt()
        debt_by_ccy = []
        for k, v in older_debt.items():
            ccy_debt = {"ccy": k, "amount": edited_amount(v, currency=k)}
            debt_by_ccy.append(ccy_debt)
        report_data["older_debt"] = debt_by_ccy
        worrying_debt = debt_by_age.worrying_debt()
        debt_by_ccy = []
        for k, v in worrying_debt.items():
            ccy_debt = {"ccy": k, "amount": edited_amount(v, currency=k)}
            debt_by_ccy.append(ccy_debt)
        report_data["worrying_debt"] = debt_by_ccy
        #print(report_data)
        self.text = self.template.render(age_data=report_data)

    def write_file(self):
        """ Output the age report to a file. """

        if not (hasattr(self, "text") and self.text):
            self.write_report()
        age_report_name = ("Age-report" +
                           date.today().strftime(config["DATE_FORMAT"]) +
                           datetime.today().strftime("%H:%M"))
        with open("output/" + age_report_name, "w") as report_file:
            report_file.write(self.text)

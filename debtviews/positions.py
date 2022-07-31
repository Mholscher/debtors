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
from debtmodels.overdue import OverdueActions
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


class DebtByStatus(object):
    """ Debt by status

    The status is the last overdue action executed. If that is writing
    the second overdue letter the status will be "secondletter". For
    each status there will be a method compiling the debt totals.

    For each status a small dictionary will be built for debt totals
    per currency, for it obviously is useless to have a position
    where part is Euro and part is Yen.
    """

    def _get_totals_by_currency(self, action):
        """ Return totals by currency for this action """

        actions = OverdueActions.get_all_last_action(action)
        totals_by_currency = dict()
        for action in actions:
            if action.bill.billing_ccy in totals_by_currency:
                totals_by_currency[action.bill.billing_ccy] += action.bill.total()
            else:
                totals_by_currency[action.bill.billing_ccy] = action.bill.total()
        return totals_by_currency

    def transferred(self):
        """ Return the totals of debt in for status transfer """

        return self._get_totals_by_currency("transfer")

    def second_letter(self):
        """ Return the totals of debt in for status second letter """

        return self._get_totals_by_currency("secondletter")

    def first_letter(self):
        """ Return the totals of debt in for status first letter """

        return self._get_totals_by_currency("firstletter")

class DebtStatusReport():
    """ This object creates and renders the debt report by last action """

    def __init__(self):

        self.template = rtfenvironment.get_template("debtstatusreport.rtf")

    def write_report(self):
        """ Create the data and write the report """

        debt_by_status = DebtByStatus()
        report_data = dict()
        report_data["date_report"] = date.today().strftime(config["DATE_FORMAT"])
        report_data["time_report"] = datetime.today().strftime("%H:%M")
        debt_by_ccy = []
        debt_first_letter = debt_by_status.first_letter()
        for k, v in debt_first_letter.items():
            ccy_debt = {"ccy": k, "amount": v}
            debt_by_ccy.append(ccy_debt)
        report_data["first_letter"] = debt_by_ccy
        debt_by_ccy = []
        debt_second_letter = debt_by_status.second_letter()
        for k, v in debt_second_letter.items():
            ccy_debt = {"ccy": k, "amount": v}
            debt_by_ccy.append(ccy_debt)
        report_data["second_letter"] = debt_by_ccy
        debt_by_ccy = []
        debt_transferred = debt_by_status.transferred()
        for k, v in debt_transferred.items():
            ccy_debt = {"ccy": k, "amount": v}
            debt_by_ccy.append(ccy_debt)
        report_data["transferred"] = debt_by_ccy
        self.text = self.template.render(status_data=report_data)

    def write_file(self):
        """ Output the status report to a file. """

        if not (hasattr(self, "text") and self.text):
            self.write_report()
        status_report_name = ("Status-report" +
                           date.today().strftime(config["DATE_FORMAT"]) +
                           datetime.today().strftime("%H:%M"))
        with open("output/" + status_report_name, "w") as report_file:
            report_file.write(self.text)

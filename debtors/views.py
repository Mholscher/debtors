from debtors import app
from flask import redirect, url_for


@app.route('/')
def index():
    """This is the index page of the application. It shows
    a list of accounts
    """
    return redirect(url_for('list_clients')) 

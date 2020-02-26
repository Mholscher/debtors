from debtors import app


@app.route('/')
def index():
    """This is the index page of the application. It shows
    a list of accounts
    """
    return "Hello from your debtors application"

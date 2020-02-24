import os
os.environ['FLASK_ENV']='development'

from debtors import app

app.run(debug=True)

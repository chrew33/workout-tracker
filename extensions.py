from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# this was created so multiple instances of the DB is not made at app.py and ini model.py
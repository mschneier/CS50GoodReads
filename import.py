import csv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import os
from models import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

SQLAlchemy().init_app(app)

def main():
    with open("books.csv") as f:
        rows = csv.reader(f, delimiter=",", quotechar='"')
        for row in rows:
            isbn = int(row[0].replace("X", "")) if row[0] else 1
            title = row[1].replace("'", "").replace('"', "")
            author = row[2].replace("'", "").replace('"', "")
            year = int(row[3]) if row[3] else 1
            db.execute(
                f"INSERT INTO books(isbn, title, author, year) VALUES({isbn}, '{title}', '{author}', {year})"
            )
            db.commit()


if __name__ == "__main__":
    with app.app_context():
        main()

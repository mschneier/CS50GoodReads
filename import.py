import csv
from flask import Flask
import os
from models import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

sql.init_app(app)

def main():
    with open("books.csv") as f:
        rows = csv.reader(f, delimiter=",", quotechar='"')
        for row in rows:
            book = Book(
                isbn=row[0],
                title=row[1],
                author=row[2],
                year=row[3]
            )
            sql.session.add(book)


if __name__ == "__main__":
    with app.app_context():
        main()

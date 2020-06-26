from flask_sqlalchemy import SQLAlchemy
from os import getenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker


sql = SQLAlchemy()

### FROM: https://www.fullstackpython.com/sqlalchemy-model-examples.html ###
engine = create_engine(
    getenv("DATABASE_URL"),
    convert_unicode=True
)
db_session = scoped_session(
    sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
)
Model = declarative_base(name='Model')
Model.query = db_session.query_property()
############################################################################


class User(sql.Model):
    """User class."""

    __tablename__ = "users"
    id = sql.Column(sql.Integer, primary_key="true")
    username = sql.Column(sql.String(50), nullable="false")
    password = sql.Column(sql.String(999), nullable="false")

    def __init__(self, username, password):
        self.username = username
        self.password = password


class Book(sql.Model):
    """Book class."""

    __tablename__ = "books"
    id = sql.Column(sql.Integer, primary_key=True)
    isbn = sql.Column(sql.Integer, nullable=False)
    title = sql.Column(sql.String(999), nullable=False)
    author = sql.Column(sql.String(200), nullable=False)
    year = sql.Column(sql.Integer, nullable=False)

    def __init__(self, isbn, title, author, year):
        self.isbn = isbn
        self.title = title
        self.author = author
        self.year = year


class Review(sql.Model):
    """Review class."""

    __tablename__ = "reviews"
    id = sql.Column(sql.Integer, primary_key=True)
    user = sql.Column(sql.Integer, nullable=False)
    book = sql.Column(sql.Integer, nullable=False)
    score = sql.Column(sql.Integer, nullable=False)
    review = sql.Column(sql.String(999), nullable=False)


    def __init__(self, username, isbn, score, review):
        self.username = username
        self.isbn = isbn
        self.score = score
        self.review = review


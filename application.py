import os
import requests

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from models import *
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from xmltodict import parse

app = Flask(__name__)
key = os.getenv("KEY")

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
Session(app)
SQLAlchemy().init_app(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    return redirect("/search")


@app.route("/login/", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    if request.method == "POST":
        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")
        if not username:
            flash("Must provide username.")
            return render_template("login.html")
        # Ensure password was submitted
        elif not password:
            flash("Must provide password.")
            return render_template("login.html")

        # Query database for password and id.
        user = db.execute(
            "SELECT id, password FROM users WHERE username=:username",
            {"username": username}
        ).fetchone()
        # Ensure password is correct
        if check_password_hash(user[1], password):
            flash("Invalid username and/or password.")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = user[0]

        # Redirect user to home page
        return redirect("/search")

    return render_template("login.html")


@app.route("/logout/")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register/", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        # Ensure username was submitted
        if not username:
            flash("Must provide username.")
            return render_template("register.html")
        # Ensure password was submitted
        elif not password:
            flash("Must provide password.")
            return render_template("register.html")
        elif password != confirmation:
            flash("Confirmation must equal password.")
            return render_template("register.html")
        db.execute(
            "INSERT INTO users(username, password) VALUES(:username, :password)",
            {"username": username, "password": password}
        )
        db.commit()
        flash("You can now login.")
        return redirect("/login")
    return render_template("register.html")


@app.route("/search/", methods=["GET", "POST"])
@login_required
def search():
    """Register user"""
    if request.method == "POST":
        
        isbn = request.form.get("isbn") if request.form.get("isbn") else 0
        author = request.form.get("author")
        title = request.form.get("title")
        
        if isbn:
            books = db.execute(
                f"""SELECT * FROM books WHERE isbn={isbn}
                AND author LIKE '%{author}%' and  title LIKE '%{title}%'"""
            ).fetchall()
        else:
            books = db.execute(
                f"""SELECT * FROM books WHERE author LIKE '%{author}%'
                AND title LIKE '%{title}%'"""
            )
        print(books)
        return render_template(
            "result.html",
            books=books,
            isbn=isbn,
            author=author,
            title=title,
        )
    return render_template("search.html")


@app.route("/api/<int:isbn>/")
def api(isbn):
    """ISBN API."""
    book = db.execute(
        "SELECT * FROM books WHERE isbn=:isbn",
        {"isbn": isbn}
    ).fetchone()
    res = parse(requests.get(
        f"https://www.goodreads.com/search.xml?key={key}&q={book.title}",
    ).content)
    response = res["GoodreadsResponse"]["search"]["results"]["work"][0]
    if not book:
        return "That isbn doesn't exist", 404
    bookDict = {
        "title": book[2],
        "author": book[3],
        "year": book[4],
        "isbn": book[1],
        "review_count": response["ratings_count"]["#text"],
        "average_score": response["average_rating"],
    }
    return jsonify(bookDict)


@app.route("/book/<int:isbn>/", methods=["GET", "POST"])
@login_required
def book(isbn):
    """Book details."""
    isbn = str(isbn)
    user = db.execute(
        "SELECT id, username FROM users WHERE id=:userID",
        {"userID": session["user_id"]}
    ).fetchone()
    book = db.execute(
        "SELECT * FROM books WHERE isbn=:isbn",
        {"isbn": isbn}
    ).fetchone()
    if not book:
        return "That isbn doesn't exist", 404
    userReviews = db.execute(
        f"SELECT * FROM reviews WHERE user LIKE '%{user[1]}%'",
        {"user": user}
    ).fetchall()
    if request.method == "POST":
        if userReviews:
            flash("You already submitted a review for this book.")
            return redirect("/")
        newReview = request.form.get("newReview")
        score = int(request.form.get("score"))
        db.execute(
            "INSERT INTO reviews(user, book, score, review) VALUES(:user, :book, :score, :review)",
            {"user": user[0], "book": book, "score": score, "review": newReview}
        )
        db.commit()
        flash("You posted a review.")
        return redirect(f"/book/{isbn}")
    isbn = book[1]
    title = book[2]
    author = book[3]
    year = book[4]
    reviews = db.execute(
        "SELECT * FROM reviews WHERE book=:book",
        {"book": book[0]}
    ).fetchall()
    modReviews = [list(review) for review in reviews]
    for review in modReviews:
        review[1] = db.execute(
            "SELECT username FROM users WHERE id=:userID",
            {"userID": review[1]}
        ).fetchone()[0]
    res = parse(requests.get(
        f"https://www.goodreads.com/search.xml?key={key}&q={book.title}",
    ).content)
    response = res["GoodreadsResponse"]["search"]["results"]["work"][0]
    return render_template(
        "book.html",
        isbn=isbn,
        title=title,
        author=author,
        year=year,
        reviews=modReviews,
        userReviews=userReviews,
        reviewCount=response["ratings_count"]["#text"],
        averageScore=response["average_rating"],
    )

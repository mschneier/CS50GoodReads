import os

from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from functools import wraps
from models import *
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlClasses import Book, User
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
key = os.getenv("KEY")

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

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

        # Query database for username
        rows = User.query.filter_by(username=username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password.")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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
        confirmation = request.form.get("confirmtation")
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
        usernames = User.query.filter_by(username=username)
        if usernames:
            flash("Username already taken.")
            return render_template("register.html")
        user = User(
            username=username, password=password
        )
        sql.session.add(user)
        return redirect("/")
    return render_template("register.html")


@app.route("/search/", methods=["GET", "POST"])
@login_required
def search():
    """Register user"""
    if request.method == "POST":
        isbn = request.form.get("isbn")
        author = request.form.get("author")
        title = request.form.get("title")
        searches = 0
        for search in [isbn, author, title]:
            if search:
                searches += 1
        if not searches:
            flash("You can only search for one search term.")
            return render_template("search.html")
        books = Book.query.filter(
            Book.isbn.like(f"%{isbn}%"),
            Book.author.like(f"%{author}%"),
            Book.title.like(f"%{title}%")
        ).all()
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
    isbn = str(isbn)
    res = requests.get(
        "https://www.goodreads.com/book/review_counts.json",
        params={"key": key, "isbns": isbn}
    ).json()
    book = Book.query.filter_by(isbn=isbn)
    if len(book) != 1:
        return "That isbn doesn't exist", 404
    bookDict = {
        "title": book[2],
        "author": book[3],
        "year": book[4],
        "isbn": book[1],
        "review_count": res["review_count"],
        "average_score": res["average_rating"],
    }
    return jsonify(bookDict)


@app.route("/book/<int:isbn>/", methods=["GET", "POST"])
@login_required
def book(isbn):
    """Book details."""
    isbn = str(isbn)
    userId = User.query.filter_by(username=session["user_id"])[0]
    book = Book.query.filter_by(isbn=isbn)
    if not book:
        return "That isbn doesn't exist", 404
    if request.method == "POST":
        userReviews = Review.query.filter_by(username=session["user_id"])
        if userReviews:
            flash("You already submitted a review for this book.")
            return redirect("/")
        newReview = request.form.get("newReview")
        score = request.form.get("score")
        bookId = Book.query.filter_by(isbn=isbn)[0]
        review = Review(
            user=userId,
            book=bookId,
            score=score,
            review=newReview
        )
        sql.session.add(review)
        return redirect(f"/book/{isbn}")
    isbn = book[1]
    title = book[2]
    author = book[3]
    year = book[4]
    reviews = Review.query.filter_by(isbn=isbn)
    userReviews = Review.query.filter_by(user=userId)
    res = requests.get(
        "https://www.goodreads.com/book/review_counts.json",
        params={"key": key, "isbns": isbn}
    ).json()
    return render_template(
        "book.html",
        isbn=isbn,
        title=title,
        author=author,
        year=year,
        reviews=reviews,
        userReviews=userReviews,
        reviewCount=res["review_count"],
        averageScore=res["average_rating"],
    )

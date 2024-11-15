from flask import Flask, render_template, redirect, request, flash, jsonify, send_file, json
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv
import io
import csv

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
Scss(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATION"] = False
db = SQLAlchemy(app)

class Inventory(db.Model):
    __tablename__ = 'inventory'

    entry_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(100), nullable=True)
    publication_date = db.Column(db.Date, nullable=True)
    isbn = db.Column(db.String(13), unique=True, nullable=False)

    def __repr__(self):
        return f"Task{self.entry_id}"

with app.app_context():
        db.create_all()

# home page
@app.route("/", methods=["POST", "GET"])
def index():
    # Add book logic remains the same...
    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        genre = request.form.get("genre")
        publication_date = request.form.get("publication_date")
        isbn = request.form.get("isbn")

        # Validate and process the publication date
        if publication_date:
            try:
                publication_date = datetime.strptime(publication_date, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.")
                return redirect("/")

        # Create a new Inventory record
        new_book = Inventory(
            title=title,
            author=author,
            genre=genre,
            publication_date=publication_date,
            isbn=isbn
        )

        # Add to the database and commit
        try:
            db.session.add(new_book)
            db.session.commit()
            flash("Book successfully added!")
        except Exception as e:
            flash(f"Error adding book: {str(e)}")
        return redirect("/")

    # Initialize an empty list for books
    books = []
    filter_applied = False

    # Filtering logic for GET requests
    title = request.args.get("title")
    author = request.args.get("author")
    genre = request.args.get("genre")
    publication_date = request.args.get("publication_date")

    # Apply filters only if they are provided
    if title or author or genre or publication_date:
        books_query = Inventory.query
        if title:
            books_query = books_query.filter(Inventory.title.ilike(f"%{title}%"))
        if author:
            books_query = books_query.filter(Inventory.author.ilike(f"%{author}%"))
        if genre:
            books_query = books_query.filter(Inventory.genre.ilike(f"%{genre}%"))
        if publication_date:
            try:
                publication_date = datetime.strptime(publication_date, "%Y-%m-%d").date()
                books_query = books_query.filter(Inventory.publication_date == publication_date)
            except ValueError:
                flash("Invalid date format for filtering. Please use YYYY-MM-DD.")

        books = books_query.all()
        filter_applied = True

    # Render the template with books and filter state
    return render_template("index.html", books=books, filter_applied=filter_applied,
                           title=title, author=author, genre=genre, publication_date=publication_date)


@app.route("/export", methods=["GET"])
def export_books():
    # Use the same filtering logic from the index route
    title = request.args.get("title")
    author = request.args.get("author")
    genre = request.args.get("genre")
    publication_date = request.args.get("publication_date")
    export_format = request.args.get("format", "csv").lower()

    books_query = Inventory.query

    # Apply filters if present
    if title:
        books_query = books_query.filter(Inventory.title.ilike(f"%{title}%"))
    if author:
        books_query = books_query.filter(Inventory.author.ilike(f"%{author}%"))
    if genre:
        books_query = books_query.filter(Inventory.genre.ilike(f"%{genre}%"))
    if publication_date:
        try:
            publication_date = datetime.strptime(publication_date, "%Y-%m-%d").date()
            books_query = books_query.filter(Inventory.publication_date == publication_date)
        except ValueError:
            return "Invalid date format. Use YYYY-MM-DD.", 400

    books = books_query.all()

    # Export as CSV
    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        writer.writerow(["Entry ID", "Title", "Author", "Genre", "Publication Date", "ISBN"])
        for book in books:
            writer.writerow([book.entry_id, book.title, book.author, book.genre, 
                             book.publication_date, book.isbn])

        output.seek(0)
        return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                         mimetype="text/csv",
                         as_attachment=True,
                         download_name="filtered_books.csv")

    # Export as JSON
    elif export_format == "json":
        books_list = [{
            "entry_id": book.entry_id,
            "title": book.title,
            "author": book.author,
            "genre": book.genre,
            "publication_date": str(book.publication_date),
            "isbn": book.isbn
        } for book in books]

        output = io.StringIO()
        output.write(json.dumps(books_list, indent=4))  
        output.seek(0)

        return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                         mimetype="application/json",
                         as_attachment=True,
                         download_name="filtered_books.json")

    # If unsupported format is provided
    return "Unsupported format. Use 'csv' or 'json'.", 400


if __name__ == "__main__":
    
    app.run(debug=True)
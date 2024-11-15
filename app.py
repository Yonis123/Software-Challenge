from flask import Flask, render_template, redirect, request, flash, jsonify, send_file, json
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import io
import csv

# Initialize the Flask application
app = Flask(__name__)

# Set the secret key for session management and security
app.secret_key = "sdfjhuherwutgobkdjfgdsdf4"

# Enable SCSS for styling
Scss(app)

# Configure the SQLite database and disable modification tracking to reduce overhead
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATION"] = False
db = SQLAlchemy(app)

# Define the Inventory model representing a book in the database
class Inventory(db.Model):
    __tablename__ = 'inventory'

    entry_id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # Unique ID for each book
    title = db.Column(db.String(255), nullable=False)  # Book title
    author = db.Column(db.String(255), nullable=False)  # Book author
    genre = db.Column(db.String(100), nullable=True)  # Book genre
    publication_date = db.Column(db.Date, nullable=True)  # Date of publication
    isbn = db.Column(db.String(13), unique=True, nullable=False)  # ISBN, must be unique

    def __repr__(self):
        return f"Task{self.entry_id}"  # Represents each book entry with its ID for easy debugging

# Create database tables within the app context
with app.app_context():
        db.create_all()

# Home page route for displaying and managing the book inventory
@app.route("/", methods=["POST", "GET"])
def index():
    # Handle book addition when a POST request is made
    if request.method == "POST":
        title = request.form.get("title")
        author = request.form.get("author")
        genre = request.form.get("genre")
        publication_date = request.form.get("publication_date")
        isbn = request.form.get("isbn")

        # Process and validate the publication date format
        if publication_date:
            try:
                publication_date = datetime.strptime(publication_date, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.")
                return redirect("/")

        # Create a new Inventory record to add to the database
        new_book = Inventory(
            title=title,
            author=author,
            genre=genre,
            publication_date=publication_date,
            isbn=isbn
        )

        # Attempt to save the new book to the database and handle errors
        try:
            db.session.add(new_book)
            db.session.commit()
            flash("Book successfully added!")
        except Exception as e:
            flash(f"Error adding book: {str(e)}")  # Display error message if something goes wrong
        return redirect("/")

    # Initialize an empty list for books and a flag to indicate if a filter was applied
    books = []
    filter_applied = False

    # Gather filter criteria from the GET request parameters
    title = request.args.get("title")
    author = request.args.get("author")
    genre = request.args.get("genre")
    publication_date = request.args.get("publication_date")

    # Only apply filters if at least one filter criterion is provided
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

        # Get all filtered books and set filter_applied to True
        books = books_query.all()
        filter_applied = True

    # Render the index template with the books and filter state
    return render_template("index.html", books=books, filter_applied=filter_applied,
                           title=title, author=author, genre=genre, publication_date=publication_date)

# Route to handle exporting books in CSV or JSON format
@app.route("/export", methods=["GET"])
def export_books():
    # Gather filter criteria from the request for exporting specific data
    title = request.args.get("title")
    author = request.args.get("author")
    genre = request.args.get("genre")
    publication_date = request.args.get("publication_date")
    export_format = request.args.get("format", "csv").lower()

    books_query = Inventory.query

    # Apply the same filters as in the index route
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

    # Handle CSV export
    if export_format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)

        # Write the CSV headers
        writer.writerow(["Entry ID", "Title", "Author", "Genre", "Publication Date", "ISBN"])
        
        # Write book data to CSV
        for book in books:
            writer.writerow([book.entry_id, book.title, book.author, book.genre, 
                             book.publication_date, book.isbn])

        output.seek(0)  # Reset pointer to the beginning of the file for reading
        return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                         mimetype="text/csv",
                         as_attachment=True,
                         download_name="filtered_books.csv")

    # Handle JSON export
    elif export_format == "json":
        # Create a list of dictionaries representing each book
        books_list = [{
            "entry_id": book.entry_id,
            "title": book.title,
            "author": book.author,
            "genre": book.genre,
            "publication_date": str(book.publication_date),
            "isbn": book.isbn
        } for book in books]

        # Convert to JSON format
        output = io.StringIO()
        output.write(json.dumps(books_list, indent=4))  
        output.seek(0)

        return send_file(io.BytesIO(output.getvalue().encode("utf-8")),
                         mimetype="application/json",
                         as_attachment=True,
                         download_name="filtered_books.json")

    # Return an error if an unsupported format is requested
    return "Unsupported format. Use 'csv' or 'json'.", 400


if __name__ == "__main__":
    # Run the application in debug mode for development purposes
    app.run(debug=True)
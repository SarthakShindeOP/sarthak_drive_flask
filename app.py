from flask import Flask, request, render_template, redirect, session, url_for, flash, send_from_directory
import os
import mysql.connector
import bcrypt
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'secret_key'

# MySQL Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'cloud'
}

UPLOAD_FOLDER = 'documents'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper function to execute queries
def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['email'] = user['email']
            session['user_id'] = user['id']
            session['username'] = user['name']  # Save username in the session
            return redirect('/dashboard')
        else:
            return render_template('login.html', error='Invalid user')

    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'email' not in session:
        return redirect('/login')

    user_id = session['user_id']
    username = session['username']  # Access the username from the session

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        file_name = request.form['file_name']
        file_description = request.form['file_description']
        file = request.files['file']

        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')  # Normalize path
            file.save(file_path)

            cursor.execute(
                "INSERT INTO files (user_id, file_name, file_description, file_path) VALUES (%s, %s, %s, %s)",
                (user_id, file_name, file_description, file_path)
            )
            conn.commit()
            flash('File uploaded successfully!', 'success')
        else:
            flash('Please upload a valid PDF file.', 'danger')

    cursor.execute("SELECT * FROM files WHERE user_id = %s", (user_id,))
    files = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('dashboard.html', files=files, username=username)

# Route to view a file
@app.route('/view/<path:filename>')
def view_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route to download a file
@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('user_id', None)
    session.pop('username', None)  # Remove username from session
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, session,url_for,send_file,Response
import smtplib
from email.message import EmailMessage
import random
import re
from database import (db_init, db_verification_insert, 
                      db_verifyotp, db_insert, db_login,
                      db_checkuser,db_updatepassword,db_getnotes,
                      db_notesinsert, db_getnote,db_updatenote,db_deletenote,db_insertfile,db_getfiles,db_getfile, db_deletefile,db_search)
from itsdangerous import URLSafeTimedSerializer
import os
import io
import csv

app = Flask(__name__)
db_init()
app.secret_key = 'my app'
serializer = URLSafeTimedSerializer(secret_key = app.secret_key)

admin_email = 'vishunu2125@gmail.com'
admin_password = 'tdug arfw bzgf njck'
app.config["UPLOAD_FOLDER"]="uploads"
os.makedirs(app.config["UPLOAD_FOLDER"],exist_ok=True)

def send_mail(to_email, body):    
    msg = EmailMessage()
    msg.set_content(body)
    msg['To'] = to_email
    msg['From'] = admin_email
    msg['Subject'] = 'OTP verification'
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(admin_email, admin_password)
        smtp.send_message(msg)
        
   
@app.route('/')
def home(): 
    session.clear()   
    return render_template('home.html')

@app.route('/register', methods = ['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not re.match(r'^[\w\.-]+@[\w]+\.[\w]+$', email):
            message = 'Invalid Email'
            message_type = 'error'
            return render_template('register.html', message = message, message_type = message_type)
        
        elif not ((5 <= len(password) <= 8) and (password[0].isupper()) and (not password.isalnum())):
            message = '''Password should have a min of 5 and max of 8 characters.
            First character should be upper case. There should be atleast one 
            character other than alphabets and numbers.            
                      '''
            message_type = 'error'
            return render_template('register.html', message = message, message_type = message_type)
        
        elif db_checkuser(email):
            message = "Email already exists"
            message_type = 'error'
            return render_template('login.html', message = message, message_type = message_type)
        
        otp = str(random.randint(100000, 999999))
        body = f'Your OTP for verification is {otp}'
        send_mail(email, body)
        db_verification_insert(username, email, password, otp)
        return redirect(url_for('verify_otp', email = email))
    return render_template('register.html')

@app.route('/verify_otp/<email>',methods = ['POST', 'GET'])
def verify_otp(email):
    message = ''
    msg_type = ''
    
    if request.method == 'POST':
        otp = request.form.get('otp')
        status = db_verifyotp(email,otp)
        if status:
            db_insert(email)
            return redirect(url_for('login'))
        else:
            message = 'Invalid OTP'
            msg_type = 'error' 
               
    return render_template('verify_otp.html',email = email, message = message, message_type = msg_type)

@app.route('/login', methods = ['POST', 'GET'])
def login():
    message = ''
    message_type = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = db_login(username, password)
        user_id = user['USER_ID']
        if user:
            session['user_id'] = user_id
            session['username'] = username
            return redirect(url_for('dashboard'))
            
        else:
            message = 'Bad credentials'
            message_type = 'error'        
    return render_template('login.html', message = message, message_type = message_type)

@app.route('/dashboard')
def dashboard():
    if 'user_id'in session:
        return render_template('dashboard.html')    
    return redirect(url_for('login'))


@app.route('/forgot_password', methods = ['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if db_checkuser(email):
            token = serializer.dumps(email, salt = 'password-reset')
            reset_url = url_for('reset_password', token = token, _external = True )
            body = f"Please click on this link to reset: {reset_url}" 
            send_mail(email,body) 
            msg = "Email sent" 
            msg_type = 'success'
            return render_template('login.html', message = msg, message_type= msg_type)   
        else:
            msg = 'Not a registered User'
            msg_type = 'error'
            return render_template('register.html', message = msg, message_type = msg_type)
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods = ['GET', 'POST'])
def reset_password(token):
    email = serializer.loads(token, salt = 'password-reset')
    if request.method == 'POST':
        new_password = request.form.get('password')
        db_updatepassword(email, new_password)
        msg = 'Updated Successfully'
        msg_type = 'success'
        return render_template('login.html', message = msg, message_type = msg_type)
        
    return render_template('reset_password.html', token = token)
   
@app.route('/add_note', methods = ['GET', 'POST'])
def add_note():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        user_id = session.get('user_id')
        db_notesinsert(user_id, title, content)
        return redirect(url_for('view_notes'))
    return render_template('add_note.html')

@app.route('/view_notes')
def view_notes():
    user_id = session['user_id']
    notes = db_getnotes(user_id)
    print(notes)
    return render_template('view_notes.html', notes = notes)

@app.route('/view_note/<nid>')
def view_note(nid): 
    note = db_getnote(nid)  
    return render_template('view_note.html', note = note)

@app.route('/update_note/<nid>', methods = ['POST', 'GET'])
def update_note(nid):
    note = db_getnote(nid)
    if request.method == 'POST':
        title = request.form.get('title') 
        content = request.form.get('content')  
        user_id = session['user_id']
        db_updatenote(user_id, nid, content,title)
        msg = 'Updated successfully'
        msg_type = 'success'
        return render_template("update_note.html",message=msg,message_type=msg_type,note=note)
        
    return render_template('update_note.html', note = note)

@app.route('/delete_note/<nid>')
def delete_note(nid):
    db_deletenote(nid)   
    return redirect(url_for('view_notes'))

@app.route('/upload_file',methods=['POST','GET'])
def upload_file():
    if request.method=='POST':
        file=request.files.get('file')
        file_name=file.filename
        file_path=os.path.join(app.config['UPLOAD_FOLDER'],file_name)
        file.save(file_path)
        user_id=session["user_id"]
        db_insertfile(user_id,file_name,file_path)
        return redirect(url_for("view_files"))
    return render_template("upload_file.html")

@app.route('/view_files')
def view_files():
    user_id = session['user_id']
    files = db_getfiles(user_id)
    return render_template('view_files.html', files = files)

@app.route('/view_file/<fid>')
def view_file(fid):
    file = db_getfile(fid)
    file_path = file['FILE_PATH']
    return send_file(file_path, as_attachment = False)

@app.route('/download_file/<fid>')
def download_file(fid):
    file = db_getfile(fid)
    file_path = file['FILE_PATH']
    return send_file(file_path, as_attachment = True)

@app.route('/delete_file/<fid>')
def delete_file(fid):
    file = db_getfile(fid)
    file_path = file['FILE_PATH']
    os.remove(file_path)
    db_deletefile(fid)
    return redirect(url_for('view_files'))


@app.route('/search', methods = ['POST', 'GET'])
def search():
    if not session['user_id']:
        return redirect(url_for('login.html'))
    if request.method == 'POST':
        query = request.form.get('query')
        user_id = session['user_id']
        notes = db_search(query,user_id)
        return render_template('search.html', notes = notes)
    return render_template('search.html')

@app.route('/export_notes')
def export_notes():
    user_id = session["user_id"]
    notes = db_getnotes(user_id)   # function should return list of dicts

    if not notes:
        return "No notes to export."

    # Build text content
    export_content = "Your Notes Export\n\n"
    for note in notes:
        export_content += f"Title: {note['TITLE']}\n"
        export_content += f"Content: {note['CONTENT']}\n"
       
        export_content += "-" * 60 + "\n"

    return Response(
        export_content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=notes_export.txt"}
    )

@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.clear()        
    return render_template('login.html')

app.run(debug = True)
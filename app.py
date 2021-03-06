import os
from flask import Flask, render_template,request,flash,redirect,url_for,session,logging
from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form,DateField,IntegerField,StringField,TextAreaField,FileField,PasswordField,validators,SelectField
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from passlib.hash import sha256_crypt
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict

app = Flask(__name__,static_url_path='/static')
app.debug = True

#config mysql
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'yourkraft'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

#init MYSQL_DB
mysql = MySQL(app)


Articles = Articles()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/artist')
def articles():
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM profile_a")
    artists = cur.fetchall()
    app.logger.info(artists)
    if result > 0:
        return render_template('articles.html', artists=artists)
    else:
        msg = "No artist available "
        return render_template('articles.html', msg=msg)

    cur.close()


class Booking(Form):
    Detail = TextAreaField('Details',[validators.DataRequired(),validators.Length(min=1,max=250)])
    Venue = StringField('Venue',[validators.DataRequired(),validators.Length(min=6,max=30)])
    Genre = SelectField('Genre',choices=[('Pop','Pop'),('Rock','Rock')])
    Amount = IntegerField('Quotation',[validators.NumberRange(min=3000)])
    Date = DateField('Date',format='%Y-%m-%d')

@app.route('/artist/booking/<string:id>', methods=['GET','POST'])
def booking(id):
    form = Booking(request.form)
    if request.method ==  'POST' and form.validate():
        Detail = form.Detail.data
        Venue = form.Venue.data
        Genre = form.Genre.data
        Amount = form.Amount.data
        Date1 = str(form.Date.data)

        #create cur
        cur = mysql.connection.cursor()

        #execute
        cur.execute("INSERT INTO booking(Username_B,Username_A,Venue,Amount,Date,Genre,Detail) VALUES(%s,%s,%s,%s,%s,%s,%s)",(session['Username'],id,Venue,Amount,Date1,Genre,Detail))

        mysql.connection.commit()

        cur.close()

        flash('Booking sent, Wait for confirmation..','info')

        return redirect(url_for('dashboard'))
    return render_template('booking.html',form=form,id=id)

#single article
@app.route('/article/<string:id>/')
def article(id):
    return render_template('article.html', id = id)

# User Register form
class RegisterForm(Form):
    Username = StringField('Username',[validators.DataRequired(),validators.Length(min=1,max=15)])
    Email = StringField('Email',[validators.DataRequired(),validators.Length(min=6,max=30)])
    Password = PasswordField('Password',[
        validators.DataRequired(),
        validators.EqualTo('Confirm', message='Password do not match')
    ])
    Confirm = PasswordField('Confirm Password')
    Type_Acc = SelectField('Account Type',choices=[('Artist','Artist'),('Business','Business')])

# user register
@app.route('/register', methods= ['GET','POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        Username = form.Username.data
        Email = form.Email.data
        Password = sha256_crypt.encrypt(str(form.Password.data))
        Type_Acc = form.Type_Acc.data

        #create cursor
        cur = mysql.connection.cursor()

        session['logged_in'] = True
        session['Username'] = Username
        session['Type_Acc'] = Type_Acc
        session['account'] = True
        result = cur.execute("SELECT * FROM users WHERE Username = %s ",[Username])
        #if username is taken
        if result > 0:
            flash('Username is taken.','danger')
            cur.close()
            return redirect(url_for('register'))
        else:
            #execute
            cur.execute("INSERT INTO users(Username,Email,Password,Type_Acc) VALUES(%s, %s, %s, %s)", (Username,Email,Password,Type_Acc))

            #commit
            mysql.connection.commit()

            #close connection
            cur.close()

            flash('You are now registered and can log in','success')
        return redirect(url_for('profile_a'))
    return render_template('register.html',form = form)

#User Login
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        # Get form fields
        Username = request.form['Username']
        Password_candidate = request.form['Password']

        #cursor
        cur = mysql.connection.cursor()

        #Get user by username
        result = cur.execute("SELECT * FROM users WHERE Username = %s ",[Username])

        if result > 0:
            # Get stored Hash
            data = cur.fetchone()
            Password = data['Password']
            Type_Acc = data['Type_Acc']

            #compare
            if sha256_crypt.verify(Password_candidate,Password):
                #passed
                session['logged_in'] = True
                session['Username'] = Username
                session['Type_Acc'] = Type_Acc
                session['account'] = True

                flash('you are now logged in', 'sucess')
                return redirect(url_for('dashboard'))
            else:
                error =  'Password not found'
                return render_template('login.html',error=error)
            # close connection
            cur.close()
        else:
            error =  'Username not found'
            return render_template('login.html',error=error)

    return render_template('login.html')

#check if user logged_in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash('Please Login','danger')
            return redirect(url_for('login'))
    return wrap


#logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

#accept
@app.route('/accept/<string:id>/')
@is_logged_in
def accept(id):
    cur = mysql.connection.cursor()
    #app.logger.info(id)

    result = cur.execute("SELECT * FROM booking WHERE id = %s ",id)
    if result>0:
        app.logger.info(id)
        cur.execute("UPDATE booking SET Status = %s WHERE id = %s",('Accepted',id))
        flash("You have accepted..",'success')
        cur.connection.commit()

    cur.close()


    return redirect(url_for('dashboard'))

#ignore
@app.route('/decline/<string:id>/')
@is_logged_in
def decline(id):
    cur = mysql.connection.cursor()
    #app.logger.info(id)
    result = cur.execute("SELECT * FROM booking WHERE id = %s ",id)
    if result>0:
        app.logger.info(id)
        cur.execute("UPDATE booking SET Status = %s WHERE id = %s",('Decline',id))
        flash("You have declined..",'danger')
        cur.connection.commit()

    cur.close()
    return redirect(url_for('dashboard'))

#delete booking
@app.route('/delete_b/<string:id>/',methods=['POST'])
@is_logged_in
def delete_b(id):
    #cursor
    cur = mysql.connection.cursor()

    #execute
    cur.execute("DELETE FROM booking WHERE id = %s",[id])

    cur.connection.commit()

    cur.close()
    flash("Booking Deleted...",'success')
    return redirect(url_for('dashboard'))


# dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():

    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM booking WHERE Username_A = %s OR Username_B = %s ",[session['Username'],session['Username']])

    booking = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html',bookings=booking)

    else:
        msg='Nothing Yet!! Please wait..'
        return render_template('dashboard.html',msg=msg)

    cur.close()

    return render_template('dashboard.html')


#Profile Page
@app.route('/profile/<string:id>/')
@is_logged_in
def profile(id):
    session["account"] = True
    app.logger.info(session["account"])
    if id == session['Username']:
        cur = mysql.connection.cursor()
        #app.logger.info(id)

        if session['Type_Acc'] == 'Artist':
            result = cur.execute("SELECT * FROM profile_a WHERE Username = %s ",[session['Username']])

            #fetchone
            profi = cur.fetchone()

            result1=cur.execute("SELECT * FROM booking WHERE Username_A = %s",[session['Username']])
            booking = cur.fetchall()
            #booking fetching


            app.logger.info(profi['Username'])
            if result > 0:
                #for second time users
                return render_template('profile.html', profi=profi,bookings = booking)
                cur.close()
            else:
                #for first time
                cur.close()
                return redirect(url_for('profile_a'))
        else:
            result = cur.execute("SELECT * FROM profile_b WHERE Username = %s ",[session['Username']])

            profi = cur.fetchone()

            if result > 0:
                #for second time users
                return render_template('profile.html', profi=profi,)
                cur.close()
            else:
                #for first time
                cur.close()
                return redirect(url_for('profile_a'))
    else:
        cur = mysql.connection.cursor()
        app.logger.info(id)
        app.logger.info(session["account"])
        if session['Type_Acc'] == 'Business':

            result = cur.execute("SELECT * FROM profile_a WHERE Username = %s ",[id])

            #fetchall
            profi = cur.fetchone()
            if result > 0:
                #for second time users
                session["account"] = False
                app.logger.info(session["account"])
                return render_template('profile.html', profi=profi)
                cur.close()
            else:
                #for first time
                cur.close()
                return redirect(url_for('profile_a'))
        else:
            result = cur.execute("SELECT * FROM profile_b WHERE Username = %s ",[id])

            profi = cur.fetchone()

            if result > 0:
                #for second time users
                return render_template('profile.html', profi=profi)
                cur.close()
            else:
                #for first time
                cur.close()
                return redirect(url_for('profile_a'))

    return render_template('profile.html',id=id)

#profile form  for artist edit
class Profile_A(Form):
    First_name = StringField('First Name',[validators.DataRequired(),validators.Length(min=1,max=15)])
    Last_name = StringField('Last Name',[validators.DataRequired(),validators.Length(min=1,max=15)])
    About = TextAreaField('About',[validators.DataRequired(),validators.Length(min=1,max=250)])
    Genre = SelectField('Genre',choices=[('Pop','Pop'),('Rock','Rock')])
    Location = SelectField('Location',choices=[('Bangalore','Bangalore'),('Mysore','Mysore')])
    Experience = IntegerField('Experience',[validators.NumberRange(min=0)])
    Language = SelectField('Language',choices=[('English','English'),('Kannada','Kannada')])


#Profile form for business edit
class Profile_B(Form):
    First_name = StringField('First Name',[validators.DataRequired(),validators.Length(min=1,max=15)])
    Last_name = StringField('Last Name',[validators.DataRequired(),validators.Length(min=1,max=15)])
    About = TextAreaField('About',[validators.DataRequired(),validators.Length(min=1,max=250)])
    Location = SelectField('Location',choices=[('Bangalore','Bangalore'),('Mysore','Mysore')])
    Language = SelectField('Language',choices=[('English','English'),('Kannada','Kannada')])

#Profile update
@app.route('/profile/edit',methods=['GET','POST'])
@is_logged_in
def profile_a():
    form = Profile_A(request.form)
    form1 = Profile_B(request.form)
    #artist
    if request.method == 'POST' and form.validate() and session['Type_Acc'] == "Artist":
        Username = session['Username']
        First_name = form.First_name.data
        Last_name = form.Last_name.data
        About = form.About.data
        Genre = form.Genre.data
        Location = form.Location.data
        Experience = form.Experience.data
        Language = form.Language.data
        Profile_pic = request.files['file']
        filename = secure_filename(Profile_pic.filename)

        app.logger.info(Profile_pic)
        app.logger.info(filename)

        #connection open
        cur = mysql.connection.cursor()
        #app.logger.info(session['Type_Acc'])
        #artist database

        #upload
        if filename != None:
            Profile_pic.save('static/upload/img/'+Username+'.avatar.jpg')
            filename = Username+'.avatar.jpg'


        result = cur.execute("SELECT * FROM profile_a WHERE Username = %s ",[Username])

        if result > 0:
                #for second time users
            cur.execute("UPDATE profile_a SET Username =  %s,First_name =  %s,Last_name =  %s,About =  %s,Genre =  %s,Location =  %s,Experience =  %s,Language =  %s, Profile_pic=%s WHERE Username = %s",(Username,First_name,Last_name,About,Genre,Location,Experience,Language,filename,Username))
        else:
                #for first time
            cur.execute("INSERT INTO profile_a(Username,First_name,Last_name,About,Genre,Location,Experience,Language,Profile_pic) VALUES(%s, %s, %s, %s, %s, %s, %s, %s,%s)", (Username,First_name,Last_name,About,Genre,Location,Experience,Language,filename))

        mysql.connection.commit()

        #close connection
        cur.close()

        flash('Profile Updated..','success')
        return redirect(url_for('profile',id=Username))

    #business
    #else:
    elif request.method == 'POST' and session['Type_Acc'] == "Business":
        Username = session['Username']
        First_name = form1.First_name.data
        Last_name = form1.Last_name.data
        About = form1.About.data
        Location = form1.Location.data
        Language = form1.Language.data
        Profile_pic = request.files['file']
        filename = secure_filename(Profile_pic.filename)

            #cursor
        cur = mysql.connection.cursor()
        #app.logger.info(session['Type_Acc'])
            #database

        #File save
        if filename != None:
            Profile_pic.save('static/upload/img/'+Username+'.avatar.jpg')
            filename = Username+'.avatar.jpg'


        result = cur.execute("SELECT * FROM profile_b WHERE Username = %s ",[Username])

        if result > 0:
                #for second time users
            cur.execute("UPDATE profile_b SET Username =  %s,First_name =  %s,Last_name =  %s,About =  %s,Location =  %s,Language =  %s,Profile_pic=%s WHERE Username = %s",(Username,First_name,Last_name,About,Location,Language,filename,Username))
        else:
                #for first time
            cur.execute("INSERT INTO profile_b(Username,First_name,Last_name,About,Location,Language,Profile_pic) VALUES(%s, %s, %s, %s, %s, %s, %s)", (Username,First_name,Last_name,About,Location,Language,filename))

        mysql.connection.commit()
        cur.close()

        flash('Profile Updated..','success')
        return redirect(url_for('profile',id=Username))
    return render_template('profile_edit.html', form=form, form1=form1)

if __name__ == '__main__':
    app.secret_key = 'secret_key9845307903'
    app.run()

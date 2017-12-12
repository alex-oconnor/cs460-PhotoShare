######################################
# author ben lawson <balawson@bu.edu> 
######################################
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask.ext.login as flask_login
import time
from itertools import combinations
#for image uploading
from werkzeug import secure_filename
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'suppup'
app.config['MYSQL_DATABASE_DB'] = 'photoshare8'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users") 
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users") 
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd 
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out') 

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html') 

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')  

@app.route("/register", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		password=request.form.get('password')
		first_name=request.form.get('first_name')
		last_name=request.form.get('last_name')
		dob=request.form.get('dob')
		gender=request.form.get('gender')
		hometown=request.form.get('hometown')
	except:
		print "couldn't find all tokens" #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print cursor.execute("INSERT INTO Users (email, password, first_name, last_name, dob, gender, hometown) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(email, password, first_name, last_name, dob, gender, hometown))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print "couldn't find all tokens"
		return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, U.first_name, U.last_name, P.user_id FROM Pictures P, Users U WHERE P.user_id = U.user_id AND P.user_id = '{0}' ORDER BY P.picture_id DESC".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	anon = cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	if anon == 0:
		return -1
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)): 
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code



@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('profile.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		tags = request.form.get('tag')
		album_name = request.form.get('album')
		photo_data = base64.standard_b64encode(imgfile.read())
		cursor = conn.cursor()

		cursor.execute("SELECT name FROM Albums WHERE user_id = '{0}'".format(uid))
		all_albums = cursor.fetchall()
		t = 0
		for i in range(len(all_albums)):
			temp = str(all_albums[i][0])
			if album_name == temp:
				t += 1
		if t == 0:
			return render_template('upload.html', message='This is not a valid Album; try again! Remember to create an album before uploading a picture!')

		cursor.execute("INSERT INTO Pictures (imgdata, user_id, caption) VALUES ('{0}', '{1}', '{2}' )".format(photo_data,uid,caption))
		conn.commit()

		photo_id = cursor.lastrowid

		cursor.execute("SELECT album_id FROM Albums WHERE user_id = '{0}' AND name = '{1}'".format(uid,album_name))
		album_id = cursor.fetchone()[0]
		cursor.execute("INSERT INTO Stored_In(picture_id, album_id) VALUES ('{0}', '{1}')".format(photo_id, album_id))
		conn.commit()

		tag_split = tags.split()
		cursor1 = conn.cursor()


		for i in range(len(tag_split)):
			cursor1.execute("INSERT INTO Tags(tag) VALUES ('{0}')".format(tag_split[i]))
			conn.commit()
			tag_id = cursor1.lastrowid
			cursor1.execute("INSERT INTO Tagged_Picture(picture_id, tag_id) VALUES ('{0}', '{1}')".format(photo_id, tag_id))
			conn.commit()

		return render_template('photo_stream.html', name=flask_login.current_user.id, message='Photo uploaded!',user=uid, photos=getUsersPhotos(uid) )
		
	#The method is GET so we return a  HTML form to upload the a photo.
	return render_template('upload.html')
#end photo uploading code 

@app.route('/tag_search', methods=['GET', 'POST'])
def tag_search():
	if request.method == 'POST':

		tags = request.form.get('tags')
		all_tags = tags.split()

		return render_template('tag_search.html', photos=getTaggedPhotos(all_tags))

	return render_template('tag_search.html')



def getTaggedPhotos(tags):
	output = []
	cursor = conn.cursor()
	for i in range(len(tags)):
		cursor.execute("SELECT P.imgdata, T.tag, P.caption, U.first_name, U.last_name FROM Users U, Pictures P, Tagged_Picture TP, Tags T WHERE U.user_id = P.user_id AND P.picture_id = TP.picture_id AND TP.tag_id = T.tag_id AND T.tag = '{0}'".format(tags[i]))
	 	output+= cursor.fetchall()
	return output


@app.route('/pictures', methods=['GET','POST'])
def comment():
	
	if  getUserIdFromEmail(flask_login.current_user) == -1:
		uid = -1
		name = 'Anonymous'
		#cursor = conn.cursor()
		#cursor.execute("INSERT INTO Users(user_id, first_name) VALUES ('{0}', '{1}')".format(uid, name))
	else:
		uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'POST':
		
		photo_user_id = request.form.get('user_id')
		photo_user_id = int(photo_user_id)
		if uid - photo_user_id == 0:
			return render_template('hello.html', message='You cant comment on your own photo!', user=uid, photos=getAllPhotos())
		else:
			photo_id = request.form.get('picture_id')
			comment = request.form.get('comment')
			date = time.strftime('%Y-%m-%d')
			cursor = conn.cursor()
			cursor.execute("INSERT INTO Comments(user_id, date_written, words) VALUES ('{0}', '{1}', '{2}')".format(uid, date, comment))
			conn.commit()
			comment_id = cursor.lastrowid

			cursor.execute("INSERT INTO Commented_on(comment_id, picture_id) VALUES ('{0}', '{1}')".format(comment_id,photo_id))
			conn.commit()

			return render_template('hello.html', message='Comment added!', user=uid, photos=getAllPhotos())

	return render_template('hello.html', message='Here are the most recent photos',user=uid, photos=getAllPhotos())

def getComments(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT C.words, U.first_name, U.last_name, C.date_written FROM Users U, Comments C, Commented_On CO WHERE U.user_id = C.user_id AND C.comment_id = CO.comment_id AND CO.picture_id = '{0}' ORDER BY C.comment_id".format(picture_id))
	return cursor.fetchall()

def getLikes(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(user_id) FROM Liked_Pictures WHERE picture_id = '{0}'".format(picture_id))
	return cursor.fetchall()
def getTags(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT T.tag FROM Tags T, Tagged_Picture TP WHERE T.tag_id = TP.tag_id AND TP.picture_id = '{0}'".format(picture_id))
	return cursor.fetchall()


def mostRecentUserPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, U.first_name, U.last_name, P.user_id FROM Pictures P, Users U WHERE P.user_id = U.user_id AND P.user_id = '{0}' ORDER BY P.picture_id DESC".format(uid))
	return cursor.fetchall()

@app.route('/photo_stream', methods=['GET', 'POST'])
def displayUserPhotos():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'POST':
		photo_id = request.form.get('picture_id')
		deletePicture(photo_id)
		
		return render_template('photo_stream.html', name=flask_login.current_user.id, user= uid,message='Here are all your photos!', photos=mostRecentUserPhotos(uid))

	return render_template('photo_stream.html', name=flask_login.current_user.id, user= uid,message='Here are all your photos!', photos=mostRecentUserPhotos(uid) )

def deletePicture(photo_id):
	cursor = conn.cursor()
		
	cursor.execute("DELETE FROM Liked_pictures WHERE picture_id = '{0}'".format(photo_id))
	conn.commit()

	cursor.execute("SELECT comment_id FROM Commented_on WHERE picture_id = '{0}'".format(photo_id))
	comments = cursor.fetchall()

	cursor.execute("DELETE FROM Commented_on WHERE picture_id = '{0}'".format(photo_id))
	conn.commit()
		
	for j in range(len(comments)):
		cursor.execute("DELETE FROM Comments WHERE comment_id = '{0}'".format(comments[j][0]))
		conn.commit()

	cursor.execute("SELECT tag_id FROM Tagged_Picture WHERE picture_id = '{0}'".format(photo_id))
	tags = cursor.fetchall()

	cursor.execute("DELETE FROM Tagged_Picture WHERE picture_id = '{0}'".format(photo_id))
	conn.commit()
		
	for i in range(len(tags)):
		cursor.execute("DELETE FROM Tags WHERE tag_id = '{0}'".format(tags[i][0]))
		conn.commit()

	cursor.execute("DELETE FROM Stored_In WHERE picture_id = '{0}'".format(photo_id))
	conn.commit()

	cursor.execute("DELETE FROM Pictures WHERE picture_id = '{0}'".format(photo_id))
	conn.commit()


def getAllPhotos():
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, U.first_name, U.last_name, P.user_id, U.user_id FROM Pictures P, Users U WHERE P.user_id = U.user_id ORDER BY P.picture_id DESC")
	pictures = cursor.fetchall()

	final = []
	for i in range(len(pictures)):
		temp_pics = []

		temp_id = int(pictures[i][1])
		for j in range(len(pictures[i])):
			a = [pictures[i][j]]
			temp_pics += a

		comments = getComments(temp_id)
		temp_comments = []
		for k in range(len(comments)):
			b = [comments[k]]
			temp_comments.append(comments[k])

		temp_pics.append(temp_comments)

		likes = getLikes(temp_id)
		temp_likes = []
		for m in range(len(likes)):
			c = [likes[m]]
			temp_likes += c

		temp_pics += temp_likes

		tags = getTags(temp_id)
		temp_tags = []
		for n in range(len(tags)):
			d = [tags[n]]
			temp_tags += d

		temp_pics.append(temp_tags)

		final.append(temp_pics)


	return final

@app.route('/pictures', methods=['GET', 'POST'])
def allPictures():
	return render_template('hello.html', message='Here are the most recent photos', photos=getAllPhotos())


@app.route('/view_likes', methods=['GET', 'POST'])
def viewLikes():
	if request.method == 'POST':

		photo_id = request.form.get('picture_id')
		num_likes = getLikes(photo_id)
		if num_likes > 0:

			cursor = conn.cursor()
			cursor.execute("SELECT U.first_name, U.last_name FROM Users U, Liked_Pictures L WHERE L.user_id = U.user_id AND L.picture_id = '{0}'".format(photo_id))
			people = cursor.fetchall()

			return render_template('people_who_liked.html', message='Here are the people who liked this photo', names=people)
	return render_template('hello.html', message='Here are the most recent photos', user=uid, photos=getAllPhotos()) 

@app.route('/friend_search', methods=['GET', 'POST'])
@flask_login.login_required
def searchFriends():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		email = request.form.get('email')
		cursor = conn.cursor()
		
		cursor.execute("SELECT user_id FROM Users WHERE email = '{0}'".format(email))
		friend_id = cursor.fetchone()[0]

		cursor.execute("SELECT friend_uid FROM Friends_with WHERE user_id = '{0}'".format(uid))
		friend_list = cursor.fetchall()
		filler = []
		for j in range(len(friend_list)):
			filler += friend_list[j]

		for i in range(len(friend_list)):
			if friend_id == friend_list[i]:
				return render_template('friend_search.html', message= 'You are already friends with this person!')

		return render_template('friend_search_results.html', message= 'Here are the results', friends=friendLookup(email))

	return render_template('friend_search.html')

def friendLookup(email):
	cursor = conn.cursor()
	cursor.execute("SELECT first_name, last_name, user_id FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchall()

@app.route('/friend_search_results', methods= ['GET', 'POST'])
@flask_login.login_required
def addFriend():
	if request.method == 'POST':

		uid = getUserIdFromEmail(flask_login.current_user.id)
		friend_id = request.form.get('friend_id')

		cursor = conn.cursor()

		cursor.execute("INSERT INTO Friends_with(user_id, friend_uid) VALUES ('{0}', '{1}')".format(uid, friend_id))
		conn.commit()
		return render_template('friend_search.html', message='Congrats! You have added a new friend!')
	return render_template('friend_search_results.html')

@app.route('/friend_list', methods= ['GET'])
@flask_login.login_required
def listFriends():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('friend_list.html', message='These are all your friends', friends=getAllFriends(uid))

def getAllFriends(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT first_name, last_name FROM Users WHERE user_id IN (SELECT friend_uid FROM Friends_with WHERE user_id = '{0}')".format(uid))
	return cursor.fetchall()

@app.route('/like', methods=['GET', 'POST'])
@flask_login.login_required
def likePicture():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'POST':

		photo_id = request.form.get('picture_id')
		photo_id = int(photo_id)
		cursor = conn.cursor()
		cursor.execute("SELECT picture_id FROM Liked_Pictures WHERE user_id = '{0}'".format(uid))
		liked_pics = cursor.fetchall()
		for i in range(len(liked_pics)):
			temp = int(liked_pics[i][0])
			if photo_id == temp:
				return render_template('hello.html',message='You already liked this picture!', user=uid, photos=getAllPhotos())
		cursor.execute("INSERT INTO Liked_Pictures(user_id, picture_id) VALUES ('{0}', '{1}')".format(uid, photo_id))
		conn.commit()

		return render_template('hello.html', message='You Liked a Picture', user=uid, photos=getAllPhotos())
	return render_template('hello.html', message='Here are the most recent photos',user=uid, photos=getAllPhotos())

@app.route('/create_album', methods=['GET', 'POST'])
@flask_login.login_required
def createAlbum():
	if request.method == 'POST':

		uid = getUserIdFromEmail(flask_login.current_user.id)
		name = request.form.get('name')
		date = time.strftime('%Y-%m-%d')
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Albums(name, user_id, date_started) VALUES ('{0}', '{1}','{2}')".format(name, uid, date))
		conn.commit()
		return render_template('hello.html', message='Your album has been created!')
	return render_template('create_album.html')

@app.route('/albums', methods=['GET', 'POST'])
@flask_login.login_required
def listAlbums():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'POST':
		return render_template('albums.html', albums=getAlbums(uid))
	return render_template('albums.html', albums=getAlbums(uid))

def getAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT A.name, COUNT(S.picture_id), A.album_id FROM Albums A, Stored_In S WHERE A.album_id = S.album_id AND A.user_id = '{0}' GROUP BY A.name, A.album_id".format(uid))
	output = cursor.fetchall()
	return output

@app.route('/see_photos', methods=['GET', 'POST'])
@flask_login.login_required
def albumPhotos():
	if request.method == 'POST':

		uid = getUserIdFromEmail(flask_login.current_user.id)
		name = request.form.get('name')
		cursor = conn.cursor()
		cursor.execute("SELECT P.imgdata, P.picture_id, P.caption FROM Pictures P, Albums A, Stored_In S WHERE A.album_id = S.album_id AND S.picture_id = P.picture_id AND A.name = '{0}' AND A.user_id = '{1}'".format(name, uid))
		pictures = cursor.fetchall()
		return render_template('photo_stream.html', name=flask_login.current_user.id, user= uid, photos=pictures)

	return render_template('albums.html')

@app.route('/delete_album', methods= ['GET', 'POST'])
@flask_login.login_required
def deleteAlbum():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'POST':

		album_id = request.form.get('album_id')
		cursor = conn.cursor()
		cursor.execute("SELECT picture_id FROM Stored_In WHERE album_id = '{0}'".format(album_id))
		all_pics = cursor.fetchall()

		for i in range(len(all_pics)):
			temp = int(all_pics[i][0])
			deletePicture(temp)

		cursor.execute("DELETE FROM Albums WHERE album_id = '{0}'".format(album_id))
		conn.commit()

		return render_template('albums.html', message='Your album and photos have been deleted.', albums=getAlbums(uid))
	
	return render_template('albums.html', albums=getAlbums(uid))


@app.route('/popular_tags', methods = ['GET', 'POST'])
def popularTags():
	if request.method == 'POST':

		tag = request.form.get('tag')
		cursor = conn.cursor()
		cursor.execute("SELECT P.imgdata, T.tag, P.caption, U.first_name, U.last_name FROM Users U, Pictures P, Tagged_Picture TP, Tags T WHERE U.user_id = P.user_id AND P.picture_id = TP.picture_id AND TP.tag_id = T.tag_id AND T.tag = '{0}'".format(tag))
		output = cursor.fetchall()

		return render_template('tag_search.html', message='Here are the photos for this tag! Search for other tags here!', photos=output)

	return render_template('popular_tags.html', tags=getTopTenTags())

def getTopTenTags():
	cursor = conn.cursor()
	cursor.execute("SELECT tag, COUNT(tag) FROM Tags GROUP BY tag ORDER BY COUNT(tag) DESC LIMIT 10")
	return cursor.fetchall()


def getTopTenUsers():
	cursor = conn.cursor()
	pictures = " SELECT user_id, COUNT(picture_id) AS num_pics FROM Pictures P GROUP BY user_id"
	comments = "SELECT user_id, COUNT(comment_id) AS num_comments FROM Comments C GROUP BY user_id"
	total_sum = pictures + " UNION " + comments + " ORDER BY num_pics DESC"

	final = "SELECT t1.user_id, SUM(t1.num_pics) AS total_sum FROM (" + total_sum + ") AS t1 GROUP BY t1.user_id ORDER BY total_sum DESC LIMIT 10"
	cursor.execute(final)
	output = cursor.fetchall()
	
	blank = []
	for i in range(len(output)):
		temp = int(output[i][0])
		cursor.execute("SELECT first_name, last_name FROM Users WHERE user_id = '{0}'".format(temp))
		blank += cursor.fetchall()
	return blank


@app.route('/tag_recommendation', methods=['GET', 'POST'])
@flask_login.login_required
def recommendedTags():
	if request.method == 'POST':

		tags = request.form.get('tags')
		all_tags = tags.split()

		cursor = conn.cursor()
		popular_tags = []
		filler_list = []
		for i in range(len(all_tags)):
			temp_tag = str(all_tags[i])
			filler_list += [temp_tag]
		statement = "SELECT T.tag, COUNT(T.tag) FROM Tags T, Tagged_Picture TP  WHERE T.tag_id = TP.tag_id AND TP.picture_id IN( SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE T.tag_id = TP.tag_id AND T.tag = %s ) GROUP BY T.tag ORDER BY COUNT(T.tag) DESC LIMIT 5"
		cursor.executemany(statement, filler_list)
		popular_tags += cursor.fetchall()

		final_tags = []
		for j in range(len(popular_tags)):
			temp_tag2 = str(popular_tags[j][0])
			if temp_tag2 not in filler_list:
				final_tags += [temp_tag2]


		return render_template('tag_recommendation.html', message='Here are your recommended tags', tags=final_tags)
	return render_template('profile.html')

@app.route('/recommended_pics', methods=['GET'])
@flask_login.login_required
def recommendedPics():

	check_list = []

	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT T.tag, COUNT(T.tag) FROM Tags T, Tagged_Picture TP, Pictures P WHERE T.tag_id = TP.tag_id AND TP.picture_id = P.picture_id AND P.user_id = '{0}' GROUP BY T.tag ORDER BY COUNT(T.tag) DESC LIMIT 5".format(uid))
	tags = cursor.fetchall()

	tag_list = []
	for i in range(len(tags)):
		tag_list += [tags[i][0]]

	string_list = []
	one = tag_list[0]
	string_list += [one]
	two = tag_list[1]
	string_list += [two]
	three = tag_list[2]
	string_list += [three]
	four = tag_list[3]
	string_list += [four]
	five = tag_list[4]
	string_list += [five]

	output = sum([map(list, combinations(string_list, i)) for i in range(len(string_list) + 1)], [])

	photo_list = []

	cursor.execute(" SELECT t1.picture_id FROM ((SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{0}') AS t1, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{1}') AS t2, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{2}') AS t3, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{3}') AS t4, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{4}') AS t5) WHERE t1.picture_id = t2.picture_id AND t2.picture_id = t3.picture_id AND t3.picture_id = t4.picture_id AND t4.picture_id = t5.picture_id".format(one,two,three,four,five))
	longest = cursor.fetchall()
	size = len(longest)
	if size > 0:	
		check_list += [longest[0][0]]
	
	for i in range(len(longest)):
		picture_id = longest[i][0]
		if checkUser(picture_id, uid):
			cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, U.first_name, U.last_name, U.user_id FROM Pictures P, Users U WHERE P.user_id = U.user_id AND P.picture_id = '{0}'".format(picture_id))
			holder = cursor.fetchall()
			photo_list += holder

	helper1 = []
	for j in range(26, 31):
		cursor.execute(" SELECT t1.picture_id FROM ((SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{0}') AS t1, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{1}') AS t2, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{2}') AS t3, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{3}') AS t4) WHERE t1.picture_id = t2.picture_id AND t2.picture_id = t3.picture_id AND t3.picture_id = t4.picture_id".format(output[j][0],output[j][1],output[j][2],output[j][3]))
		longest1 = cursor.fetchall()

		helper1 += longest1

	for k in range(len(helper1)):
		picture_id = helper1[k][0]
		if recommendedPicsHelper(picture_id, check_list):
			if checkUser(picture_id, uid):
				check_list += [picture_id]
				cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, U.first_name, U.last_name, U.user_id FROM Pictures P, Users U WHERE P.user_id = U.user_id AND P.picture_id = '{0}'".format(picture_id))
				holder = cursor.fetchall()
				photo_list += holder

	helper2 = []
	for l in range(16, 26):
		cursor.execute(" SELECT t1.picture_id FROM ((SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{0}') AS t1, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{1}') AS t2, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{2}') AS t3) WHERE t1.picture_id = t2.picture_id AND t2.picture_id = t3.picture_id".format(output[l][0],output[l][1],output[l][2]))
		longest2 = cursor.fetchall()
		helper2 += longest2

	for m in range(len(helper2)):
		picture_id = helper2[m][0]
		if recommendedPicsHelper(picture_id, check_list):
			if checkUser(picture_id, uid):
				check_list += [picture_id]
				cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, U.first_name, U.last_name, U.user_id FROM Pictures P, Users U WHERE P.user_id = U.user_id AND P.picture_id = '{0}'".format(picture_id))
				holder = cursor.fetchall()
				photo_list += holder

	helper3 = []
	for n in range(6, 16):
		cursor.execute(" SELECT t1.picture_id FROM ((SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{0}') AS t1, (SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{1}') AS t2) WHERE t1.picture_id = t2.picture_id".format(output[n][0],output[n][1]))
		longest3 = cursor.fetchall()
		helper3 += longest3

	for q in range(len(helper3)):
		picture_id = helper3[q][0]
		if recommendedPicsHelper(picture_id, check_list):
			if checkUser(picture_id, uid):
				check_list += [picture_id]
				cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, U.first_name, U.last_name, U.user_id FROM Pictures P, Users U WHERE P.user_id = U.user_id AND P.picture_id = '{0}'".format(picture_id))
				holder = cursor.fetchall()
				photo_list += holder

	helper4 = []
	for s in range(1,6):
		cursor.execute(" SELECT t1.picture_id FROM ((SELECT TP.picture_id FROM Tagged_Picture TP, Tags T WHERE TP.tag_id = T.tag_id AND T.tag = '{0}') AS t1)".format(output[s][0]))
		longest4 = cursor.fetchall()
		helper4 += longest4

	for t in range(len(helper4)):
		picture_id = helper4[t][0]
		if recommendedPicsHelper(picture_id, check_list):
			check_list += [picture_id]
			cursor.execute("SELECT P.imgdata, P.picture_id, P.caption, U.first_name, U.last_name, U.user_id FROM Pictures P, Users U WHERE P.user_id = U.user_id AND P.picture_id = '{0}'".format(picture_id))
			holder = cursor.fetchall()
			photo_list += holder

	return render_template('recommended_pics.html', message='Here are some pictures you might like', photos=photo_list)

def recommendedPicsHelper(picture_id, checklist):
	if picture_id not in checklist:
		return True
	else:
		return False

def checkUser(picture_id, user_id):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Pictures WHERE picture_id = '{0}'".format(picture_id))
	temp_id = cursor.fetchone()[0]
	if user_id != temp_id:
		return True
	else:
		return False

#default page  
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', users= getTopTenUsers(), message='Welecome to Photoshare')



if __name__ == "__main__":
	#this is invoked when in the shell  you run 
	#$ python app.py 
	app.run(port=5000, debug=True)

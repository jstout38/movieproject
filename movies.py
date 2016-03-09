#This module includes the overall archtiecture of the Movie Log web app. Flask allows for routing
#based on user ids and SQLalchemy allows for quick SQL searches

import random
import string
import time
import httplib2
import json
import requests

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
app = Flask(__name__)
from flask import session as login_session
from flask import make_response
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Movie
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError


CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "The Movie List"
state = ''
engine = create_engine('postgres://afmaywensnnldv:p5LzOYcun5fEgr5aougoyg917H@ec2-54-83-3-38.compute-1.amazonaws.com:5432/d60gq6hm9tap55')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


#Inject a function that determines the current state for access in Jinja templates
@app.context_processor
def inject_state():
	def current_state(): 
		return login_session['state']
	return dict(STATE=current_state)


#Inject a function that determines the current user for access in Jinja templates
@app.context_processor
def inject_login():
	def current_login():
		try:
			return login_session['username']
		except:
			return None
	return dict(login=current_login)


#Inject a function that returns the current user's picture
@app.context_processor
def inject_picture():
	def current_picture():
		try:
			return login_session['picture']
		except:
			return None
	return dict(picture=current_picture)


#Root directory for the web abb, visiting it determines the current state and displays four random users and their most recently watched movies.
#The original index page was a list of users, hence the name. The name may be changed to a more descriptive one in future versions.
@app.route('/')
@app.route('/users/')
def users():
	#Create a random state
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
	login_session['state'] = state
	#Returns a list of users excluding an administrator account. Better checks for administrators will be implemented in future versions.
	users = session.query(User).filter(User.email != "jstout38@gmail.com").all()
	#Returns four users at random
	filteredUsers = session.query(User).filter(User.email != "jstout38@gmail.com").order_by(func.random()).limit(4)
	#Creates a dictionary where every users email is matched with an array containing the Movie Database 
	#ids of their most recent four movies. This will be used in the jinja template to display these movies.
	movies = {}
	for user in users:
		userMovies = session.query(Movie).filter_by(user_id = user.id).order_by(Movie.datewatched.desc()).limit(4)
		movies[user.email] = []
		for movie in userMovies:
			movies[user.email].append(movie.mdbid)
	#Passes the four chosen users and the dictionary of Movie Database ids to the jinja template
	return render_template('users.html', users = filteredUsers, movies = movies)


#Calls a POST request using the Google authentication API that results in the user being logged in
@app.route('/gconnect', methods=['POST'])
def gconnect():
	#Various checks to make sure the user is logging in properly
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	code = request.data
	try:
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	#Make the call to log the user in through Google and do more validation
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])
	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type'] = 'application/json'
	gplus_id = credentials.id_token['sub']	
	if result['user_id'] != gplus_id:
		response = make_response(
			json.dumps("Token's user ID doesn't match given user ID."), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	if result['issued_to'] != CLIENT_ID:
		response = make_response(
			json.dumps("Token's client ID does not match app's."), 401)
		print "Token's client ID does not match app's."
		response.headers['Content-Type'] = 'application/json'
		return response
	stored_credentials = login_session.get('credentials')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_credentials is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response

	#If we've made it this far, user is ready to log in
	login_session['credentials'] = credentials
	login_session['gplus_id'] = gplus_id

	#Store the information retrieved via the Google authentication API in the current login session
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': credentials.access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params = params)
	data = answer.json()
	print login_session
	login_session['username'] = data["name"]
	login_session['picture'] = data["picture"]
	login_session['email'] = data["email"]
	login_session['provider'] = 'google'

	#Checks to see if the user that just logged in is in the database, if not 
	#creates a new user using the information in login_session and returns a 
	#redirect message and the user id so that the user will be redirected to their new page
	user_id = getUserID(data["email"])
	if not user_id:
		output = ''
		user_id = CreateUser(login_session)
		output += 'Welcome! Redirecting to your page...'
		flash("you have been registered")
		login_session['user_id'] = user_id
		return jsonify({'message': output, 'user': str(user_id)})
	#If the user already exists, change the current login to their database user id
	login_session['user_id'] = user_id
	output = 'Welcome Back! Redirecting...'
	return jsonify({'message': output, 'user': str(login_session['user_id'])})


#Calls a POST request using the Google authentication API that results in the user being logged in
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
	#Does validation checks on login info and then retrieves the user's info via Facebook
	if request.args.get('state') != login_session['state']:
		reponse = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	access_token = request.data
	app_id = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_id']
	app_secret = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_secret']
	url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id,app_secret,access_token)
	h = httplib2.Http()
	result = h.request(url, 'GET')[1]

	userinfo_url = "https://graph.facebook.com/v2.5/me"
	token = result.split("&")[0]

	url = 'https://graph.facebook.com/v2.5/me?%s&fields=name,id,email' % token
	h = httplib2.Http()
	result = h.request(url, 'GET')[1]
	data = json.loads(result)

	#Store the information retrieved via the Facebook authentication API in the current login session
	login_session['username'] = data["name"]
	login_session['email'] = data["email"]
	login_session['facebook_id'] = data["id"]
	login_session['provider'] = 'facebook'

	stored_token = token.split("=")[1]
	login_session['access_token'] = stored_token

	url = 'https://graph.facebook.com/v2.5/me/picture?%s&redirect=0&height=200&width=200' % token
	h = httplib2.Http()
	result = h.request(url, 'GET')[1]
	data = json.loads(result)

	login_session['picture'] = data["data"]["url"]

	#Checks to see if the user that just logged in is in the database, if not 
	#creates a new user using the information in login_session and returns a 
	#redirect message and the user id so that the user will be redirected to their new page
	user_id = getUserID(login_session['email'])
	if not user_id:
		output = ''
		user_id = CreateUser(login_session)
		output += 'Welcome! Redirecting to your page...'
		flash("you have been registered")
		login_session['user_id'] = user_id
		return jsonify({'message': output, 'user': str(user_id)})
	#If the user already exists, change the current login to their database user id
	login_session['user_id'] = user_id
	output = 'Welcome Back! Redirecting...'
	return jsonify({'message': output, 'user': str(login_session['user_id'])})


#Disconnects the session using Google API
@app.route("/gdisconnect")
def gdisconnect():
	credentials = login_session.get('credentials')
	access_token = credentials.access_token
	print 'In gdisconnect access token is %s', access_token
	print 'User name is: '
	print login_session.get('username')
	#Checks to make sure user is actually connected
	if credentials is None:
		print 'Access Token is None'
		response = make_response(json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	#
	#Makes the call to revoke the current session
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]
	if result['status'] != '200':
		response = make_response(json.dumps('Failed to revoke token for given user.'), 400)
		response.headers['Content-Type'] = 'application/json'
		return response
	

#Disconnects the session using Facebook API
@app.route("/fbdisconnect")
def fbdisconnect():
	facebook_id = login_session['facebook_id']
	access_token = login_session['access_token']
	url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
	h = httplib2.Http()
	result = h.request(url, 'DELETE')[1]
	return "you have been logged out"


#Checks which way the user logged in, then makes the appropriate API call and deletes the session information
@app.route('/disconnect')
def disconnect():
	if 'provider' in login_session:
		if login_session['provider'] == 'google':
			gdisconnect()
			del login_session['gplus_id']
			del login_session['credentials']			
		if login_session['provider'] == 'facebook':
			fbdisconnect()
			del login_session['facebook_id']
		del login_session['username']
		del login_session['email']
		del login_session['picture']
		del login_session['user_id']
		del login_session['provider']
		flash("You have successfully been logged out.")
		return redirect(url_for('users'))
	else:
		flash("You were not logged in to begin with!")
		return redirect(url_for('users'))


#Method only accessible to administrator for adding users without logging in through Google or Facebook
@app.route('/users/new/', methods=['GET', 'POST'])
def newUser():
	if 'username' not in login_session or login_session['email'] != 'jstout38@gmail.com':
		return redirect('/users')
	if request.method == 'POST':
		newUser = User(name = request.form['name'], email = request.form['email'], picture = request.form['pic'])
		session.add(newUser)
		session.commit()
		flash("user created")
		return redirect(url_for('users'))
	else:
		return render_template('newUser.html')


#Deletes a user, only accessible to the appropriate user or administrator
@app.route('/user/<int:user_id>/delete/', methods=['GET', 'POST'])
def deleteUser(user_id):
	if 'username' not in login_session:
			return redirect('/')
	currentUser = session.query(User).filter_by(id=user_id).one()
	if login_session['email'] != currentUser.email and login_session['email'] !="jstout38@gmail.com":
		return redirect('/')
	if request.method == 'POST':
		session.delete(currentUser)
		session.commit()
		flash("user deleted!")
		return redirect(url_for('disconnect'))
	else:
		return render_template('deleteUser.html', user = currentUser)


#Shows the movie log for the appropriate user
@app.route('/user/<int:user_id>/movies/')
def showMovies(user_id):
	#Pulls the list of movies for the appropriate user, if it's longer than five items calls the multiple page method
	movielist = session.query(Movie).filter_by(user_id = user_id).order_by(Movie.datewatched.desc()).all()
	if len(movielist)>5:
		return redirect(url_for('showMoviesPages', user_id = user_id, page = 1))
	#Creates a boolean variable to determine whether jinja template gives options to add/delete/edit
	isCurrentUser = False
	currentUser = session.query(User).filter_by(id=user_id).one()
	if 'username' in login_session:
		if currentUser.email == login_session['email'] or login_session['email'] == "jstout38@gmail.com":
			isCurrentUser = True
	#Passes the current user, their movies, whether they're the logged in user and a variable denoting no multiple page format to the jinja template
	return render_template('showMovies.html', user = currentUser, movies = movielist, isCurrentUser = isCurrentUser, page = 0)


#Method for handling longer lists of movies on multiple pages
@app.route('/user/<int:user_id>/movies/p=<int:page>')
def showMoviesPages(user_id, page):
	#Creates a boolean variable to determine whether jinja template gives options to add/delete/edit
	isCurrentUser = False
	currentUser = session.query(User).filter_by(id=user_id).one()
	if 'username' in login_session:
		if currentUser.email == login_session['email'] or login_session['email'] == "jstout38@gmail.com":
			isCurrentUser = True
	#Pulls the movies for the user and determines which ones go on this page
	movielist = session.query(Movie).filter_by(user_id = user_id).order_by(Movie.datewatched.desc()).all()
	filteredmovies = movielist[(page-1)*5:page*5]
	#Passes the current user, the total number of pages (for page number links), the movies for this page, whether the user is the logged in user, and the current page for the jinja template
	return render_template('showMovies.html', user = currentUser, noPages = int((len(movielist) - 1)/5 + 1), movies = filteredmovies, isCurrentUser = isCurrentUser, page = page)


#Allows logged in users to add a movie to their page
@app.route('/user/<int:user_id>/add/', methods=['GET', 'POST'])
def addMovie(user_id):
	if 'username' not in login_session:
			return redirect('/')
	#Determines today's date to pass as a default to the jinja template
	todaysDate = time.strftime("%Y-%m-%d")
	currentUser = session.query(User).filter_by(id=user_id).one()
	if login_session['email'] != currentUser.email and login_session['email'] != "jstout38@gmail.com":
		return redirect('/')
	#Post method creates the new movie using an API call from the page's javascript
	if request.method == 'POST':
		#Requires a date
		if request.form['dateWatched'] == '':
			return redirect(url_for('addMovie', user_id = user_id))
		newMovie = Movie(name = request.form['title'], datewatched = request.form['dateWatched'], review = request.form['review'], mdbid = request.form['mdbid'], rating = request.form['rating'], user_id = user_id)
		session.add(newMovie)
		session.commit()
		flash("movie added")
		#Returns a redirect to the user's movie page
		return jsonify({'status':'OK', 'redirect_url':url_for('showMovies', user_id = user_id)})
	else:
		#Passes the current user and today's date to the jinja template
		return render_template('addMovie.html', user = currentUser, todaysDate = todaysDate)
	#return "Add a movie for user number %i" % user_id


#Allows logged in users to edit a movie's record
@app.route('/user/<int:user_id>/<int:movie_id>/edit/', methods=['GET', 'POST'])
def editMovie(user_id, movie_id):
	if 'username' not in login_session:
			return redirect('/')
	currentUser = session.query(User).filter_by(id=user_id).one()
	if login_session['email'] != currentUser.email and login_session['email'] !="jstout38@gmail.com":
		return redirect('/')
	currentMovie = session.query(Movie).filter_by(id=movie_id).one()
	#Post method creates a replacement movie record using an API call from the page's javascript
	if request.method == 'POST':
		if request.form['dateWatched']:
			currentMovie.datewatched = request.form['dateWatched']
		if request.form['rating']:
			currentMovie.rating = request.form['rating']
		if request.form['review']:
			currentMovie.review = request.form['review']
		session.add(currentMovie)
		session.commit()
		flash("movie edited")
		return jsonify({'status':'OK', 'redirect_url':url_for('showMovies', user_id = user_id)})
	else:
		#Passes the current user and the movie to be edited to the jinja template
		return render_template('editMovie.html', user = currentUser, movie = currentMovie)


#Allows logged in users to delete a movie record. Displays a confirmation request.
@app.route('/user/<int:user_id>/<int:movie_id>/delete/', methods=['GET', 'POST'])
def deleteMovie(user_id, movie_id):
	if 'username' not in login_session:
			return redirect('/')
	currentUser = session.query(User).filter_by(id=user_id).one()
	if login_session['email'] != currentUser.email and login_session['email'] != "jstout38@gmail.com":
		return redirect('/')
	currentMovie = session.query(Movie).filter_by(id=movie_id).one()
	#Post method uses a simple form to determine whether to delete
	if request.method == 'POST':
		session.delete(currentMovie)
		session.commit()
		flash("movie deleted")
		return redirect(url_for('showMovies', user_id = user_id))
	else:
		#Passes the current user and the movie to be delted to the jinja template
		return render_template('deleteMovie.html', user = currentUser, movie = currentMovie)


#Post method for returning jsonified data on which users have listed a certain Movie based on the Movie Database id
@app.route('/movielookup/<int:movie_id>/users/', methods=['POST'])
def movieLookup(movie_id):
	selectedMovies = session.query(Movie).filter_by(mdbid = movie_id).all()
	usersWithMovie = []
	for movie in selectedMovies:
		usersWithMovie.append(session.query(User).filter_by(id = movie.user_id).one())
	return jsonify(Users = [u.serialize for u in usersWithMovie])


#Returns jsonified data on users
@app.route('/users/JSON')
def usersJSON():
	userlist = session.query(User).all()
	return jsonify(Users=[u.serialize for u in userlist])


#Returns jsonified data on movies
@app.route('/user/<int:user_id>/movies/JSON')
def userMoviesJSON(user_id):
	movielist = session.query(Movie).filter_by(user_id = user_id).all()
	return jsonify(Movies=[m.serialize for m in movielist])


#Returns jsonified data on an individual movie
@app.route('/user/<int:user_id>/movies/<int:movie_id>/JSON')
def movieDetailsJSON(user_id, movie_id):
	movie = session.query(Movie).filter_by(id = movie_id).one()
	return jsonify(Details=[movie.serialize])


#Helper function for getting a user's database ID based on their email
def getUserID(email):
	try:
		user = session.query(User).filter_by(email = email).one()
		return user.id
	except:
		return None


#Helper function to return the current State
def getCurrentState():
	return STATE


#Helper function to return a full User record using their id
def getUserInfo(user_id):
	user = session.query(User).filter_by(id = user_id).one()
	return user


#Helper function to create a new user and return the new id
def CreateUser(login_session):
	newUser = User(name = login_session['username'], email = login_session['email'], picture = login_session['picture'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email = login_session['email']).one()
	return user.id


app.secret_key = 'super_secret_key'
app.debug = True

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
app = Flask(__name__)

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Movie

from flask import session as login_session
import random, string, time

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "The Movie List"

state = ''

engine = create_engine('postgres://afmaywensnnldv:p5LzOYcun5fEgr5aougoyg917H@ec2-54-83-3-38.compute-1.amazonaws.com:5432/d60gq6hm9tap55')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()




@app.context_processor
def inject_state():
	def current_state(): 
		return login_session['state']
	return dict(STATE=current_state)

@app.context_processor
def inject_login():
	def current_login():
		try:
			return login_session['username']
		except:
			return None
	return dict(login=current_login)

@app.context_processor
def inject_picture():
	def current_picture():
		try:
			return login_session['picture']
		except:
			return None
	return dict(picture=current_picture)

@app.route('/')
@app.route('/users/')
def users():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
	login_session['state'] = state
	numberofUsers = session.query(func.count(User.id)).scalar()
	randoms = random.sample(range(numberofUsers),3)
	users = session.query(User).filter(User.email != "jstout38@gmail.com").all()
	filteredUsers = session.query(User).filter(User.email != "jstout38@gmail.com").order_by(func.random()).limit(4)
	movies = {}
	for user in users:
		userMovies = session.query(Movie).filter_by(user_id = user.id).order_by(Movie.datewatched.desc()).limit(4)
		movies[user.email] = []
		for movie in userMovies:
			movies[user.email].append(movie.mdbid)
	return render_template('users.html', users = filteredUsers, movies = movies)


@app.route('/gconnect', methods=['POST'])
def gconnect():
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

	login_session['credentials'] = credentials
	login_session['gplus_id'] = gplus_id

	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': credentials.access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params = params)
	data = answer.json()
	print login_session
	login_session['username'] = data["name"]
	login_session['picture'] = data["picture"]
	login_session['email'] = data["email"]
	login_session['provider'] = 'google'

	user_id = getUserID(data["email"])
	if not user_id:
		output = ''
		user_id = CreateUser(login_session)
		output += 'Welcome! Redirecting to your page...'
		flash("you have been registered")
		login_session['user_id'] = user_id
		return jsonify({'message': output, 'user': str(user_id)})
	login_session['user_id'] = user_id
	

	#output +='<h1>Welcome, '
	#output += login_session['username']

	#output += '!</h1>'
	#output += '<img src="'
	#output += login_session['picture']
	#output +=' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	#flash("you are now logged in as %s" %login_session['username'])
	#return output
	#return login_session['user_id'].str()
	output = 'Welcome Back! Redirecting...'
	return jsonify({'message': output, 'user': str(login_session['user_id'])})

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
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

	user_id = getUserID(login_session['email'])
	if not user_id:
		output = ''
		user_id = CreateUser(login_session)
		output += 'Welcome! Redirecting to your page...'
		flash("you have been registered")
		login_session['user_id'] = user_id
		return jsonify({'message': output, 'user': str(user_id)})
	login_session['user_id'] = user_id

	#output = ''
	#output +='<h1>Welcome, '
	#output += login_session['username']

	#output +='!</h1>'
	#output +='!<img src="'
	#output += login_session['picture']
	#output +=' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	output = 'Welcome Back! Redirecting...'
	return jsonify({'message': output, 'user': str(login_session['user_id'])})

@app.route("/gdisconnect")
def gdisconnect():
	credentials = login_session.get('credentials')
	access_token = credentials.access_token
	print 'In gdisconnect access token is %s', access_token
	print 'User name is: '
	print login_session.get('username')
	if credentials is None:
		print 'Access Token is None'
		response = make_response(json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]
	print result
	print url
	if result['status'] != '200':
		response = make_response(json.dumps('Failed to revoke token for given user.'), 400)
		response.headers['Content-Type'] = 'application/json'
		return response
	
@app.route("/fbdisconnect")
def fbdisconnect():
	facebook_id = login_session['facebook_id']
	access_token = login_session['access_token']
	url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id, access_token)
	h = httplib2.Http()
	result = h.request(url, 'DELETE')[1]
	return "you have been logged out"

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

#@app.route('/users/new/', methods=['GET', 'POST'])
#def newUser():
#	if 'username' not in login_session:
#		return redirect('/users')
#	if request.method == 'POST':
#		newUser = User(name = request.form['name'], email = request.form['email'], picture = request.form['pic'])
#		session.add(newUser)
#		session.commit()
#		flash("user created")
#		return redirect(url_for('users'))
#	else:
#		return render_template('newUser.html')

#@app.route('/user/<int:user_id>/edit/', methods=['GET', 'POST'])
#def editUser(user_id):
#	if 'username' not in login_session:
#		return redirect('/login')
#	editedUser = session.query(User).filter_by(id=user_id).one()
#	if request.method == 'POST':
#		if request.form['name']:
#			editedUser.name = request.form['name']
#		if request.form['email']:
#			editedUser.email = request.form['email']
#		session.add(editedUser)
#		session.commit()
#		flash("user edited!")
#		return redirect(url_for('users'))
#	else:
#		return render_template('editUser.html', user = editedUser)

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
	#return "Delete user number %i" % user_id

@app.route('/user/<int:user_id>/movies/')
def showMovies(user_id):
	movielist = session.query(Movie).filter_by(user_id = user_id).order_by(Movie.datewatched.desc()).all()
	if len(movielist)>5:
		return redirect(url_for('showMoviesPages', user_id = user_id, page = 1))
	isCurrentUser = False
	currentUser = session.query(User).filter_by(id=user_id).one()
	if 'username' in login_session:
		if currentUser.email == login_session['email'] or login_session['email'] == "jstout38@gmail.com":
			isCurrentUser = True
	return render_template('showMovies.html', user = currentUser, movies = movielist, isCurrentUser = isCurrentUser, page = 0)
	#return render_template('showMoviesNE.html', user = currentUser, movies = movielist, isCurrentUser = isCurrentUser)

@app.route('/user/<int:user_id>/movies/p=<int:page>')
def showMoviesPages(user_id, page):
	isCurrentUser = False
	currentUser = session.query(User).filter_by(id=user_id).one()
	if 'username' in login_session:
		if currentUser.email == login_session['email'] or login_session['email'] == "jstout38@gmail.com":
			isCurrentUser = True
	movielist = session.query(Movie).filter_by(user_id = user_id).order_by(Movie.datewatched.desc()).all()
	filteredmovies = movielist[(page-1)*5:page*5]
	return render_template('showMovies.html', user = currentUser, noPages = int((len(movielist) - 1)/5 + 1), movies = filteredmovies, isCurrentUser = isCurrentUser, page = page)

@app.route('/user/<int:user_id>/add/', methods=['GET', 'POST'])
def addMovie(user_id):
	if 'username' not in login_session:
			return redirect('/')
	todaysDate = time.strftime("%Y-%m-%d")
	currentUser = session.query(User).filter_by(id=user_id).one()
	if login_session['email'] != currentUser.email and login_session['email'] != "jstout38@gmail.com":
		return redirect('/')
	if request.method == 'POST':
		if request.form['dateWatched'] == '':
			return redirect(url_for('addMovie', user_id = user_id))
		newMovie = Movie(name = request.form['title'], datewatched = request.form['dateWatched'], review = request.form['review'], mdbid = request.form['mdbid'], rating = request.form['rating'], user_id = user_id)
		session.add(newMovie)
		session.commit()
		flash("movie added")
		return jsonify({'status':'OK', 'redirect_url':url_for('showMovies', user_id = user_id)})
	else:
		return render_template('addMovie.html', user = currentUser, todaysDate = todaysDate)
	#return "Add a movie for user number %i" % user_id

@app.route('/user/<int:user_id>/<int:movie_id>/edit/', methods=['GET', 'POST'])
def editMovie(user_id, movie_id):
	if 'username' not in login_session:
			return redirect('/')
	currentUser = session.query(User).filter_by(id=user_id).one()
	if login_session['email'] != currentUser.email and login_session['email'] !="jstout38@gmail.com":
		return redirect('/')
	currentMovie = session.query(Movie).filter_by(id=movie_id).one()
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
		return render_template('editMovie.html', user = currentUser, movie = currentMovie)
	#return "Edit movie number %i for user number %i" % (movie_id, user_id)

@app.route('/user/<int:user_id>/<int:movie_id>/delete/', methods=['GET', 'POST'])
def deleteMovie(user_id, movie_id):
	if 'username' not in login_session:
			return redirect('/')
	currentUser = session.query(User).filter_by(id=user_id).one()
	if login_session['email'] != currentUser.email and login_session['email'] != "jstout38@gmail.com":
		return redirect('/')
	currentMovie = session.query(Movie).filter_by(id=movie_id).one()
	if request.method == 'POST':
		session.delete(currentMovie)
		session.commit()
		flash("movie deleted")
		return redirect(url_for('showMovies', user_id = user_id))
	else:
		return render_template('deleteMovie.html', user = currentUser, movie = currentMovie)
	#return "Delete movie number %i for user number %i" % (movie_id, user_id)

@app.route('/users/JSON')
def usersJSON():
	userlist = session.query(User).all()
	return jsonify(Users=[u.serialize for u in userlist])

@app.route('/user/<int:user_id>/movies/JSON')
def userMoviesJSON(user_id):
	movielist = session.query(Movie).filter_by(user_id = user_id).all()
	return jsonify(Movies=[m.serialize for m in movielist])

@app.route('/user/<int:user_id>/movies/<int:movie_id>/JSON')
def movieDetailsJSON(user_id, movie_id):
	movie = session.query(Movie).filter_by(id = movie_id).one()
	return jsonify(Details=[movie.serialize])

def getUserID(email):
	try:
		user = session.query(User).filter_by(email = email).one()
		return user.id
	except:
		return None

def getCurrentState():
	return STATE

def getUserInfo(user_id):
	user = session.query(User).filter_by(id = user_id).one()
	return user

def CreateUser(login_session):
	newUser = User(name = login_session['username'], email = login_session['email'], picture = login_session['picture'])
	session.add(newUser)
	session.commit()
	user = session.query(User).filter_by(email = login_session['email']).one()
	return user.id

#if __name__ == '__main__':
app.secret_key = 'super_secret_key'
app.debug = True
#app.run(host = '0.0.0.0', port = 5000)
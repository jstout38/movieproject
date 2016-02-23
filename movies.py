from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Movie

from flask import session as login_session
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "The Movie List"

engine = create_engine('sqlite:///movieratings.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
@app.route('/users/')
def users():
	userlist = session.query(User).all()
	return render_template('users.html', users = userlist)
	#return "Here is a list of users"

@app.route('/login')
def showLogin():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
	login_session['state'] = state
	return render_template('login.html', STATE=state)

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

	output = ''
	output +='<h1>Welcome, '
	output += login_session['username']

	output += '!</h1>'
	output += '<img src="'
	output += login_session['picture']
	output +=' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	flash("you are now logged in as %s" %login_session['username'])
	return output

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
	if result['status'] == '200':
		del login_session['credentials']
		del login_session['gplus_id']
		del login_session['username']
		del login_session['email']
		del login_session['picture']

		response = make_response(json.dumps('Successfully disconnected.'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response
	else:
		response = make_response(
			json.dumps('Failed to revoke token for given user.', 400))
		response.headers['Content-Type'] = 'application/json'
		return response

@app.route('/users/new/', methods=['GET', 'POST'])
def newUser():
	if 'username' not in login_session:
		return redirect('/login')
	if request.method == 'POST':
		newUser = User(name = request.form['name'], email = request.form['email'])
		session.add(newUser)
		session.commit()
		flash("user created")
		return redirect(url_for('users'))
	else:
		return render_template('newUser.html')
	#return "Creating a new user"

@app.route('/user/<int:user_id>/edit/', methods=['GET', 'POST'])
def editUser(user_id):
	if 'username' not in login_session:
		return redirect('/login')
	editedUser = session.query(User).filter_by(id=user_id).one()
	if request.method == 'POST':
		if request.form['name']:
			editedUser.name = request.form['name']
		if request.form['email']:
			editedUser.email = request.form['email']
		session.add(editedUser)
		session.commit()
		flash("user edited!")
		return redirect(url_for('users'))
	else:
		return render_template('editUser.html', user = editedUser)
	#return "Edit user number %i" % user_id

@app.route('/user/<int:user_id>/delete/', methods=['GET', 'POST'])
def deleteUser(user_id):
	if 'username' not in login_session:
		return redirect('/login')
	deletedUser = session.query(User).filter_by(id=user_id).one()
	if request.method == 'POST':
		session.delete(deletedUser)
		session.commit()
		flash("user deleted!")
		return redirect(url_for('users'))
	else:
		return render_template('deleteUser.html', user = deletedUser)
	#return "Delete user number %i" % user_id

@app.route('/user/<int:user_id>/movies/')
def showMovies(user_id):
	currentUser = session.query(User).filter_by(id=user_id).one()
	movielist = session.query(Movie).filter_by(user_id = user_id).all()
	return render_template('showMovies.html', user = currentUser, movies = movielist)
	#return "Show movies for user number %i" % user_id

@app.route('/user/<int:user_id>/add/', methods=['GET', 'POST'])
def addMovie(user_id):
	if 'username' not in login_session:
		return redirect('/login')
	currentUser = session.query(User).filter_by(id=user_id).one()
	if request.method == 'POST':
		newMovie = Movie(name = request.form['title'], datewatched = request.form['dateWatched'], review = request.form['review'], mdbid = request.form['mdbid'], rating = request.form['rating'], user_id = user_id)
		session.add(newMovie)
		session.commit()
		flash("movie added")
		return jsonify({'status':'OK', 'redirect_url':url_for('showMovies', user_id = user_id)})
	else:
		return render_template('addMovie.html', user = currentUser)
	#return "Add a movie for user number %i" % user_id

@app.route('/user/<int:user_id>/<int:movie_id>/edit/', methods=['GET', 'POST'])
def editMovie(user_id, movie_id):
	if 'username' not in login_session:
		return redirect('/login')
	currentUser = session.query(User).filter_by(id=user_id).one()
	currentMovie = session.query(Movie).filter_by(id=movie_id).one()
	if request.method == 'POST':
		if request.form['name']:
			currentMovie.name = request.form['name']
		if request.form['description']:
			currentMovie.description = request.form['description']
		if request.form['review']:
			currentMovie.review = request.form['review']
		session.add(currentMovie)
		session.commit()
		flash("movie edited")
		return redirect(url_for('showMovies', user_id = user_id))
	else:
		return render_template('editMovie.html', user = currentUser, movie = currentMovie)
	#return "Edit movie number %i for user number %i" % (movie_id, user_id)

@app.route('/user/<int:user_id>/<int:movie_id>/delete/', methods=['GET', 'POST'])
def deleteMovie(user_id, movie_id):
	if 'username' not in login_session:
		return redirect('/login')
	currentUser = session.query(User).filter_by(id=user_id).one()
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

if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host = '0.0.0.0', port = 5000)
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Movie

from flask import session as login_session
import random, string

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
	return render_template('login.html')

@app.route('/users/new/', methods=['GET', 'POST'])
def newUser():
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
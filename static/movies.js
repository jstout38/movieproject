//Stores the movie information for a new movie to pass to the back end
var newMovie = {
	title: '',
	mdbid: 0,
	dateWatched: '',
	rating: 0,
	review: ''
}

//Stores edited information to pass to the back end
var editInfo = {
	dateWatched: '',
	rating: 0,
	review: ''
}

//Variable used later in the autocomplete timeout
var timeoutId;

//Function to help store info from the ajax call
var updateMovie = function(title, id) {
	newMovie.title = title;
	newMovie.mdbid = id;
	console.log(newMovie);
};

//Main function for the search interface for adding a movie
function searchResults() {
 	//If anything has been entered in the search box, make the call
 	if ( $('#new-movie').val().trim() ) {
 		var key = '924332c90e5f89d0bc88e02232ff0723';
 		var query = $('#new-movie').val().trim();
 		var url = 'https://api.themoviedb.org/3/search/movie?api_key=' + key + '&query=' + query;

 		$.ajax({
 			'url': url,
 			'dataType': 'jsonp',
 			'type': 'GET',
 			'contentType': 'application/json',
 			'async': false,
 			'success': function(data, textStats, XMLHttpRequest) {
 				//Display each autocomplete result and attach a click handler
 				for (var i = 0; i < data.results.length; i++) {
 					var result = data.results[i];
 					var title = result.original_title;
 					var year = result.release_date.substring(0, 4);
 					$( "#searchresults" ).append('<li class="list-group-item">' + title + ' (' + year + ')</li>');
 					//On click, add the movie's poster and info to the movie-container div
 					$('li:last' ).on('click', (function(result, title, year) {
 						return function() {
 							updateMovie(title, result.id);
 							$( '#searchresults' ).html('');
 							$('#new-movie').val('');
 							//Clear anything previously in the movie container and add the info/poster
 							$( '#movie-container' ).html('');
 							$( '#movie-container' ).append('<h2 id="searchtitle">' + title + ' (' + year + ')</h2>');
 							$( '#movie-container' ).append('<img width=200 src="https://image.tmdb.org/t/p/w396/' + result.poster_path + '">');
 							$( '#movie-container' ).append('<p>' + result.overview + '</p>');
 							//Enable the add movie button
 							$( '#addMovie').attr("class", "btn btn-default enabled");
 							//Show the rest of the add movie options
 							$( '#datecontainer').css("display", "block");
 							$( '#ratingcontainer').css("display", "block");
 							$( '#reviewcontainer').css("display", "block");
 						};
 					})(result, title, year));
 				}
 			},
 			'error': function() {
 				alert('There was a problem.');
 			}
 		});
 	}
 	//Clear the search results
 	$( "#searchresults" ).html('');
 }

//Function to finish creating the new movie and then use an ajax call to pass it to the back end
function addMovie() {
	//Pull the date, rating, and review
	newMovie.dateWatched = $('#date-watched').val();
 	if (newMovie.dateWatched == '') {
 		alert('You must select a date!');
 	}
 	newMovie.rating = $('#rating-system').val();
 	newMovie.review = $('#review').val().trim();
 	//Find the URL for the ajax call
 	var currentURL = $(location).attr('href');
	var cutoff = currentURL.lastIndexOf("user");
	var userID = currentURL.substring(cutoff + 5, currentURL.length);
	userID = userID.replace('/add/','');
	
	$.ajax({
		url: '/user/' + userID + '/add/',
		data: newMovie,
		type: 'POST',
		dataType: 'json',
		success: function(response) {
			window.location.href = response.redirect_url;
		},
		error: function(error) {
			console.log(error);
		}
	});	
 }

//Finish editing a movie's info and then pass to the back end with an ajax call
function editMovie() {
	//Pull the edited info
	editInfo.dateWatched = $('#date-watched').val();
	editInfo.rating = $('#rating-system').val();
	editInfo.review = $('#review').val();
	//Find the URL for the ajax call
	var currentURL = $(location).attr('href');
	var cutoff = currentURL.lastIndexOf("user");
	var userID = currentURL.substring(cutoff + 5, currentURL.length);
	userID = userID.replace('/edit/', '');
	
	$.ajax({
		url: '/user/' + userID + '/edit/',
		data: editInfo,
		type: 'POST',
		dataType: 'json',
		success: function(response) {
			window.location.href = response.redirect_url;
		},
		error: function(error) {
			console.log(error);
		}
	});
}

//Add the movie info and the users who have watched the movie to the modal, fires on modal being shown
$('#movie-modal').on('shown.bs.modal', function(event){
	//Pull the movie database id from the poster
	var poster = $(event.relatedTarget);
	var recipient = poster.data('movieid');
  	var key = '924332c90e5f89d0bc88e02232ff0723';
	var url = 'https://api.themoviedb.org/3/movie/' + recipient + '?api_key=' + key;
	//Get the movie info and put it in the modal
	$.ajax({
		'url': url,
		'dataType': 'jsonp',
		'type': 'GET',
		'contentType': 'application/json',
		'async': false,
		'success': function(data, textStats, XMLHttpRequest) {
			$('.modal-title').html(data.title)
			$('#mb').html('<p><img width=100 src="https://image.tmdb.org/t/p/w396/' + data.poster_path + '"></p>');
			$('#mb').append('<p class="black"><b>(' + data.release_date.substring(0,4) + ')</b> ');
			for (var i = 0; i < data.genres.length; i++) {
				$('#mb').append(data.genres[i].name);
				if (i < data.genres.length - 1) {
					$('#mb').append(', ');
				}
			}
			$('#mb').append('</p>');
			$('#mb').append('<p class="black">' + data.overview + '</p>');
		},
		'error': function() {
			console.log('There was a problem.');
		}
	});
	//Find the users who have watched this movie and put them in the modal
	$.ajax({
		url: '/movielookup/' + recipient + '/users/',
		type: 'POST',
		dataType: 'json',
		success: function(response) {
			$('.modal-footer').html('Watched by: ')
			currentURL = window.location.href;
			host = currentURL.substring(0, currentURL.indexOf('/'))
			var foundUsers = response['Users'];
			console.log(response['Users']);
			for (var i = 0; i < foundUsers.length; i++) {
				$('.modal-footer').append('<a href="' + host + '/user/' + foundUsers[i].id + '/movies/"><img class="smpic" src="' + foundUsers[i].picture + '">');
			}
		},
		error: function(error) {
			console.log(error);
		}
	});

			
});

//Clear the modal on closing
$('#movie-modal').on('hidden.bs.modal', function() {
	$('.modal-title').html('');
	$('#mb').html('');
	$('.modal-footer').html('');
});

//Creates a delay on the autocorrect to make it a smoother process
$('#new-movie').on('keypress', function(e){
    clearTimeout(timeoutId);
    timeoutId = setTimeout(searchResults, 200);
});

//Click handler for add movie button
$('#addMovie').on('click', function(){
	addMovie();
});

//Click handler for edit movie button
$('#editMovie').on('click', function(){
	editMovie();
});

//Helps display star ratings
$(document).on('ready', function(){
	$('.rating-loading').rating({displayOnly: true});
});

 
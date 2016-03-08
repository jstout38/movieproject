var newMovie = {
	title: '',
	mdbid: 0,
	dateWatched: '',
	rating: 0,
	review: ''
}

var editInfo = {
	dateWatched: '',
	rating: 0,
	review: ''
}

var timeoutId;

var updateMovie = function(title, id) {
	newMovie.title = title;
	newMovie.mdbid = id;
	console.log(newMovie);
};

 function searchResults() {
 	
 	if ( $('#new-movie').val().trim() ) {
 		var key = '924332c90e5f89d0bc88e02232ff0723';
 		var query = $('#new-movie').val().trim();
 		var url = 'https://api.themoviedb.org/3/search/movie?api_key=' + key + '&query=' + query;

 		$.ajax({
 			'url': url,
 			'dataType': 'jsonp',
 			//'jsonpCallback': 'testing',
 			'type': 'GET',
 			'contentType': 'application/json',
 			'async': false,
 			'success': function(data, textStats, XMLHttpRequest) {
 				//$( "#searchresults" ).html('');
 				//$( "#searchresults" ).show();
 				for (var i = 0; i < data.results.length; i++) {
 					var result = data.results[i];
 					var title = result.original_title;
 					var year = result.release_date.substring(0, 4);
 					$( "#searchresults" ).append('<li class="list-group-item">' + title + ' (' + year + ')</li>');
 					$('li:last' ).on('click', (function(result, title, year) {
 						return function() {
 							updateMovie(title, result.id);
 							$( '#searchresults' ).html('');
 							$('#new-movie').val('');
 							$( '#movie-container' ).html('');
 							$( '#movie-container' ).append('<h2 id="searchtitle">' + title + ' (' + year + ')</h2>');
 							$( '#movie-container' ).append('<img width=200 src="https://image.tmdb.org/t/p/w396/' + result.poster_path + '">');
 							$( '#movie-container' ).append('<p>' + result.overview + '</p>');
 							$( '#addMovie').attr("class", "btn btn-default enabled");
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
 	$( "#searchresults" ).html('');
 }

 function addMovie() {
 	newMovie.dateWatched = $('#date-watched').val();
 	if (newMovie.dateWatched == '') {
 		alert('You must select a date!');
 	}
 	newMovie.rating = $('#rating-system').val();
 	newMovie.review = $('#review').val().trim();
 	console.log(newMovie);
 	var currentURL = $(location).attr('href');
	var cutoff = currentURL.lastIndexOf("user");
	var userID = currentURL.substring(cutoff + 5, currentURL.length);
	userID = userID.replace('/add/','');
	console.log(userID);
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

function editMovie() {
	editInfo.dateWatched = $('#date-watched').val();
	editInfo.rating = $('#rating-system').val();
	editInfo.review = $('#review').val();
	console.log(editInfo);
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


	$('#movie-modal').on('shown.bs.modal', function(event){
  			var poster = $(event.relatedTarget);
  			var recipient = poster.data('movieid');
  			var key = '924332c90e5f89d0bc88e02232ff0723';
			var url = 'https://api.themoviedb.org/3/movie/' + recipient + '?api_key=' + key;

			$.ajax({
				'url': url,
				'dataType': 'jsonp',
				'type': 'GET',
				'contentType': 'application/json',
				'async': false,
				'success': function(data, textStats, XMLHttpRequest) {
					console.log(data);
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

$('#movie-modal').on('hidden.bs.modal', function() {
	$('.modal-title').html('');
	$('#mb').html('');
	$('.modal-footer').html('');
});

  $('#new-movie').on('keypress', function(e){
           clearTimeout(timeoutId);
           timeoutId = setTimeout(searchResults, 200);
        });

  $('#addMovie').on('click', function(){
  		addMovie();
  });

  $('#editMovie').on('click', function(){
  		editMovie();
  });

  
  //$('#new-movie').focusout(function(){
  	//	$( "#searchresults" ).html('');
  //});

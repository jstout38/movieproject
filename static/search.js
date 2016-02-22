var newMovie = {
	title: '',
	mdbid: 0,
	dateWatched: '',
	rating: 0,
	review: ''
}

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
 		console.log(url)

 		$.ajax({
 			'url': url,
 			'dataType': 'jsonp',
 			'jsonpCallback': 'testing',
 			'type': 'GET',
 			'contentType': 'application/json',
 			'async': false,
 			'success': function(data, textStats, XMLHttpRequest) {
 				$( "#searchresults" ).html('');
 				$( "#searchresults" ).show();
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
 							$( '#movie-container' ).append('<h3>' + title + ' (' + year + ')</h3>');
 							$( '#movie-container' ).append('<img width=200 src="https://image.tmdb.org/t/p/w396/' + result.poster_path + '">');
 							$( '#movie-container' ).append('<p>' + result.overview + '</p>');
 						};
 					})(result, title, year));
 				}
 				console.log(data);
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
 	newMovie.rating = $('#rating').val();
 	newMovie.review = $('#review').val().trim();
 	console.log(newMovie);
 	var currentURL = $(location).attr('href');
	var userID = currentURL.substring(currentURL.length - 6, currentURL.length - 5);
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

function renderMovies() {

}

  $('#new-movie').on('keypress', function(e){
           if (e.which == 13) {
                searchResults();
           }
           else {
           		console.log("Yep")
           		$( "#searchresults" ).html('');
           }
        });

  $('#addMovie').on('click', function(){
  		addMovie();
  });

  
  //$('#new-movie').focusout(function(){
  	//	$( "#searchresults" ).html('');
  //});

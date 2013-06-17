$(document).ready(function() {
    showTopTags();
    $('#entry').focus();
    $('#bookmarks').slimScroll(
        { height: parseInt($(window).height() * 0.7) 
        }
    );
    // clickHandler for search button
    $('#search').click(function() {
        var _entry = $('#entry').val().trim();
        if (_entry.length < 2) {
            displayErrorMessage('Enter a tag name or URL to bookmark');
            return false;
        }
        if (_entry.substr(0,5) == "tags:") {
            // a tag query
            getUrls(_entry);
        } else {
            // post a new entry
            $('#extra').modal('show').one('shown', function() {
                $.ajax({
                    url: '/url',
                    type: "POST",
                    data: {entry: _entry},
                    async: true,
                }).done(function(msg) {
                    var data = JSON.parse(msg);
                    $('#tags').val(data.join(", "));
                    $('#tags').focus();
                });
            });
            $('#extra #tagsubmit').unbind('click', postURL);
            $('#extra #tagsubmit').bind('click', postURL);
        }
        showTopTags();
//        alert('container height = ' + $('div.container dl').height());
 //       alert('window height = ' + $(window).height());
        return false;
    });
});

function getUrls(tags) {
    var resp = null;
    $.post('/tags', 
        {entry: tags},
        function (d) {
            resp = JSON.parse(d);
            // lets remove the existing bookmarks displayed by the browser
            $('dl#bookmarks').fadeIn('slow');
            $('dl#bookmarks').children().remove();
//            $('dl#bookmarks').append('<h4>Bookmarks</h4>');
            $('dl#bookmarks').siblings('h4').remove(); 
            $('<h4>Bookmarks</h4>').insertBefore('dl#bookmarks');
            for (var e in resp) {
                var t = resp[e].tags.join(', ');
                var d = new Date(resp[e].date_added * 1000);
                var _title = resp[e].title;
                if (_title.length > 50) {
                    _title = resp[e].title.substr(0,49) + '...';
                }
                var ele = '<a href="' + resp[e].url + '" target="_blank">' + _title + '</a>';
                $('dl#bookmarks').append('<dt>' + ele + '</dt><dd>['+t+']&nbsp;&nbsp;<span class="edit">EDIT</span>'+
                    '&nbsp;&nbsp;<span class="delete">DELETE</span></dd>');
            }
            $('dl#bookmarks dd').hover(
                function() {
                    $(this).children('span.edit').fadeIn();
                    $(this).children('span.delete').fadeIn();
                },
                function() {
                    $(this).children('span.edit').fadeOut();
                    $(this).children('span.delete').fadeOut();
                }
            );
            $('span.edit').click(function(ev) {
                ev.stopPropagation();
                ev.preventDefault();
                var _url = $(this).parent().prev().children('a').attr('href');
                $('#entry').val(_url).focus();
                $('dl#bookmarks').fadeOut('slow');
                return false;
            });
            // Not sure if unbind is really required. But observed
            // multiple remove ajax queries being fired upon clicking a
            // single DELETE button. Even stopPropagation did not help
            // Okay. Moving this out of the enclosing foor loop should
            // do the trick
            $('span.delete').click(function(ev) {
                ev.stopPropagation();
                ev.preventDefault();
                var _url = $(this).parent().prev().children('a').attr('href');
                $.post('/remove',
                    {entry: _url},
                    function (d) {
/*                        $('#footer .status').remove();
                        $('#footer').append('<div class="container status">Removed '+ _url + '</div>');
                        setTimeout(function() {
                                     $('#footer .status')
                                                .fadeOut('slow')
                                                .remove();
                        }, 5000);*/
                        updateStatus("Removed " + _url);
                    }
                ).done(function() {
                    $('#search').trigger('click');
                });
                return false;
            });
        }
      ).done(function() {
          return resp;
      });
}

function displayErrorMessage(msg) {
    $('#not-found div.modal-body').children('p').html(msg);
    $('#not-found').modal('show');
    $('#close-modal').click(function() {
        $('#not-found').modal('hide');
    });
}    

function getTags(url) {
    var result;
    $.ajax({
        url: '/url',
        type: "POST",
        data: {entry: url},
        async: false,
        dataType: "json",
    }).done(function(d) {
        result =  d;
    });
    return result;
}

var postURL = function(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var t = $("#tags").val().trim();
        var _url = $('#entry').val().trim();
        var _etags = getTags(_url);
        $('#extra').modal('hide');
        $('#extra #tagsubmit').unbind('click');
        console.log('show spinner invoked');
        showSpinner();
        if (console)
            console.log('db tags=' + _etags.toString() + ' user tags = ' + t.replace(/ /g, ''));
        if (_etags.toString() == t.replace(/ /g, '')) {
            updateStatus('Nothing to update!');
            return false;
        }
        // url in _entry and tags in tags 
        $.post('/post',
            {entry: $('#entry').val().trim(),
                tags: t
            },
            function (d) {
                var resp = JSON.parse(d);
//                console.log(resp);
            }
        ).done(function() {
            $('#entry').val('tags:'+t);
            $('#entry').focus();
//                    $('#search').trigger('click');
        }).always(function() {
            console.log('removing loader');
            $('div.loader').remove();
        });
        return false;
};

var showTopTags = function() {
    $.ajax({
        url: '/toptags',
        type: "POST",
        async: true,
    }).done(function(msg) {
        var data = JSON.parse(msg);
        $('#sidebar ul').remove();
        $('#sidebar').append('<ul></ul>');
        for (i in data) {
            $('#sidebar ul').append('<li><a href="#">'+data[i].name+'</a></li>');
            $('#sidebar ul').append('<li>'+data[i].count+'</li><br>');
            if (i > 20)
                break;
        }
        $('#sidebar li > a').unbind('click', tagClickHandler);
        $('#sidebar li > a').bind('click', tagClickHandler);
    });
};

var tagClickHandler = function(ev) {
    ev.stopPropagation();
    ev.preventDefault();
    var tagName = $(this).text();
    $('#entry').val('tags:'+ tagName);
    $('#search').trigger('click');
};

function updateStatus(msg) {
    $('#footer .status').remove();
    $('#footer').append('<div class="container status">'+ msg + '</div>');
    setTimeout(function() {
         $('#footer .status')
                    .fadeOut('slow')
                    .remove();
    }, 5000);
}

function showSpinner() {
    $('div.loader').remove();
    $('<div class="loader">').css({
                'position': 'absolute',
                'top': 0,
                'left': 0,
                'width': '100%',
                'height': '100%', 
                'background-repeat': 'no-repeat',
                'background-image': 'url("/img/gear.gif")',
                'background-position': 'center',
                'z-index': '9999',
            }).appendTo('body');
    $('<div class="loader">').css({
                'position': 'fixed',
                'top': 0,
                'left': 0,
                'right': 0,
                'bottom': 0,
                'width': '100%',
                'height': '100%', 
                'background-color': 'rgba(0, 0, 0, 0.4)',
                'z-index': '9998',
    }).appendTo('body');
}

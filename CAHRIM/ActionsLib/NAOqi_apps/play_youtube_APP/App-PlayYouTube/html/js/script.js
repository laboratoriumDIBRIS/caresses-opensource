
window.console = {
  log: function(str){
    var node = document.createElement("div");
    node.appendChild(document.createTextNode(str));
    document.getElementById("myLog").appendChild(node);
  }
}

// keeping a pointer to the session is very useful!
var session;
var player;

// id and start time of the video
var id;
var startSeconds;
var url;
var cueUrl;
var playerLastState;
var check_unavailable;

var tag = document.createElement('script');
tag.id = 'iframe-demo';
tag.src = 'https://www.youtube.com/iframe_api';
var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

var YTdeferred = $.Deferred();
function onYouTubeIframeAPIReady() {
  console.log('API ready');
  // resolve when youtube callback is called
  // passing YT as a parameter
  YTdeferred.resolve(window.YT);
};

try {
  QiSession( function (s) {
    console.log('connected!');
    session = s;
    s.service('ALMemory').then(function (memory) {
      memory.subscriber('pepper/music/play').then(function (subscriber) {
        subscriber.signal.connect(onPlayMusic);
      });

      memory.subscriber('pepper/music/pause').then(function (subscriber) {
        subscriber.signal.connect(onPauseMusic);
      });

      memory.subscriber('pepper/music/reload').then(function (subscriber) {
        subscriber.signal.connect(onRequestNewVideoId);
      });

    });
  });
} catch (err) {
  console.log("Error when initializing QiSession: " + err.message);
  console.log("Make sure you load this page from the robots server.")
}

// json : '{ "id":"6_AeMmTE2pc", "startSeconds":"0"}'
// onPlayMusic('{ "id":"5RWYh1rsGMg", "startSeconds":"0"}')

function parseRequestData(data) {
  data = JSON.parse(data);
  id = data.id;
  startSeconds = parseInt(data.startSeconds);
  url = "https://www.youtube.com/embed/" + id + "?enablejsapi=1";
  cueUrl = "http://www.youtube.com/v/" + id + "?version=3";
}

function onRequestNewVideoId(data) {
  parseRequestData(data);
  player.loadVideoByUrl(cueUrl, startSeconds, 'default');
}

function onPlayMusic(data) {
  try {
    parseRequestData(data);

    $("#ytplayer").attr('src', url);
    YTdeferred.done(function(YT) {
      console.log('Player ready');
      player = new YT.Player('ytplayer', {
        height: '390',
        width: '640',
        events: {
            'onReady': onPlayerReady,
            'onStateChange': onPlayerStateChange
        }
      });
    });
  } catch (err)
  {
    console.log('Error : ' + err.message);
  }
}

function onPlayerReady(event) {
  event.target.cueVideoByUrl(cueUrl, startSeconds, 'default');
  event.target.playVideo();
}

function onPlayerStateChange(event) {
  // console.log(event.data);
  switch (event.data) {
    case YT.PlayerState.ENDED:
      console.log("State : ENDED");
      session.service('ALMemory').then(function (memory) {
        memory.raiseEvent('pepper/music/ended','ended');
      });
      break;

    case YT.PlayerState.PLAYING:
      console.log("State : PLAYING");
      break;
    
    case YT.PlayerState.PAUSED:
      console.log("State : PAUSED");
      // session.service('ALMemory').then(function (memory) {
      //   memory.raiseEvent('pepper/music/paused', player.getCurrentTime());
      // });
      break;

    case YT.PlayerState.BUFFERING:
      console.log("State : BUFFERING");
      break;

    case YT.PlayerState.CUED:
      console.log("State : CUED");
      break;
    
    default:
      console.log("State : UNKNOWN");
      if (check_unavailable)
        clearInterval(check_unavailable);
      check_unavailable = setInterval(timer_check_unavailable, 5000);
      break;
  }

  playerLastState = event.data;
}

function timer_check_unavailable() {
  if (playerLastState == -1) {
    console.log("State : UNAVAILABLE");
    session.service('ALMemory').then(function (memory) {
      memory.raiseEvent('pepper/music/unavailable', 'unavailable');
    });
  }
  // document.getElementById('myLog').innerHTML = "";
  clearInterval(check_unavailable);
}

function onPauseMusic(data) {
  try {
    var stop_seconds = player.getCurrentTime();
    session.service('ALMemory').then(function (memory) {
      memory.insertData('pepper/music/stop_seconds', stop_seconds);
    });
    player.stopVideo();
  } catch (err) {
    console.log('Error : ' + err.message);
  }
}

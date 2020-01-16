// keeping a pointer to the session is very useful!

window.console = {
  log: function(str){
    var node = document.createElement("div");
    node.appendChild(document.createTextNode(str));
    document.getElementById("myLog").appendChild(node);
    // $('.surprise').show();
  }
}

var session;

try {
  QiSession( function (s) {
    console.log('connected!');
    session = s;
    s.service('ALMemory').then(function (memory) {
      memory.subscriber('/face/emotion').then(function (subscriber) {
      subscriber.signal.connect(onInfoUpdated);
      });
      
    });
  });
} catch (err) {
  console.log("Error when initializing QiSession: " + err.message);
  console.log("Make sure you load this page from the robots server.")
}

function onSpeechReconized(data) {
  $('#say').text(data);
}

function onInfoUpdated(data) {
  $('#hello').hide();
  $('.anger').hide();
  $('.happiness').hide();
  $('.neutral').hide();
  $('.sadness').hide();
  $('.surprise').hide();

  if (data[0] == 'angry')
    $('.anger').show();
  else if (data[0] == 'happy')
    $('.happiness').show();
  else if (data[0] == 'neutral')
    $('.neutral').show();
  else if (data[0] == 'sad')
    $('.sadness').show();
  else if (data[0] == 'surprised')
    $('.surprise').show();
  }
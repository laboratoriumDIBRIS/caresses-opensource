$(document).ready(function() {
    // document.body.style.zoom = 3.0;
});

// keeping a pointer to the session is very useful!

window.console = {
    log: function(str){
        var node = document.createElement("div");
        node.appendChild(document.createTextNode(str));
        document.getElementById("myLog").appendChild(node);
    }
}

var session;
var player;

try {
    QiSession( function (s) {
        console.log('connected!');
        session = s;

        s.service('ALMemory').then(function (memory) {
            memory.subscriber('pepper/ihouse/temperature').then(function (subscriber) {
                subscriber.signal.connect(loadTemperature);
            });
        });
        
    });
} 

catch (err) {
    console.log("Error when initializing QiSession: " + err.message);
    console.log("Make sure you load this page from the robots server.")
}

function loadTemperature(data) {
    try {
        console.log(data);
        temp = data + '&deg;';
        $(".temperature").html(temp);
    } catch (err) {
        console.log(err.message);
    }
}

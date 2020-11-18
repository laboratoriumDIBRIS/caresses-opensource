
$(document).ready(function() {
});

window.console = {
    log: function (str) {
        var node = document.createElement("div");
        node.appendChild(document.createTextNode(str));
        document.getElementById("myLog").appendChild(node);
    }
}

var appKey = "e0750e2ae2304dd9ca21c5e6cdaa320a";

var session;

// loadData("Tokyo");

try {
    QiSession(function (s) {
        console.log("Connected");
        session = s;
        is_talked = false;

        session.service('ALMemory').then(function (memory) {
            memory.subscriber('pepper/weather/location').then(function (subscriber) {
                subscriber.signal.connect(loadData);
            });
        });

    });
} catch (err) {
    console.log(err.message);
}

function loadData(data) {
    console.log(data);
    var searchLink = "https://api.openweathermap.org/data/2.5/weather?q=" + data + "&units=metric" + "&appid=" + appKey;
    console.log(searchLink);
    httpRequestAsync(searchLink, theResponse);
}

function getIconCode(jsonObject) {
    var nowTimestamp = Math.floor(Date.now() / 1000);
    var weatherClass = 'wi wi-owm-';
    weatherClass += (nowTimestamp >= jsonObject.sys.sunrise && nowTimestamp <= jsonObject.sys.sunset ? 'day' : 'night');
    weatherClass += ('-' + jsonObject.weather[0].id);
    console.log(weatherClass);
    return weatherClass;
}

function theResponse(response) {
    var jsonObject = JSON.parse(response);
    // console.log(jsonObject);

    code = String(jsonObject.cod);

    if (code == "200") {
        city = jsonObject.name;
        temp = parseFloat(jsonObject.main.temp.toFixed(1));
        wind = jsonObject.wind.speed;
        humidity = jsonObject.main.humidity;

        // set up html
        $(".location").text(city);
        $(".temperature").html(temp + '&deg;');
        $(".windspeed").html('<p>' + wind + '</p><p>m/s</p>');
        $(".humidity").text(humidity + ' %');
        $(".icon-now").addClass(getIconCode(jsonObject));

        info = jsonObject.weather[0].main + ';' + jsonObject.weather[0].id + ';' + temp
    } else {
        info = "ERROR";
    }
    // send data to robot
    try
    {
        console.log("Info: " + info);
        session.service('ALMemory').then(function (memory) {
            memory.raiseEvent('pepper/weather/info', info);
        });
    }
    catch (err)
    {
        console.log(err);
    }
}

function httpRequestAsync(url, callback) {
    console.log("httpRequestAsync");
    var httpRequest = new XMLHttpRequest();
    httpRequest.onreadystatechange = function () {
        if (httpRequest.readyState == 4)
            callback(httpRequest.responseText);
    }
    httpRequest.open("GET", url, true); // true for asynchronous 
    httpRequest.send();
}
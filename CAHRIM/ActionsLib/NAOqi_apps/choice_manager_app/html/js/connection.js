/****************************************************/
/* Aldebaran Project Hopias                         */
/* connection.js                                    */
/* Innovation - Protolab - mcaniot@aldebaran.com    */
/* Aldebaran Robotics (c) 2016 All Rights Reserved. */
/* This file is confidential.                       */
/****************************************************/

// New session naoqi
var session = new QiSession();

// Subscribe to the event "nameSubscribe"
function startSubscribe(nameSubscribe) {

    session.service("ALMemory").done(function (ALMemory) {
        ALMemory.subscriber(nameSubscribe).done(function(subscriber) {
            // Call the function "toTabletHandler" when a signal raised on the event.
            // This function is defined in the other js files.
            subscriber.signal.connect(toTabletHandler);
        });    
    });

    session.service("ALMemory").done(function (ALMemory) {
        ALMemory.subscriber("HTMLHumanFace").done(function(subscriber) {
            // Call the function "toTabletHandler" when a signal raised on the event.
            // This function is defined in the other js files.
            subscriber.signal.connect(humanFace);
        });    
    });

    session.service("ALMemory").done(function (ALMemory) {
        ALMemory.subscriber("HTMLHumanSay").done(function(subscriber) {
            // Call the function "toTabletHandler" when a signal raised on the event.
            // This function is defined in the other js files.
            subscriber.signal.connect(humanSay);
        });    
    });

    session.service("ALMemory").done(function (ALMemory) {
        console.log("ALMemory");
        ALMemory.raiseEvent("isLoaded", "ok");
    });   
}

// Send data to choregraphe thank to the event "tabletResponse"
function sendToChoregraphe(response) {
    session.service("ALMemory").done(function (ALMemory) {
        console.log("ALMemory");
        ALMemory.raiseEvent("tabletResponse", response);
    });    
}

// Close the window et send the information to the event "PepperQiMessaging/fromTabletStop"
function stopProgramm(response) {
    window.close();
    session.service("ALMemory").done(function (ALMemory) {
        console.log("ALMemory");
        ALMemory.raiseEvent("PepperQiMessaging/fromTabletStop", response);
    });
}

function humanFace(value) { 
    if (value === "erase_all"){
        document.images["humanFace"].src =  ""
        document.getElementById("objectHumanFace").style.display = 'none'
    }
    else {
        if (document.images["humanFace"].src === value){
            console.log("Same Human")
        }
        else{
            document.getElementById("objectHumanFace").style.display = 'block'
            document.images["humanFace"].src =  value
        }
    }
       
}

function humanSay(value) { 
    if (value === "erase_all"){
        document.getElementById("objectTalkBubble").style.display = 'none'
    }
    else {
        document.getElementById("objectTalkBubble").style.display = 'block'
        document.getElementById("humanSay").innerHTML = value;  
    }
}

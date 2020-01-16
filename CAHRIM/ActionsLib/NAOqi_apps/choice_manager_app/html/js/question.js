/****************************************************/
/* Aldebaran Project Hopias                         */
/* question.js                                      */
/* Innovation - Protolab - mcaniot@aldebaran.com    */
/* Aldebaran Robotics (c) 2016 All Rights Reserved. */
/* This file is confidential.                       */
/****************************************************/

// List of the name of the button
var list_answer = []

var nb_max_button = 10

// Create a new button
function addButton(nameButton){
    list_answer.push(nameButton)

    var space = document.createTextNode(" ");
    var btn = document.createElement("div");
    $(btn).addClass("button")

	btn.value = nameButton;
	btn.id = nameButton;

    // Function called when the button is clicked
	btn.addEventListener("touchstart",function(event){
        sendToChoregraphe(btn.value);
        event.preventDefault();
        //erase()
        setTimeout(function(){
            erase()
        }, 500);
        clickAnimation(this)
    });
    var txt = document.createTextNode(nameButton);

    btn.appendChild(txt);

    if (nameButton == "NEXT") {
        var id = "nextButton"
    } else if (nameButton == "BACK"){
        var id = "backButton"
    } else if (nameButton == "EXIT") {
        var id = "exitButton"
    } else {
        var id = "objectButton"
    }

	document.getElementById(id).appendChild(btn);

	document.getElementById(id).appendChild(space);
}

// Function who manage the command sent by choregraphe
function choice(tmp){
    for(var i= 0; i < list_answer.length; i++)
    {
        if (list_answer[i] === tmp){
            erase();
            sendToChoregraphe(tmp);
            break;
        }
    }
}

// This function is called when a signal is sent by choregraphe thank to an event.
function toTabletHandler(value) {
    document.getElementById("command").value= value;
    tmp = document.getElementById("command").value;
    if (tmp.length > 1){
        if (tmp[0] === "erase_all"){
            erase();
        }
        else {
            if (tmp[0] === "human_answer") {
                choice(tmp[1]);
            }
            else{
                writeQuestion(tmp[0]);
                listToButton(tmp[1]);
            }
        }
    }

}

// Write Question
function writeQuestion(tmp){
    $.getScript("js/write.js", function(){
        textFullScreen(tmp,"#objectQuestion","Block")

    });
}


// Erase Question and button answer
function erase(){
    while (document.getElementById("objectButton").firstChild) {
        document.getElementById("objectButton").removeChild(document.getElementById("objectButton").firstChild);
    }
    while (document.getElementById("nextButton").firstChild){
        document.getElementById("nextButton").removeChild(document.getElementById("nextButton").firstChild);
    }
    while (document.getElementById("backButton").firstChild){
        document.getElementById("backButton").removeChild(document.getElementById("backButton").firstChild);
    }
    while (document.getElementById("exitButton").firstChild){
        document.getElementById("exitButton").removeChild(document.getElementById("exitButton").firstChild);
    }
    $("#objectQuestion").empty()
}

// creation button with a list: example listToButton("word 1;word 2;word 3 ;...;word n ")
function listToButton(tmp){
    var tmp_list = tmp.split(";")
    for (j = 0; j < tmp_list.length; j++) {
        if (j < nb_max_button){
            addButton(tmp_list[j]);
        }
        else{
            list_answer.push(tmp_list[j])
        }
    }
}


// animation when the button is clicked
function clickAnimation(element) {
    clickSound()
    setTimeout(function(){
        $(element).removeClass("buttonGrey")
        $(element).addClass = "button"
    }, 250);
    $(element).addClass("buttonGrey")
}


// Sound heard when the button is clicked
var audio = new Audio('sound/click.mp3');

// Play sound
function clickSound(){
    audio.play();
}

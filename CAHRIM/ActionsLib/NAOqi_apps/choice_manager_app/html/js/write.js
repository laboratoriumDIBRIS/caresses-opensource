/****************************************************/
/* Aldebaran Project Hopias                         */
/* write.js                                         */
/* Innovation - Protolab - mcaniot@aldebaran.com    */
/* Aldebaran Robotics (c) 2016 All Rights Reserved. */
/* This file is confidential.                       */
/****************************************************/


// Number of line
var line = 0;

// Number of Letter
var nbLetter = 0;

// Number maximal of letter by line
var tailleMax = 35;

// Number Maximal of line by page
var nbLineMax = 6;

// position of text ("Center" or "Left")
var oldPosition = "none";
 
// This function is called when a signal is sent by choregraphe thank to an event.
function toTabletHandler(value) { 
    document.getElementById("command").value= value;
    tmp = document.getElementById("command").value;
    if (tmp.length > 2) {
        if (tmp[0] === "erase_all"){
            erase_text()
        }
        else {
            if (oldPosition != "none" && oldPosition != tmp[1]){ 
                erase_text()
            }
            textFullScreen(tmp[0] + " ","#objectText"+tmp[1],tmp[2])
            oldPosition = tmp[1]  
        }
    }
}

// Print the message letter by letter 
var printLetterByLetter = function( target, message, index, interval){
    if (index < message.length) {
        $(target).append(message[index++]);
        processTextWithIndice()
        setTimeout(function () { printLetterByLetter(target, message, index, interval); }, interval);
    }
}

// clear the page when there is "nbLineMax" lines with indice
function processTextWithIndice(){
    nbLetter = nbLetter + 1
    if (nbLetter >= tailleMax * nbLineMax){
        erase_text()
        line = 0;
        nbLetter = 0
    }
}

// Process the text and clear the page when there is "nbLineMax" lines
function processText(tmp){
    line = line + (tmp.length)/tailleMax
    if (line >= nbLineMax){
        erase_text()
        line = 0;
    }
}

// Print the text in a specific position
function textFullScreen(tmp,positionText, mode){

    processText(tmp);

    // print letter by letter
    if (mode === "Letter"){
        $(function () {

        printLetterByLetter(positionText,tmp, 0, 50);   

        }); 
    }

    // print in one block
    if (mode === "Block"){
        $(positionText).append(tmp);
    }   
    
}

// erase the text on the screen
function erase_text(){
    $("#objectTextCenter").empty()
    $("#objectTextLeft").empty()
}

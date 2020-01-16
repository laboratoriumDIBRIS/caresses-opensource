var session;

// Sound heard when the button is clicked
var audio = new Audio('click.mp3');

// Play sound
function clickSound(){
    audio.play();
}

function init() {
    session = new QiSession();
}


function addNumber(element){

    clickSound()

    str = document.getElementById('mvar').value

    if (element.value == "  x  "){
        str = "              ";
        document.getElementById('mvar').value = str;
    } 

    else {
        for (i = 0; i < 14; i++) { 
            if (str.charAt(i)==" "){
            break
            }  
        }  
        str = str.replace(str.charAt(i), element.value.replace(/ /g, ""));
        document.getElementById('mvar').value = str;    
    }

}   


function exitSelector(element){
     clickSound()
    console.info("Done...")
    element.style.background = '#c5c5c5';
    session.service("ALMemory").done(function (ALMemory) {
        ALMemory.raiseEvent("CARESSES/CustomNumber/number", document.getElementById('mvar').value.replace(/ /g, ""));
    }); 
}

function exit(element){
     clickSound()
    console.info("Exiting...")
    element.style.background = '#c5c5c5';
    session.service("ALMemory").done(function (ALMemory) {
        ALMemory.raiseEvent("CARESSES/CustomNumber/exit", document.getElementById('mvar').value.replace(/ /g, ""));
    }); 
}
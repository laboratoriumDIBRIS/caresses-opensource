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

function enterTime(time) {
    session.service("ALMemory").done(function (ALMemory) {
        ALMemory.raiseEvent("CARESSES/DateTimeSelector/time24", time);
    });    
}

function addNumber(element){

    //clickSound()

    str = document.getElementById('mvar').value;

    complete = true; 
    for (i = 0; i < 5; i++) { 

        if (i == 2){
            continue
        }
        if (isNaN(str.charAt(i))){
            complete = false;
            break
        }        
           
    }

    if (element.value == "  x  "){
        if (i == 1){
            str = replaceAt(str, 'h', 0);
        } else if (i == 3){
            str = replaceAt(str, 'h', 1);
        } else if (3 < i && i <= 5){
            str = replaceAt(str, 'm', i - 1);
        }
        document.getElementById('mvar').value = str;
    } else if (element.value == "  v  "){
        console.info(document.getElementById('mvar').value)
        enterTime(document.getElementById('mvar').value)
    }else {
        if (complete == false){
            str = str.replace(str.charAt(i), element.value.replace(/ /g, ""));
            document.getElementById('mvar').value = str;
        }
    }

    str_after = document.getElementById('mvar').value;
    hour = str_after.substring(0, 2);
    minutes = str_after.substring(3, 5);

    if (! isNaN(hour)){
        if (Number(hour) > 23){
            str_after = replaceAt(str_after, 'hh', 0);
        }
    }
    if (! isNaN(minutes)){
        
        if (Number(minutes) > 59){
            str_after = replaceAt(str_after, 'mm', 3);
        }
    }
    document.getElementById('mvar').value = str_after;
}   

function replaceAt(string, replacement, index){
    return string.substr(0, index) + replacement + string.substr(index + replacement.length);
}

function exitSelector(element){
    console.info("Exiting...")
    element.style.background = '#c5c5c5';
    session.service("ALMemory").done(function (ALMemory) {
        ALMemory.raiseEvent("CARESSES/DateTimeSelector/exit", true);
    });  
}
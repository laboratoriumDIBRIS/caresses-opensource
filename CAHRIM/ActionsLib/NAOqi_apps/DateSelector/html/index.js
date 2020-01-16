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

function enterDate(date) {
    session.service("ALMemory").done(function (ALMemory) {
        ALMemory.raiseEvent("CARESSES/DateTimeSelector/date", date);
    });    
}

function addNumber(element){

    //clickSound()

    str = document.getElementById('mvar').value;

    complete = true; 
    for (i = 0; i < 10; i++) { 

        if ((i == 2) || (i == 5)){
            continue
        }
        if (isNaN(str.charAt(i))){
            complete = false;
            break
        }        
           
    }

    if (element.value == "  x  "){
        switch(i){
            case 1:
                str = replaceAt(str, 'd', 0);
            case 3:
                str = replaceAt(str, 'd', 1);
            case 4:
                str = replaceAt(str, 'm', 3);
            case 6:
                str = replaceAt(str, 'm', 4);
            case 7:
                str = replaceAt(str, 'y', 6);
            case 8:
                str = replaceAt(str, 'y', 7);
            case 9:
                str = replaceAt(str, 'y', 8);
            case 10:
                str = replaceAt(str, 'y', 9);
        }
        document.getElementById('mvar').value = str;
    } else if (element.value == "  v  "){
        console.info(document.getElementById('mvar').value)
        enterDate(document.getElementById('mvar').value)
    }else {
        if (complete == false){
            str = str.replace(str.charAt(i), element.value.replace(/ /g, ""));
            document.getElementById('mvar').value = str;
        }
    }

    str_after = document.getElementById('mvar').value;
    day = str_after.substring(0, 2);
    month = str_after.substring(3, 5);
    year = str_after.substring(6, 10);

    if (! isNaN(day)){
        if (Number(day) > 31){
            str_after = replaceAt(str_after, 'dd', 0);
        }
    }
    if (! isNaN(month)){
        
        if (Number(month) > 12){
            str_after = replaceAt(str_after, 'mm', 3);
        }
    }
    if (! isNaN(year)){
        
        if (Number(year) > 2999){
            str_after = replaceAt(str_after, 'yyyy', 6);
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
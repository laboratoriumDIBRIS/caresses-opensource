import speech as sp
language="english"
conf = sp.Speech("speech_conf.json", language, writedebug=False)
KEYWORDS = "KEYWORDS"
AFFIRMATIVE = "affirmative"
NEGATIVE = "negative"
OPTIONS = "options"
STOP="stop"
REPEAT="repeat"
STOP_INTERACTION = "STOP-INTERACTION"


reader = open('speechLog.log','r')
writer = open('speechLogproc.log', 'w')
lines=[]

for line in reader.readlines():
    lines.append(line)

for index, line in enumerate(lines):
    if "[    ] USER >" in line:
        writer.write(line.replace("[    ]","[FROZEN]"))
    else:
        writer.write(line)
    if sp.TAGS[2] in line or sp.TAGS[3] in line or sp.TAGS[4] in line or sp.TAGS[11] in line:
        if sp.TAGS[2] in line:
            usertag="AACo"
        elif sp.TAGS[3] in line:
            usertag="AAEv"
        elif sp.TAGS[11] in line:
            usertag="AALo"
        else:
            usertag="AAGe"


        if(index<len(lines)-1) and ("USER >" in lines[index+1]) and (any((" "+affirmative+" ") in (" "+lines[index+1].split("\n")[0]+" ") for affirmative in conf.script[KEYWORDS][AFFIRMATIVE][language]) or any(("'"+affirmative+"'") in lines[index+1] for affirmative in conf.script[KEYWORDS][AFFIRMATIVE][language])):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Po]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-1) and ("USER >" in lines[index+1]) and (any((" "+negative+" ") in (" "+lines[index+1].split("\n")[0]+" ") for negative in conf.script[KEYWORDS][NEGATIVE][language]) or any(("'"+negative+"'") in lines[index+1] for negative in conf.script[KEYWORDS][NEGATIVE][language])):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Ne]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and ("USER >" in lines[index+1]) and (conf.script[KEYWORDS][OPTIONS][language] in lines[index+1] or ("["+conf.script[KEYWORDS][OPTIONS][language]+"]" in lines[index+1])):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Op]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and ("USER >" in lines[index+1]) and any((" "+stop+" ") in (" "+lines[index+1].split("\n")[0]+" ") for stop in conf.script[KEYWORDS][STOP][language]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"St]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and ("USER >" in lines[index+1]) and any((" "+repeat+" ") in (" "+lines[index+1].split("\n")[0]+" ") for repeat in conf.script[KEYWORDS][REPEAT][language]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Re]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-2) and ("USER >" in lines[index+1]) and (sp.TAGS[0] in lines[index+2] or sp.TAGS[24] in lines[index+2]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"NU]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-3) and ("USER >" in lines[index+1]) and conf.script[STOP_INTERACTION][language] in lines[index+3]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"SI]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-2) and conf.script[STOP_INTERACTION][language] in lines[index+2]:
            writer.write("xxxxxxxxxxxxxxxxxxxxxxxx- INFO: ["+usertag+"SI]\n")
        elif (index<len(lines)-1) and ("PEPPER >" in lines[index+1]) and lines[index].split("]")[1]==lines[index+1].split("]")[1]:
            writer.write("xxxxxxxxxxxxxxxxxxxxxxxx- INFO: ["+usertag+"NR]\n")
        elif (index<len(lines)-1) and ("USER >" in lines[index+1]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Ge]"))
            lines.remove(lines[index+1])

    elif sp.TAGS[5] in line or sp.TAGS[24] in line:
        usertag="AAPa"

        if (index<len(lines)-1) and ("USER >" in lines[index+1]) and (conf.script[KEYWORDS][OPTIONS][language] in lines[index+1] or ("["+conf.script[KEYWORDS][OPTIONS][language]+"]" in lines[index+1])):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Op]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and ("USER >" in lines[index+1]) and any((" "+stop+" ") in (" "+lines[index+1].split("\n")[0]+" ") for stop in conf.script[KEYWORDS][STOP][language]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"St]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and ("USER >" in lines[index+1]) and any((" "+repeat+" ") in (" "+lines[index+1].split("\n")[0]+" ") for repeat in conf.script[KEYWORDS][REPEAT][language]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Re]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-2) and ("USER >" in lines[index+1]) and (sp.TAGS[0] in lines[index+2] or sp.TAGS[24] in lines[index+2]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"NU]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-3) and ("USER >" in lines[index+1]) and conf.script[STOP_INTERACTION][language] in lines[index+3]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"SI]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-2) and conf.script[STOP_INTERACTION][language] in lines[index+2]:
            writer.write("xxxxxxxxxxxxxxxxxxxxxxxx- INFO: ["+usertag+"SI]\n")
        elif (index<len(lines)-1) and ("PEPPER >" in lines[index+1]) and lines[index].split("]")[1]==lines[index+1].split("]")[1]:
            writer.write("xxxxxxxxxxxxxxxxxxxxxxxx- INFO: ["+usertag+"NR]\n")
        elif (index<len(lines)-1) and ("USER >" in lines[index+1]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Pa]"))
            lines.remove(lines[index+1])

    elif sp.TAGS[22] in line:
        usertag="RAPr"

        number=None
        usertag2=""
        for i in range(index+1, len(lines)):
            if("PEPPER >" in lines[i]):
                if "[C" in lines[i] and ("EXIT" in lines[i-2] or "''" in lines[i-2]):
                    usertag2="SI"
                elif "[C" in lines[i]:
                    usertag2="Cc"
                elif any((" "+repeat+" ") in (" "+lines[i-1].split("\n")[0]+" ") for repeat in conf.script[KEYWORDS]["repeat_chitchat"][language]):
                    usertag2="Re"
                elif any((" "+freeze+" ") in (" "+lines[i-1].split("\n")[0]+" ") for freeze in conf.script[KEYWORDS]["freeze"][language]):
                    usertag2="Fr"
                elif any((" "+revise+" ") in (" "+lines[i-1].split("\n")[0]+" ") for revise in conf.script[KEYWORDS]["revise"][language]):
                    usertag2="Rv"
                elif any((" "+options+" ") in (" "+lines[i-1].split("\n")[0]+" ") for options in conf.script[KEYWORDS]["options2"][language]) or "TABLET TOUCHED" in lines[i-1]:
                    usertag2="Op"
                elif sp.TAGS[22] in lines[i] and "USER > \n" in lines[i-1]:
                    usertag2="NR"
                elif sp.TAGS[22] in lines[i]:
                    usertag2="Op"
                elif sp.TAGS[21] in lines[i]:
                    usertag2="Go"
                elif sp.TAGS[20] in lines[i]:
                    usertag2="Go"
                number=i
                break

        if number!=None:
            for i in range(index+1,number):
                if usertag2=="SI" or usertag2=="Cc":
                    if(i<number-2):
                        writer.write(lines[index+1].replace("[    ]","["+usertag+"Pr]"))
                        lines.remove(lines[index+1])
                    else:
                        writer.write(lines[index+1].replace("[    ]","["+usertag+usertag2+"]"))
                        lines.remove(lines[index+1])
                else:
                    if(i<number-1):
                        writer.write(lines[index+1].replace("[    ]","["+usertag+"Pr]"))
                        lines.remove(lines[index+1])
                    else:
                        writer.write(lines[index+1].replace("[    ]","["+usertag+usertag2+"]"))
                        lines.remove(lines[index+1])                   


    elif sp.TAGS[21] in line:
        usertag="RACo"

        if(index<len(lines)-1) and ("USER >" in lines[index+1]) and conf.script["AcceptRequest"]["yes"][language] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Po]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and ("USER >" in lines[index+1]) and conf.script["AcceptRequest"]["no"][language] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Ne]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-3) and ("USER >" in lines[index+2]) and "[C" in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"SI]"))
            lines.remove(lines[index+1])

    elif sp.TAGS[17] in line:
        usertag="CAQu"
        if(index<len(lines)-1) and "[R" in lines[index+1]:
            writer.write("xxxxxxxxxxxxxxxxxxxxxxxx- INFO: ["+usertag+"SI]\n")
        elif(index<len(lines)-2) and "[R" in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"SI]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and (conf.script["Chitchat"]["repeat"][language] in lines[index+1] or conf.script["Chitchat"]["say_again"][language] in lines[index+1]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Re]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and conf.script[KEYWORDS]["revise"][language][0] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Rv]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and conf.script[KEYWORDS]["freeze"][language][0] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Fr]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and sp.TAGS[17] in lines[index+2] and "TABLET TOUCHED" in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Op]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-2) and sp.TAGS[17] in lines[index+2] and "USER > \n" in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"NR]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-2) and sp.TAGS[17] in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Qu]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and sp.TAGS[12] in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"NU]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and (sp.TAGS[14] in lines[index+2] or sp.TAGS[18] in lines[index+2]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Po]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and sp.TAGS[15] in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Ne]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and sp.TAGS[16] in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Go]"))
            lines.remove(lines[index+1])

    elif sp.TAGS[23] in line:
        usertag="CAQc"
        if(index<len(lines)-1) and "[R" in lines[index+1]:
            writer.write("xxxxxxxxxxxxxxxxxxxxxxxx- INFO: ["+usertag+"SI]\n")
        elif(index<len(lines)-2) and "[R" in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"SI]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and (conf.script["Chitchat"]["repeat"][language] in lines[index+1] or conf.script["Chitchat"]["say_again"][language] in lines[index+1]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Re]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and conf.script[KEYWORDS]["revise"][language][0] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Rv]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and conf.script[KEYWORDS]["freeze"][language][0] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Fr]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and sp.TAGS[23] in lines[index+2] and "TABLET TOUCHED" in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Op]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and sp.TAGS[16] in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Go]"))
            lines.remove(lines[index+1])
        else:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Ge]"))
            lines.remove(lines[index+1])


    elif sp.TAGS[19] in line:
        usertag="CAQg"
        if(index<len(lines)-1) and "[R" in lines[index+1]:
            writer.write("xxxxxxxxxxxxxxxxxxxxxxxx- INFO: ["+usertag+"SI]\n")
        elif(index<len(lines)-2) and "[R" in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"SI]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and (conf.script["Chitchat"]["repeat"][language] in lines[index+1] or conf.script["Chitchat"]["say_again"][language] in lines[index+1]):
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Re]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and conf.script[KEYWORDS]["revise"][language][0] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Rv]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and conf.script[KEYWORDS]["freeze"][language][0] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Fr]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and sp.TAGS[23] in lines[index+2] and "TABLET TOUCHED" in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Op]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and sp.TAGS[16] in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Go]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-4) and "[A" in lines[index+4]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Po]"))
            lines.remove(lines[index+1])
        else:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Ne]"))
            lines.remove(lines[index+1])

    elif sp.TAGS[18] in line:
        usertag="CAWa"
        if(index<len(lines)-2) and "[R" in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"SI]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-4) and "[R" in lines[index+4] and "USER >" in lines[index+1] and "USER >" in lines[index+2] and "USER >" in lines[index+3]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Op]"))
            lines.remove(lines[index+1])
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Wa]"))
            lines.remove(lines[index+1])
            writer.write(lines[index+1].replace("[    ]","["+usertag+"SI]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-3) and sp.TAGS[16] in lines[index+1] and (conf.script["Chitchat"]["repeat"][language] in lines[index+3] or conf.script["Chitchat"]["say_again"][language] in lines[index+3]):
            writer.write(lines[index+3].replace("[    ]","["+usertag+"Re]"))
            lines.remove(lines[index+3])
        elif (index<len(lines)-1) and sp.TAGS[16] in lines[index+1] and conf.script[KEYWORDS]["revise"][language][0] in lines[index+3]:
            writer.write(lines[index+3].replace("[    ]","["+usertag+"Rv]"))
            lines.remove(lines[index+3])
        elif (index<len(lines)-1) and sp.TAGS[16] in lines[index+1] and conf.script[KEYWORDS]["freeze"][language][0] in lines[index+3]:
            writer.write(lines[index+3].replace("[    ]","["+usertag+"Fr]"))
            lines.remove(lines[index+3])
        elif (index<len(lines)-2) and sp.TAGS[16] in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Go]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-4) and sp.TAGS[16] in lines[index+4] and "USER >" in lines[index+1] and "USER >" in lines[index+2] and "USER >" in lines[index+3]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Op]"))
            lines.remove(lines[index+1])
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Wa]"))
            lines.remove(lines[index+1])
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Go]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-2) and "PEPPER > " in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Wa]"))
            lines.remove(lines[index+1])
        elif(index<len(lines)-4) and "PEPPER > " in lines[index+4] and "USER >" in lines[index+1] and "USER >" in lines[index+2] and "USER >" in lines[index+3]: 
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Op]"))
            lines.remove(lines[index+1])
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Wa]"))
            lines.remove(lines[index+1])
            lines.remove(lines[index+1])

    elif sp.TAGS[16] in line:
        usertag="CACo"
        if(index<len(lines)-1) and ("USER >" in lines[index+1]) and conf.script["AcceptRequest"]["yes"][language] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Po]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-1) and ("USER >" in lines[index+1]) and conf.script["AcceptRequest"]["no"][language] in lines[index+1]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"Ne]"))
            lines.remove(lines[index+1])
        elif (index<len(lines)-2) and ("USER >" in lines[index+1]) and "[R" in lines[index+2]:
            writer.write(lines[index+1].replace("[    ]","["+usertag+"SI]"))
            lines.remove(lines[index+1])


reader.close()
writer.close()
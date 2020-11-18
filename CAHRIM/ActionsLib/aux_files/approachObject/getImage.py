#! /usr/bin/env python
# -*- encoding: UTF-8 -*-
'''
Example: Get an image. Display it and save it using PIL
http://doc.aldebaran.com/2-5/dev/python/examples/vision/get_image.html
'''

import qi
import argparse
import sys
import time
from PIL import Image

def main(session, img_name):
    video_service = session.service("ALVideoDevice")
    AL_kVGA	 = 2    # VGA
    colorSpace = 11   # RGB
    videoClient = video_service.subscribe("python_client", AL_kVGA, colorSpace, 5)
    naoImage = video_service.getImageRemote(videoClient)
    video_service.unsubscribe(videoClient)
    imageWidth = naoImage[0]
    imageHeight = naoImage[1]
    array = naoImage[6]
    image_string = str(bytearray(array))
    im = Image.frombytes("RGB", (imageWidth, imageHeight), image_string)
    im.save(str(img_name)+".png", "PNG")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="150.65.205.196",
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")
    parser.add_argument("--name", type=str, default="Image",
                        help="Naoqi port number")

    args = parser.parse_args()
    session = qi.Session()
    try:
        session.connect("tcp://" + args.ip + ":" + str(args.port))
    except RuntimeError:
        print ("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) +".\n"
               "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)
    main(session, args.name)

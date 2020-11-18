#! /usr/bin/env python
# -*- encoding: UTF-8 -*-


import qi
import argparse
import sys
import numpy
import Image


def main(session):
    """
    This example uses the explore method.
    """
    # Get the services ALNavigation and ALMotion.
    navigation_service = session.service("ALNavigation")
    motion_service = session.service("ALMotion")

    # Wake up robot
    motion_service.wakeUp()

    # Input the radious of exploration area
    radius = 5

    error_code = navigation_service.explore(radius)
    if error_code != 0:
        print "Exploration failed."
    return
    

    # Start localization to navigate in map
    navigation_service.startLocalization()

    # Come back to initial position
    navigation_service.navigateToInMap([0., 0., 0.])

    # Stop localization
    navigation_service.stopLocalization()
    # Retrieve and display the map built by the robot



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="150.65.206.220",
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    args = parser.parse_args()
    session = qi.Session()
    try:
        session.connect("tcp://" + args.ip + ":" + str(args.port))
    except RuntimeError:
        print ("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) +".\n"
               "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)
    main(session)

# Action: Mapping Process 

1. run
  
   		$ roscore
  
2. To connect with Pepper, in new terminal, run
	
		$ roslaunch naoqi_driver naoqi_driver.launch nao_ip:= <IP Adress> network_interface:= <Network Interface>
    
  	In this step, we need to install “ naoqi_driver ” package from ROS by running
	
		$ sudo apt-get install ros-<ros distro>-naoqi-driver
	
3. Start map building,
	
   		$ roslaunch Navigations mapping.launch
    
4. Use Rviz to visualize the map building process.
    
   		$ rosrun rviz rviz
	
	4.1. Add display type![alt tag](https://i.imgur.com/QoB64Hi.png)and change the Topic (/map). We can rename the display type to Local Map

	4.2. Add display type![alt tag](https://i.imgur.com/QoB64Hi.png)and change the Topic (/map). We can rename the display type to Global Map

5. For exploration, we can explore by two ways
	
	5.1. Manual by run

		$ rosrun teleop_twist_keyboard teleop_twist_keyboard.py
	
	In this step, we need “teleop_twist_keyboard” package from ROS to control the 		           robot. Running
		
		$ sudo apt-get install ros-kinetic-teleop-twist-keyboard
	
  	
	5.2. Autonomous exploration, in this step, the code is modified from the exploration API from 		       [Aldebaran](http://doc.aldebaran.com/2-5/naoqi/motion/exploration-api.html#exploration-api) .
	
		$  rosrun Navigations Env_mapping.py

6. Save a map when your picture in Rviz is good enough. 
	
		$ rosrun map_server map_saver -f /<Your_map_directory>/<map_name>
	
	Example

		$ rosrun map_server map_saver -f /home/<user_name>/Navigations/Map/ pepper_map_inlabmap_3.yaml



# Action: Go To Location
    
1. run
  
   		$ roscore

2. To connect with Pepper, in new terminal, run
 
   		$ roslaunch naoqi_driver naoqi_driver.launch nao_ip:= <IP Adress> network_interface:= <Network Interface>
   
  	In this step, we need to install “naoqi_driver ” package from ROS

3. To navigate the robot to specific location, we run

		$ roslaunch Navigation Pepper_Nav.launch

	However, in Pepper_Nav.launch file, you should modify name and directory relate to where you save the map. For exmaple, 
    ```javascript
	<arg name="map"   default="$(find Navigations)/Map/pepper_map_inlabmap_3.yaml" />
	```
4. Use Rviz to visualize the navigation process.

   		$ rosrun rviz rviz

5. Assign destination
	
	5.1.  First help robot to estimate the initial location of the robot by using ![alt tag](https://i.imgur.com/HH1OVpd.png)

	5.2. Assign the destination by using ![alt tag](https://i.imgur.com/MnlgDyG.png)to select the location and direction of destination on the visual map in rviz.
	
	5.3. Assign the destination by giving the coordination and angle of destination. Run	
		
		$ rosrun Navigation goToLocation.py

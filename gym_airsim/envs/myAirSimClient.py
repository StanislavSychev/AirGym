import numpy as np
import time
import math
import cv2
from pylab import array, arange, uint8 
from PIL import Image
import eventlet
from eventlet import Timeout
import multiprocessing as mp
# Change the path below to point to the directoy where you installed the AirSim PythonClient
# sys.path.append('C:/Users/Kjell/Google Drive/MASTER-THESIS/AirSimpy')

from airsim import *

from airsim.types import *


class myAirSimClient(MultirotorClient):

    def __init__(self):        
        self.img1 = None
        self.img2 = None

        MultirotorClient.__init__(self)
        MultirotorClient.confirmConnection(self)
        self.enableApiControl(True)
        self.armDisarm(True)
    
        self.home_pos = self.simGetGroundTruthKinematics().position
    
        self.home_ori = self.simGetGroundTruthKinematics().orientation
        
        self.z = -6
    
    def straight(self, duration, speed):
        pitch, roll, yaw  = self.getPitchRollYaw()
        vx = math.cos(yaw) * speed
        vy = math.sin(yaw) * speed
        self.moveByVelocityZAsync(vx, vy, self.z, duration, DrivetrainType.ForwardOnly)
        start = time.time()
        return start, duration
    
    def yaw_right(self, duration):
        self.rotateByYawRateAsync(30, duration)
        start = time.time()
        return start, duration
    
    def yaw_left(self, duration):
        self.rotateByYawRateAsync(-30, duration)
        start = time.time()
        return start, duration
    
    
    def take_action(self, action):
		
        #check if copter is on level cause sometimes he goes up without a reason
        x = 0
        while self.simGetGroundTruthKinematics().position.z_val < -7.0:
            self.moveToZ(-6, 3)
            time.sleep(1)
            print(self.simGetGroundTruthKinematics().position.z_val, "and", x)
            x = x + 1
            if x > 10:
                return True        
        
    
        start = time.time()
        duration = 0 
        
        collided = False

        if action == 0:

            start, duration = self.straight(1, 4)
        
            while duration > time.time() - start:
                if self.simGetCollisionInfo().has_collided == True:
                    return True    
                
            self.moveByVelocityAsync(0, 0, 0, 1)
            self.rotateByYawRateAsync(0, 1)
            
            
        if action == 1:
         
            start, duration = self.yaw_right(0.8)
            
            while duration > time.time() - start:
                if self.simGetCollisionInfo().has_collided == True:
                    return True
            
            self.moveByVelocityAsync(0, 0, 0, 1)
            self.rotateByYawRateAsync(0, 1)
            
        if action == 2:
            
            start, duration = self.yaw_left(1)
            
            while duration > time.time() - start:
                if self.simGetCollisionInfo().has_collided == True:
                    return True
                
            self.moveByVelocityAsync(0, 0, 0, 1)
            self.rotateByYawRateAsync(0, 1)
            
        return collided

    @staticmethod
    def toEulerianAngle(q):
        z = q.z_val
        y = q.y_val
        x = q.x_val
        w = q.w_val
        ysqr = y * y

        # roll (x-axis rotation)
        t0 = +2.0 * (w * x + y * z)
        t1 = +1.0 - 2.0 * (x * x + ysqr)
        roll = math.atan2(t0, t1)

        # pitch (y-axis rotation)
        t2 = +2.0 * (w * y - z * x)
        if t2 > 1.0:
            t2 = 1
        if t2 < -1.0:
            t2 = -1.0
        pitch = math.asin(t2)

        # yaw (z-axis rotation)
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (ysqr + z * z)
        yaw = math.atan2(t3, t4)

        return pitch, roll, yaw

    def getPitchRollYaw(self):
        return self.toEulerianAngle(self.simGetGroundTruthKinematics().orientation)

    def goal_direction(self, goal, pos):
        
        pitch, roll, yaw = self.getPitchRollYaw()
        yaw = math.degrees(yaw) 
        
        pos_angle = math.atan2(goal[1] - pos.y_val, goal[0]- pos.x_val)
        pos_angle = math.degrees(pos_angle) % 360

        track = math.radians(pos_angle - yaw)  
        
        return ((math.degrees(track) - 180) % 360) - 180    
    
    
    def getScreenDepthVis(self, track):

        responses = self.simGetImages([ImageRequest(0, ImageType.DepthPerspective, True, False)])
        img1d = np.array(responses[0].image_data_float, dtype=np.float)
        img1d = 255/np.maximum(np.ones(img1d.size), img1d)
        img2d = np.reshape(img1d, (responses[0].height, responses[0].width))
        
        
        image = np.invert(np.array(Image.fromarray(img2d.astype(np.uint8), mode='L')))
        
        factor = 10
        maxIntensity = 255.0 # depends on dtype of image data
        
        # Decrease intensity such that dark pixels become much darker, bright pixels become slightly dark 
        newImage1 = (maxIntensity)*(image/maxIntensity)**factor
        newImage1 = array(newImage1,dtype=uint8)
        
        
        small = cv2.resize(newImage1, (0,0), fx=0.39, fy=0.38)
                
        cut = small[20:40,:]
        
        info_section = np.zeros((10,cut.shape[1]),dtype=np.uint8) + 255
        info_section[9,:] = 0
        
        line = np.int((((track - -180) * (100 - 0)) / (180 - -180)) + 0)
        
        if line != (0 or 100):
            info_section[:,line-1:line+2]  = 0
        elif line == 0:
            info_section[:,0:3]  = 0
        elif line == 100:
            info_section[:,info_section.shape[1]-3:info_section.shape[1]]  = 0
            
        total = np.concatenate((info_section, cut), axis=0)
            
        #cv2.imshow("Test", total)
        #cv2.waitKey(0)
        
        return total


    def AirSim_reset(self):
        
        self.reset()
        time.sleep(0.2)
        self.enableApiControl(True)
        self.armDisarm(True)
        time.sleep(1)
        self.moveToZAsync(self.z, 3)
        time.sleep(3)
        
    
    def AirSim_reset_old(self):
        
        reset = False
        z = -6.0
        while reset != True:

            now = self.simGetGroundTruthKinematics().position
            self.simSetPose(Pose(Vector3r(now.x_val, now.y_val, -30),Quaternionr(self.home_ori.w_val, self.home_ori.x_val, self.home_ori.y_val, self.home_ori.z_val)), True) 
            now = self.simGetGroundTruthKinematics().position
            
            if (now.z_val - (-30)) == 0:
                self.simSetPose(Pose(Vector3r(self.home_pos.x_val, self.home_pos.y_val, -30),Quaternionr(self.home_ori.w_val, self.home_ori.x_val, self.home_ori.y_val, self.home_ori.z_val)), True)
                now = self.simGetGroundTruthKinematics().position
                
                if (now.x_val - self.home_pos.x_val) == 0 and (now.y_val - self.home_pos.y_val) == 0 and (now.z_val - (-30)) == 0 :
                    self.simSetPose(Pose(Vector3r(self.home_pos.x_val, self.home_pos.y_val, self.home_pos.z_val),Quaternionr(self.home_ori.w_val, self.home_ori.x_val, self.home_ori.y_val, self.home_ori.z_val)), True)
                    now = self.simGetGroundTruthKinematics().position
                    
                    if (now.x_val - self.home_pos.x_val) == 0 and (now.y_val - self.home_pos.y_val) == 0 and (now.z_val - self.home_pos.z_val) == 0:
                        reset = True
                        self.moveByVelocity(0, 0, 0, 1)
                        time.sleep(1)
                        
        self.moveToZ(z, 3)  
        time.sleep(3)

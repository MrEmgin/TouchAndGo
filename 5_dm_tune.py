# Copyright (C) 2021 Denis Bakin a.k.a. MrEmgin
#
# This file is a part of TouchAndGo project for blind people.
# It was completed as an individual project in the 10th grade
#
# TouchAndGo is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# TouchAndGo is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with TouchAndGo tutorial.
# If not, see <http://www.gnu.org/licenses/>.
#
#          <><><> SPECIAL THANKS: <><><>
#
# Thanks for StereoPi tutorial https://github.com/realizator/stereopi-fisheye-robot
# for base concepts of stereovision in OpenCV


import cv2
import os
from matplotlib import pyplot as plt
from matplotlib.widgets import Slider, Button
import numpy as np
import json
import time
from camera_manager import *

# Global variables preset
imageToDisp = './scenes/01'
photo_width = 640
photo_height = 240


def get_left_path():
    return imageToDisp + 'L' + '.png'


def get_right_path():
    return imageToDisp + 'R' + '.png'


if not os.path.isfile(get_right_path()) or not os.path.isfile(get_left_path()):
    print('Can not read image from file \"' + get_left_path() + '\"')
    # No image! Let's take it...
    print("Taking photo...")
    man = CameraManager()
    frameL, frameR = man.get_stereo()
    cv2.imwrite(get_left_path(), frameL)
    cv2.imwrite(get_right_path(), frameR)
    print("Done!")
    man.stop()
print('Read images...')
imgLeft = cv2.imread(get_left_path())
imgRight = cv2.imread(get_right_path())
imgLeft = cv2.cvtColor(imgLeft, cv2.COLOR_BGR2GRAY)
imgRight = cv2.cvtColor(imgRight, cv2.COLOR_BGR2GRAY)

# Implementing calibration data
print('Read calibration data and rectifying stereo pair...')

try:
    npzfile = np.load('./calibration_data/{}p/stereo_camera_calibration.npz'.format(photo_height))
except:
    print(
        "Camera calibration data not found in cache, file " + './calibration_data/{}p/stereo_camera_calibration.npz'.format(
            photo_height))
    exit(0)

# imageSize = tuple(npzfile['imageSize'])
leftMapX = npzfile['leftMapX']
leftMapY = npzfile['leftMapY']
rightMapX = npzfile['rightMapX']
rightMapY = npzfile['rightMapY']

width_left, height_left = imgLeft.shape[:2]
width_right, height_right = imgRight.shape[:2]

if 0 in [width_left, height_left, width_right, height_right]:
    print("Error: Can't remap image.")

imgL = cv2.remap(imgLeft, leftMapX, leftMapY, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
imgR = cv2.remap(imgRight, rightMapX, rightMapY, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
# imgL = imgLeft
# imgR = imgRight
cv2.imshow('Left CALIBRATED', imgL)
cv2.imshow('Right CALIBRATED', imgR)
cv2.waitKey(0)
rectified_pair = (imgL, imgR)

loading_settings = 0
# Depth map function
SWS = 7
PFS = 7
PFC = 29
MDS = -3
NOD = 48
TTH = 13
UR = 3
SR = 14
SPWS = 2


def stereo_depth_map(rectified_pair):
    print('SWS=' + str(SWS) + ' PFS=' + str(PFS) + ' PFC=' + str(PFC) + ' MDS=' + \
          str(MDS) + ' NOD=' + str(NOD) + ' TTH=' + str(TTH))
    print(' UR=' + str(UR) + ' SR=' + str(SR) + ' SPWS=' + str(SPWS))
    c, r = rectified_pair[0].shape
    disparity = np.zeros((c, r), np.uint8)
    sbm = cv2.StereoBM_create(numDisparities=16, blockSize=15)
    # sbm.SADWindowSize = SWS
    sbm.setPreFilterType(1)
    sbm.setPreFilterSize(PFS)
    sbm.setPreFilterCap(PFC)
    sbm.setMinDisparity(MDS)
    sbm.setNumDisparities(NOD)
    sbm.setTextureThreshold(TTH)
    sbm.setUniquenessRatio(UR)
    sbm.setSpeckleRange(SR)
    sbm.setSpeckleWindowSize(SPWS)
    dmLeft = rectified_pair[0]
    dmRight = rectified_pair[1]
    # cv2.FindStereoCorrespondenceBM(dmLeft, dmRight, disparity, sbm)
    disparity = sbm.compute(dmLeft, dmRight)
    # disparity_visual = cv.CreateMat(c, r, cv.CV_8U)
    local_max = disparity.max()
    local_min = disparity.min()
    print("MAX " + str(local_max))
    print("MIN " + str(local_min))
    disparity_visual = (disparity - local_min) * (1.0 / (local_max - local_min))
    local_max = disparity_visual.max()
    local_min = disparity_visual.min()
    print("MAX " + str(local_max))
    print("MIN " + str(local_min))
    # cv.Normalize(disparity, disparity_visual, 0, 255, cv.CV_MINMAX)
    # disparity_visual = np.array(disparity_visual)
    return disparity_visual


# Set up and draw interface
# Draw left image and depth map
axcolor = 'lightgoldenrodyellow'
fig = plt.subplots(1, 2)
plt.subplots_adjust(left=0.15, bottom=0.5)
plt.subplot(1, 2, 1)
dmObject = plt.imshow(rectified_pair[0], 'gray')

saveax = plt.axes([0.3, 0.38, 0.15, 0.04])  # stepX stepY width height
buttons = Button(saveax, 'Save settings', color=axcolor, hovercolor='0.975')


def save_map_settings(event):
    buttons.label.set_text("Saving...")
    print('Saving to file...')
    result = json.dumps({'SADWindowSize': SWS, 'preFilterSize': PFS, 'preFilterCap': PFC, \
                         'minDisparity': MDS, 'numberOfDisparities': NOD, 'textureThreshold': TTH, \
                         'uniquenessRatio': UR, 'speckleRange': SR, 'speckleWindowSize': SPWS}, \
                        sort_keys=True, indent=4, separators=(',', ':'))
    fName = '3dmap_set.txt'
    f = open(str(fName), 'w')
    f.write(result)
    f.close()
    buttons.label.set_text("Save to file")
    print('Settings saved to file ' + fName)


buttons.on_clicked(save_map_settings)

loadax = plt.axes([0.5, 0.38, 0.15, 0.04])  # stepX stepY width height
buttonl = Button(loadax, 'Load settings', color=axcolor, hovercolor='0.975')


def load_map_settings(event):
    global SWS, PFS, PFC, MDS, NOD, TTH, UR, SR, SPWS, loading_settings
    loading_settings = 1
    fName = '3dmap_set.txt'
    print('Loading parameters from file...')
    buttonl.label.set_text("Loading...")
    f = open(fName, 'r')
    data = json.load(f)
    sSWS.set_val(data['SADWindowSize'])
    sPFS.set_val(data['preFilterSize'])
    sPFC.set_val(data['preFilterCap'])
    sMDS.set_val(data['minDisparity'])
    sNOD.set_val(data['numberOfDisparities'])
    sTTH.set_val(data['textureThreshold'])
    sUR.set_val(data['uniquenessRatio'])
    sSR.set_val(data['speckleRange'])
    sSPWS.set_val(data['speckleWindowSize'])
    f.close()
    buttonl.label.set_text("Load settings")
    print('Parameters loaded from file ' + fName)
    print('Redrawing depth map with loaded parameters...')
    loading_settings = 0
    update(0)
    print('Done!')


buttonl.on_clicked(load_map_settings)

# Building Depth Map for the first time
disparity = stereo_depth_map(rectified_pair)

plt.subplot(1, 2, 2)
dmObject = plt.imshow(disparity, aspect='equal', cmap='jet')

# Draw interface for adjusting parameters
print('Start interface creation (it takes up to 30 seconds)...')

SWSaxe = plt.axes([0.15, 0.01, 0.7, 0.025], facecolor=axcolor)  # stepX stepY width height
PFSaxe = plt.axes([0.15, 0.05, 0.7, 0.025], facecolor=axcolor)  # stepX stepY width height
PFCaxe = plt.axes([0.15, 0.09, 0.7, 0.025], facecolor=axcolor)  # stepX stepY width height
MDSaxe = plt.axes([0.15, 0.13, 0.7, 0.025], facecolor=axcolor)  # stepX stepY width height
NODaxe = plt.axes([0.15, 0.17, 0.7, 0.025], facecolor=axcolor)  # stepX stepY width height
TTHaxe = plt.axes([0.15, 0.21, 0.7, 0.025], facecolor=axcolor)  # stepX stepY width height
URaxe = plt.axes([0.15, 0.25, 0.7, 0.025], facecolor=axcolor)  # stepX stepY width height
SRaxe = plt.axes([0.15, 0.29, 0.7, 0.025], facecolor=axcolor)  # stepX stepY width height
SPWSaxe = plt.axes([0.15, 0.33, 0.7, 0.025], facecolor=axcolor)  # stepX stepY width height

sSWS = Slider(SWSaxe, 'SWS', 5.0, 255.0, valinit=5)
sPFS = Slider(PFSaxe, 'PFS', 5.0, 255.0, valinit=5)
sPFC = Slider(PFCaxe, 'PreFiltCap', 5.0, 63.0, valinit=29)
sMDS = Slider(MDSaxe, 'MinDISP', -100.0, 100.0, valinit=-25)
sNOD = Slider(NODaxe, 'NumOfDisp', 16.0, 256.0, valinit=128)
sTTH = Slider(TTHaxe, 'TxtrThrshld', 0.0, 1000.0, valinit=100)
sUR = Slider(URaxe, 'UnicRatio', 1.0, 20.0, valinit=10)
sSR = Slider(SRaxe, 'SpcklRng', 0.0, 40.0, valinit=15)
sSPWS = Slider(SPWSaxe, 'SpklWinSze', 0.0, 300.0, valinit=100)


# Update depth map parameters and redraw
def update(val):
    global SWS, PFS, PFC, MDS, NOD, TTH, UR, SR, SPWS
    SWS = int(sSWS.val / 2) * 2 + 1  # convert to ODD
    PFS = int(sPFS.val / 2) * 2 + 1
    PFC = int(sPFC.val / 2) * 2 + 1
    MDS = int(sMDS.val)
    NOD = int(sNOD.val / 16) * 16
    TTH = int(sTTH.val)
    UR = int(sUR.val)
    SR = int(sSR.val)
    SPWS = int(sSPWS.val)
    if (loading_settings == 0):
        print('Rebuilding depth map')
        disparity = stereo_depth_map(rectified_pair)
        dmObject.set_data(disparity)
        print('Redraw depth map')
        plt.draw()


# Connect update actions to control elements
sSWS.on_changed(update)
sPFS.on_changed(update)
sPFC.on_changed(update)
sMDS.on_changed(update)
sNOD.on_changed(update)
sTTH.on_changed(update)
sUR.on_changed(update)
sSR.on_changed(update)
sSPWS.on_changed(update)

print('Show interface to user')
plt.show()

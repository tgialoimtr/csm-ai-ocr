'''
Created on Oct 3, 2017

@author: loitg
'''

from pylab import *
from common import ASHOW, args, DSHOW, summarize
from ocrolib import psegutils,morph,sl
from scipy.ndimage.filters import gaussian_filter,uniform_filter,maximum_filter, minimum_filter
import ocrolib
import cv2


def removedot2(imgbin, objects, scale):
    temp = minimum_filter(imgbin, (3,1))
    temp = maximum_filter(temp, (3,1))
    temp = imgbin - temp
    for o in objects:
#         h = sl.dim0(o)
#         w = sl.dim1(o)
#         tempbox = binary[o]
#         ave = mean(tempbox)
#         ratio = float(h)/w if h > w else float(w)/h
#         if ratio > 4: continue
        if (sl.area(o) > scale*scale/4) and (sl.area(o) < scale*scale*4):
            temp[o] = 0   
    ASHOW('houghlines3.jpg',temp,scale=2.0, waitKey=True)
    
    
    return imgbin


def removedot(imgbin, smalldot, scale):   
#     ellipsis_map = zeros(imgbin.shape,dtype=uint8)
    horizental = maximum_filter(smalldot, (1,scale))
    horizental = minimum_filter(horizental, (1,scale))
    horizental = minimum_filter(horizental, (1,scale*3))
    horizental = maximum_filter(horizental, (1,scale*3))    
    
    linemap = horizental
    linemap = maximum_filter(linemap, (3,3))  
#     ASHOW('linemap', linemap)
#     ASHOW('smalldot', smalldot)
    rs = cv2.cvtColor(smalldot*255, cv2.COLOR_GRAY2BGR)
    
#     lines = cv2.HoughLinesP(smalldot,2,np.pi/90,20,minLineLength=imgbin.shape[1]/2,maxLineGap=imgbin.shape[1]/2)
#     if lines is not None: 
#         for line in lines:
#             x1,y1,x2,y2 = line[0]
#             if abs(x1-x2) < 2*scale or abs(y1-y2) < 2*scale:
#                 cv2.line(ellipsis_map,(x1,y1),(x2,y2),(1,1,1),6)
#                 cv2.line(rs,(x1,y1),(x2,y2),(0,0,255),1)

    ellipsis_map = cv2.bitwise_and(smalldot, smalldot, mask=linemap)
    return cv2.subtract(imgbin, ellipsis_map)
    
#     ASHOW('houghlines3.jpg',rs,scale=2.0, waitKey=True)
#     lines = cv2.HoughLines(boxmap,2,np.pi/90,150)
#     print lines.shape
#     for line in lines:
#         rho,theta = line[0]
#         a = np.cos(theta)
#         b = np.sin(theta)
#         x0 = a*rho
#         y0 = b*rho
#         x1 = int(x0 + 1000*(-b))
#         y1 = int(y0 + 1000*(a))
#         x2 = int(x0 - 1000*(-b))
#         y2 = int(y0 - 1000*(a))
#         cv2.line(rs,(x1,y1),(x2,y2),(0,0,255),2)
    
    
    return imgbin

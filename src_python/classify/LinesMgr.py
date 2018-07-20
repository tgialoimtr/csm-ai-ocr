# -*- coding: utf-8 -*-
'''
Created on Oct 3, 2017

@author: loitg
'''

from common import args, summarize, ASHOW, DSHOW, GST1, UNI_STR
import cv2
from numpy.ctypeslib import ndpointer
from pylab import *
from scipy.ndimage import filters,interpolation,morphology,measurements, uniform_filter1d, maximum_filter1d, minimum_filter1d
from scipy.ndimage.filters import gaussian_filter,uniform_filter,maximum_filter, minimum_filter
from scipy import stats
import multiprocessing
import ocrolib
from time import time
from fuzzywuzzy import fuzz
import string
import copy,re

from ocrolib import psegutils,morph,sl
from ocrolib.toplevel import *

from PIL import Image
import pytesseract
from common import summarize
import lineest


def pre_check_line(line):
    project = mean(1-line, axis=0)
    project = uniform_filter1d(project, line.shape[0]/3)
    m = mean(project)
    if (m > 0.13) & (1.0*line.shape[1]/line.shape[0] > 1.7):
        return True
    else:
        return False
    
def compute_boxmap(binary,scale,oriimg,threshold=(.5,4),dtype='i'):
    labels,n = morph.label(binary)
    objects = morph.find_objects(labels)
    boxmap = zeros(binary.shape,dtype)
    for i,o in enumerate(objects):
        h = sl.dim0(o)
        w = sl.dim1(o)
        ratio = float(h)/w if h > w else float(w)/h
        if h > 2*scale or h < scale/3:
            continue
        if ratio > 8: continue
#         if sl.area(o)**.5<threshold[0]*scale: continue
#         if sl.area(o)**.5>threshold[1]*scale: continue

        boxmap[o] = 1
    return boxmap

def compute_gradmaps(binary,scale):
    # use gradient filtering to find baselines
    binaryary = morph.r_opening(binary.astype(bool), (1,1))# CMND
    boxmap = compute_boxmap(binaryary,scale,binary)
    cleaned = boxmap*binaryary
    if args.usegauss:
        # this uses Gaussians
        grad = gaussian_filter(1.0*cleaned,(args.vscale*0.3*scale,
                                            args.hscale*6*scale),order=(1,0))
    else:
        # this uses non-Gaussian oriented filters
        grad = gaussian_filter(1.0*cleaned,(max(4,args.vscale*0.3*scale),
                                            args.hscale*1.0*scale),order=(1,0))
        grad = uniform_filter(grad,(args.vscale,args.hscale*1*scale)) # CMND
    bottom = ocrolib.norm_max((grad<0)*(-grad))
#     bottom = minimum_filter(bottom,(2,6*scale))
    top = ocrolib.norm_max((grad>0)*grad)
#     top = minimum_filter(top,(2,6*scale))
    return bottom,top,boxmap

def compute_line_seeds(binaryary,bottom,top,scale):
    """Base on gradient maps, computes candidates for baselines
    and xheights.  Then, it marks the regions between the two
    as a line seed."""
    t = args.threshold
    vrange = int(args.vscale*scale)
    bmarked = maximum_filter(bottom==maximum_filter(bottom,(vrange,0)),(2,2))
    bmarked = bmarked*(bottom>t*amax(bottom)*t)
    tmarked = maximum_filter(top==maximum_filter(top,(vrange,0)),(2,2))
    tmarked = tmarked*(top>t*amax(top)*t/2)
    tmarked = maximum_filter(tmarked,(1,20))
    seeds = zeros(binaryary.shape,'i')
    delta = max(3,int(scale/2))
    for x in range(bmarked.shape[1]):
        transitions = sorted([(y,1) for y in find(bmarked[:,x])]+[(y,0) for y in find(tmarked[:,x])])[::-1]
        transitions += [(0,0)]
        for l in range(len(transitions)-1):
            y0,s0 = transitions[l]
            if s0==0: continue
            seeds[y0-delta:y0,x] = 1
            y1,s1 = transitions[l+1]
            if s1==0 and (y0-y1)<5*scale: seeds[y1:y0,x] = 1
    seeds = maximum_filter(seeds,(1,int(1+scale)))
#     DSHOW("lineseeds",[0.4*seeds,0.3*tmarked+0.7*bmarked,binaryary])
    return seeds

@checks(SEGMENTATION)
def spread_labels(labels,maxdist=9999999):
    """Spread the given labels to the background"""
    distances,features = morphology.distance_transform_edt(labels==0,sampling=[1,1], return_distances=1,return_indices=1) #CMND
    indexes = features[0]*labels.shape[1]+features[1]
    spread = labels.ravel()[indexes.ravel()].reshape(*labels.shape)
    spread *= (distances<maxdist)
    return spread


class LinesMgr(object):

    def __init__(self, binpage, originalpage):
        self.originalpage = originalpage
        self.binpage = binpage
        self.lines = []
    def replaceString(self, s):
        return s.replace('.','').replace(u'²','2').replace(u'º','o').replace(u'»','-').replace(u'—',':').replace(UNI_STR,':194').replace(u'iên', GST1)
        
    def replaceCommonError(self):
        rs = []
        for line in self.lines:
            if len(line.text1) < 4 and len(line.text2) < 4: continue
            temp = copy.copy(line)
            temp.text1 = self.replaceString(line.text1)
            temp.text2 = self.replaceString(line.text2)
            rs.append(temp)
        return rs
            
            
    def findString(self,key, scale, mode):
        lines = self.replaceCommonError()
        for line in lines:
            if len(line.text1) < len(key) and len(line.text2) < len(key): continue
            sim = fuzz.partial_ratio(line.text1, key)
            temp = fuzz.partial_ratio(line.text2, key)
            if temp > sim: sim = temp
#             print key,sim,line.text1,line.text2
            if (mode == 'cu' and sim > 50) or (mode == 'moi' and sim > 70):
                linemap = []
                for j, insertedline in enumerate(lines):
                    if insertedline == line: continue
                    if mode == 'cu':
                        dist = insertedline.bounds[1].start - line.bounds[1].stop
                        if dist > -8*scale and dist < 8*scale:
                            value = abs(line.bounds[0].stop - insertedline.bounds[0].stop)
                            if value < 3*scale:
                                linemap.append((value, insertedline))
                    elif mode == 'moi':
                        dist = insertedline.bounds[1].start - line.bounds[1].stop
                        value = insertedline.bounds[0].stop - line.bounds[0].stop
                        if dist > -3*scale and dist < 3*scale and value + scale > 0 and value < 2*scale:
                            linemap.append((value, insertedline))
                print key + ': '
                if (':' in line.text2) and (line.text2.rfind(':') > 0) and (line.text2.rfind(':') + 3 < len(line.text2)):
                    print '---' + line.text2[line.text2.rfind(':')+1:]             
                elif len(linemap) > 0:
                    _, rs = min(linemap)
#                     print '---' + rs.text1
                    print '---' + rs.text2
                return          
    
    def extract(self, scale, mode):
        if mode == 'cu':
            ten = u'Ho ten'
            dob = u'Sinh ngay'
            que = u'Nguyên quan'
            rs = self.findString(ten, scale, mode)
            rs = self.findString(dob, scale, mode)
            rs = self.findString(que, scale, mode)
        elif mode == 'moi':
            ten = u'Ho va ten khai sinh'
            dob = u'Ngay, thang, nam sinh'
            gioitinh = u'Gioi tinh'
            dt = u'Dan toc'
            rs = self.findString(ten, scale, mode)
            rs = self.findString(dob, scale, mode)
            rs = self.findString(gioitinh, scale, mode)
            rs = self.findString(dt, scale, mode)
            lines = self.replaceCommonError()
            pid = re.compile('([O\dIl]{10,12})')
            print 'ID: '
            for line in lines:
                m2 = pid.search(line.text2)
                if m2:
                    print '---' + m2.group(1)
    
    
    def calc(self, objects, scale):      
        if self.binpage is None:
            return
        tt=time()

        bottom,top,boxmap = compute_gradmaps(self.binpage,scale)
#         DSHOW('hihi', [0.5*bottom+0.5*top,self.binpage, boxmap])
        seeds0 = compute_line_seeds(self.binpage,bottom,top,scale)
        seeds,_ = morph.label(seeds0)

        llabels = morph.propagate_labels(boxmap,seeds,conflict=0)
        spread = spread_labels(seeds,maxdist=scale)
        llabels = where(llabels>0,llabels,spread*self.binpage)
        segmentation = llabels*self.binpage     
        self.binpage = ocrolib.remove_noise(self.binpage,args.noise)
        lines = psegutils.compute_lines(segmentation,scale)
        binpage_reversed = 1 - self.binpage
#         print 'pre line ', time() - tt
        tt=time()
        self.lines = []
        for i,l in enumerate(lines):
            tt = time()            
            binline = psegutils.extract_masked(binpage_reversed,l,pad=args.pad,expand=args.expand) # black text
            binline = (1-binline)
            le = lineest.CenterNormalizer(binline.shape[0]) # white text
            binline = binline.astype(float)
            le.measure(binline)
            binline = le.normalize(binline)
            binline = where(binline > 0.5, 0, 1) # black text
#             print 'line time ', time()-tt
            
            print '-----------------------'
            pilimg = Image.fromarray((binline*255).astype(uint8))
            pred_legacy = pytesseract.image_to_string(pilimg,lang='eng', config='--oem 0 --psm 7')
            print '00', pred_legacy
            pred_lstm = pytesseract.image_to_string(pilimg,lang='eng', config='--oem 1 --psm 7')
            print '11', pred_lstm
#             ASHOW('line',binline, scale=2.0)
##             pred_both = pytesseract.image_to_string(pilimg,lang='vie', config='--oem 2 --psm 7')
##             print '22', pred_both
            result = psegutils.record(bounds = l.bounds, text1=pred_legacy, text2=pred_lstm, img = binline)
            self.lines.append(result)


#             cv2.rectangle(self.originalpage, (l.bounds[1].start,l.bounds[0].start), (l.bounds[1].stop,l.bounds[0].stop), (0,0,0), 2)
#             print binpage_reversed.shape
#             cv2.rectangle(self.originalpage,(50,50),(300,300), 0, 2)
            
#         ASHOW('lines', self.originalpage)
        
        
        
        
        
        
        
        
        
        
        
        
        

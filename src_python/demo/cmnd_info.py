# -*- coding: utf-8 -*-
'''
Created on Nov 2, 2017

@author: loitg
'''
import Image
import pytesseract
import cv2,os
from classify.common import sauvola, sharpen, simplefirstAnalyse, ASHOW, summarize
from classify.removedot import removedot
from classify.LinesMgr import compute_gradmaps, spread_labels, compute_line_seeds
from classify import lineest
from ocrolib import psegutils,morph
import ocrolib
from numpy import where, linspace, uint8, ones, array

# Compare location of main template and name template to see if they are at same location
def validateTextRegion(img, ((startX, startY), (endX, endY)), ((startXName, startYName), (endXName, endYName))):
    ratio1 = abs(startXName - startX)/float(endX - startX)
    ratio2 = abs(startYName - startY)/float(endY - startY)
    if ratio1 < 0.05 and ratio2 < 0.05:
        return True
    else:
        return False

# Compare location of main template and NoiThuongTru template to see if NoiThuongTru near side of main 
def validateNTTRegion(img, ((startX, startY), (endX, endY)), ((startXName, startYName), (endXName, endYName))):
    ratio1 = abs(startXName - startX)/float(endX - startX)
    ratio2 = abs(startYName - startY)/float(endY - startY)
    if ratio1 < 0.05 and ratio2 > 0.75 and ratio2 < 0.85:
        return True
    else:
        return False
    
class CMND(object):
    def __init__(self, name, templatepath, maskpath, tmpnamepath):
        self.name = name
        if self.name == 'Can Cuoc Cong Dan': 
            self.noithuongtru = cv2.imread(os.path.dirname(templatepath) + '/noithuongtru_tmp.tif', 0)
            self.noithuongtru = sauvola(self.noithuongtru,w=self.noithuongtru.shape[0])*255
        # main template # cmnd_tmp.tiff
        self.template = cv2.imread(templatepath, 0)
        # Estimate scale of characters
        self.scale = self.template.shape[1]/24.5/0.65
        # Binarize main template
        self.template = sauvola(self.template, w=2*self.scale, scaledown=0.4)*255
        # template of name # cmnd_tmpname.tiff
        self.tmpname = cv2.imread(tmpnamepath, 0)
        self.tmpname = sauvola(self.tmpname,w=self.tmpname.shape[0], scaledown=0.4)*255
        # mask text from main template
        self.mask = cv2.imread(maskpath, 0)
        _, self.mask = cv2.threshold(self.mask, 127, 255, cv2.THRESH_BINARY)
        self.mask_inv = cv2.bitwise_not(self.mask)
        
    def addLineDesc(self, linepos):
        self.linepos = linepos
        
    def findTextRegion(self, img):
        (h, w) = img.shape[:2]
        # gray image
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  
        # binarized image
        img0 = sauvola(img_gray, k=0.2, w=2*self.scale, scaledown=0.4)*255
        # Initialize variable    
        found = None
        foundname = None
        foundNTT = None
        (tH, tW) = self.template.shape[:2]
        (tHname, tWname) = self.tmpname.shape[:2]
        if self.name == 'Can Cuoc Cong Dan': (tHNTT, tWNTT) = self.noithuongtru.shape[:2]
        # translate gray image left and up (move text to center)
        translated = ones(array(img0.shape), dtype=uint8)*255
        padx = w/8; pady = h/8
        translated[:-pady, :-padx] = img_gray[pady:,padx:]
        img_gray = translated
        # translate binarized image left and up (move text to center)
        translated = ones(array(img0.shape), dtype=uint8)*255
        padx = w/8; pady = h/8
        translated[:-pady, :-padx] = img0[pady:,padx:]
        img0 = translated
        
        # Resize image with different scale to see at which scale the image match template most
        scalemax = tW/0.55/w
        scalemin = tW/0.8/w
        for scale in linspace(scalemin, scalemax, 30):
            resized = cv2.resize(img0, None,fx=scale,fy=scale)
            r = w / float(resized.shape[1])
            # if after resize is smaller than template, just ignore this resize
            if resized.shape[0] < tH or resized.shape[1] < tW or resized.shape[0] < tHname or resized.shape[1] < tWname:
                continue        
            # match main template
            result = cv2.matchTemplate(resized, self.template, method=cv2.TM_SQDIFF , mask = self.mask)
            (minVal,maxVal, minLoc,maxLoc) = cv2.minMaxLoc(result)
            if found is None or minVal < found[0]:
                found = (minVal, minLoc, r)
            # match template of name
            resultname = cv2.matchTemplate(resized, self.tmpname, method=cv2.TM_SQDIFF_NORMED)
            (minVal,maxVal, minLoc,maxLoc) = cv2.minMaxLoc(resultname)    
            if foundname is None or minVal < foundname[0]:
                foundname = (minVal, minLoc, r)
            # match template of "Noi Thuong Tru" (only for Can Cuoc)
            if self.name == 'Can Cuoc Cong Dan':
                resultNTT = cv2.matchTemplate(resized, self.noithuongtru, method=cv2.TM_SQDIFF_NORMED)
                (minVal,maxVal, minLoc,maxLoc) = cv2.minMaxLoc(resultNTT)  
                if foundNTT is None or minVal < foundNTT[0]:
                    foundNTT = (minVal, minLoc, r)   
        
        # extract matched region in the image, note that size is different from the template because image is at different scale             
        def extract(foundResult, relative_x, relative_y, temp_width, temp_height):
            region_x = foundResult[1][0] + relative_x
            region_y = foundResult[1][1] + relative_y
            (startX, startY) = (int(region_x  * foundResult[2]), int(region_y * foundResult[2]))
            (endX, endY) = (int((region_x + temp_width) * foundResult[2]), int((region_y + temp_height) * foundResult[2]))
            if startX > w or endX > w or startY > h or endY > h:
                return None
            return ((startX, startY), (endX, endY))
        dimention = extract(found, 0,0,tW,tH)
        dimentionname = extract(foundname, 0,0,tWname,tHname)
        
        if dimention is None or dimentionname is None:
            return False,0
        if self.name == 'Can Cuoc Cong Dan':
            dimentionNTT = extract(foundNTT, 0,0,tWNTT,tHNTT)
            if dimentionNTT is None:
                return False,0

        if validateTextRegion(img0, dimention, dimentionname):
            (startX, startY), (endX, endY) = dimention
            self.dimention = dimention
            mask = cv2.resize(self.mask_inv, ((endX - startX), (endY - startY)), None)

            if self.name == 'Can Cuoc Cong Dan':
                if validateNTTRegion(img0, dimention, dimentionNTT):
                    x0 = startX; y0=startY
                    (startXNTT, startYNTT), (endXNTT, endYNTT) = dimentionNTT
                    mask[startYNTT-y0:endYNTT-y0, startXNTT-x0:endXNTT-x0] = uint8(0)
            
            # prepare line position for printResult to extract line
            self.linepos1 = {}
            for k in self.linepos:
                self.linepos1[k] = (found[2]*self.linepos[k][0],found[2]*self.linepos[k][1])
            # prepare mask for printResult to extract line
            _, self.patch_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
            # prepare patch for printResult to extract line
            self.patch = img_gray[startY:endY, startX:endX]
            return True, foundname[0]
        else:
            return False,0
    
    
    # Extract lines from self.patch, then tesseract these lines
    def printResult(self, outputfile):
        # Some pre-process
#         print 'text area before'
#         cv2.imshow('patch', self.patch)
#         cv2.waitKey(-1)
        patch = sharpen(self.patch)
        binary = sauvola(patch, w=int(self.template.shape[1]/24.5*2), k=0.33, scaledown=0.5, reverse=True)
        binary = cv2.bitwise_and(binary, binary, mask=self.patch_mask)
#         print 'text area after'
#         cv2.imshow('patch', binary*255)
#         cv2.waitKey(-1)
        dotremoved = binary
        scale = self.scale
        # Line extraction copied  from Ocropus source code
        bottom,top,boxmap = compute_gradmaps(dotremoved,scale)
        seeds0 = compute_line_seeds(dotremoved,bottom,top,scale)
        seeds,_ = morph.label(seeds0)

        llabels = morph.propagate_labels(boxmap,seeds,conflict=0)
        spread = spread_labels(seeds,maxdist=scale)
        llabels = where(llabels>0,llabels,spread*dotremoved)
        segmentation = llabels*dotremoved
        dotremoved = ocrolib.remove_noise(dotremoved, 8)
        lines = psegutils.compute_lines(segmentation,scale/2)
        binpage_reversed = 1 - dotremoved
        
        self.lines = []
        outputfile.write('-----------' + self.name + '------------'  + '\n')
        for i,l in enumerate(lines):
            # Line extraction copied from Ocropus source code
            binline = psegutils.extract_masked(binpage_reversed,l,pad=int(scale/2),expand=0) # black text
            binline = (1-binline)
            le = lineest.CenterNormalizer(binline.shape[0]) # white text
            binline = binline.astype(float)
            le.measure(binline)
            binline = le.normalize(binline)
#             print 'normalized'
#             cv2.imshow('line', binline)
#             cv2.waitKey(-1)
            binline = cv2.resize(binline, None, fx=2.0, fy=2.0)
#             print 'resized'
#             cv2.imshow('line', binline)
#             cv2.waitKey(-1)
            binline = where(binline > 0.5, uint8(0), uint8(255)) # black text
#             print 'black text'
#             cv2.imshow('line', binline)            
#             cv2.waitKey(-1)
            pilimg = Image.fromarray(binline)
            pos = l.bounds[0].stop
            # Prediction using Tesseract 4.0
            if pos > self.linepos1['id'][0] and pos < self.linepos1['id'][1]: #ID, all numbers
                pred = pytesseract.image_to_string(pilimg,lang='eng', config='--oem 0 --psm 7 -c tessedit_char_whitelist=0123456789')
            elif pos > self.linepos1['dob'][0] and pos < self.linepos1['dob'][1]: # DOB, number, - , /
                pred = pytesseract.image_to_string(pilimg,lang='eng', config='--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789-/')
            else:
                pred = pytesseract.image_to_string(pilimg,lang='vie', config='--oem 1 --psm 7')
            print pred
            pred = pred.replace(u'²','2').replace(u'º','o').replace(u'»','-')
            outputfile.write(pred + '\n')
        
        
        
        
        
        
        
        
        
        
        
        
        
        
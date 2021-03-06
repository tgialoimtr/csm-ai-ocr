'''
Created on Dec 12, 2017

@author: loitg
'''
import cv2
import sys
import numpy as np
from classify.common import sauvola, sharpen
from time import time
from posix import ttyname
from text import MRZ
from textutils import getFullDate, getGender, getNation, ocr
from scipy.ndimage.filters import maximum_filter, minimum_filter
import json
        
class passport(object):
    def __init__(self):
        self.roi = None
        self.name = 'Passport'

    def findTextRegion(self, img):
        (h0,w0,d0) = img.shape
        padw = int(w0/12)
        padh = int(h0/12)
        image = np.ones(np.array((h0+2*padh,w0+2*padw,d0)), dtype=np.uint8)*255
        image[padh:-padh, padw:-padw, :] = img[:,:,:]
        rectKernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        sqKernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         print 'height ', image.shape[1]
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, rectKernel)
#         print 'blackhat'
#         cv2.imshow('hihi', blackhat)
#         cv2.waitKey(-1)
        # compute the Scharr gradient of the blackhat image and scale the
        # result into the range [0, 255]
        gradX = cv2.Sobel(blackhat, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
        gradX = np.absolute(gradX)
#         print 'gradx'
#         cv2.imshow('hihi', gradX)
#         cv2.waitKey(-1)
        (minVal, maxVal) = (np.min(gradX), np.max(gradX))
        gradX = (255 * ((gradX - minVal) / (maxVal - minVal))).astype("uint8")
#         print 'gradx norm'
#         cv2.imshow('hihi', gradX)
#         cv2.waitKey(-1)
        # apply a closing operation using the rectangular kernel to close
        # gaps in between letters -- then apply Otsu's thresholding method
        gradX = cv2.morphologyEx(gradX, cv2.MORPH_CLOSE, rectKernel)
#         print 'gradx morph'
#         cv2.imshow('hihi', gradX)
#         cv2.waitKey(-1)
        thresh = cv2.threshold(gradX, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
#         print 'thresh 1'
#         cv2.imshow('hihi', thresh)
#         cv2.waitKey(-1)
        # perform another closing operation, this time using the square
        # kernel to close gaps between lines of the MRZ, then perform a
        # series of erosions to break apart connected components
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, sqKernel)
        thresh = cv2.erode(thresh, None, iterations=4)
        # during thresholding, it's possible that border pixels were
        # included in the thresholding, so let's set 5% of the left and
        # right borders to zero
#         print 'thresh 2'
#         cv2.imshow('hihi', thresh)
#         cv2.waitKey(-1)
        
        p = int(image.shape[1] * 0.05)
        thresh[:, 0:p] = 0
        thresh[:, image.shape[1] - p:] = 0
        thresh = minimum_filter(thresh, (10,10))
        thresh = maximum_filter(thresh, (10,10))
#         cv2.imshow('hihi', thresh)
#         cv2.waitKey(-1)
        
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
     
        # loop over the contours
        for c in cnts:
            # compute the bounding box of the contour and use the contour to
            # compute the aspect ratio and coverage ratio of the bounding box
            # width to the width of the image
            (x, y, w, h) = cv2.boundingRect(c)
            ar = w / float(h)
            crWidth = w / float(gray.shape[1])
     
            # check to see if the aspect ratio and coverage width are within
            # acceptable criteria
            if ar > 10 and ar < 17  and crWidth > 0.65:
                # pad the bounding box since we applied erosions and now need
                # to re-grow it
                pX = int((x + w) * 0.03)
                pY = int((y + h) * 0.03)
                (x, y) = (x - pX, y - pY)
                (w, h) = (w + (pX * 2), h + (pY * 2))
     
                # extract the ROI from the image and draw a bounding box
                # surrounding the MRZ
                self.roi = image[y:y + h, x:x + w].copy()
#                 print ar
#                 cv2.imshow("ROI", self.roi)
#                 cv2.waitKey(-1)
#                 cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                return True, 0
            
        return False,0
        
        
        
    def printResult(self, outputfile):
        if self.roi is None:
            return
        gray = cv2.resize(self.roi, None, fx=2.0, fy=2.0)
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
        gray = sharpen(gray)
        gray = sauvola(gray, scaledown = 0.3, w=gray.shape[0]/3.0)*255
        
#         cv2.imshow('hihi', gray)
        
        pred = ocr(gray, "--psm 6 --oem 0 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789>< -c load_system_dawg=F -c load_freq_dawg=F")
#         print pred
#         cv2.waitKey(-1)
        rs = MRZ.from_ocr(pred)
        rs = rs.to_dict()
        
#         pred = '-----------Passport------------\n'
#         if 'names' in rs: pred += 'Given Name: ' + rs['names'] + '\n'
#         if 'surname' in rs: pred += 'Family Name: ' + rs['surname'] + '\n'
#         if 'nationality' in rs: pred += 'Nationality: ' + rs['nationality'] + ' - ' + getNation(rs['nationality']) + '\n'
#         if 'date_of_birth' in rs: pred += 'Date of Birth: ' + getFullDate(rs['date_of_birth']) + ' (validity: ' + str(rs['valid_date_of_birth']) + ')\n'
#         if 'sex' in rs: pred += 'Gender: ' + getGender(rs['sex'])+ '\n'
#         if 'country' in rs: pred += 'Issuing Country: ' + rs['country'] + ' - ' + getNation(rs['country']) + '\n'
#         if 'number' in rs: pred += 'Number: ' + rs['number'] + ' (validity: ' + str(rs['valid_number']) + ')\n'
#         if 'expiration_date' in rs: pred += 'Expiration Date: ' + getFullDate(rs['expiration_date']) + ' (validity: ' + str(rs['valid_expiration_date']) + ')\n'

        readrs = {}
        readrs['type'] = 'Passport'
        readrs['idNumber'] = rs['number'].replace('<','')
        readrs['dateOfBirth'] = getFullDate(rs['date_of_birth']) if rs['valid_date_of_birth'] else None
        readrs['Gender'] = getGender(rs['sex'])
        readrs['Dantoc'] = getNation(rs['nationality'])
        readrs['NguyenQuan'] = getNation(rs['country'])
        readrs['fullName'] = rs['surname'] + ' ' + rs['names']
        readrs['NgayHetHan'] = getFullDate(rs['expiration_date']) if rs['valid_expiration_date'] else None

        outputfile.write(json.dumps(readrs))
    
    
    

if __name__ == '__main__':
    p = passport()
    img = cv2.imread('/home/loitg/Downloads/cmnd_data/passport/thuha.jpg')
#     (w,h) =img.shape[1],img.shape[0]
#     rotM = cv2.getRotationMatrix2D((w/2,h/2),5,1)
#     img = cv2.warpAffine(img,rotM,(w,h))
    rr= 600.0/img.shape[1]
    img = cv2.resize(img, None, fx=rr, fy=rr)
    
    isCard, conf = p.findTextRegion(img)
    if isCard:
        p.printResult(sys.stdout)
    else:
        print 'No card found'
    
    
    
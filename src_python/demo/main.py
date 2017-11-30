'''
Created on Oct 31, 2017

@author: loitg
'''
import os, sys
# Config PYTHONPATH and template folder relatively according to current file location
project_dir = os.path.dirname(__file__) + '/../'
template_path = project_dir + '/template/'
sys.path.insert(0, project_dir)

import cv2
import datetime, time
from cmnd_info import CMND
from classify.common import estimate_skew_angle
from numpy import linspace
import codecs


# Calculate blurness of image using Laplacian operator
def calcBlur(img):
    if len(img.shape) > 1:
        temp = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        temp = img
    return cv2.Laplacian(temp, cv2.CV_64F).var()


if __name__ == '__main__':

    cmnd12 = CMND('CMND moi - 12 so', template_path + 'cmnd12_tmp.tiff', template_path + 'cmnd12_mask.tiff', template_path + 'cmnd12_tmpname.tiff')
    cmnd12.addLineDesc({'id':(40,64), 'dob':(147,160)})
    cancuoc = CMND('Can Cuoc Cong Dan', template_path + 'cancuoc_tmp.tiff', template_path + 'cancuoc_mask.tiff', template_path + 'cancuoc_tmpname.tiff')
    cancuoc.addLineDesc({'id':(40,64), 'dob':(122,137)})
    cmnd9 = CMND('CMND cu - 9 so', template_path + 'cmnd9_tmp.tiff', template_path + 'cmnd9_mask.tiff', template_path + 'cmnd9_tmpname.tiff')
    cmnd9.addLineDesc({'id':(40,64),'dob':(123,143)})
#     gplxmoi = CMND('Giay Phep Lai Xe moi', template_path + 'gplxmoi_tmp.tiff', template_path + 'gplxmoi_mask.tiff', template_path + 'gplxmoi_tmpname.tiff')
#     gplxmoi.addLineDesc({'id':(35,48), 'dob':(81,94)})
#     gplxcu = CMND('Giay Phep Lai Xe cu', template_path + 'gplxcu_tmp.tiff', template_path + 'gplxcu_mask.tiff', template_path + 'gplxcu_tmpname.tiff')
#     gplxcu.addLineDesc({'id':(0,0), 'dob':(0,0)})

#     allcards = [cmnd12, cancuoc, cmnd9, gplxmoi, gplxcu]
    allcards = [cmnd12, cancuoc, cmnd9]
    
#     sys.argv = ['main.py','/home/loitg/Downloads/cmnd_data/moi/00.JPG','/home/loitg/temp.txt']
    if len(sys.argv) < 3:
        sys.exit(1)

    with codecs.open(sys.argv[2], 'w', encoding='utf-8') as rstext: #sys.argv[2] is output text
        img = cv2.imread(sys.argv[1]) #sys.argv[1] is image location
        if img is None:
            rstext.write('Input file is not an image.')
            sys.exit(0)
        rr= 720.0/img.shape[1]
        img = cv2.resize(img, None, fx=rr, fy=rr)
        blurness = calcBlur(img)
        if blurness < 50:
            rstext.write('Detected blurred image.')
            sys.exit(0)
        (h, w) = img.shape[:2]
        
        # Rotate image to deskew
        img0 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img00 = cv2.resize(img0[h/3:,w/3:],None,fx=0.5,fy=0.5) # scale down to estimate skew faster
        angle = estimate_skew_angle(img00,linspace(-5,5,42))
        rotM = cv2.getRotationMatrix2D((w/2,h/2),angle,1)
        img = cv2.warpAffine(img,rotM,(w,h))
    
        recognized_cards = []
        for card in allcards:
            # Check if img is this card or not, if yes, how confident it is
            isCard, conf = card.findTextRegion(img)
            if isCard: recognized_cards.append((card, conf))
        
        if len(recognized_cards) > 0:
            # Pick the most appropriate card
            foundcmnd,_ = min(recognized_cards)
            foundcmnd.printResult(rstext)
        else:
            rstext.write('No ID Card found.')            
               

        
    
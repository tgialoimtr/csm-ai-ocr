# -*- coding: utf-8 -*-
'''
Created on Oct 16, 2017

@author: loitg
'''
import os,sys
import cv2
from numpy import where, float32, linspace, uint8
from common import sharpen, sauvola, args, firstAnalyse, ASHOW
from LinesMgr import LinesMgr
from removedot import removedot
import codecs
from searcher import Searcher

partall_path = '/home/loitg/Downloads/part2/'
output_path = '/home/loitg/workspace/receipttest/rescources/db/'

if __name__ == '__main__':
    searcher = Searcher(output_path + 'top200.csv')
    prediction = {}
    with codecs.open(output_path + 'images.txt', 'r', encoding='utf-8') as prediction_file:
        filename=''
        for line in prediction_file:
            line = line.rstrip('\n')
            if len(line) > 20 and line[:11] == 'filename---':
                filename = line[11:]
                prediction[filename] =[]
            else:
                prediction[filename].append(line)
         
    sorted_filelist = sorted(os.listdir(partall_path))
    for filename in sorted_filelist:
        if filename[-3:] !='jpg' and filename[-3:] !='JPG': continue
        print filename + '-----------'
        searcher.search(prediction[filename])
        k = raw_input('input: ')
     
    

#     if len(sys.argv) > 1:
#         partall_path = sys.argv[1]
#         output_path = sys.argv[2]
#     with codecs.open(output_path, 'a+', encoding='utf-8') as outfile:
#         sorted_filelist = sorted(os.listdir(partall_path))
#         found = False
#         for filename in sorted_filelist:
#             if filename[-3:] !='jpg' and filename[-3:] !='JPG': continue
#              
#             img_grey = cv2.imread(partall_path + filename, 0)
#             h,w = img_grey.shape
#             img_grey = img_grey[:min(h/2,w),:]
#             img_grey = cv2.normalize(img_grey.astype(float32), None, 0.0, 0.99, cv2.NORM_MINMAX)
#             img_grey = sharpen(img_grey)
#             img_bin_reversed = sauvola(img_grey, w=128, k=0.2, scaledown=args.binmaskscale, reverse=True)
#     #         ASHOW('ori', img_bin_reversed)
#             objects, smalldot, scale = firstAnalyse(img_bin_reversed)
#              
#             dotremoved = removedot(img_bin_reversed, smalldot, scale)
#             linesMgr = LinesMgr(dotremoved, cv2.cvtColor((img_grey*255).astype(uint8), cv2.COLOR_GRAY2BGR))
#             linesMgr.calc(objects, scale)
#             desc = ''
#             outfile.write('filename---' + filename + '\n')
#             for l in linesMgr.lines:
#                 outfile.write(l.text1 + '\n')
#                 outfile.write(l.text2 + '\n')
            
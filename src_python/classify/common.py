# -*- coding: utf-8 -*-
'''
Created on Oct 3, 2017

@author: loitg
'''

from pylab import *
import cv2
from scipy.ndimage import interpolation
from skimage.filters import threshold_sauvola, gaussian
from ocrolib import psegutils,morph,sl

cmnd_path = '/home/loitg/workspace/cmnd/scanned/'
cmnd_path = '/home/loitg/workspace/receipttest/img/'
hoadon_path = '/home/loitg/workspace/python/python/img/'
tmp_path = '/tmp/loitg/'

class obj:
    def __init__(self):
        pass
args = obj()
args.binmaskscale = 0.4
args.heavyprocesscale = 0.4
args.deskewscale = 0.1
args.range = 10

args.zoom = 0.5
args.range = 20
args.debug = 1
args.perc= 80
args.escale = 1.0
args.threshold = 0.5
args.lo = 5
args.hi = 90
args.usegauss = False
args.vscale = 1.0
args.hscale = 1.0
args.threshold = 0.2
args.pad = 0
args.expand = 3
args.model = '/home/loitg/workspace/receipttest/model/receipt-model-460-700-00590000.pyrnn.gz'
args.connect = 4
args.noise = 8
args.mode = 'cu'

def summarize(a):
    b = a.ravel()
    return a.dtype, a.shape, [amin(b),mean(b),amax(b)], percentile(b, [0,20,40,60,80,100])

def DSHOW(title,image):
    if not args.debug: return
    if type(image)==list:
        assert len(image)==3
        image = transpose(array(image),[1,2,0])
        if args.debug>0: imshow(image); ginput(timeout=-1)
    elif args.debug>0: 
        imshow(image, cmap='gray'); ginput(timeout=-1)
    
def ASHOW(title, image, scale=1.0, waitKey=False):
    HEIGHT = 600.0
    if len(image.shape) > 2:
        h,w,_ = image.shape
    else:
        h,w = image.shape
    canhlon = h if h > w else w
    tile = HEIGHT/canhlon
    
    mm = amax(image)
    if mm > 0:
        temp = image.astype(float)/mm
    else:
        temp = image.astype(float)
    
#     if len(image.shape) > 2:
#         temp = cv2.resize(temp,None,fx=tile*scale,fy=tile*scale)
#     else:
#         temp = interpolation.zoom(temp, tile*scale)
    temp = cv2.resize(temp,None,fx=tile*scale,fy=tile*scale)
    cv2.imshow(title, temp)
    if waitKey:
        cv2.waitKey(-1)

def sharpen(binimg):
#     blurred_l= gaussian(binimg,2)
    blurred_l= gaussian(binimg,0.8) #CMND
#     filter_blurred_l = gaussian(blurred_l, 1)
    filter_blurred_l = gaussian(blurred_l, 0.4)  # CMND
    alpha = 30
    return blurred_l + alpha * (blurred_l - filter_blurred_l) 
    
def estimate_skew_angle(image,angles):
    estimates = []
    binimage = sauvola(image, 11, 0.1).astype(float)
#     cv2.imshow('debug',binimage)
#     cv2.waitKey(-1)
    for a in angles:
        rotM = cv2.getRotationMatrix2D((binimage.shape[1]/2,binimage.shape[0]/2),a,1)
        rotated = cv2.warpAffine(binimage,rotM,(binimage.shape[1],binimage.shape[0]))
        v = mean(rotated,axis=1)
        d = [abs(v[i] - v[i-1]) for i in range(1,len(v))]
        d = var(d)
        estimates.append((d,a))
#     if args.debug>0:
#         plot([y for x,y in estimates],[x for x,y in estimates])
#         ginput(1,args.debug)
    _,a = max(estimates)
    return a

def sauvola(grayimg, w=51, k=0.2, scaledown=None, reverse=False):
    mask =None
    if scaledown is not None:
        mask = cv2.resize(grayimg,None,fx=scaledown,fy=scaledown)
        w = int(w * scaledown)
        if w % 2 == 0: w += 1
        mask = threshold_sauvola(mask, w, k)
        mask = cv2.resize(mask,(grayimg.shape[1],grayimg.shape[0]),fx=scaledown,fy=scaledown)
    else:
        if w % 2 == 0: w += 1
        mask = threshold_sauvola(grayimg, w, k)
    if reverse:
        return where(grayimg > mask, uint8(0), uint8(1))
    else:
        return where(grayimg > mask, uint8(1), uint8(0))
    
def simplefirstAnalyse(binary):
    binaryary = morph.r_closing(binary.astype(bool), (1,1))
    labels,_ = morph.label(binaryary)
    objects = morph.find_objects(labels) ### <<<==== objects here
    smalldot = zeros(binaryary.shape, dtype=binary.dtype)
    scale = int(binary.shape[0]*0.7)
    for i,o in enumerate(objects):       
        if (sl.width(o) < scale/2) or (sl.height(o) < scale/2):
            smalldot[o] = binary[o]
        if sl.dim0(o) > 3*scale:
            mask = where(labels[o] != (i+1),uint8(255),uint8(0))
            binary[o] = cv2.bitwise_and(binary[o],binary[o],mask=mask)
            continue
    return objects, smalldot, scale

def firstAnalyse(binary):
    binaryary = morph.r_closing(binary.astype(bool), (1,1))
    labels,_ = morph.label(binaryary)
    objects = morph.find_objects(labels) ### <<<==== objects here
    bysize = sorted(range(len(objects)), key=lambda k: sl.area(objects[k]))
#     bysize = sorted(objects,key=sl.area)
    scalemap = zeros(binaryary.shape)
    smalldot = zeros(binaryary.shape, dtype=binary.dtype)
    for i in bysize:
        o = objects[i]
        if amax(scalemap[o])>0: 
#             mask = where(labels[o] != (i+1),uint8(255),uint8(0))
#             binary[o] = cv2.bitwise_and(binary[o],binary[o],mask=mask)
            continue
        scalemap[o] = sl.area(o)**0.5
    scale = median(scalemap[(scalemap>3)&(scalemap<100)]) ### <<<==== scale here

    for i,o in enumerate(objects):       
        if (sl.width(o) < scale/2) or (sl.height(o) < scale/2):
            smalldot[o] = binary[o]
        if sl.dim0(o) > 3*scale:
            mask = where(labels[o] != (i+1),uint8(255),uint8(0))
            binary[o] = cv2.bitwise_and(binary[o],binary[o],mask=mask)
            continue
    return objects, smalldot, scale

GST1 = 'o ten:'
UNI_STR = '194'

#             def hihi(a):
#                 return int(a*1.0/args.heavyprocesscale)
#             l.bounds = slice(hihi(l.bounds[0].start), hihi(l.bounds[0].stop)),slice(hihi(l.bounds[1].start), hihi(l.bounds[1].stop))
#             l.mask = cv2.resize(l.mask.astype(float),(l.bounds[1].stop - l.bounds[1].start,l.bounds[0].stop - l.bounds[0].start),fx=1.0/args.heavyprocesscale,fy=1.0/args.heavyprocesscale)
#             l.mask = where(l.mask > 0.5, True, False)
#             y0,x0,y1,x1 = [int(x) for x in [l.bounds[0].start,l.bounds[1].start, \
#               l.bounds[0].stop,l.bounds[1].stop]]
#             pad = (y1-y0)/4
#             try:
#                 line = self.originalpage[y0-pad:y1+pad,x0-pad:x1+pad]
#             except Exception as e:
#                 print e
#                 continue
#             mask = filters.maximum_filter(l.mask,(args.expand,args.expand))
#             cval=0
#             expand_mask = ones(array(mask.shape)+2*pad)
#             expand_mask[:,:] = amax(mask) if cval==inf else cval
#             expand_mask[pad:-pad,pad:-pad] = mask
#                
#             line = cv2.cvtColor(line, cv2.COLOR_BGR2GRAY)
#             line = sharpen(line)
#             w=line.shape[0]/4
#             if w % 2 ==0: w -= 1
#             binline = sauvola(line, w=w, k=0.3, scaledown=0.25)
#             binline = where(expand_mask, binline, 255)/255



# if __name__ == '__main__':
#     linesMgr = LinesMgr(None,None)
#     linesMgr.lines = []
#                 
#     result = psegutils.record(bounds = (slice(0L, 42L, None), slice(883L, 1488L, None)), text1=u'THỤL nau nuum vun nam', text2=u'4 HT CHỤ NAN',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(1L, 86L, None), slice(708L, 1306L, None)), text1=u'"Ứrẩặẩlỉp .… \'g do - Hạnh Ehũc', text2=u'º Đạ: lập — Tự dº — Hạnh phúc',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(50L, 143L, None), slice(306L, 508L, None)), text1=u'', text2=u'',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(98L, 160L, None), slice(654L, 1359L, None)), text1=u'CHỨNG MINH NHÂN DÂN', text2=u'CHỨNG MÌNH NHÂN DÂN',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(195L, 243L, None), slice(666L, 1344L, None)), text1=u'861042048000025', text2=u'sổ: 04²0480000²5',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(269L, 328L, None), slice(618L, 932L, None)), text1=u'Họvùtènkheislnh:', text2=u'Họ và tên khai sinh:',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(294L, 356L, None), slice(866L, 1269L, None)), text1=u'NGUYỄN LÂM HỌ!', text2=u'NGUYỄN LÂM HỢI',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(365L, 425L, None), slice(596L, 926L, None)), text1=u'Họ và tán gọi khác:', text2=u'Hº và tên gọi khác:;',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(402L, 481L, None), slice(203L, 490L, None)), text1=u'\'u Ễ_Ẹ', text2=u't ».',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(458L, 506L, None), slice(614L, 1139L, None)), text1=u'Ngày tháng năm sinh 1948', text2=u'Ngày tháng năm sinh 1948',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(481L, 529L, None), slice(343L, 462L, None)), text1=u'l…\\', text2=u'g dem,',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(490L, 549L, None), slice(1039L, 1257L, None)), text1=u'Dân tộc: Kinh', text2=u'Dân tộc: Kinh',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(518L, 553L, None), slice(637L, 878L, None)), text1=u'em um: Nam', text2=u'Giới tính: Nam',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(529L, 576L, None), slice(343L, 459L, None)), text1=u'bar.', text2=u'— ự',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(566L, 611L, None), slice(941L, 1336L, None)), text1=u'Đưc Thọ. Ha Tinh', text2=u'Đực Thọ, Ha Tĩnh',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(577L, 620L, None), slice(575L, 796L, None)), text1=u'__ Quê quán:', text2=u'.. . Quê quán:',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(588L, 700L, None), slice(363L, 637L, None)), text1=u'~ <-', text2=u'# :§.',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(591L, 671L, None), slice(162L, 252L, None)), text1=u'l', text2=u'wa!',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(637L, 700L, None), slice(332L, 445L, None)), text1=u'', text2=u'',img=None)
#     linesMgr.lines.append(result)
#     linesMgr.extract(32.2,'moi')

#     result = psegutils.record(bounds = (slice(21L, 48L, None), slice(220L, 682L, None)), text1=u'CÔNG HÒA XA HỘI CHỦ NGHTA VIET NAM', text2=u'CÔNG HÒA XÃ Hội CHỦ NGHĨA VIẾT NAM',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(50L, 78L, None), slice(306L, 591L, None)), text1=u'_ ĐỆIịg-Tưdo-Hgnhgul:', text2=u'— Đạp ~ Tướa — gợn phụ',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(51L, 97L, None), slice(77L, 182L, None)), text1=u'/“\\', text2=u'/“^^',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(78L, 110L, None), slice(264L, 662L, None)), text1=u'GIẤY cnứuc. Man nui… mỉm', text2=u'GIẤY CHỨNG MINH NHÂN DÂN',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(99L, 128L, None), slice(127L, 183L, None)), text1=u'_ i', text2=u'— ụø',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(94L, 128L, None), slice(72L, 127L, None)), text1=u'L', text2=u'kỳ',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(120L, 161L, None), slice(296L, 360L, None)), text1=u'so', text2=u's',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(124L, 153L, None), slice(370L, 432L, None)), text1=u'6“', text2=u'6—',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(128L, 161L, None), slice(83L, 174L, None)), text1=u'W', text2=u'',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(168L, 204L, None), slice(228L, 625L, None)), text1=u'Họtan .LB PHƯƠNG THẢO', text2=u'Hiên LÊ PHƯỢNG THẢO',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(232L, 274L, None), slice(420L, 650L, None)), text1=u'08/ĩ12/1996', text2=u'08/1²/1996',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(257L, 274L, None), slice(111L, 149L, None)), text1=u'', text2=u'',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(250L, 278L, None), slice(228L, 361L, None)), text1=u'Slnh ngày', text2=u'Sinh ngày',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(286L, 321L, None), slice(228L, 700L, None)), text1=u'Nguyên quán Tân Long,?hụng Hiệp', text2=u'Nguyên quân — Tân Tºng, Phụng Hiệp',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(290L, 307L, None), slice(109L, 142L, None)), text1=u'.—-', text2=u'—.',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(319L, 355L, None), slice(418L, 651L, None)), text1=u'Tình Cần Thơ', text2=u'Tỉnh Cẩn Thơ',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(359L, 388L, None), slice(104L, 175L, None)), text1=u'° F', text2=u'² m',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(371L, 397L, None), slice(212L, 671L, None)), text1=u'NHI ĐKHKIÌIWIIgIN Xã Tân Long', text2=u'Na ĐKHK thương ru — Xã Tân bºng',img=None)
#     linesMgr.lines.append(result)
#     result = psegutils.record(bounds = (slice(399L, 435L, None), slice(279L, 700L, None)), text1=u'Phụng Hiệp, Tình Cần Thơ', text2=u'Phụng Hiệp, Tinh Cần Thơ',img=None)
#     linesMgr.lines.append(result)
#     linesMgr.extract(15,'cu')



        
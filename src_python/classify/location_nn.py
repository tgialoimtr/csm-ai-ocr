'''
Created on Sep 17, 2017

@author: loitg
'''

import editdistance
import pandas as pd
from time import time
import string
import os
from math import exp, e, tanh
import re
import numpy as np
from ctypes import cdll

class SingleWord:
    def __init__(self, word):
        self.word = word
        self.p = None
        self.count = 1
        
    def setAbsSimilarity(self, val):
        self.p = val

    def updateAbsSimilarity(self, val):
        if val > self.p:
            self.p = val
            
    def getSimilarity(self):
        return 1.0 * self.p / (1+0.05*self.count)

class MultiValColMgr:
    def __init__(self, db, name):
        self.db = db
        self.name = name
        self.init()
    
    def init(self):
        self.mall_dict = {}
        mall_set = set(self.db[self.name])
        for mallname in mall_set:   
            for word in mallname.split(' '):
                if word in self.mall_dict:
                    self.mall_dict[word].count += 1
                else:
                    self.mall_dict[word] = SingleWord(word)
    
    def reportItem(self, item):
        pass
    

        

class SingleValColMgr:
    def __init__(self, db, name, standardize=None, error2prob=2, naScale=1.0, multiValues=False, singleWordPunish = 2.0, shortWordPunish = 4):
        self.db = db
        self.name = name
        self.value_dict = {}
        if standardize:
            self.standardize = standardize
        else:
            self.standardize = lambda x: x
        self.error2prob = error2prob
        self.naScale = naScale
        self.multiValues = multiValues
        self.shortWordPunish = shortWordPunish
        self.singleWordPunish = singleWordPunish
        self.init()
    
    def init(self):
        self.notNullCount = 0
        self.nullCount = 0
        for x in self.db[self.name]:
            if (x != ''):
                x = self.standardize(x)
                self.value_dict[x] = 1E-40
                self.notNullCount += 1
            else:
                self.nullCount += 1

    def legacyCompare(self, item, value):
        items = item.split(' ')
        values = value.split(' ')
        l = []
        for v in values:
            temp = 0.0
            x = len(v)*len(v)
            for i in items:
                prob = editdistance.eval(i, v)*1.0
                prob = exp(-prob/self.error2prob)*x/(x+self.shortWordPunish)
                if prob > temp: temp = prob
            l.append(temp)
        l.sort(reverse=True)
        val = 0.0
        if len(l) > 1:
            val = l[0]*l[1]
        elif len(l) == 1:
            val = l[0]*l[0]/self.singleWordPunish
        return val

    def loitgCompare2(self, item, value):
        x = len(value)
        y = x - 2 - 4
        if y < 0:
            y = 0
        if y > 8:
            y = 8
        y=1.0*y/8        
        comp_vec = []
        
        for i in range(len(item) - len(value) + 1):
            temp = 0
            for j in range(len(value)):
                if value[j] == item[i+j]:
                    temp += 1
            comp_vec.append(temp)
        val = 0.0
        for i in range(1,len(comp_vec) -1):
            temp = comp_vec[i] + y*(comp_vec[i-1] + comp_vec[i-1])
            if temp > val: val = temp
            
        x = (x-3)*(x-3)
        return val
        
            
    def loitgCompare(self, item, value):
        pad = 1
        val = 0.0
        x = len(value)
        y = x - 2 - 4
        if y < 0:
            y = 0
        if y > 8:
            y = 8
        y=1.0*y/8
            
        r = len(item)+2*pad + 1- x
#         print '--'+item+'--'
#         print '--'+value+'--'
        if r > 0:
            comp_mat = np.zeros(shape=(len(item)+2*pad, x), dtype=float)
            for j in range(comp_mat.shape[1]):
                for i in range(len(item)):
                    if (item[i] == value[j]):
                        if comp_mat[i,j] == 0.0: comp_mat[i,j] = y
                        comp_mat[i+pad,j] = 1
                        if comp_mat[i+2*pad,j] == 0.0: comp_mat[i+2*pad,j] = y
#             print comp_mat
            for i in range(r):
                s = 0.0
                for j in range(x):
                    s += comp_mat[i + j, j]
                if s / x > val:
                    val = s / x
        
        x = (x-3)*(x-3)
        val=0.5*tanh(15*(val-0.8))+0.5
        return val*x/(x+8)

    def compare(self, numword, item, value):
        item = self.standardize(item)
        if self.multiValues:
            values = value.split('|')
            prob = 0.0
            for v in values:
                if numword > 0.6*len(v):
                    temp = self.loitgCompare2(item, ' '+v+' ')#self.standardize(v))
                    if temp > prob:
                        prob = temp
            return prob
        else:
            prob = editdistance.eval(item, value)*1.0
            prob = exp(-prob/self.error2prob)
            return prob
                
    def reportItem(self, item):
        ret = []
        numword = sum((c.isalpha() | c.isspace()) for c in item)
        print numword,'/',len(item)
        if self.multiValues: item = '('+item+')'
        for value in self.value_dict.iterkeys():
            if len(value) > 2:
                prob = self.compare(numword, item, value)
                ret.append((prob, value))
                if prob > self.value_dict[value]:
                    self.value_dict[value] = prob
        ret.sort(reverse=True)
        return ret[0]      

    def calcProbs(self):
        def temp(value):
            v = self.standardize(value)
            if v != '':
                return self.value_dict[v]
            else:
                return np.nan
        self.db[self.name + '_prob'] = self.db[self.name].apply(temp)
        summ = self.db[self.name + '_prob'].sum()
        probForNull = self.nullCount * self.naScale / (self.nullCount + self.notNullCount)
        probForNotNull = 1.0 - probForNull        
        def calc(val):
            v = self.standardize(val)
            if val == '':
                return 1.0/self.nullCount * probForNull
            else:
                return self.value_dict[v]/summ * probForNotNull    
        self.db[self.name + '_prob'] = self.db[self.name].apply(calc)


def to_string(number):
    if np.isnan(number):
        return ''
    else:
        return str(number)

similarity_table = string.maketrans('5l1:08O','SIIIOBO')
char2num = string.maketrans('Oo$DBQSIl','005080511')

def standardize(unitext):
    temp = unitext.strip()
    temp = temp.translate(similarity_table).upper()
    temp = re.sub(' +',' ', temp)
    return temp

def standardize_loitg(unitext):
    return ' '+standardize(unitext)+' '

def standardize_gst(gst):
    if len(gst) > 4:
        temp = gst.upper()
        temp = re.sub('[ -]+','', temp)
        temp = temp[:2] + temp[2:-1].translate(char2num) +temp[-1]
        return temp
    else:
        return ''

def standardize_zipcode(zc):
    if len(zc) > 0:
        temp = zc.translate(char2num).upper()
        return temp
    else:
        return ''

ignore_line_keyword = ['visa','total', 'date', 'time', 'receipt', 'submit', 'charge', 'thank', 'discount', 'description']
# ignore_line_keyword = []
pgst1 = re.compile('\W+([MHNl21I][\dOo$DBQRSIl\']-?[\dOoDBQ$SIl\']{7,8}[ ]{0,3}-?[ ]{0,3}\w)\W+')
pgst2 = re.compile('([rR][eE][gG]|[gG][$sS5][tT]).*?(\w{1,2}-?\w{6,8}-?\w{1,2})\W')
pzc1 = re.compile('([sS5][li1I][nN]|[pP][oO0][rR][eE]).*?([\dOoDBQSIl\']{5,7})\W+')
pzc2 = re.compile('\W(\([S5]\)|[S5][GE]?)[ ]{0,3}\(?([\dOoDBQSIl\']{5,7})\)?\W+')
    
if __name__ == '__main__':
    stores = pd.read_csv('/home/loitg/trung_kw_3.csv')
    stores.fillna('', inplace=True)
    stores['zipcode'] = stores['zipcode'].apply(str)
    
    storeNameCol = SingleValColMgr(stores, 'store_kw', standardize=standardize_loitg, multiValues=True)
    mallNameCol = SingleValColMgr(stores, 'mall_kw', standardize=standardize_loitg, multiValues=True, singleWordPunish=1.0)
    zipCodeCol = SingleValColMgr(stores, 'zipcode', standardize=standardize_zipcode)
    gstCol = SingleValColMgr(stores, 'gstNoPattern', standardize=standardize_gst)

#     print storeNameCol.loitgCompare(standardize_loitg('BIRKENSTOCK RAFFLES CITY 1'), standardize_loitg('BIRKENSTOCK '))    
#     print storeNameCol.loitgCompare(standardize_loitg('Navy 41 CLA'), standardize_loitg('VA'))
#     print storeNameCol.loitgCompare(standardize_loitg('Salesperson 2: Stxre. 004A'), standardize_loitg('STERED'))
#     print storeNameCol.loitgCompare(standardize_loitg('PAPLLIO (SiPTE. LTD.'), standardize_loitg('DTD'))    
#       
#       
#     exit(0)

    
    text_path = '/home/loitg/Downloads/textResult/'
    for filename in os.listdir(text_path):
#         mallNameCol.init()
#         gstCol.init()
#         zipCodeCol.init()
        storeNameCol.init()
        f = open(text_path+filename,'r')
        print filename, '---------------------------'
        lines = []
        for line in f:
            cont = False
            for w in ignore_line_keyword:
                if w.upper() in line.upper():
                    cont = True
                    break
            if cont: continue
            lines.append(line)
             
        result = []
        for line in lines:
            m1 = pgst1.search(line)
            if m1:
                suspectgst = m1.group(1)
                rs = gstCol.reportItem(suspectgst)
                print suspectgst,rs
            m2 = pgst2.search(line)
            if m2:
                suspectgst = m2.group(2)
                rs=gstCol.reportItem(suspectgst)
                print suspectgst,rs
                
            if (not m1) & (not m2):       
                print line.strip()
                rs = storeNameCol.reportItem(line)
                result.append((rs[0], rs[1], line))
                                
#             if (not m1) & (not m2):       
#                 print line.strip()
#                 rs = mallNameCol.reportItem(line)
#                 result.append((rs[0], rs[1], line))
#             m1 = pzc1.search(line)
#             if m1:
#                 suspect_zc = m1.group(2)
#                 rs = zipCodeCol.reportItem(suspect_zc)
#                 print suspect_zc,rs
#             m2 = pzc2.search(line)
#             if m2:
#                 suspect_zc = m2.group(2)
#                 rs = zipCodeCol.reportItem(suspect_zc) 
#                 print suspect_zc,rs       
        result.sort(reverse=True)
          
        for rs in result[:15]:
            print rs[0],rs[1]
            print rs[2]
            
#         storeNameCol.calcProbs()
#         mallNameCol.calcProbs()
#         zipCodeCol.calcProbs()
#         gstCol.calcProbs()
        
        
#         print stores[['store_kw','mall_kw','zipcode','gstNoPattern', 'store_kw_prob']].sort_values(['store_kw_prob'], ascending=False).head(5)

#         stores['location_prob'] = stores['mall_kw_prob'] * stores['zipcode_prob']
#         
#         
#         
#         stores['prob'] = stores['mall_kw_prob'] * stores['zipcode_prob'] * stores['gstNoPattern_prob']
#         
#         temp = stores.groupby('mall_kw')['mall_kw_prob'].agg(['mean','size']).sort_values(['mean'],ascending=False)
#         print temp[:2]
#         print temp['mean'][0]/temp['mean'][1]
#         temp = stores.groupby('zipcode')['zipcode_prob'].agg(['mean','size']).sort_values(['mean'],ascending=False)
#         print temp[:2]
#         print temp['mean'][0]/temp['mean'][1]
#         temp = stores.groupby(['mall_kw', 'zipcode'])['location_prob'].agg(['mean','size']).sort_values(['mean'], ascending=False)
#         print temp[:2]
#         print temp['mean'][0]/temp['mean'][1]
#         temp = stores.groupby(['gstNoPattern'])['gstNoPattern_prob'].agg(['mean','size']).sort_values(['mean'], ascending=False)
#         print temp[:2]
#         print temp['mean'][0]/temp['mean'][1]
#         temp = stores.groupby(['mall_kw', 'zipcode', 'gstNoPattern_prob'])['prob'].agg(['mean','size']).sort_values(['mean'], ascending=False)
#         print temp[:5]
#         print temp['mean'][0]/temp['mean'][1]        
        
     
        k = raw_input('-----')
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
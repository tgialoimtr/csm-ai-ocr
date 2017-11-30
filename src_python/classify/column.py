'''
Created on Oct 17, 2017

@author: loitg
'''
import string, re, math
# from fuzzywuzzy import fuzz
import editdistance
import unicodedata
import numpy as np

def match(text, pattern):
    n = len(text)
    m = len(pattern)
    g = np.empty(shape=(m+1, n+1), dtype=int)
    distance = 999;
    for i in range(m+1):
        g[i,0] = i
    for j in range(1, n+1):
        for i in range(1, m+1):
            delta = 1
            if text[j-1] == pattern[i-1]:
                delta = 0
            g[i,j] = min(g[i-1,j-1] + delta, g[i-1,j] + 1, g[i,j-1] + 1)
        if g[m,j] <= distance:
            distance = g[m,j]
    return distance

        
#     for (int j = 1; j < n + 1; ++j) {
#         for (int i = 1; i < m + 1; ++i) {
#             int delta = 1;
#             if (text.charAt(j - 1) == pattern.charAt(i - 1)) {
#                 delta = 0;
#             }
#             g[i][j] = min(g[i - 1][j - 1] + delta,
#                           g[i - 1][j] + 1,
#                           g[i][j - 1] + 1);
#         }
#         if (g[m][j] <= distance) {
#             distance = g[m][j];
#         }
#     }
#     return distance;   
    
similarity_table = string.maketrans('5l1:08O','SIIIOBO')
char2num = string.maketrans('Oo$DBQSIl','005080511')

def standardize(unitext):
    temp = ' ' + unitext + ' '
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
        temp = zc.translate(char2num).upper().strip()
        return temp
    else:
        return ''

class Store(object):
    LOCATION_CODE = 'CRM LocationCode'
    STORE_NAME = 'Text to identify Merchant'
    MALL_NAME = 'Text to identify Mall'
    ZIPCODE = 'ZipCode to identify Mall'
    GST_NO = 'GST to identify Merchant'
    
    @staticmethod   
    def standardizeByName(colname, rawValue):
        if type(rawValue) == unicode:
            rawValue = unicodedata.normalize('NFKD', rawValue).encode('ascii', 'ignore')
        if colname == Store.LOCATION_CODE:
            return ''
        elif colname == Store.MALL_NAME or colname == Store.STORE_NAME:
            return standardize(rawValue)
        elif colname == Store.ZIPCODE:
            return standardize_zipcode(rawValue)
        elif colname == Store.GST_NO:
            return standardize_gst(rawValue)
        else:
            return ''
    
    def __init__(self, storedict):
        self.locationCode = storedict[Store.LOCATION_CODE]
        self.storeKeyword = storedict[Store.STORE_NAME]
        self.mallKeyword = storedict[Store.MALL_NAME]
        self.zipcode = storedict[Store.ZIPCODE]
        self.gstNoPattern = storedict[Store.GST_NO]
        self.storedict = storedict
        
    def getByColName(self, colname):
        return self.storedict[colname]

class Column(object):

    def __init__(self, name, e2p, swp):
        self.name = name
        self.e2p = e2p
        self.swp = swp
        self.values = {}
    
    def initAddRow(self, store):
        rawval = store.getByColName(self.name)
        if rawval == '': return
        newvals = rawval.split('|')
        for val in newvals:
            val = Store.standardizeByName(self.name, val)
            if val in self.values:
                self.values[val].add(store)
            else:
                self.values[val] = set([store])
    def search(self, items):
        result1 = {}
        if len(items) == 0: return result1
        for value, stores in self.values.iteritems():
            if len(value) < 3: continue
            prob = 0.0
            for item in items:
                punish = len(value)*1.0
                sim = (punish - editdistance.eval(item, value))/punish
                x = sim - 0.6
                punish = punish - 2;
                punish = punish*punish;
                punish = punish/(punish + self.swp)
                temp = (0.5*math.tanh(8*x)+0.5)*punish
                if temp > prob:
                    prob = temp
            if prob > 0.4:
                for store in stores:
                    if (store not in result1) or (store in result1 and result1[store] < prob):
                        result1[store] = prob
        return result1
            
    def searchLong(self, alllines):
        result1 = {}
        allines_std = Store.standardizeByName(self.name, alllines)
        for value, stores in self.values.iteritems():
            if len(value) < 3: continue
#             sim = fuzz.partial_ratio(value, allines_std)*1.0/100.0
#             sim = loitgCompare(allines_std, value)
            punish = len(value)*1.0
            sim = (punish - match(allines_std, value))/punish
            x = sim - 0.75
            punish = punish - 2;
            punish = punish*punish;
            punish = punish/(punish + self.swp)
            prob = (0.5*math.tanh(15*x)+0.5)*punish
            if prob > 0.4:
                for store in stores:
                    if (store not in result1) or (store in result1 and result1[store] < prob):
                        result1[store] = prob
        return result1
    
    def printResult(self, result):
        for k, v in result.iteritems():
            print k.getByColName(self.name) + '---' + str(v)
                        
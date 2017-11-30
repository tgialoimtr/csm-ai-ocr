'''
Created on Oct 17, 2017

@author: loitg
'''

import pandas as pd
from column import Column, Store
import numpy as np
import re
from time import time

class Searcher(object):
    '''
    classdocs
    '''
    pgst1 = re.compile('\W+([MHNl21I][\dOo$DBQRSIl\']-?[\dOoDBQ$SIl\']{7,8}[ ]{0,3}-?[ ]{0,3}\w)\W+')
    pgst2 = re.compile('([rR][eE][gG]|[gG][$sS5][tT]).*?(\w{1,2}-?\w{6,8}-?\w{1,2})\W')
    pzc1 = re.compile('([sS5][li1I][nN]|[pP][oO0][rR][eE]).*?([\dOoDBQSIl\']{5,7})\W+')
    pzc2 = re.compile('\W(\([S5]\)|[S5][GE]?)[ ]{0,3}\(?([\dOoDBQSIl\']{5,7})\)?\W+')

    def __init__(self, database_file):
        self.mallCol = Column(Store.MALL_NAME, 2.0, 8.0)
        self.zipcodeCol = Column(Store.ZIPCODE, 2.0, 1.0)
        self.gstCol = Column(Store.GST_NO, 2.0, 1.0)
        self.storeCol = Column(Store.STORE_NAME, 2.0, 8.0)
        self.readCSV(database_file);
        for store in self.data:
            self.mallCol.initAddRow(store)
            self.zipcodeCol.initAddRow(store)
            self.gstCol.initAddRow(store)
            self.storeCol.initAddRow(store)
#         total = 0
#         for k,v in self.mallCol.values.iteritems():
#             total += len(v)
#             print k + '-' + str(len(v))
#         print total
      
      
    def readCSV(self, csv_file):
        temp = pd.read_csv(csv_file, dtype={'Rank':np.str, 'ZipCode to identify Mall':np.str, 'GST to identify Merchant':np.str})
        temp.fillna('', inplace=True)
        temp = temp.to_dict('records')
        self.data = []
        for s in temp:
            self.data.append(Store(s))
            
    def search(self, lines):
        gst_list = []
        zipcode_list = []
        alllines = ''
        for line in lines:
            print line
            m1 = Searcher.pgst1.search(line+'\n')
            if m1:
                temp = m1.group(1)
                print line + '--->' + temp
                gst_list.append(Store.standardizeByName(Store.GST_NO, temp))
            m2 = Searcher.pgst2.search(line+'\n')
            if m2:
                temp = m2.group(2)
                print line + '--->' + temp
                gst_list.append(Store.standardizeByName(Store.GST_NO, temp))  
            m1 = Searcher.pzc1.search(line+'\n')
            if m1:
                temp = m1.group(2)
#                 print line + '--->' + temp
                zipcode_list.append(Store.standardizeByName(Store.ZIPCODE, temp))          
            m2 = Searcher.pzc2.search(line+'\n')
            if m2:
                temp = m2.group(2)
#                 print line + '--->' + temp
                zipcode_list.append(Store.standardizeByName(Store.ZIPCODE, temp)) 
            alllines += line + ' '            
        tt = time()
        rs1 = self.gstCol.search(gst_list)
#         self.gstCol.printResult(rs1)
        rs2 = self.storeCol.searchLong(alllines)
#         self.storeCol.printResult(rs2)
        rs3 = self.mallCol.searchLong(alllines)
#         self.mallCol.printResult(rs3)
        rs4 = self.zipcodeCol.search(zipcode_list)
#         self.zipcodeCol.printResult(rs4)
        print 'search: ', time() - tt
        tt = time()
        def getprob(result, store):
            if store in result:
                return result[store]
            else:
                return 0.02
        rs = []
        for store in self.data:
            gstprob = getprob(rs1, store)
            storeprob = getprob(rs2, store)
            mallprob = getprob(rs3, store)
            zcprob = getprob(rs4, store)
            
            
            
            
            prob = max(mallprob, zcprob) * max(gstprob, storeprob)
            rs.append((prob, store))
        rs.sort(reverse=True)
        if len(rs) > 0:
            print str(rs[0][0])+':'+rs[0][1].storeKeyword+'--'+rs[0][1].mallKeyword
        if len(rs) > 1:
            print str(rs[1][0])+':'+rs[1][1].storeKeyword+'--'+rs[1][1].mallKeyword
            
        print 'combine: ', time() - tt
        
        
        
        
        
        
        
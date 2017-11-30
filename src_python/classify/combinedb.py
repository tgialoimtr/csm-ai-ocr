# -*- coding: utf-8 -*-
'''
Created on Oct 17, 2017

@author: loitg
'''
import pandas as pd
import copy
import numpy as np
import codecs

output_path = '/home/loitg/workspace/receipttest/rescources/db/'
top90csv_path = '/home/loitg/Downloads/top90.csv'
top150xls_path = '/home/loitg/Downloads/OCR to identify Mall %2F Merchant - 16 Oct 2017.xlsx'
mall_map = {
    'Tampines Mall':'TAMPINES MALL|TAMPINES CENTRAL',
    'The Star Vista':'STAR VISTA|1 VISTA EXCHANGE GREEN',
    'IMM Building':'IMM BUILDING|IMM MALL|IMM BRANCH|IMM BLDG',
    'Bukit Panjang Plaza':'BUKIT PANJANG PLAZA|1 JELEBU ROAD',
    'Lot One':'LOT 1|LOT ONE|CHOA CHU KANG',
    'Junction 8':'JUNCTION 8|9 BISHAN PLACE',
    'Bedok Mall':'BEDOK MALL|311 NEW UPPER',
    'Westgate':'3 GATEWAY DRIVE|WESTGATE',
    'Sembawang Shopping Centre':'SEMBAWANG SHOPPING|604 SEMBAWANG',
    'Plaza Singapura':'PLAZA SINGAPURA|68 ORCHARD ROAD',
    'Bugis Junction':'BUGIS JUNCTION|201 VICTORIA|230 VICTORIA',
    'Raffles City Singapore':'RAFFLES CITY|NORTH BRIDGE',
    'JCube':'JCUBE MALL'
    }

def combine(s1, s2):
    a = set(s1.split('|'))
    b = set(s2.split('|'))
    return '|'.join(a|b-set(['']))

if __name__ == '__main__':
    top150 = pd.read_excel(top150xls_path, converters={'Rank':str, 'ZipCode to identify Mall':str, 'GST to identify Merchant':str})
    top150.fillna('', inplace=True)
#     top150['Rank'] =  top150['Rank'].astype(int).astype(str)
#     top150['ZipCode to identify Mall'] =  top150['ZipCode to identify Mall'].astype(str)
#     top150['GST to identify Merchant'] =  top150['GST to identify Merchant'].astype(str)
    print top150.dtypes
    top150 = top150.to_dict(orient='records')
    top90 = pd.read_csv(top90csv_path, dtype={'Rank':np.str, 'ZipCode to identify Mall':np.str, 'GST to identify Merchant':np.str})
    top90.fillna('', inplace=True)
#     top90['Rank'] =  top90['Rank'].astype(int).astype(str)
#     top90['ZipCode to identify Mall'] =  top90['ZipCode to identify Mall'].astype(str)
#     top90['GST to identify Merchant'] =  top90['GST to identify Merchant'].astype(str)
    print top90.dtypes
    top90 = top90.to_dict(orient='records')
    
    
    rs = codecs.open(output_path + 'top200.csv', 'w', encoding='utf8')
    rs.write('Rank,CRM LocationCode,CRM Location Name,Text to identify Mall,Text to identify Merchant,ZipCode to identify Mall,GST to identify Merchant\n');
    combined = {}
    for r150 in top150:
        for r90 in top90:
            c150 = r150['CRM LocationCode']
            c90 = r90['CRM LocationCode']
            if c150 not in combined:
                combined[c150] = copy.deepcopy(r150)
#                 combined[c150]['Rank'] = ''
#                 combined[c150]['status'] = 0
            if c90 not in combined:
                combined[c90] = copy.deepcopy(r90)
                combined[c90]['Rank'] = ''
#                 combined[c90]['status'] = 0                
            if c150 == c90:
                combined[c90] = {}
                combined[c90]['Rank'] = r150['Rank']
                combined[c90]['CRM Location Name'] = combine(r150['CRM Location Name'], r90['CRM Location Name'])
                combined[c90]['Text to identify Mall'] = combine(r150['Text to identify Mall'], r90['Text to identify Mall'])
                combined[c90]['Text to identify Merchant'] = combine(r150['Text to identify Merchant'], r90['Text to identify Merchant'])
                combined[c90]['ZipCode to identify Mall'] = combine(r150['ZipCode to identify Mall'], r90['ZipCode to identify Mall'])
                combined[c90]['GST to identify Merchant'] = combine(r150['GST to identify Merchant'], r90['GST to identify Merchant'])
                
    
    for code, row in combined.iteritems():
        print type(row['CRM Location Name'])
        print row
        rs.write(row['Rank'] + ',' +\
                 code + ',' +\
                 row['CRM Location Name'] + ',' +\
                 row['Text to identify Mall'] + ',' +\
                 row['Text to identify Merchant'].encode('utf8') + ',' +\
                 row['ZipCode to identify Mall'] + ',' +\
                 row['GST to identify Merchant'] + '\n')
    
    
    
    
    pd.Index([u'Rank', u'CRM LocationCode', u'CRM Location Name',
           u'Text to identify Mall', u'Text to identify Merchant',
           u'ZipCode to identify Mall', u'GST to identify Merchant'],
          dtype='object')
    pd.Index([u'PIC', u'Rank', u'CRM LocationCode', u'CRM Location Name',
           u'Text to identify Mall', u'Text to identify Merchant',
           u'ZipCode to identify Mall', u'GST to identify Merchant', u'Status',
           u'Remarks'],
          dtype='object')    
    
    
    
    
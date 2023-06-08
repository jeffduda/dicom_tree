import sys
import os
import argparse
import pydicom
from pydicom.sequence import Sequence
from pydicom.dataset import Dataset
#from prettytable import PrettyTable
import pandas as pd
from pydicom.uid import generate_uid
from datetime import datetime
import logging
import json

def get_tag(struct, check):
    el = check.get('Group')+check.get('Element')
    return( struct.get(el) )

def check_tag(struct, check):
    tag_val = get_tag(struct, check).get('Value')

    idx = check.get('Index')
    if idx is None:
        idx=0
    tag_val=tag_val[0]

    valid_value = check_value(tag_val, check)
    return(valid_value)

def check_value(value, check):

    valid=True
    if check.get('Operator')=='eq':
        value == check.get('Value')
    return(valid)

def get_value(instance, name, index=0):
    return_value="NA"
    if name in instance:
        value = instance.get(name).get('Value')
        if value is None:
            return "NA"

        if index is None:
            if len(value) == 1:
                return(str(value[0]))
            else:
                return(str(value))
        
        if index < len(value):
            return_value = str(value[index])

    return(return_value)

def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    #my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter', required=True)  
    my_parser.add_argument('trees', type=str, nargs='+', help='list of json fles') 
    my_parser.add_argument('-k', '--key', type=str, help='json file of dicom tags to extract', required=True)
    my_parser.add_argument('-o', '--output', type=str, help='output csv file', required=True) 
    args = my_parser.parse_args()

    logging.info("Reading key file: %s" % args.key)
    key_file = open(args.key)
    key = json.load(key_file)

    rows=[]
    for tree in args.trees:

        logging.info("Reading tree file: %s" % tree)
        tree_file = open(tree)
        tree = json.load(tree_file)

        for study in tree['StudyList']:
            for series in study['SeriesList']:
                row={}
                for study_key in key['Study']:
                    if study_key in study:
                        row[study_key] = get_value(study, study_key, index=None)
                    else:
                        row[study_key] = "NA"

                for series_key in key['Series']:
                    if series_key in series:
                        row[series_key] = get_value(series, series_key, index=None)
                    else:
                        row[series_key] = "NA"
                
                for instance_key in key['Instance']:
                    if instance_key in series['InstanceList'][0]:
                        row[instance_key] = get_value(series['InstanceList'][0], instance_key, index=None)
                    else:
                        row[instance_key] = "NA"

                row['NumberInstances'] = len(series['InstanceList'])

                rows.append(row)
            
            

    df = pd.DataFrame(rows)
    print(df)
    df.to_csv(args.output, index=False)


    return(0)

if __name__=="__main__":
    sys.exit(main())

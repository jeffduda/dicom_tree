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
        
        if index < len(value):
            return_value = str(value[index])

    return(return_value)

def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter (one series only)', required=True) 
    my_parser.add_argument('-d', '--dicom_tags', type=str, nargs='+', help='series level dicom tags to extract', required=True)
    my_parser.add_argument('-i', '--instance_tags', type=str, nargs='+', help='instance level dicom tags to extract', required=False)
    my_parser.add_argument('-s', '--stats', type=str, nargs='+', help='stats to add', required=True)
    my_parser.add_argument('-c', '--constants', type=str, nargs='+', help='values for each row', required=False)
    my_parser.add_argument('-o', '--output', type=str, help='output file', required=True)
    args = my_parser.parse_args()

    logging.info("Reading tree file: %s" % args.tree)
    tree_file = open(args.tree)
    tree = json.load(tree_file)

    # For now, limited to a tree with only one study and one series
    if len(tree['StudyList']) > 1:
        logging.error("More than one study in tree file")
        return(1)
    if len(tree['StudyList'][0]['SeriesList']) > 1:
        logging.error("More than one series in tree file")
        return(1)
    
    study=tree['StudyList'][0]
    series=study['SeriesList'][0]
    instance=series['InstanceList'][0]

    # Values from the tree will be in every line of the output
    series_dict={}
    for idx in range(0, len(args.dicom_tags), 2):
        tag_name = args.dicom_tags[idx]
        value_index = int(args.dicom_tags[idx+1])

        if tag_name in series:
            val_list = series[tag_name]['Value']
            if value_index < len(val_list):
                series_dict[tag_name] = val_list[value_index]
            else:
                logging.error("Index %d out of range for tag %s" % (value_index, tag_name))
                return(1)
        else:
            logging.error("Tag %s not found in series" % tag_name)
            return(1)

    if args.instance_tags is not None:
        for idx in range(0, len(args.instance_tags), 2):
            tag_name = args.instance_tags[idx]
            value_index = int(args.instance_tags[idx+1])

            if tag_name in instance:
                val_list = instance[tag_name]['Value']
                if value_index < len(val_list):
                    series_dict[tag_name] = val_list[value_index]
                else:
                    logging.error("Index %d out of range for tag %s" % (value_index, tag_name))
                    return(1)
            else:
                logging.error("Tag %s not found in instance" % tag_name)
                return(1)
            
    for idx in range(0, len(args.constants), 2):
        tag_name = args.constants[idx]
        value = args.constants[idx+1]
        series_dict[tag_name] = value

    col_names = list(series_dict.keys())
    col_names.extend(['label', 'measure', 'metric', 'value'])
    #df = pd.DataFrame(columns=col_names)
    dat = []

    for stat_file in args.stats:
        with open(stat_file) as f:
            stats = json.load(f)
            for stat in stats.keys():
                label=stat
                stat_dict = stats[stat]
                for measure in stat_dict.keys():
                    measure_dict = stat_dict[measure]
                    for metric in measure_dict.keys():
                        metric_value=measure_dict[metric]
                        row = series_dict.copy()
                        row['label'] = label
                        row['measure'] = measure
                        row['metric'] = metric
                        row['value'] = metric_value
                        dat.append(row)

    df = pd.DataFrame(dat, columns=col_names)
    df.to_csv(args.output, index=False, float_format='%.4f')

    return(0)

if __name__=="__main__":
    sys.exit(main())

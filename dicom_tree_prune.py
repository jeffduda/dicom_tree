import sys
import os
import argparse
import pydicom
from pydicom.sequence import Sequence
from pydicom.dataset import Dataset
from prettytable import PrettyTable
import pandas as pd
from pydicom.uid import generate_uid
from datetime import datetime
import logging
import json

def get_tag(struct, check):
    el = check.get('Group')+check.get('Element')
    return( struct.get(el) )

def check_tag(struct, check):

    tag = get_tag(struct, check)

    # Check for existence conditions
    if check.get('Operator')=='dne':
        return(tag is None)
    elif check.get('Operator')=='exists':
        return(tag is not None)

    # If tag does not exist, return false
    if tag is None:
        return(False)
    
    if 'Value' not in tag:
        return(False)

    # Get value of tag in struct
    tag_val = tag.get('Value')

    idx = check.get('Index')
    if idx is None:
        idx=0
    tag_val=tag_val[0]

    val_type = check.get('Type')
    if val_type=='str':
        tag_val=str(tag_val)
    if val_type=='int':
        tag_val=int(tag_val)
    if val_type=='float':
        tag_val=float(tag_val)

    valid_value = check_value(tag_val, check)
    return(valid_value)

def check_value(value, check):

    # "dne" and "exists" are handled in check_tag

    valid=True
    if check.get('Operator')=='eq':
        check_value = check.get('Value')
        valid = check_value==value
    elif check.get('Operator')=='ne':
        check_value = check.get('Value')
        valid = check_value != value
    elif check.get("Operator")=="gt":
        check_value = check.get("Value")
        valid = value > check_value
    elif check.get("Operator")=="lt":
        check_value = check.get("Value")
        valid = value < check_value
    elif check.get("Operator")=="ge":
        check_value = check.get("Value")
        valid = value >= check_value    
    elif check.get("Operator")=="le":
        check_value = check.get("Value")
        valid = value <= check_value
    elif check.get("Operator")=="in":
        check_value = check.get("Value")
        valid = value in check_value
    elif check.get("Operator")=="not_in":
        check_value = check.get("Value")
        valid = value not in check_value



    else:
        logging.error("Unknown operator: "+str(check.get("Operator")))
        valid=False

    return(valid)

def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter', required=True)
    my_parser.add_argument('-f', '--filter', type=str, help='json file of dicom tags to filter on', required=True)
    my_parser.add_argument('-o', '--output', type=str, help='filtered dicom tree', required=True)
    args = my_parser.parse_args()

    logging.info("Reading tree file: %s" % args.tree)
    tree_file = open(args.tree)
    tree = json.load(tree_file)

    logging.info("Reading filter file: %s" % args.filter)
    filter_file = open(args.filter)
    filter = json.load(filter_file)

    out_studies = []

    for study in tree['StudyList']:
        keep_study=True

        print("Check study: "+str(study.get("0020000D").get("Value")))
        print("Check study: "+str(study.get("00080050").get("Value")))

        # Check study level tags
        if 'Study' in filter:
            print("Checking study level tags")
            for check in filter['Study']:
                keep_study=keep_study and check_tag(study, check)

        # If study level tag fail, move to next study
        if not keep_study:
            logging.info("Ignore study: "+str(study.get("0020000D")))
            print("call continue")
            continue
        print("Keep study: "+str(study.get("0020000D").get("Value")))
        print("Keep study: "+str(study.get("00080050").get("Value")))
        

        # Keep study but empty the series list
        study_copy = study.copy()
        study_copy['SeriesList']=[]
        print("Reset series list")

        # Check series level tags
        if 'Series' in filter:
            print("Checking "+str(len(study['SeriesList'])) +" series")
            for series in study['SeriesList']:
                print("  Check series: "+str(series.get("0020000E").get("Value")[0]))

                keep_series=True
                for check in filter['Series']:
                    print(" -- Series level "+str(check['Group']+" "+str(check["Element"])))
                    keep_series = keep_series and check_tag( series, check )
                if not keep_series:
                    logging.info("Ignore series: "+str(series.get("0020000E")))
                    print("call continue")
                    continue;

                # Keep series but empty the instance list
                series_copy = series.copy()
                series_copy['InstanceList'] = []
                print("  Checking instances for: "+str(series.get("0020000E").get("Value")[0]))
                print("  Checking n="+str(len(series['InstanceList'])))

                idx=0
                instList=[]
                if 'Instance' in filter:
                    for instance in series['InstanceList']:
                        #print("    checking: "+str(idx))
                        idx=idx+1
                        keep_instance=True
                        for check in filter['Instance']:
                            keep_instance = keep_instance and check_tag(instance, check)

                        if keep_instance:
                            #print(keep_instance)
                            instList.append(instance)
                            #print( "      "+str(len(series_copy['InstanceList'])))

                series_copy['InstanceList']=instList

                if len(series_copy['InstanceList']) > 0:
                    study_copy['SeriesList'].append(series_copy)
                    print("  had "+str(len(series["InstanceList"]))+" instances")
                    print("  now has "+str(len(series_copy["InstanceList"]))+" instances")
                else:
                    print("Pruned: "+str(series.get("0020000E").get("Value")[0]))

        if len(study_copy['SeriesList']) > 0 :
            out_studies.append(study_copy)

    if len(out_studies) > 0:
        out_tree={'Directory': tree['Directory'], 'StudyList': out_studies}
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(out_tree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

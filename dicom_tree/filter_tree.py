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
        check_value = check.get('Value')
        valid = check_value==value
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
                print("  "+str(len(series_copy['InstanceList'])))

                if 'Instance' in filter:
                    for instance in series['InstanceList']:
                        for check in filter['Instance']:
                            if check_tag(instance, check):
                                series_copy['InstanceList'].append(instance)
                                print( "    "+str(len(series_copy['InstanceList'])))

                if len(series_copy['InstanceList']) > 0:
                    study_copy['SeriesList'].append(series_copy)
                    print("  had "+str(len(series["InstanceList"]))+" instances")
                    print("  now has "+str(len(series_copy["InstanceList"]))+" instances")

        if len(study_copy['SeriesList']) > 0 :
            out_studies.append(study_copy)

    if len(out_studies) > 0:
        out_tree={'Directory': tree['Directory'], 'StudyList': out_studies}
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(out_tree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

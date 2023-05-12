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

def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter', required=True)   
    args = my_parser.parse_args()

    logging.info("Reading tree file: %s" % args.tree)
    tree_file = open(args.tree)
    tree = json.load(tree_file)


    for study in tree['StudyList']:
        keep_study=True

        print(str(study.get("StudyInstanceUID").get("Value")[0]))
        #print("Check study: "+str(study.get("00080050").get("Value")))



        for series in study['SeriesList']:
            acq_list = []
            mod_list = []
            for instance in series['InstanceList']:
                if "AcquisitionNumber" in instance:
                    acq = str(instance.get("AcquisitionNumber").get("Value")[0])
                    if acq not in acq_list:
                        acq_list.append(acq)
                if "Modality" in instance:
                    mod = str(instance.get("Modality").get("Value")[0])
                    if mod not in mod_list:
                        mod_list.append(mod)

            print("  series: "+str(series.get("SeriesInstanceUID").get("Value")[0]))
            print("    description: "+str(series.get("SeriesDescription").get("Value")[0]))
            print("    number: "+str(series.get("SeriesNumber").get("Value")[0]))
            print("    modality: "+str(series.get("Modality").get("Value")[0]))
            print("    nInstances: "+str(len(series['InstanceList'])))
            print("    acquisitions: ["+",".join(acq_list)+"]")


    return(0)

if __name__=="__main__":
    sys.exit(main())

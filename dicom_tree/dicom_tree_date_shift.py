import sys
import os
import argparse
import pydicom
from pydicom.sequence import Sequence
from pydicom.dataset import Dataset
from prettytable import PrettyTable
import pandas as pd
from pydicom.uid import generate_uid
import datetime
import logging
import json

def shift_date(date, days):
    date_stmp = datetime.datetime.strptime(date, '%Y%m%d')
    date_stmp = date_stmp + datetime.timedelta(days=days)
    return( date_stmp.strftime('%Y%m%d') )

def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-i', '--input', type=str, help='json file of dicom studies to filter', required=True)
    my_parser.add_argument('-d', '--days_offset', type=float, help='days to shift dates by', required=True)
    my_parser.add_argument('-o', '--output', type=str, help='date shifted dicom tree', required=True)
    args = my_parser.parse_args()

    args.days_offset = int(args.days_offset)

    logging.info("Reading tree file: %s" % args.input)
    tree_file = open(args.input)
    tree = json.load(tree_file)

    if 'Dicom' not in tree:
        logging.error("No Dicom key found in tree")
        return(1)
    study = tree['Dicom']

    if 'StudyDate' in study:
        study['StudyDate']['Value'][0]=shift_date(study['StudyDate']['Value'][0], args.days_offset)

    if 'SeriesDate' in study:
        study['SeriesDate']['Value'][0]=shift_date(study['SeriesDate']['Value'][0], args.days_offset)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

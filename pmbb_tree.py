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
import pandas as pd

def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-i', '--input', type=str, help='input tree', required=True)
    my_parser.add_argument('-k', '--key', type=str, help='id key file', required=True)
    my_parser.add_argument('-o', '--output', type=str, help='output tree', required=True)
    args = my_parser.parse_args()

    logging.info("Reading input tree file: %s" % args.input)
    tree_file = open(args.input)
    tree = json.load(tree_file)

    logging.info("Reading input key file: %s" % args.key)
    df=pd.read_csv(args.key)
    df["EMPI"]=df["EMPI"].astype('str')
    df["PMBB_ID"]=df["PMBB_ID"].astype('str')

    instance = tree['StudyList'][0]['SeriesList'][0]['InstanceList'][0]['Filename']
    dcm = pydicom.dcmread(instance,stop_before_pixels=True)
    PatientID = dcm.get("PatientID")
    PMBBID="INVALID"
    if not PatientID is None:
        try:
            PMBBID = (df.loc[df['EMPI'] == PatientID,"PMBB_ID"])
            PMBBID = (PMBBID.tolist()[0])
            print(str(PMBBID))
        except:
            print("Invalid ID")
    
    if not PMBBID=="INVALID":
        for study in tree['StudyList']:
            study["PMBBID"]=PMBBID
            for series in study['SeriesList']:
                series["PMBBID"]=PMBBID

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

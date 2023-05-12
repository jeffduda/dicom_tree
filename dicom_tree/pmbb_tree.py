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
import pandas as pd



def main():

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-i', '--input', type=str, help='input tree', required=True)
    my_parser.add_argument('-k', '--key', type=str, help='id key file', required=True)
    my_parser.add_argument('-o', '--output', type=str, help='output tree', required=True)
    my_parser.add_argument('-l', '--log', type=str, help='logfile', required=False, default=None)
    args = my_parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
    logger=logging.getLogger("pmbb_tree")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if args.log is not None:
        print("  add logging file: "+args.log)
        fh = logging.FileHandler(args.log, 'a')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.info("Reading input tree file: %s" % args.input)
    tree_file = open(args.input)
    tree = json.load(tree_file)

    logger.info("Reading input key file: %s" % args.key)
    df=pd.read_csv(args.key)
    df["EMPI"]=df["EMPI"].astype('str')
    df["PMBB_ID"]=df["PMBB_ID"].astype('str')
    df["calico_id"]=df["calico_id"].astype('str')
    df["days_offset"]=df["days_offset"].astype('int')

    instance = tree['StudyList'][0]['SeriesList'][0]['InstanceList'][0]['Filename']
    dcm = pydicom.dcmread(instance,stop_before_pixels=True)
    PatientID = dcm.get("PatientID")
    PMBBID="INVALID"
    calico_id="INVALID"
    patient_date_shift=0
    if not PatientID is None:
        try:
            calico_id = (df.loc[df['EMPI'] == PatientID,"calico_id"])
            calico_id = (calico_id.tolist()[0])
            logger.info("Assigning calico_id: "+str(calico_id))

            patient_date_shift = (df.loc[df['EMPI'] == PatientID,"days_offset"])
            patient_date_shift = int(patient_date_shift.tolist()[0])

        except:
             logger.error("Invalid ID")

    
    if not calico_id=="INVALID":
        if not "Calico" in tree:
            tree["Calico"]={}
        tree["Calico"]["calico_id"]=calico_id
        
        for study in tree['StudyList']:
            for series in study['SeriesList']:
                series["PMBBID"]=PMBBID

    # shift dates
    if patient_date_shift!=0:
        for study in tree['StudyList']:
            if 'StudyDate' in study:
                study_date = study['StudyDate']['Value'][0]
                study_date = datetime.datetime.strptime(study_date, '%Y%m%d')
                study_date = study_date + datetime.timedelta(days=patient_date_shift)
                study['StudyDate']['Value'][0] = study_date.strftime('%Y%m%d')

            for series in study['SeriesList']:
                if 'StudyDate' in series:
                    study_date = series['StudyDate']['Value'][0]
                    study_date = datetime.datetime.strptime(study_date, '%Y%m%d')
                    study_date = study_date + datetime.timedelta(days=patient_date_shift)
                    series['StudyDate']['Value'][0] = study_date.strftime('%Y%m%d')
                if 'SeriesDate' in series:
                    series_date = series['SeriesDate']['Value'][0]
                    series_date = datetime.datetime.strptime(series_date, '%Y%m%d')
                    series_date = series_date + datetime.timedelta(days=patient_date_shift)
                    series['SeriesDate']['Value'][0] = series_date.strftime('%Y%m%d')

                for instance in series['InstanceList']:
                    if 'StudyDate' in instance:
                        study_date = instance['StudyDate']['Value'][0]
                        study_date = datetime.datetime.strptime(study_date, '%Y%m%d')
                        study_date = study_date + datetime.timedelta(days=patient_date_shift)
                        instance['StudyDate']['Value'][0] = study_date.strftime('%Y%m%d')
                    if 'SeriesDate' in instance:
                        series_date = instance['SeriesDate']['Value'][0]
                        series_date = datetime.datetime.strptime(series_date, '%Y%m%d')
                        series_date = series_date + datetime.timedelta(days=patient_date_shift)
                        instance['SeriesDate']['Value'][0] = series_date.strftime('%Y%m%d')

    with open(args.output, 'w', encoding='utf-8') as f:
        logger.info("Writing to: "+args.output)
        json.dump(tree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

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


class DicomTree:

    def __init__(self, directory=None):

        self.directory = directory
        self.files = []             # list of files to scan
        self.study_tags = []        # list of study level tags to extract
        self.series_tags = []       # list of series level tags to extract
        self.instance_tags = []     # list of instance level tags to extract

        self._study_dict = None
        self._series_dict = None
        self._instance_dict = None

        self.studies = []           # list of studies (dicts) found in the files

        self._instance_code = "00080018"
        self._series_code = "0020000E"
        self._study_code = "0020000D"

        # some default study level tags of interest
        self.default_study_tags = [
            {"Group": "0008", "Element": "0050", "Name": "AccessionNumber"},
            {"Group": "0008", "Element": "0020", "Name": "StudyDate"},
            {"Group": "0008", "Element": "0030", "Name": "StudyTime"},
            {"Group": "0008", "Element": "1030", "Name": "StudyDescription"},
        ]    

        # some default series level tags of interest
        self.default_series_tags = [
            {"Group": "0008", "Element": "0060", "Name": "Modality"},
            {"Group": "0008", "Element": "0021", "Name": "SeriesDate"},
            {"Group": "0008", "Element": "0031", "Name": "SeriesTime"},
            {"Group": "0008", "Element": "103E", "Name": "SeriesDescription"},
            {"Group": "0020", "Element": "0011", "Name": "SeriesNumber"}
        ]

        # some default instance level tags of interest
        self.default_instance_tags = [
            {"Group": "0018", "Element": "0050", "Name": "SliceThickness"},
            {"Group": "0008", "Element": "0008", "Name": "ImageType"}
        ]

    def tag_to_dict_entry(self, tag):
        key=tag["Group"]+tag["Element"]
        name=""
        if 'Name' in tag:
            name=tag["Name"]
        else:
            name = pydicom.DataElement((tag["Group"],tag["Element"]), None, None).name
        return( (key, name) )

    def tag_list_to_dict(self, tag_list):
        rlist = [ self.tag_to_dict_entry(x) for x in tag_list ]
        return( dict(rlist) )

    def get_tag_dicts(self):
        self._study_dict = self.tag_list_to_dict(self.study_tags)
        self._series_dict = self.tag_list_to_dict(self.series_tags)
        self._instance_dict = self.tag_list_to_dict(self.instance_tags)

    def set_default_tags(self):
        self.set_default_study_tags()
        self.set_default_series_tags()
        self.set_default_instance_tags()

    def set_default_study_tags(self):
        self.study_tags = self.default_study_tags

    def set_default_series_tags(self):
        self.series_tags = self.default_series_tags

    def set_default_instance_tags(self):
        self.instance_tags = self.default_instance_tags

    def create_instance(self, js, filename=None):
        instance = {self._instance_code: js[self._instance_code]} #SOPInstanceUID is a required tag
        if not filename is None:
            instance['Filename'] = filename
            
        for tag in self._instance_dict.keys():
            if tag in js:
                instance[tag] = js[tag]
        return instance

    def create_series(self, js):
        instance = self.create_instance(js)
        series = {self._series_code: js[self._series_code], "InstanceList": [instance]} #SeriesInstanceUID is a required tag

        for tag in self._series_dict.keys():
            if tag in js:
                series[tag] = js[tag]

        return series

    def create_study(self, js):
 
        series = self.create_series(js)
        study = {self._study_code: js[self._study_code], "SeriesList": [series]} #StudyInstanceUID is a required tag

        for tag in self._study_dict.keys():
            if tag in js:
                study[tag] = js[tag]

        return study

    def study_exists(self, study_uid):
        for study in self.studies:
            if study_uid == study[self._study_code]['Value'][0]:
                return True
        return False

    def is_series_in_study(self, study, series_uid):
        for series in study["SeriesList"]:
            if series_uid == series[self._series_code]['Value'][0]:
                return True
        return False

    def is_instance_in_series(self, series, instance_uid):
        for instance in series["InstanceList"]:
            if instance_uid == instance[self._instance_code]['Value'][0]:
                return True
        return False

    def add_instance(self, filename, ds):
        study=None
        series=None
        js = ds.to_json_dict()
        instance=self.create_instance(js, filename=filename)
        #instance['Filename'] = filename

        if not self.study_exists(js[self._study_code]['Value'][0]):    
            logging.info("Adding new study: %s" % js[self._study_code]['Value'][0])
            study = self.create_study(js)
            logging.info("Adding new series: %s" % study['SeriesList'][0][self._series_code]['Value'][0])
            self.studies.append(study)

        else:
            study = [x for x in self.studies if x[self._study_code]==js[self._study_code]][0]

        if not self.is_series_in_study(study, js[self._series_code]['Value'][0]):
            logging.info("Adding new series: %s" % js[self._series_code]['Value'][0])
            series = self.create_series(js)
            study['SeriesList'].append(series)
        else:
            series = [x for x in study['SeriesList'] if x[self._series_code]==js[self._series_code]][0]

        if not self.is_instance_in_series(series, js[self._instance_code]['Value'][0]):
            #logging.info("Adding new instance: %s" % js[self._instance_code]['Value'][0])
            series['InstanceList'].append(instance)


    def read_directory(self, recursive=0):

        self.get_tag_dicts()

        for level, (dirpath, dirnames, filenames) in enumerate(os.walk(self.directory)):
            fullnames = [os.path.join(dirpath,x) for x in filenames]
            self.files.extend(fullnames)
            if level >= recursive:
                break       

        logging.info("Found %i candidate files" % len(self.files)) 

        for f in self.files:
            ds=None
            try:
                ds = pydicom.dcmread(f,stop_before_pixels=True)
            except:
                logging.warning("Could not read file: %s" % f)

                # Force reading can be problematic. Need more checks on the
                # file before adding to ensure it is a valid dicom file

                #try:
                #    ds = pydicom.dcmread(f,force=True,stop_before_pixels=True)
                #except:
                #    logging.warning("Could not read file: %s" % f)
                #else:
                #    logging.warning("Forced reading of file: %s" % f)

            if not ds is None:
                self.add_instance(f,ds)

    # Get a value for a dicom tag from the tag name
    def get_tag_value( self, tag ):

        value = tag.value
        if isinstance(value, pydicom.multival.MultiValue):
            #value="/".join(list(value))
            value = list(value)
        elif isinstance(value, pydicom.Sequence):
            print("sequence value")
            print(value)

        if tag=="00081032":
            print("Found CPT Code")

        return(value)

def main():

    logging.basicConfig(level=logging.DEBUG)

    my_parser = argparse.ArgumentParser(description='Display DICOM Header Info')
    my_parser.add_argument('-p', '--path', type=str, help='the path to the directory', required=True)
    my_parser.add_argument('-a', '--accession', type=str, help='accession number', required=False)
    my_parser.add_argument('-r', '--recursive', dest="recursive", help="how many directories deep to search", type=int, default=0)
    my_parser.add_argument('-o', '--output', type=str, help='output json file', required=True)
    my_parser.add_argument('-t', '--tagfile', type=str, help='json file of dicom tags to include', required=False)
    args = my_parser.parse_args()
    print(args)
    start = datetime.now()

    tags=None
    if not args.tagfile is None:
        logging.info("Reading tag file: %s" % args.tagfile)
        with open(args.tagfile) as f:
            tags = json.load(f)


    if os.path.isdir(str(args.path)):
        logging.info("Scanning directory: %s" % args.path)
        dicomTree = DicomTree(args.path)

        # Define the tags to extract from dicom files
        if tags is None:
            dicomTree.set_default_tags()
        else:
            if 'Study' in tags:
                dicomTree.study_tags=tags['Study']
            else:  
                dicomTree.set_default_study_tags()

            if 'Series' in tags:
                dicomTree.series_tags=tags['Series']
            else:
                dicomTree.set_default_series_tags()

            if 'Instance' in tags:
                dicomTree.instance_tags=tags['Instance']
            else:
                dicomTree.set_default_instance_tags()


        dicomTree.read_directory(args.recursive)
        

    finish = datetime.now()
    logging.info("Finished in %s" % str(finish-start))

    outTree = {"Directory": args.path, "StudyList": dicomTree.studies}

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(outTree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

import sys
import os
import argparse
import pydicom
from pydicom.sequence import Sequence
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid

#from prettytable import PrettyTable
import pandas as pd
from pydicom.uid import generate_uid
from datetime import datetime
import logging
import json


class DicomTree:

    def __init__(self, directory=None, make_logger=True):

        self.directory = directory
        self.files = []             # list of files to scan
        self.study_tags = []        # list of study level tags to extract
        self.series_tags = []       # list of series level tags to extract
        self.instance_tags = []     # list of instance level tags to extract

        self._study_dict = None
        self._series_dict = None
        self._instance_dict = None

        self.studies = []           # list of studies (dicts) found in the files

        self._instance_code = {"Group":"0008", "Element": "0018", "Name": "SOPInstanceUID"}
        self._series_code = {"Group": "0020", "Element": "000E", "Name": "SeriesInstanceUID"}
        self._study_code = {"Group": "0020", "Element": "000D", "Name": "StudyInstanceUID"}

        self._study_code_key = self._study_code["Group"]+self._study_code["Element"]
        self._series_code_key = self._series_code["Group"]+self._series_code["Element"]
        self._instance_code_key = self._instance_code["Group"]+self._instance_code["Element"]

        self.uid_prefix=None
        self.use_name=False

        self.logger=None

        if make_logger:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
            self.logger=logging.getLogger("dicom_tree")
            #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            #if args.log is not None:
            #    print("  add logging file: "+args.log)
            #    fh = logging.FileHandler(args.log, 'a')
            #    fh.setFormatter(formatter)
            #    self.logger.addHandler(fh)


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

    def __repr__(self):
        print("Directory: "+str(self.directory))
        print(str(self.studies))
        return("")

    # Check for valid group,element and add name if not defined
    def tag_to_dict_entry(self, tag):
        # this is what pydicom uses in '.to_json_dict()'
        key = tag["Group"]+tag["Element"]

        try:
            name = pydicom.DataElement((tag["Group"],tag["Element"]), None, None).name
        except:
            self.logger.warning("Unknown tag: "+str(tag))
            return None
        
        if 'Name' in tag:
            name=tag["Name"]

        return( (key, {"Name": name, "Group": tag["Group"], "Element": tag["Element"]}) )

    # Convert a list of tags to a dictionary
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

    def get_entry(self, tag, value):
        val=None
        if "Value" in value:
            val = value["Value"]
        dat = {"Group": tag["Group"], "Element": tag["Element"], "vr": value["vr"], "Value": val}
        entry = { tag["Name"]:  dat }
        return entry

    def create_instance(self, js, filename=None):
        #self.logger.info("DicomTree.create_instance("+str(filename)+")")
        if self._instance_code_key not in js:
            self.logger.warning("Missing required tag: "+str(self._instance_code))
            return None
        
        instance = self.get_entry(self._instance_code, js[self._instance_code_key] )
        if not filename is None:
            instance['Filename'] = filename
            
        for key in self._instance_dict.keys():
            if key in js:
                instance.update(self.get_entry(self._instance_dict[key], js[key]))
        
        return instance

    def create_series(self, dat, filename=None):
        self.logger.info("DicomTree.create_series()")
        instance=None

        if self._series_code_key not in dat:
            self.logger.info("Creating new series UID")
            series_uid_dat = {"vr": "UI", "Value": pydicom.generate_uid()}
            series_uid_dat["Group"]=self._series_code["Group"]
            series_uid_dat["Element"]=self._series_code["Element"]
            series_uid_dat["Name"]=self._series_code["Name"]
            dat[self._series_code_key] = series_uid_dat
        
        instance = self.create_instance(dat, filename=filename)
        series = self.get_entry(self._series_code, dat[self._series_code_key])
        
        # Get series level entries
        for key in self._series_dict.keys():
            if key in dat:
                series.update(self.get_entry(self._series_dict[key], dat[key]))

        series.update({"InstanceList": [instance]})
        return series

    def create_study(self, js, filename=None):

        self.logger.info("DicomTree.create_study()")
 
        series = self.create_series(js, filename)
        study = self.get_entry( self._study_code, js[self._study_code_key] )

        for tag in self._study_dict.keys():
            if tag in js:
                study.update(self.get_entry(self._study_dict[tag], js[tag]))
        study.update({"SeriesList": [series]})

        return study

    def study_exists(self, study_uid):
        for study in self.studies:
            if study_uid == study[self._study_code['Name']]['Value'][0]:
                return True
        return False
    
    def get_study(self, study_uid):
        for study in self.studies:
            if study_uid == study[self._study_code['Name']]['Value'][0]:
                return study
        return None

    def is_series_in_study(self, study, series_uid):
        for series in study["SeriesList"]:
            if series_uid == series[self._series_code['Name']]['Value'][0]:
                return True
        return False

    def get_series_from_study(self, study, series_uid):
        for series in study["SeriesList"]:
            if series_uid == series[self._series_code['Name']]['Value'][0]:
                return series
        return None
    
    def get_instance_from_series(self, series, instance_uid):
        for instance in series["InstanceList"]:
            if instance_uid == instance[self._instance_code['Name']]['Value'][0]:
                return instance
        return None

    def is_instance_in_series(self, series, instance_uid):
        for instance in series["InstanceList"]:
            if instance_uid == instance[self._instance_code['Name']]['Value'][0]:
                return True
        return False

    def add_instance(self, filename, ds):

        js = ds.to_json_dict()

        instance_study_uid = js[self._study_code_key]['Value'][0]
        instance_series_uid = js[self._series_code_key]['Value'][0]
        instance_instance_uid = js[self._instance_code_key]['Value'][0]

        #self.logger.info("File has study UID: %s" % instance_study_uid)
        #print(js["0020000D"])
        # Create new study if it doesn't exist
        study = self.get_study(instance_study_uid)
        if study is None:
            self.logger.info("Adding new study")
            study = self.create_study(js, filename)
            self.logger.info("Adding new series")
            self.studies.append(study)

        series = self.get_series_from_study(study, instance_series_uid)
        if series is None:
            self.logger.info("Adding new series")
            series = self.create_series(js, filename)
            study['SeriesList'].append(series)

        instance = self.get_instance_from_series(series, instance_instance_uid)
        if instance is None:
            #self.logger.info("Adding new instance: %s" % instance_instance_uid)
            instance = self.create_instance(js, filename)
            series['InstanceList'].append(instance)


        #if not self.is_instance_in_series(series, js[self._instance_code_key]['Value'][0]):
        #    logging.info("Adding new instance: %s" % js[self._instance_code_key]['Value'][0])
        #    series['InstanceList'].append(instance)


    def read_directory(self, recursive=0):

        self.get_tag_dicts()

        for level, (dirpath, dirnames, filenames) in enumerate(os.walk(self.directory)):
            fullnames = [os.path.join(dirpath,x) for x in filenames]
            self.files.extend(fullnames)
            if level >= recursive:
                break       

        self.logger.info("Found %i candidate files" % len(self.files)) 

        for i,f in enumerate(self.files):
            #print(i)
            ds=None
            try:
                ds = pydicom.dcmread(f,stop_before_pixels=True)
            except:
                self.logger.warning("Could not read file: %s" % f)

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

        return(value)

    def grow(self, directory):
        self.directory = directory
        self.studies = []

    def grow_study(self, study={}):
        new_study = study.copy()
        if self._study_code not in new_study:
            uid = generate_uid(prefix=self.uid_prefix)
            self.logger.info("Generating new study UID: "+uid)
            new_study[self._study_code] = uid

        if "SeriesList" not in new_study:
            new_study["SeriesList"]= []
        self.studies.append(new_study)

    def grow_series(self, study_id, series={}):
        new_series = series.copy()

        if self._series_code not in new_series:
            uid = generate_uid(prefix=self.uid_prefix)
            self.logger.info("Generating new series UID: "+uid)
            new_series[self._series_code] = uid

        if "InstanceList" not in new_series:
            new_series["InstanceList"]= []

        study_idx = None
        if isinstance(study_id, int):
            study_idx = study_id
        if isinstance(study_id, str):
            study_list = [i for i, x in enumerate(self.studies) if x[self._study_code] == study_id]
            if len(study_list)==0:
                self.logger.error("Could not find study: "+study_id)
                return
            else:
                study_idx = study_list[0]

        if study_idx >= len(self.studies):
            self.logger.error("Study index out of range: "+str(study_id))
            return

        self.studies[study_idx]["SeriesList"].append(new_series)

    def to_json(self, filename):
        outTree = {"Directory": self.directory, "StudyList": self.studies}

        with open(filename, 'w', encoding='utf-8') as f:
            self.logger.info("Writing to: "+filename)
            json.dump(outTree, f, ensure_ascii=False, indent=4)


def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Display DICOM Header Info')
    my_parser.add_argument('-p', '--path', type=str, help='the path to the directory', required=True)
    my_parser.add_argument('-a', '--accession', type=str, help='accession number', required=False)
    my_parser.add_argument('-r', '--recursive', dest="recursive", help="how many directories deep to search", type=int, default=0)
    my_parser.add_argument('-o', '--output', type=str, help='output json file', required=True)
    my_parser.add_argument('-t', '--tagfile', type=str, help='json file of dicom tags to include', required=False)
    my_parser.add_argument('-l', '--log', type=str, help='logfile', required=False, default=None)
    my_parser.add_argument('-n', '--name', help='include name of each tag', default=False, required=False, action='store_true')
    args = my_parser.parse_args()
    print(args)

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
    logger=logging.getLogger("dicom_tree")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if args.log is not None:
        #print("  add logging file: "+args.log)
        fh = logging.FileHandler(args.log, 'a')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    ch = logging.StreamHandler()

    start = datetime.now()

    tags=None
    if not args.tagfile is None:
        logger.info("Reading tag file: %s" % args.tagfile)
        with open(args.tagfile) as f:
            tags = json.load(f)


    if os.path.isdir(str(args.path)):
        logger.info("Scanning directory: %s" % args.path)
        dicomTree = DicomTree(args.path)
        dicomTree.use_name=args.name

        dicomTree.logger=logger

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
    logger.info("Finished in %s" % str(finish-start))

    outTree = {"Directory": args.path, "StudyList": dicomTree.studies}

    with open(args.output, 'w', encoding='utf-8') as f:
        logger.info("Writing to: "+args.output)
        json.dump(outTree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

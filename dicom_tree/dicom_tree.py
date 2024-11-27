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

def longest_identical_sequence_indices(lst, tolerance=None):
    """Finds the indices of the longest sequence of identical values in a list.

    Args:
        lst: The input list.

    Returns:
        A list of tuples, where each tuple contains the starting and ending indices of a longest sequence.
    """

    if not lst:
        return []

    max_len = 1
    max_start = 0
    max_end = 0
    current_len = 1
    current_start = 0

    for i in range(1, len(lst)):

        continuous=False
        if tolerance is not None:
            if abs(lst[i] - lst[i - 1]) <= tolerance:
                continuous=True
        else:
            if lst[i] == lst[i - 1]:
                continuous=True 

        if continuous:
            current_len += 1
        else:
            if current_len > max_len:
                max_len = current_len
                max_start = current_start
                max_end = i - 1
            current_len = 1
            current_start = i

    # Check for the last sequence
    if current_len > max_len:
        max_len = current_len
        max_start = current_start
        max_end = len(lst) - 1

    return (max_start, max_end)

def longest_evenly_spaced_sequences(nums):
    """
    Finds the longest sequences of evenly spaced values in a list.

    Args:
        nums: A list of numeric values.

    Returns:
        A list of lists, where each list contains all values in the longest sequence.
    """

    nums.sort()
    diffs=[0 for i in range(len(nums)-1)]

    for idx,num in enumerate(nums):
        if idx>0:
            diffs[idx-1]=num-nums[idx-1]

    chain=longest_identical_sequence_indices(diffs, tolerance=0.0001)
    evenly_spaced=nums[chain[0]:chain[1]+1]
    return evenly_spaced

def longest_consecutive_sequences(nums, first=False):
    """
    Finds the longest sequences of contiguous integers in a list.

    Args:
        nums: A list of integers.

    Returns:
        A list of tuples, where each tuple contains the starting and ending indices of a longest sequence.
    """

    num_set = set(nums)
    max_length = 0
    longest_sequences = []

    for num in nums:
        if num - 1 not in num_set:
            current_num = num
            current_length = 1

            while current_num + 1 in num_set:
                current_num += 1
                current_length += 1

            if current_length > max_length:
                max_length = current_length 

                longest_sequences = [(num, num + current_length - 1)]
            elif current_length == max_length:
                longest_sequences.append((num, num + current_length - 1))
    longest_chains=[]
    for i in longest_sequences:
        inst_list=[j for j in range(i[0],i[1]+1)]
        longest_chains.append(inst_list)
    
    if first:
        return longest_chains[0]
    
    return longest_chains


def list_files(path, levels=2):
    file_list = [f.path for f in os.scandir(path) if f.is_file()]
    if levels > 1:
        for d in list_dirs(path, levels=levels-1):
            file_list.extend(list_files(d, levels=1))

    return file_list

def list_dirs(path, levels=2):
    dir_list = [d.path for d in os.scandir(path) if d.is_dir()]
    if levels > 1:
        for d in dir_list:
            dir_list.extend(list_dirs(d, levels=levels-1))

    return dir_list

class DicomTree:

    def __init__(self, directory=None, make_logger=True):

        self.directory = directory
        self.files = []             # list of files to scan
        self.study_tags = []        # list of study level tags to extract
        self.series_tags = []       # list of series level tags to extract
        self.instance_tags = []     # list of instance level tags to extract

        self.comprehensive = False  # Use as many tags as possible

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

        # some default study level tags of interest
        self.default_study_tags = [
            {"Group": "0008", "Element": "0050", "Name": "AccessionNumber"},
            {"Group": "0008", "Element": "0020", "Name": "StudyDate"},
            {"Group": "0008", "Element": "0030", "Name": "StudyTime"},
            {"Group": "0008", "Element": "1030", "Name": "StudyDescription"},
            {"Group": "0008", "Element": "1032", "Name": "ProcedureCodeSequence"},
            {"Group": "0020", "Element": "000D", "Name": "StudyInstanceUID"},
            {"Group": "0020", "Element": "0010", "Name": "StudyID"}
        ]    

        # some default series level tags of interest
        self.default_series_tags = [
            {"Group": "0008", "Element": "0060", "Name": "Modality"},
            {"Group": "0008", "Element": "0021", "Name": "SeriesDate"},
            {"Group": "0008", "Element": "0031", "Name": "SeriesTime"},
            {"Group": "0008", "Element": "103E", "Name": "SeriesDescription"},
            {"Group": "0018", "Element": "0015", "Name": "BodyPartExamined"},
            {"Group": "0018", "Element": "1030", "Name": "ProtocolName"},
            {"Group": "0018", "Element": "5100", "Name": "PatientPosition"},
            {"Group": "0020", "Element": "0011", "Name": "SeriesNumber"},
            {"Group": "0020", "Element": "0060", "Name": "Laterality"}

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
            
        tag_list = self._instance_dict.keys()

        for key in tag_list:
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

    def fix_empty_PN(self, ds):
        for de in ds:
            if de.VR == "PN":
                replace=False
                pn_value = de.value
                for v,val in enumerate(de.value):
                    if len(val)==0:
                        replace=True
                        val = " "
                        pn_value[v] = val

                if replace:
                    de.value = pn_value
                    ds[de.tag] = de                
                         

    def add_instance(self, filename, ds):

        js=None
        try:
            js = ds.to_json_dict()
        except:
            self.fix_empty_PN(ds)
            js = ds.to_json_dict()
            return

        # Use all non-private tags
        if self.comprehensive:
            instance_dict={}
            for elem in ds:
                if not elem.is_private:
                    tag=elem.tag
                    key=f"{tag:>08X}"
                    value={"Name": elem.keyword, "Group": f"{tag.group:>04X}", "Element": f"{tag.element:>04X}"}
                    instance_dict[key]=value

            self._instance_dict = instance_dict

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


    def read_directory(self, recursive=1):

        self.get_tag_dicts()

        #for level, (dirpath, dirnames, filenames) in enumerate(os.walk(self.directory)):
        #    fullnames = [os.path.join(dirpath,x) for x in filenames]
        #    self.files.extend(fullnames)
        #    if level >= recursive:
        #        break       
        self.files = list_files(self.directory, levels=2)

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

    def contiguous_series(self):
        for study in self.studies:
            for series in study["SeriesList"]:
                inst_list=[]
                position_list=[]
                for instance in series["InstanceList"]:
                    if "InstanceNumber" in instance:
                        inst_list.append(instance["InstanceNumber"]["Value"][0])
                    if "SliceLocation" in instance:
                        position_list.append(instance["SliceLocation"]["Value"][0])

                inst_num_consecutive = longest_consecutive_sequences(inst_list, first=True)
                inst_consecutive=[]
                for instance in series["InstanceList"]:
                    if "InstanceNumber" in instance:
                        if instance["InstanceNumber"]["Value"][0] in inst_num_consecutive:
                            inst_consecutive.append(instance)   

                series["InstanceList"]=inst_consecutive



def main():

    my_parser = argparse.ArgumentParser(description='Extract DICOM Header Info')
    my_parser.add_argument('-p', '--path', type=str, help='the path to the directory', required=True)
    my_parser.add_argument('-a', '--accession', type=str, help='accession number', required=False)
    my_parser.add_argument('-r', '--recursive', dest="recursive", help="how many directories deep to search", type=int, default=0)
    my_parser.add_argument('-o', '--output', type=str, help='output json file', required=True)
    my_parser.add_argument('-t', '--tagfile', type=str, help='json file of dicom tags to include', required=False)
    my_parser.add_argument('-l', '--log', type=str, help='logfile', required=False, default=None)
    my_parser.add_argument('-n', '--name', help='include name of each tag', default=False, required=False, action='store_true')
    my_parser.add_argument('-c', '--comprehensive', help='include all non-private & non-pixel tags', default=False, required=False, action='store_true')    
    
    args = my_parser.parse_args()

    slurminfo=''
    slurmtask=os.environ.get('SLURM_ARRAY_TASK_ID')
    slurmid=os.environ.get('SLURM_JOB_ID')
    if slurmid is not None:
        slurminfo="- SLURM="+slurmid
        if slurmtask is not None:
            slurminfo = slurminfo+"_"+slurmtask


    #logging.basicConfig(
    #    format='%(asctime)s %(name)s %(levelname)-8s %(message)s',
    #    level=logging.INFO,
    #    datefmt='%Y-%m-%d %H:%M:%S')
    formatter = logging.Formatter(fmt=f'%(asctime)s %(name)s %(levelname)-8s %(message)s {slurminfo}', datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger("dicom_tree")
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    start = datetime.now()

    tags=None
    if not args.comprehensive:
        if not args.tagfile is None:
            logger.info("Reading tag file: %s" % args.tagfile)
            with open(args.tagfile) as f:
                tags = json.load(f)

    if not os.path.isdir(str(args.path)):
        logger.error("Path does not exist: %s" % args.path)
        return(1)

    logger.info("Scanning directory: %s" % args.path)
    dicomTree = DicomTree(args.path, make_logger=False)
    dicomTree.comprehensive=args.comprehensive
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
    logger.info("Tree build time: %s" % str(finish-start))

    outTree = {"Directory": args.path, "StudyList": dicomTree.studies}

    with open(args.output, 'w', encoding='utf-8') as f:
        logger.info("Writing to: "+args.output)
        json.dump(outTree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

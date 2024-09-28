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
    evenly_spaced=nums[chain[0]:chain[1]+2]
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
    my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter', required=True)   
    my_parser.add_argument('-v', '--verbose', default=False, action='store_true', help='verbose output')
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
            inst_list = []
            position_list = []
            for instance in series['InstanceList']:
                if "AcquisitionNumber" in instance:
                    acq = get_value(instance, "AcquisitionNumber")
                    if acq not in acq_list:
                        acq_list.append(acq)
                if "Modality" in instance:
                    mod = get_value(instance,"Modality")
                    if mod not in mod_list:
                        mod_list.append(mod)
                if "InstanceNumber" in instance:
                    inst = int(get_value(instance,"InstanceNumber"))
                    inst_list.append(inst)
                if "SliceLocation" in instance:
                    pos = float(get_value(instance,"SliceLocation"))
                    position_list.append(pos)   


            inst_list.sort()
            position_list.sort()

            print("  series: "+get_value(series,"SeriesInstanceUID"))
            print("    description: "+get_value(series,"SeriesDescription"))
            print("    number: "+get_value(series,"SeriesNumber"))
            print("    modality: "+get_value(series,"Modality"))
            print("    nInstances: "+str(len(series['InstanceList'])))
            print("    acquisitions: ["+",".join(acq_list)+"]")
            if args.verbose:
                print("    instances: "+str(inst_list))
                #print(longest_consecutive_sequences(inst_list, first=True))
                print("    positions: "+str(position_list))
                #print(longest_evenly_spaced_sequences(position_list))



    return(0)

if __name__=="__main__":
    sys.exit(main())

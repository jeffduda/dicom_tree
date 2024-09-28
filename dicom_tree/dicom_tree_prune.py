import sys
import os
import argparse
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


def get_tag(struct, check):
    return( struct.get(check.get('Name')) )

def check_tag(struct, check, verbose=False):

    tag = get_tag(struct, check)

    # Check for existence conditions
    if check.get('Operator')=='dne':
        result = tag is None
        if verbose and not result:
            print("Failed check for does not exist of tag: "+str(check.get('Name')))
        return(result)
    elif check.get('Operator')=='exists':
        result = tag is not None
        if verbose and not result:
            print("Failed check for existence of tag: "+str(check.get('Name'))) 
        return(result)

    # If tag does not exist, return false or default
    if tag is None:
        if check.get('Default') is not None:
            return(check.get('Default'))
        return(False)
    
    if 'Value' not in tag:
        if check.get('Default') is not None:
            return(check.get('Default'))
        return(False)

    # Get value of tag in struct
    tag_val = tag.get('Value')
    if tag_val is None:
        return(False)

    # Get value from a sequence
    if 'SeqKey' in check:
        if check.get('SeqKey') not in tag_val[0].keys():
            if verbose:
                print("Failed check for sequence key: "+str(check.get('SeqKey')))
            return(False)
        tag_val = tag_val[0].get(check.get('SeqKey'))['Value']

    idx = check.get('Index')
    if idx is None:
        idx=0

    if idx >= len(tag_val):
        if check.get('Default') is not None:
            return(check.get('Default'))
        if verbose:
            print("Failed check for index: "+str(idx)+" of tag: "+str(check.get('Name')))
        return(False)

    tag_val=tag_val[idx]

    val_type = check.get('Type')
    if val_type=='str':
        tag_val=str(tag_val)
    if val_type=='int':
        tag_val=int(tag_val)
    if val_type=='float':
        tag_val=float(tag_val)


    valid_value = check_value(tag_val, check, verbose)
    if verbose and not valid_value:
        print("Failed check for value: "+str(tag_val)+" of tag: "+str(check.get('Name')))
    return(valid_value)

def check_value(value, check, verbose=False):

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
    elif check.get("Operator")=="like":
        check_value = check.get("Value")
        valid = check_value.upper() in value.upper()
    elif check.get("Operator")=="not_like":
        check_value = check.get("Value")
        valid = not check_value.upper() in value.upper()
    else:
        logging.error("Unknown operator: "+str(check.get("Operator")))
        valid=False

    return(valid)

def contiguous_series(tree):
    for study in tree['StudyList']:
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

            position_inst_consecutive=inst_consecutive
            if len(inst_consecutive) > 1:
                
                position_list=[]
                for instance in inst_consecutive:
                    if "SliceLocation" in instance:
                        position_list.append(instance["SliceLocation"]["Value"][0])

                position_consecutive = longest_evenly_spaced_sequences(position_list)
                position_inst_consecutive=[]
                for instance in inst_consecutive:
                    if "SliceLocation" in instance:
                        if instance["SliceLocation"]["Value"][0] in position_consecutive:
                            position_inst_consecutive.append(instance)          

            series["InstanceList"]=position_inst_consecutive

    return(tree)

def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter', required=True)
    my_parser.add_argument('-f', '--filter', type=str, help='json file of dicom tags to filter on', required=False, default=None)
    my_parser.add_argument('-m', '--min_instances', type=int, help='minimum number of instances', required=False, default=1)
    my_parser.add_argument('-o', '--output', type=str, help='filtered dicom tree', required=True)
    my_parser.add_argument('-v', '--verbose', action='store_true', help='verbose output', required=False)
    my_parser.add_argument('-c', '--continguous', action='store_true', help='only keep contiguous instances', default=False, required=False)
    args = my_parser.parse_args()
    print(args)


    logging.info("Reading tree file: %s" % args.tree)
    tree_file = open(args.tree)
    tree = json.load(tree_file)

    if args.continguous:
        tree = contiguous_series(tree)

    if args.filter is None:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(tree, f, ensure_ascii=False, indent=4)
        return(0)

    logging.info("Reading filter file: %s" % args.filter)
    filter_file = open(args.filter)
    filter = json.load(filter_file)

    out_studies = []
    out_series_map = {}
    out_instance_map = {}

    study_ids=[]
    for study_id, study in enumerate(tree['StudyList']):
        print("Check accession: "+str(study.get("AccessionNumber").get("Value")[0]))
        print("Check study: "+str(study.get("StudyInstanceUID").get("Value")[0]))
        study_uid = study.get("StudyInstanceUID").get("Value")[0]
        keep_study=True
        if 'Study' in filter:
            for check in filter['Study']:
                keep_study=keep_study and check_tag(study, check)
                if args.verbose:
                    if not keep_study:
                        print("Study Failed check: "+str(check))
                        print(study.get(check.get('Name')))
                    else:
                        print("Study Passed check: "+str(check))
                        print(study.get(check.get('Name')))

        if keep_study:
            out_studies.append(study_uid)

    logging.debug("Done checking studies")
    if args.verbose:
        print(str(len(out_studies))+" studies passed Study-Level check")

    n_series=0
    for study in tree.get('StudyList'):
        study_uid = study.get("StudyInstanceUID").get("Value")[0]
        if study_uid not in out_studies:
            continue 

        series_ids=[]
        for series in study['SeriesList']:

            #print("Check series:  "+str(series.get("SeriesInstanceUID").get("Value")[0]))
            if args.verbose:
                print("Check series#: "+str(series.get("SeriesNumber").get("Value")[0]))

            series_uid = series.get("SeriesInstanceUID").get("Value")[0]
            keep_series=True
            if 'Series' in filter:
                for check in filter['Series']:
                    check_result =  check_tag(series, check, args.verbose)
                    if not check_result and args.verbose:
                        print("Failed check: "+str(check))
                        print(series.get(check.get('Name')))

                    keep_series = keep_series and check_result
                    if not keep_series and args.verbose:
                        print("Failed check: "+str(check))
                        print(series.get(check.get('Name')))

            if args.verbose and not keep_series:
                print("Series Failed check: "+str(series.get("SeriesNumber").get("Value")[0]))
            else:
                print("Series Passed check: "+str(series.get("SeriesNumber").get("Value")[0]))

            if keep_series:
                series_ids.append(series_uid)

        if len(series_ids)>0:
            out_series_map[study_uid]=series_ids              
    logging.debug("Done checking series")

    #print(out_series_map)
    if args.verbose:
        print(str(len(out_series_map.values()))+" series passed Series-Level check")
        print(out_series_map.values())

    n_instances=0
    for study in tree.get('StudyList'):
        study_uid = study.get("StudyInstanceUID").get("Value")[0]
        if study_uid not in out_studies:
            continue

        if study_uid not in out_series_map:
            continue

        for series in study.get("SeriesList"):
            series_uid = series.get("SeriesInstanceUID").get("Value")[0]
            if series_uid not in out_series_map[study_uid]:
                continue

            instance_ids=[]
            for instance in series['InstanceList']:
                keep_instance=True
                instance_uid = instance.get("SOPInstanceUID").get("Value")[0]
                logging.debug(" SOPInstanceUID: "+instance_uid)
                if 'Instance' in filter:
                    for check in filter['Instance']:
                        check_result = check_tag(instance, check)
                        keep_instance = keep_instance and check_result
                        if args.verbose:
                            if not check_result:
                                print("Failed check: "+str(check))
                                print(instance.get(check.get('Name')))

                if keep_instance:
                    instance_ids.append(instance_uid)
                    n_instances+=1

            if len(instance_ids) >= args.min_instances:
                out_instance_map[series_uid]=instance_ids

    logging.debug("Done checking instances")
    #print(str(n_instances)+" instances passed Instance-Level check")

    tree_studies=[]

    for study in tree.get('StudyList'):
        study_uid = study.get("StudyInstanceUID").get("Value")[0]

        if study_uid not in out_series_map:
            continue

        if study_uid in out_studies:

            #print("Scan study: "+str(study_uid))
            study_copy = study.copy()
            study_copy['SeriesList']=[]

            for series in study.get("SeriesList"):
                series_uid = series.get("SeriesInstanceUID").get("Value")[0]
                if series_uid in out_series_map[study_uid] and series_uid in out_instance_map:
                    #print("Scan series: "+str(series_uid))
                    series_copy = series.copy()
                    series_copy['InstanceList']=[]

                    for instance in series['InstanceList']:
                        instance_uid = instance.get("SOPInstanceUID").get("Value")[0]
                        
                        if instance_uid in out_instance_map[series_uid]:
                            #print("Keep instance: "+str(instance_uid))
                            series_copy['InstanceList'].append(instance)

                    if len(series_copy['InstanceList'])>0:
                        #print("Keep series: "+str(series_uid))
                        study_copy['SeriesList'].append(series_copy)

            if len(study_copy['SeriesList'])>0:
                #print("Keep study: "+str(study_uid))
                tree_studies.append(study_copy)


    out_tree={'Directory': tree['Directory'], 'StudyList': []}
    if len(tree_studies) > 0:
        out_tree['StudyList']=tree_studies
    else:
        print("Empty output")

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(out_tree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

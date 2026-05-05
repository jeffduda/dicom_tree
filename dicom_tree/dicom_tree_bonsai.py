import sys
import os
import argparse
import logging
import json
import copy

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
        #if verbose and not result:
        #    print("Failed check for does not exist of tag: "+str(check.get('Name')))
        return(result)
    elif check.get('Operator')=='exists':
        result = tag is not None
        #if verbose and not result:
        #    print("Failed check for existence of tag: "+str(check.get('Name'))) 
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
            #if verbose:
            #    print("Failed check for sequence key: "+str(check.get('SeqKey')))
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
    #if verbose and not valid_value:
    #    print("Failed check for value: "+str(tag_val)+" of tag: "+str(check.get('Name')))
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
        #logging.error("Unknown operator: "+str(check.get("Operator")))
        valid=False

    return(valid)

def contiguous_series(tree, logger=None):
    for study in tree['StudyList']:
        for series in study["SeriesList"]:
            inst_list=[]
            position_list=[]
            if len(series["InstanceList"]) > 2:

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
                if len(inst_consecutive) > 2:
                    
                    position_list=[]
                    for instance in inst_consecutive:
                        if "SliceLocation" in instance:
                            position_list.append(instance["SliceLocation"]["Value"][0])

                    if len(position_list) != len(inst_consecutive):
                        if logger is not None:
                            logger.WARNING("Instance/s are missing SliceLocation in series: "+str(series["SeriesNumber"]["Value"][0]))
                            #print("WARNING: Instance/s are missing SliceLocation in series: "+str(series["SeriesNumber"]["Value"][0]))
                        series["InstanceList"]=[]
                    else:
                
                        position_consecutive = longest_evenly_spaced_sequences(position_list)
                        position_inst_consecutive=[]
                        for instance in inst_consecutive:
                            if "SliceLocation" in instance:
                                if instance["SliceLocation"]["Value"][0] in position_consecutive:
                                    position_inst_consecutive.append(instance)          

                    series["InstanceList"]=position_inst_consecutive

    return(tree)

def is_empty( dicom_entry ):
    ret = dicom_entry.get('Value',None)
    return(ret is None)

def compress_instance_list( instance_list, exclude_list=[] ):

    full_list=set(range(len(instance_list)))
    keep_list=full_list-set(exclude_list)

    print(full_list)
    print(keep_list)

    print("Reference index "+str(min(keep_list)))
    reference = copy.deepcopy(instance_list[min(keep_list)])


    if len(instance_list) > 1:

        variable_set=set()
        for i in range(1,len(instance_list)):

            if i not in exclude_list:

                for entry in instance_list[i].keys():

                    if entry in reference:

                        if 'Value' in instance_list[i][entry]:
                            if isinstance(reference[entry]['Value'][0],list):
                                if instance_list[i][entry]['Value'] not in reference[entry]['Value']:
                                    reference[entry]['Value'].append(instance_list[i][entry]['Value'])

                                    variable_set.add(entry)
                            else:
                                if instance_list[i][entry]['Value']!=reference[entry]['Value']:
                                    variable_set.add(entry)
                                    #print(entry)
                                    reference[entry]['Value']=[reference[entry]['Value'],instance_list[i][entry]['Value']]

                    else:
                        variable_set.add(entry)
                        reference[entry]=instance_list[i][entry].copy()

        if len(variable_set) > 0:
            for v in variable_set:
                reference[v]['Value']=[]
                reference['Filename']=[]

            for idx in range(len(instance_list)):
                for v in variable_set:
                    val=['NA']
                    if v in instance_list[idx]:
                        val=instance_list[idx][v]['Value'].copy()
                        if len(val)==0:
                            val=[None]
                            print(instance_list[idx]['Filename'])
                            print("Missing"+v)
                    reference[v]['Value'].append(val)
                    reference['Filename'].append(instance_list[idx]['Filename'])
        reference['IsSummary']=True
            
    return reference

def main():

    my_parser = argparse.ArgumentParser(description='Shrink size of tree')
    my_parser.add_argument('-i', '--input', type=str, help='json file of dicom studies to shrink', required=True)
    my_parser.add_argument('-o', '--output', type=str, help='filtered dicom tree', required=True)
    my_parser.add_argument('-v', '--verbose', action='store_true', help='verbose output', required=False, default=False)
    args = my_parser.parse_args()

    slurminfo=''
    slurmtask=os.environ.get('SLURM_ARRAY_TASK_ID')
    slurmid=os.environ.get('SLURM_JOB_ID')
    if slurmid is not None:
        slurminfo="- SLURM="+slurmid
        if slurmtask is not None:
            slurminfo = slurminfo+"_"+slurmtask

    formatter = logging.Formatter(fmt=f'%(asctime)s %(name)s %(levelname)-8s %(message)s {slurminfo}', datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger("dicom_tree_prune")
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)


    logger.info("Reading tree file: " + args.input)

    if not os.path.exists(args.input):
        logger.error("Tree file does not exist: "+args.input)
        return(1)
    
    tree_file = open(args.input)
    tree = json.load(tree_file)

    out_studies = []
    out_series_map = {}
    out_instance_map = {}

    study_ids=[]

    for study in tree['StudyList']:
        for entry in study:
            print(entry)
            if 'Value' in study[entry]:
                print(study[entry]['Value'])
                print(type(study[entry]['Value'][0]))

        ser_poplist=[]
        for ser in study['SeriesList']:
            for entry in ser:
                #print(entry)
                #if 'Value' in ser[entry]:
                #    print( ser[entry]['Value' ])
                a=1

            global_poplist=[]
            for index,inst in enumerate(ser['InstanceList']):
                if 'ImageType' in inst:
                    itype=inst['ImageType']['Value']
                    if 'LOCALIZER' in itype:
                        global_poplist.append(index)

                inst_poplist=[]
                for entry in inst:
                    if 'Value' in inst[entry]:
                        if is_empty(inst[entry]):
                            #print( 'REMOVE: '+entry )
                            inst_poplist.append(entry)
                for rem in inst_poplist:
                    inst.pop(rem)

            if len(global_poplist) > 0:
                print("Localizers to remove: "+str(len(global_poplist)))


            if len(global_poplist) < len(ser['InstanceList']):
                one_inst = compress_instance_list(ser['InstanceList'], exclude_list=global_poplist)
                del ser['InstanceList']
                ser['InstanceList']=[one_inst]
            else:
                ser['InstanceList']=[]

        study['SeriesList'] = [x for x in study['SeriesList'] if len(x['InstanceList'])>0 ]

    #out_tree={'Directory': tree['Directory'], 'StudyList': []}
    #if len(tree_studies) > 0:
    #    out_tree['StudyList']=tree_studies
    #else:
    #    logger.info("Empty output")

    with open(args.output, 'w', encoding='utf-8') as f:
        logger.info("Writing pruned tree to: "+args.output)
        json.dump(tree, f, ensure_ascii=False, indent=4)

    return(0)

if __name__=="__main__":
    sys.exit(main())

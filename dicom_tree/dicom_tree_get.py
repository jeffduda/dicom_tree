import sys
import os
import argparse
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

def get_value(dict, name, index=None, sequence=None):

    if name not in dict.keys():
        return( "NA" )
    
    val = dict.get(name)['Value']

    # pull out tag from sequence
    if sequence is not None:
        if not type(val[0])==type({}):
            return("NA")
        else:
            if sequence not in val[0].keys():
                return("NA")
            else:
                val = val[0].get(sequence)['Value']

    # Pull out a specific index
    if index is not None:
        val = [val[index]]

    if len(val)==1:
        val = str(val[0])
    else:
        val = '['+",".join(val)+']'

    return(val)
    

    


def main():

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter', required=True)  
    my_parser.add_argument('-n', '--name', type=str, help='name of tag to check', required=True)
    my_parser.add_argument('-l', '--level', type=str, help='study/series/instance', required=False, default='study')
    my_parser.add_argument('-s', '--sequence', type=str, help='sub tag for a sequence', required=False)
    my_parser.add_argument('-i', '--index', type=str, help='index', required=False)
    args = my_parser.parse_args()

    tree_file = open(args.tree)
    tree = json.load(tree_file)

    if args.name=="nstudies":
        print(len(tree['StudyList']))
        return(0)
    
    if args.name=="nseries":
        nseries=0
        for study in tree['StudyList']:
            nseries += len(study['SeriesList'])
        print(nseries)
        return(0)
    
    if args.name=="ninstances":
        ninstances=0
        for study in tree['StudyList']:
            for series in study['SeriesList']:
                ninstances += len(series['InstanceList'])
        print(ninstances)
        return(0)

              
    output = []
    for study in tree['StudyList']:
        if args.level=='study':
            if args.name in study.keys():
                value = study.get(args.name)['Value']

                output.append(get_value(study, args.name, index=args.index, sequence=args.sequence))
        else:
            for series in study['SeriesList']:
                if args.level=='series':
                    if args.name in series.keys():
                        output.append(get_value(series, args.name, index=args.index, sequence=args.sequence))
                else:
                    for instance in series['InstanceList']:
                        if args.level=='instance':
                            if args.name in instance.keys():
                                output.append(get_value(instance, args.name, index=args.index, sequence=args.sequence))
                        else:
                            print("ERROR: Unknown level: "+args.level)
                            return(1)
    if len(output)==0:
        print("NA")
    else:                      
        print(",".join(output))

    return(0)

if __name__=="__main__":
    sys.exit(main())

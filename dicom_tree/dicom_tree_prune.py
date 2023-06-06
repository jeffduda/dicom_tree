import sys
import os
import argparse
import logging
import json

def get_tag(struct, check):
    #el = check.get('Group')+check.get('Element')
    return( struct.get(check.get('Name')) )

def check_tag(struct, check):

    tag = get_tag(struct, check)

    # Check for existence conditions
    if check.get('Operator')=='dne':
        return(tag is None)
    elif check.get('Operator')=='exists':
        return(tag is not None)

    # If tag does not exist, return false
    if tag is None:
        return(False)
    
    if 'Value' not in tag:
        return(False)

    # Get value of tag in struct
    tag_val = tag.get('Value')
    if tag_val is None:
        return(False)

    # Get value from a sequence
    if 'SeqKey' in check:
        if check.get('SeqKey') not in tag_val[0].keys():
            return(False)
        tag_val = tag_val[0].get(check.get('SeqKey'))['Value']

    idx = check.get('Index')
    if idx is None:
        idx=0

    if idx >= len(tag_val):
        return(False)

    tag_val=tag_val[idx]

    val_type = check.get('Type')
    if val_type=='str':
        tag_val=str(tag_val)
    if val_type=='int':
        tag_val=int(tag_val)
    if val_type=='float':
        tag_val=float(tag_val)


    valid_value = check_value(tag_val, check)
    return(valid_value)

def check_value(value, check):

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
    else:
        logging.error("Unknown operator: "+str(check.get("Operator")))
        valid=False

    return(valid)

def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter', required=True)
    my_parser.add_argument('-f', '--filter', type=str, help='json file of dicom tags to filter on', required=True)
    my_parser.add_argument('-o', '--output', type=str, help='filtered dicom tree', required=True)
    args = my_parser.parse_args()

    logging.info("Reading tree file: %s" % args.tree)
    tree_file = open(args.tree)
    tree = json.load(tree_file)

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

        if keep_study:
            out_studies.append(study_uid)

    logging.debug("Done checking studies")
    #print(str(len(out_studies))+" studies passed Study-Level check")

    n_series=0
    for study in tree.get('StudyList'):
        study_uid = study.get("StudyInstanceUID").get("Value")[0]
        if study_uid not in out_studies:
            continue 

        series_ids=[]
        for series in study['SeriesList']:
            #print("Check series:  "+str(series.get("SeriesInstanceUID").get("Value")[0]))
            #print("Check series#: "+str(series.get("SeriesNumber").get("Value")[0]))
            series_uid = series.get("SeriesInstanceUID").get("Value")[0]
            keep_series=True
            if 'Series' in filter:
                for check in filter['Series']:
                    check_result =  check_tag(series, check)
                    keep_series = keep_series and check_result
                    #if not check_result:
                    #    print("Failed check: "+str(check))
                    #    print(series.get(check.get('Name')))

            if keep_series:
                series_ids.append(series_uid)

        if len(series_ids)>0:
            out_series_map[study_uid]=series_ids              
    logging.debug("Done checking series")
    #print(out_series_map)
    #print(str(len(out_series_map.values()))+" series passed Series-Level check")

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
                        #if not check_result:
                        #    print("Failed check: "+str(check))
                        #    print(instance.get(check.get('Name')))

                if keep_instance:
                    instance_ids.append(instance_uid)
                    n_instances+=1

            if len(instance_ids)>0:
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

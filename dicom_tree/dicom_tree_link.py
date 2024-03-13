import sys
import os
import argparse
import logging
import json

def clean_string(in_str):

    bad_char = ['{','}','[',']','!','"','\'','.','@','#','$','%','^','&','*','(',')','+',
        ':',';','<','>',',','?','~','`','/','\\','|',' ']
    out_str = in_str
    for bc in bad_char:
        out_str = out_str.replace(bc, '_')

    #rep_char = ['__','___','____','_____']
    #for bc in rep_char:
    #    out_str = out_str.replace(bc, '_')    
    while '__' in out_str:
        out_str = out_str.replace('__', '_')

    return(out_str)


def main():

    logging.basicConfig(level=logging.DEBUG)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter', required=True)
    my_parser.add_argument('-o', '--output', type=str, help='output directory for links', required=True)
    my_parser.add_argument('-s', '--series', type=str, help='output directory for series trees', required=False)
    my_parser.add_argument('-a', '--alias', type=str, help='alias name for subdirectories', required=False)
    args = my_parser.parse_args()

    logging.info("Reading tree file: %s" % args.tree)
    tree_file = open(args.tree)
    tree = json.load(tree_file)


    for study in tree.get('StudyList'):
        for series in study.get("SeriesList"):
            alias=str(study.get("AccessionNumber").get("Value")[0])
            if args.alias is not None:
                alias=args.alias
            snum=str(series.get("SeriesNumber").get("Value")[0])
            sdesc=clean_string(series.get("SeriesDescription").get("Value")[0])
            sdir=os.path.join(args.output, alias+"_"+snum+"_"+sdesc)

            tree_name=os.path.join(args.series, alias+"_"+snum+"_"+sdesc+"_series_tree.json")
            study_copy=study.copy()
            study_copy['SeriesList']=[series]
            series_tree={"Directory": tree['Directory'], "StudyList": [study_copy]}

            if args.series is not None:
                if not os.path.exists(args.series):
                    os.makedirs(args.series)
                with open(tree_name, 'w', encoding='utf-8') as f:
                    json.dump(series_tree, f, indent=4)

            if not os.path.exists(sdir):
                os.makedirs(sdir)

            for instance in series['InstanceList']:
                fname=instance.get("Filename")
                oname=os.path.join(sdir, os.path.basename(fname))
                if not os.path.exists(oname):
                    os.symlink(fname, oname)

    return(0)

if __name__=="__main__":
    sys.exit(main())

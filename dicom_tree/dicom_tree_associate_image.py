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
import glob
import itk
import numpy as np

def condense_instance_list(series, only_original=True, key_list=None):

    # scan once to find out what all is there
    if key_list is None:
        key_list=[]
        for instance in series.get("InstanceList"):
            ikeys = list(instance.keys())
            ikeys.remove("Filename")
            key_list += ikeys
        
        key_list = set(key_list)

    instance_summary={}

    for instance in series.get("InstanceList"):
        if only_original:
            if "00080008" in instance:
                if instance["00080008"]['Value'][0] != "ORIGINAL":
                    logging.error("Non ORIGINAL image detected: "+instance["00080008"]['Value'][0])
                    continue
                if instance["00080008"]['Value'][1] != "PRIMARY":
                    logging.error("Non PRIMARY image detected: "+instance["00080008"]['Value'][1])
                    continue
                if instance["00080008"]['Value'][2] != "AXIAL":
                    logging.error("Non AXIAL image detected: "+instance["00080008"]['Value'][2])
                    continue

        for key in key_list:
            if key in instance:
                if not key in instance_summary:
                    #print("Adding tag")
                    #print(instance[key])
                    instance_summary[key]=instance[key]
                else:
                    if not instance_summary[key]==instance[key]:
                        logging.error("Inconsistent key found: "+instance[key])

    return(instance_summary)


def itk_img_dat(img_name):
    img = itk.imread(img_name)
    dat= {'Filename': os.path.basename(img_name)}
    dat['ITK-ImageDimension'] = img.GetImageDimension()
    dat['ITK-NumberOfComponentsPerPixel'] = img.GetNumberOfComponentsPerPixel()
    dat['ITK-Spacing'] = list(img.GetSpacing())
    dat['ITK-Origin'] = list(img.GetOrigin())
    dir2D = itk.array_from_matrix(img.GetDirection())
    dir1D = [ item for sub_list in dir2D for item in sub_list]
    dat['ITK-Direction'] = dir1D
    dat['ITK-Size'] = list(img.GetLargestPossibleRegion().GetSize())
    return(dat)

def main():



    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-t', '--tree', type=str, help='json file of dicom studies to filter', required=True)
    my_parser.add_argument('-p', '--path', type=str, help='path to directory with nifti images', required=True)
    my_parser.add_argument('-e', '--extension', type=str, help='extension used on image files', default=".nii.gz", required=False)
    my_parser.add_argument('-o', '--output-dir', type=str, help='output directory for files', required=True)
    my_parser.add_argument('-f', '--force', dest='force', help='force overwrite of existing files', required=False, default=False, action='store_true')
    my_parser.add_argument('-l', '--log', type=str, help='logfile', required=False, default=None)
    args = my_parser.parse_args()

    instance_key_list = ["00080008", "00082218", "00082228", "00180050", "00181050", "00280002"]
    instance_key_list += ["00280010", "00280011", "00280100", "00280101", "00280030", "00280301"]
    instance_key_list += ["00280302"]

    logging.basicConfig(level=logging.INFO, format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
    logger=logging.getLogger("dicom_tree_associate_image")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if args.log is not None:
        print("  add logging file: "+args.log)
        fh = logging.FileHandler(args.log, 'a')
        fh.setFormatter(formatter)
        logger.addHandler(fh)


    logger.info("Reading tree file: %s" % args.tree)
    tree_file = open(args.tree)
    tree = json.load(tree_file)

    if len(tree['StudyList']) > 1:
        logger.error("Can only associate for one study")
        return(0)

    logger.info("Reading image directory: %s" % args.path)
    image_files = glob.glob(args.path+"/*"+args.extension)
    logger.info("Found %d images" % len(image_files))

    for img_file in image_files:
        img_name = os.path.basename(img_file).split(args.extension)[0]
        img_name_parts = img_name.split("_")
        logger.info("Folder: "+img_name_parts[0]+'_'+img_name_parts[1])
        logger.info("SeriesNumber: "+img_name_parts[2])
        logger.info("Time: "+img_name_parts[1])
        
        series_num = int(''.join(filter(str.isdigit, img_name_parts[2])))
        logger.info("Searching for meta data for series# "+str(series_num))

        for series in tree['StudyList'][0]['SeriesList']:
            # Get Series Number by group,element
            num = series.get("00200011")
            
            if not num is None:
                snum = int(num['Value'][0])
                logging.info("Scanning series# "+str(snum))
                if int(snum)==int(series_num):
                    logger.info("* Found match for series number: "+str(snum))
                    img_dat = itk_img_dat(img_file)
                    series_copy = series.copy()
                    
                    isum = condense_instance_list(series_copy, key_list=instance_key_list)
                    for val in isum:
                        series_copy[val] = isum[val]

                    if 'InstanceList' in series_copy:
                        for i,inst in enumerate(series_copy['InstanceList']):
                            del series_copy['InstanceList'][i]['Filename']

                    series_dat = {'Image': os.path.basename(img_file), 'Dicom': series_copy, 'Image': img_dat}
                    #print(series_dat)
                    #print(img_file)
                    oname = os.path.join(args.output_dir, img_name+".json")
                    
                    write_out=True
                    if os.path.exists(oname):
                        write_out=False
                        if args.force:
                            logger.warning("Forcing overwrite of existing file")
                            conv_file=open(oname)
                            conv = json.load(conv_file)
                            
                            
                            if 'ConversionSoftware' in conv:
                                if 'Conversion' not in conv:
                                    series_dat['Conversion']=conv

                            write_out=True
                    if write_out:
                        with open( oname, 'w') as f:
                            logger.info("Writing: "+oname)
                            json.dump(series_dat, f, ensure_ascii=False, indent=4)
                    else:
                        logger.warning("Output already exists. Remove to write new or use '-f' to force overwrite")
                        

    return(0)

if __name__=="__main__":
    sys.exit(main())

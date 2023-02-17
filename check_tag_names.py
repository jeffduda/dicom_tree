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


def main():

    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Check dicom tag names')
    my_parser.add_argument('-t', '--tagfile', type=str, help='json file of dicom tags to check', required=True)
    args = my_parser.parse_args()

    logging.info("Reading tag file: %s" % args.tagfile)
    with open(args.tagfile) as f:
        tags = json.load(f)

        for tag_type in ['Study', 'Series', 'Instance']:
            if tag_type in tags:
                for tag in tags[tag_type]:
                    if 'Name' in tag:
                        pydicom_el=None
                        try:    
                            pydicom_el = pydicom.DataElement(tag['Name'], None, None)
                            if pydicom_el.tag.group != int(tag['Group'],16):
                                print("Group mismatch: " + tag['Name'])
                            if pydicom_el.tag.element != int(tag['Element'],16):
                                print("Element mismatch: " + tag['Name'])
                        except:
                            print("No tag found for: " + tag['Name'])                

    return(0)

if __name__=="__main__":
    sys.exit(main())

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
import SimpleITK as sitk
import numpy as np

from dicom_tree import DicomTree


def main():
    logging.basicConfig(level=logging.INFO)

    my_parser = argparse.ArgumentParser(description='Display DICOM Header Info')
    my_parser.add_argument('-p', '--path', type=str, help='the path to the directory', required=True)
    my_parser.add_argument('-i', '--input', type=str, help='input image', required=True)
    my_parser.add_argument('-t', '--tagfile', type=str, help='json file of dicom tags to include', required=False)
    my_parser.add_argument('-o', '--output', type=str, help='output json file', required=True)
    my_parser.add_argument('-a', '--append', action='store_true', help='add to existing file', required=False, default=False)

    args = my_parser.parse_args()
    print(args)

    logging.info("Reading Image: "+args.input)
    img_raw = sitk.ReadImage(args.input)
    filter_lps = sitk.DICOMOrientImageFilter()
    filter_lps.SetDesiredCoordinateOrientation('LPS')
    img = filter_lps.Execute(img_raw)

    img_size = img.GetSize()
    img_dim = len(img_size)
    img_arr = sitk.GetArrayFromImage(img)

        
    if img_dim < 2:
        logging.error("Image dimension is less than 2")
        return
    if img_dim > 4:
        logging.error("Image dimension is greater than 4")
        return

    nInstances = 0
    nAcqusitions = 0
    if img_dim == 2:
        nInstances = 1
        nAcquisitions = 1
    if img_dim == 3:
        nInstances = img_size[2]
        nAcquisitions = 1
    if img_dim == 4:
        nInstances = img_size[2] * img_size[3]
        nAcquisitions = img_size[3]
    

    tag_list=None
    with open(args.tagfile) as json_file:
        tag_list = json.load(json_file)
    
    # Read existing study info file
        
    instance_num=1
    series_num=1
    acquisition_num=1

    series_index=0

    study_uid = pydicom.uid.generate_uid()
    series_uid = pydicom.uid.generate_uid()
        
    for tag in tag_list['Study']:
        if tag['Group'] == '0020' and tag['Element'] == '000D':
            study_uid = tag['Value']
            break
    for tag in tag_list['Series'][series_index]:
        if tag['Group'] == '0020' and tag['Element'] == '000E':
            series_uid = tag['Value']        
            break

    image_origin = list(img.GetOrigin())

    instance_list=[]
        
    if img_dim == 3:
        logging.info("Creating new series for 3D image")

        #FIXME - flip any of these?
        #mat = itk.array_from_matrix(img.GetDirection())
        #orient = list(np.concatenate((mat[0,:], mat[1,:])))
        orient = list(img.GetDirection())[0:6]

        # FIXME - read existin json if in append mode

        
        series_uid = pydicom.uid.generate_uid()

        for i in range(img_size[2]):
            instance_uid = pydicom.uid.generate_uid()

            instance_dat = Dataset()
            instance_dat.StudyInstanceUID = study_uid
            instance_dat.SeriesInstanceUID = series_uid
            instance_dat.add( pydicom.DataElement( (0x0008, 0x0018), 'UI', instance_uid) )
            instance_dat.InstanceCreationDate = datetime.now().strftime("%Y%m%d")
            instance_dat.InstanceCreationTime = datetime.now().strftime("%H%M%S.%f")

            instance_dat.InstanceNumber = instance_num
            instance_num += 1
            instance_dat.AcquisitionNumber = acquisition_num
            instance_dat.PixelSpacing = list(img.GetSpacing())[0:2]
            instance_dat.SliceThickness = img.GetSpacing()[2]
            instance_dat.ImageOrientationPatient = orient
            instance_dat.Rows = img_size[1]
            instance_dat.Columns = img_size[0]
            instance_dat.BitsAllocated = 16
            instance_dat.BitsStored = 16
            instance_dat.HighBit = 15
            position = list(img.TransformIndexToPhysicalPoint([0,0,i]))
            instance_dat.ImagePositionPatient = position
            instance_dat.SliceLocation = position[2]
            

            for tag in tag_list['Study']:
                tag_element = pydicom.DataElement( (tag['Group'], tag['Element']), tag['vr'], tag['Value'])
                instance_dat.add(tag_element)
            if 'Series' in tag_list:
                for tag in tag_list['Series'][series_index]:
                    tag_element = pydicom.DataElement( (tag['Group'], tag['Element']), tag['vr'], tag['Value'])
                    instance_dat.add(tag_element)
            if 'Instance' in tag_list:
                for tag in tag_list['Instance'][i]:
                    tag_element = pydicom.DataElement( (tag['Group'], tag['Element']), tag['vr'], tag['Value'])
                    instance_dat.add(tag_element)      

            #FIXME - flip either axis?
            slice_img = sitk.GetArrayFromImage(img[:,:,i])
            slice_img = slice_img.astype(np.uint16)
            #slice_img = np.fliplr(slice_img)
            instance_dat.PixelData = slice_img.tobytes()


            instance_dat.is_little_endian=True
            instance_dat.is_implicit_VR=False
            
            fname = instance_dat.SOPInstanceUID+str(i)+".dcm"
            if 'Instance' in tag_list:
                if 'FileName' in tag_list['Instance'][i]:
                    fname = tag_list['Instance'][i]['FileName']    
            instance_dat.save_as(os.path.join(args.path, fname))

            instance_list.append(instance_dat)

            print(instance_dat)
            print("")

    #if img.GetImageDimension() == 4:    


if __name__ == "__main__":
    main()

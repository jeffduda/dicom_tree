# dicom_tree
To extract meta data from a directory (or directories) of dicom files, use dicom_tree.py

```
usage: dicom_tree.py [-h] -p PATH [-a ACCESSION] [-r RECURSIVE] -o OUTPUT
                     [-t TAGFILE] [-l LOG] [-n]

Extract Dicom meta data

optional arguments:
  -h, --help            show this help message and exit
  -p PATH, --path PATH  the path to the directory
  -a ACCESSION, --accession ACCESSION
                        accession number
  -r RECURSIVE, --recursive RECURSIVE
                        how many directories deep to search
  -o OUTPUT, --output OUTPUT
                        output json file
  -t TAGFILE, --tagfile TAGFILE
                        json file of dicom tags to include
  -l LOG, --log LOG     logfile
  -n, --name            include name of each tag
```

To create a directory of dicom image files from a image volume (in nifti) and a config file of desired meta data, use dicom_tree_grow.py

```
usage: dicom_tree_grow.py [-h] -p PATH -i INPUT [-t TAGFILE]

Create dicom image files

optional arguments:
  -h, --help            show this help message and exit
  -p PATH, --path PATH  path to the output directory
  -i INPUT, --input INPUT
                        input image (itk readable)
  -t TAGFILE, --tagfile TAGFILE
                        json file of dicom tags to include
```

To use a wrapper for dcm2niix
```
For this script you must set the environment var DICOMTREEPATH, e.g.

export DICOMTREEPATH=/home/myhome/dicom_tree 

usage: sh dicom_to_nii.sh -i INPUTDIR -o OUTPUTDIR [-t TAG_JSON ] [-f FILTER_JSON ]

Build nii.gz volumes from a directory of dicom images
 -i INTPUDIR          Directory of dicom files
 -o OUTPUTDIR         Directory to store output in
 -t TAG_JSON          File specifying the dicom tags to extract (default = dicom_tree/data/ct_series_dir.json)
 -f FILTER_JSON       File specifying how to filter out unwanted images (default = dicom_tree/data/default_filter.json)
 ```
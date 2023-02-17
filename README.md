# dicom_tree
Scan a directory of dicom files and build a tree (study - series - instance) with tag info

## Usage
```
python dicom_tree.py -p /path/to/dicom/directory -r 3 -o output_tree.json -t ct_series_tags.json

-p path to a directory filled with dicom images (required)
-r how many levels deep to look for files (default=0)
-o output json file that holds the tree structure of the dicom files (required)
-t json file determining what dicom tag to extract and what level to store them (options, example below)
```

## Example json file that defines what tags to extract
```
{
    "Study": [
        {"Group": "0008", "Element": "0050", "Name": "AccessionNumber"},
        {"Group": "0008", "Element": "0020", "Name": "StudyDate"},
        {"Group": "0008", "Element": "0030", "Name": "StudyTime"},
        {"Group": "0008", "Element": "1030", "Name": "StudyDescription"}
    ],
    "Series": [
        {"Group": "0008", "Element": "0060", "Name": "Modality"},
        {"Group": "0008", "Element": "0021", "Name": "SeriesDate"},
        {"Group": "0008", "Element": "0031", "Name": "SeriesTime"},
        {"Group": "0008", "Element": "103E", "Name": "SeriesDescription"},
        {"Group": "0020", "Element": "0011", "Name": "SeriesNumber"}
    ],
    "Instance": [
        {"Group": "0018", "Element": "0050", "Name": "SliceThickness"},
        {"Group": "0008", "Element": "0008", "Name": "ImageType"}
    ]
}
```
#!/bin/bash


usage() { echo "Usage: $0 -i input_dicom_dir -o output_dir  [-q queue_name]"; exit 1; } 

idir=""
odir=""
tags=""
filter=""
log=""
clean=1

while getopts c:f:i:l:o:ht: flag
do 
  case "${flag}" in
     c) clean=${OPTARG};;
     i) idir=${OPTARG};;
     l) log=${OPTARG};;
     f) filter=${OPTARG};;
     o) odir=${OPTARG};;
     t) tags=${OPTARG};;
     h) usage;;
  esac
done

if [ ! -e "${DICOMTREEPATH}/dicom_tree/dicom_tree.py" ]; then   
    echo "DICOMTREEPATH is not set"
    exit 1
fi


# Does input directory exist
if [ ! -d "${idir}" ]; then
    echo "Input directory does not exist"
fi

# Create output directory if it does not exist
if [ ! -d "${odir}" ]; then
    echo "Create output directory: ${odir}"
    mkdir -p ${odir}
fi

# If no filter, use default (original images only)
if [ "$filter" == "" ]; then
    filter="${DICOMTREEPATH}/data/default_filter.json"
fi

# If no filter, use default (original images only)
if [ "$tags" == "" ]; then
    tags="${DICOMTREEPATH}/data/default_tags.json"
fi

# Parse dicom files for metadata
alias=$(basename ${idir})

# Get "tree" of dicom metadata
python ${DICOMTREEPATH}/dicom_tree/dicom_tree.py -p ${idir} -o ${odir}/${alias}_dicom_tree.json -t ${tags}

# Prune tree based on filter
python ${DICOMTREEPATH}/dicom_tree/dicom_tree_prune.py -t ${odir}/${alias}_dicom_tree.json -o ${odir}/${alias}_pruned_tree.json -f ${filter}

# Create symbolic links to dicom files to convert (org by series)
python ${DICOMTREEPATH}/dicom_tree/dicom_tree_link.py -t ${odir}/${alias}_pruned_tree.json -s ${odir} -o ${odir}/dicom


nstudies=$(python ${DICOMTREEPATH}/dicom_tree/dicom_tree_get.py -t ${odir}/${alias}_dicom_tree.json -n nstudies)
echo "Number of studies: ${nstudies}"
cpt=$(python ${DICOMTREEPATH}/dicom_tree/dicom_tree_get.py -t ${odir}/${alias}_dicom_tree.json  -l study -n ProcedureCodeSequence -s 00080100)
echo "CPT: ${cpt}"

linkdirs=$(find ${odir}/dicom/* -type d -name "*")
count=0
for linkdir in ${linkdirs}; do
    count=$((count+1))
    echo "Processing: ${linkdir}"
    series_name=$(basename ${linkdir})

    #if [ ! -e "${odir}/${series_name}" ]; then
    #    mkdir -p ${odir}/${series_name}
    #fi
    if [ -e "${odir}/${series_name}_series_tree.json" ]; then
        python ${DICOMTREEPATH}/dicom_tree/dicom_tree_brief.py -t ${odir}/${series_name}_series_tree.json
        #mv ${odir}/${series_name}_series_tree.json ${odir}/${series_name}/
    fi

    # Convert dicom to nifti
    ${DICOMTREEPATH}/scripts/dcm2niix_wrap.sh -i ${linkdir} -o ${odir} -t ${tags}
done

# clean up
if [ $clean -eq 1 ]; then
    rm -rf ${odir}/dicom
fi

if [ ! $log == "" ]; then
    echo "${alias},${cpt},${count}" >> ${log}
fi


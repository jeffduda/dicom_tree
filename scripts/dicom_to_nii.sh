#!/bin/bash

logger () {
  d=$(date '+%Y-%m-%d %H:%M:%S')
  echo "$d dicom_to_nii.sh $1 $2 - SLURM=${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
}

usage() { echo "Usage: $0 -i input_dicom_dir -o output_dir  [-q queue_name]"; exit 1; } 

idir=""
odir=""
tags=" -c "
filter=""
log=""
ct=0
min_instances=1
alias=""
series=1
duplicates=0
naming="%f"

while getopts a:cdf:i:l:m:n:o:hs:t:x: flag
do 
  case "${flag}" in
     a) alias=${OPTARG};;
     c) ct=1;;
     d) duplicates=1;;
     i) idir=${OPTARG};;
     l) log=${OPTARG};;
     m) min_instances=${OPTARG};;
     n) naming=${OPTARG};;
     f) filter=${OPTARG};;
     o) odir=${OPTARG};;
     s) series=${OPTARG};;
     t) tags=" -t ${OPTARG} ";;
     x) exclude+=($OPTARG);;
     h) usage;;
  esac
done



if [ ! -e "${DICOMTREEPATH}/dicom_tree/dicom_tree.py" ]; then   
    logger "ERROR" "DICOMTREEPATH is not set"
    exit 1
fi


# Does input directory exist
if [ ! -d "${idir}" ]; then
    logger "INFO" "Input directory does not exist"
fi

# Create output directory if it does not exist
if [ ! -d "${odir}" ]; then
    logger "INFO" "Create output directory: ${odir}"
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

# Get name for output directory
if [ "$alias" == "" ]; then     
    alias=$(basename ${idir})
fi

# Get "tree" of dicom metadata
python ${DICOMTREEPATH}/dicom_tree/dicom_tree.py -p ${idir} -o ${odir}/${alias}_study_tree.json ${tags}

filter_opt="-f ${filter}"
if [ ! -e "${filter}" ]; then
  filter_opt=""
fi

# Prune tree based on filter
pruned="${odir}/${alias}_pruned_tree.json"
prune_cmd="python ${DICOMTREEPATH}/dicom_tree/dicom_tree_prune.py -c -t ${odir}/${alias}_study_tree.json -m $min_instances -o ${pruned} ${filter_opt}"
$prune_cmd

# Create symbolic links to dicom files to convert (org by series)
python ${DICOMTREEPATH}/dicom_tree/dicom_tree_link.py -t ${pruned} -s ${odir} -o ${odir}/dicom -a ${alias}

# Print out basic info
nstudies=$(python ${DICOMTREEPATH}/dicom_tree/dicom_tree_get.py -t ${odir}/${alias}_study_tree.json -n nstudies)
logger "INFO" "Number of studies: ${nstudies}"
cpt=$(python ${DICOMTREEPATH}/dicom_tree/dicom_tree_get.py -t ${odir}/${alias}_study_tree.json  -l study -n ProcedureCodeSequence -s 00080100)
logger "INFO" "CPT: ${cpt}"

# If no images to convert, exit
if [ ! -d "${odir}/dicom" ]; then
    logger "INFO" "No images to convert"
    exit 0
fi

# Convert each series individually
linkdirs=$(find ${odir}/dicom/* -type d -name "*")
count=0
for linkdir in ${linkdirs}; do
    count=$((count+1))
    logger "INFO" "Processing: ${linkdir}"
    series_name=$(basename ${linkdir})

    # Get rid of repeat underscores
    series_alias=$series_name
    while [[ $series_alias = *__* ]]; do
        series_alias=${series_alias//__/_}
    done 

    if [ ! -e "${odir}/${series_alias}" ]; then
        mkdir -p ${odir}/${series_alias}
    fi

    # Change to "clean" filename for sidecar
    if [ -e "${odir}/${series_name}_series_tree.json" ]; then
        #python ${DICOMTREEPATH}/dicom_tree/dicom_tree_brief.py -t ${odir}/${series_name}_series_tree.json
        mv ${odir}/${series_name}_series_tree.json ${odir}/${series_alias}/${series_alias}_series_tree.json
    fi

    # Convert dicom to nifti
    conv=`${DICOMTREEPATH}/scripts/dcm2niix_wrap.sh -i ${linkdir} -o ${odir}/${series_alias} -t ${tags} -f ${naming}`
    while read -r line; do
        logger "INFO" "dcm2niix $line"
    done <<< "$conv"


    # Remove any directory with no image volumes
    series_imgs=$(find ${odir}/${series_alias} -type f -name "*.nii.gz")
    n_imgs=${series_imgs[@]}
    if [ "${series_imgs}" == "" ]; then
        logger "INFO" "Remove emtpy series directory ${series_alias}"
        rm -Rf ${odir}/${series_alias}
    fi

done



# Eliminate images with uneven spacing
eqimgs=$(find ${odir}/*/* -type f -name "*Eq_1.nii.gz")
for eqimg in ${eqimgs}; do
    img_name=$(basename $eqimg .nii.gz)
    img_base=$(echo $img_name | rev | cut -c6- | rev)
    dir_name=$(dirname $eqimg)

    #logger "INFO" "Removing images with uneven slice spacing"
    
    if [ -e "${dir_name}/${img_base}.nii.gz" ]; then
        logger "INFO" "Removing ${dir_name}/${img_base}.nii.gz"
        rm ${dir_name}/${img_base}.nii.gz
    fi 
    if [ -e "${dir_name}/${img_base}.json" ]; then
        rm ${dir_name}/${img_base}.json
    fi     
    rm $eqimg
done


# Try to eliminate duplicate images
if [ $duplicates -eq 0 ]; then
    aimgs=$(find ${odir}/*/* -type f -name "*a.nii.gz")
    for aimg in ${aimgs}; do
        #logger "INFO" "Checking for duplicate: $aimg"
        img_name=$(basename $aimg .nii.gz)
        img_base=$(echo $img_name | rev | cut -c2- | rev)
        dir_name=$(dirname $aimg)

        #echo "  img_name=${img_name}"
        #echo "  img_base=${img_base}"
        #echo "  dir_name=${dir_name}"

        ajson="${dir_name}/${img_name}.json"
        orig_img="${dir_name}/${img_base}.nii.gz"
        #echo "Looking for: $orig_img"

        if [ -e "${orig_img}" ]; then
            #echo "Checking possible match: $orig_img"
            diff=$(diff $aimg $orig_img)
            if [ "$diff" == "" ]; then
                logger "INFO" "Removing duplicate image: ${aimg}"
                rm $aimg
                if [ -e "$ajson" ]; then
                    rm $ajson
                fi
            else
                logger "INFO" "Keeping possible duplicate: ${aimg}"
                #echo "diff: $diff"
            fi 
        fi 
    done
fi

# CT images should have a mean value < 0
# Any images with mean intensity > 0, is likely not a CT
#echo "Check mean intensity values"
if [ $ct -eq 1 ]; then
    imgs=$(find ${odir}/*/* -type f -name "*.nii.gz")
    for img in ${imgs}; do
        #echo $img
        intensity=$(c3d $img -info-full | grep Mean | cut -d : -f2)
        intensity=$(printf '%.3f' $intensity)
        #echo "Mean intensity: $intensity"
        if (( $(echo "$intensity > 0" | bc -l) )); then
            #echo "High mean intensity, unlikey to be CT: $img"
            img_name=$(basename $img .nii.gz)
            dir_name=$(dirname $img)
            rm $img
            rm ${dir_name}/${img_name}.json
        fi
    done
fi

# Eliminate images with fewer slices than min_instances
#echo "Check number of slices"
imgs=$(find ${odir}/*/* -type f -name "*.nii.gz")
for img in ${imgs}; do
    #echo $img
    nslices=$(c3d $img -info | cut -d ";" -f1 | cut -d "[" -f2 | cut -d "]" -f1 | cut -d "," -f3 | xargs)
    logger "INFO" "Number of Slices: $nslices"
    if (( $(echo "$nslices < $min_instances" | bc -l) )); then
        logger "INFO" "To few slices in image: $img"
        img_name=$(basename $img .nii.gz)
        dir_name=$(dirname $img)
        rm $img
        rm ${dir_name}/${img_name}.json
    fi
done


# Don't use a dir for each series
#echo "series level output: $series"
if [ $series -eq 0 ]; then
    for linkdir in ${linkdirs}; do
        count=$((count+1))
        series_name=$(basename ${linkdir})
        series_alias=$series_name
        while [[ $series_alias = *__* ]]; do
            series_alias=${series_alias//__/_}
        done 
        mv ${odir}/${series_alias}/* ${odir}/. 2> /dev/null
        if [ -d "${odir}/${series_alias}" ]; then 
            rmdir ${odir}/${series_alias}
        fi
    done
fi

# clean up
rm -rf ${odir}/dicom

if [ ! $log == "" ]; then
    echo "${alias},${cpt},${count}" >> ${log}
fi


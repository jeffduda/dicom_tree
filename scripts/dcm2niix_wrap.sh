#!/bin/bash
#module load dcm2niix
#module load python/3.10

logger () {
  d=$(date '+%Y-%m-%d %H:%M:%S')
  echo "$d dcm2niix_wrap.sh $1 $2 - SLURM=${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
}

load_mod () {
    x=${module load $1}
    for read -r line; do
        logger "INFO" "System: $line"
    done <<< "$x"
}

load_mod dcm2niix
load_mod python/3.10

idir=""
odir=""
name=""
tags=""
fmt="%f"

while getopts f:i:n:o:ht: flag
do 
  case "${flag}" in
     f) fmt=${OPTARG};;
     i) idir=${OPTARG};;
     n) name=${OPTARG};;
     o) odir=${OPTARG};;
     t) tags=${OPTARG};;
     h) usage;;
  esac
done

# Does input directory exist
if [ ! -d "${idir}" ]; then
    logger "ERROR" "Input directory does not exist"
fi

# Create output directory if it does not exist
if [ ! -d "${odir}" ]; then
    logger "INFO" "Create output directory: ${odir}"
    mkdir -p ${odir}
fi

# -i y ignore derived & localizers & 2D
# -z y compress
# -a y anonymize
exe="dcm2niix -i y -z y -a y -o ${odir} -f "${fmt}" ${idir}"
$exe

# remove things we don't want
eq_list=$(find ${odir} -type f -name "*Tilt_Eq_1*")
for f in $eq_list; do
    base=$(basename $f)
    dname=$(dirname $f)
    eq="${dname}/${base}.nii.gz"
    eqj="${dname}/${base}.json"
    logger "INFO" "Removing: ${f}"

    rm ${f}
    if [ -e "${eq}" ]; then
        logger "INFO" "Removing: ${eq}"
        rm ${eq}
    fi
    if [ -e "${eqj}" ]; then
        logger "INFO" "Removing: ${eqj}"
        rm ${eqj}
    fi
done

# Remove ROI images
rm ${odir}/*ROI* 2> /dev/null

# Get rid of duplicate images
afiles=$(find ${odir} -type f -name "*a.nii.gz")
for n in afiles; do 
    base=$(basename ${n})
    ibase=$(echo $base | rev | cut -c2- | rev)
    orign="${odir}/${dname}/${ibase}.nii.gz"

    if [ -e "${orign}" ]; then
        diff=$(diff $n $orign)
        if [ "$diff" == "" ]; then
            logger "INFO" "Removing duplicate image: ${n}"
            rm ${n}
        fi 
    fi 
done

# Clean up filenames (remove special characters)
file_list=$(find ${odir} -type f -name "*.nii.gz")
for f in $file_list; do
    d=$(dirname $f)
    b=$(basename $f .nii.gz)
    clean=$(echo "${b/[\{\}\[\]\!\"\'.@#$%^&*()+:;<>?~]/_}")
    if [[ ! -e "${d}/${clean}.nii.gz" ]]; then
        logger "INFO" "Renaming $b as $clean"
        mv ${d}/${b}.nii.gz ${d}/${clean}.nii.gz
        mv ${d}/${b}.json ${d}/${clean}.json
    fi
    
done
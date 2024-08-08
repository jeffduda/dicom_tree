#!/bin/bash
module load dcm2niix
module load python/3.10

idir=""
odir=""
name=""
tags=""

while getopts i:n:o:ht: flag
do 
  case "${flag}" in
     i) idir=${OPTARG};;
     n) name=${OPTARG};;
     o) odir=${OPTARG};;
     t) tags=${OPTARG};;
     h) usage;;
  esac
done

# Does input directory exist
if [ ! -d "${idir}" ]; then
    echo "Input directory does not exist"
fi

# Create output directory if it does not exist
if [ ! -d "${odir}" ]; then
    echo "Create output directory: ${odir}"
    mkdir -p ${odir}
fi

# Run dcm2niix
# ignore derived, localizers and 2D
fmt="%f"
if [ "$name" != "" ]; then
    fmt="${name}_%f"
else
    name=$(basename ${idir})
fi

# -i y ignore derived & localizers & 2D
# -z y compress
# -a y anonymize
exe="dcm2niix -i y -z y -a y -o ${odir} -f "${fmt}" ${idir}"
echo $exe
$exe

# remove things we don't want
eq_list=$(find ${odir} -type f -name "*Tilt_Eq_1*")
for f in $eq_list; do
    base=$(basename $f)
    dname=$(dirname $f)
    eq="${dname}/${base}.nii.gz"
    eqj="${dname}/${base}.json"
    echo "Removing: ${f}"

    rm ${f}
    if [ -e "${eq}" ]; then
        echo "Removing: ${eq}"
        rm ${eq}
    fi
    if [ -e "${eqj}" ]; then
        echo "Removing: ${eqj}"
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
            echo "Removing duplicate image: ${n}"
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
        echo "Renaming $b as $clean"
        mv ${d}/${b}.nii.gz ${d}/${clean}.nii.gz
        mv ${d}/${b}.json ${d}/${clean}.json
    fi
    
done
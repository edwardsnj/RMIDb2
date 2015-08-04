#!/bin/sh
DATE=`date +"%Y%m%d"`
RELEASE=`wget -q -O - ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/reldate.txt | sed -n 's/UniProt Knowledgebase Release \(.*\) consists of:$/\1/p'`

# Reviewed, Bacteria, KW: Ribosomal protein
F=uniprot.ribosomal-reviewed-bacteria.$RELEASE-$DATE.fasta
wget -q -O "$F.gz" 'http://www.uniprot.org/uniprot/?sort=score&desc=&compress=yes&query=reviewed:yes%20AND%20taxonomy:%22Bacteria%20[2]%22%20AND%20keyword:%22Ribosomal%20protein%20[KW-0689]%22&fil=&format=fasta&force=yes&include=yes'

# Reviewed, Bacteria, KW: Ribosomal protein
F=uniprot.ribosomal-bacteria.$RELEASE-$DATE.fasta
wget -q -O "$F.gz" 'http://www.uniprot.org/uniprot/?sort=score&desc=&compress=yes&query=taxonomy:%22Bacteria%20[2]%22%20AND%20keyword:%22Ribosomal%20protein%20[KW-0689]%22&fil=&format=fasta&force=yes&include=yes'


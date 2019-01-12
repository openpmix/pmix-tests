#!/bin/bash

for n in {1..1000}
do
	echo "Execution $n"
	prun -n 1 hostname
	st=$?
	if [ $st -ne 0 ]
	then
		exit
	fi
done

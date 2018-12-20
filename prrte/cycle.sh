#!/bin/bash

for n in {1..100}
do
	echo "Execution $n"
	prun -n 1 hostname
done

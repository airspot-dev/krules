#!/bin/bash

curl -s $1 -H "authorization: Bearer $3" -H "Content-Type: application/json" -d @$2
echo $(date +%d-%m-%Y_%H-%M-%S)

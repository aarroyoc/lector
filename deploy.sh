#!/usr/bin/bash

rm -rf package
poetry export -frequirements.txt > requirements.txt
pip install --target ./package -r requirements.txt
cd package
zip -r9 ../function.zip .
cd ..
zip -g function.zip static/*
zip -g function.zip templates/*
zip -g function.zip sources.opml
zip -g function.zip main.py
./terraform init
./terraform apply
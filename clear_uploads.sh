#!/bin/sh
echo Deleting upload folder contents...
find upload -type f
find upload -type f -delete
echo Done

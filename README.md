# Project351
Code to select best location for a drone delivery service for AAE 351 at Purdue.

This code needs to be run in the Tracts_Block_Groups_Only folder for the 5-year American Community Survey available from the US Census Bureau using FTP. This code has been run with the 2018 ACS 5-year dataset. 

This code also requires a path to (still zipped) shapefiles from the US Census Bureau for block groups: "BG" dataset.

The process I followed is process.ipynb -> analysis.ipynb -> graphing.ipynb. Convenience functions and objects are in census.py.

Dependencies include US, GeoPandas, numpy, scipy

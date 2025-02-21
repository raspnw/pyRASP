import os
import logging
import sys
import datetime

gdal_translate -of Gtiff -a_ullr LEFT_LON UPPER_LAT RIGHT_LON LOWER_LAT -a_srs EPSG_PROJ INPUT_PNG_FILE OUTPUT_GTIFF_FILE
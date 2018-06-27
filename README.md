# aChor
aChor
Task oriented data classification for choropleth maps (German Research Foundation funded)

This plugin aChor was designed only for polygon shapefile dataset
  You may download a test dataset here:https://goo.gl/8ixjNn

Your default aChor plugin directory is located at:
  Windows QGIS2:C:/Users/user_name/.qgis2/python/plugins/aChor
  Linux QGIS2:/home/user_name/.qgis2/python/plugins/aChor
  Windows QGIS3:C:/OSGeo4W/apps/qgis/python/plugins/aChor
  Linux QGIS3:/home/user_name/.local/share/QGIS/QGIS3/profiles/default/python/plugins/aChor

Before you deploy the plugin:

This plugin using fiona, shapely and Rtree libraries.
Rtree must be version 0.8.3 or above.

To install python packages, please using pip or easy_install in OSGEO4W shell.
Linux: sudo wget http://ftp.de.debian.org/debian/pool/main/p/python-rtree/python-rtree_0.8.3+ds-1_all.deb 
       sudo apt install /filedir/python-rtree_0.8.3+ds-1_all.deb

Windows: python -m pip install Rtree-0.8.3-cp36-cp36m-win_amd64.whl

For windows python packages, you may download them here:http://www.lfd.uci.edu/~gohlke/pythonlibs/#fiona

Check if libraries successfully installed, open the OSGEO4W shell and try to import them.
C:\> python
>>> import rtree
>>> import fiona
>>> import shapely

Notes:

You can also run the classification from OSGeo4W command shell. 

Usage:
>> python class_achor.py [class_num] [sweep_interval] [field_name] [shapefile] [method]

Method:
1: Localextremes (max and min)
2: Localmax
3: Localmin

For Examples:
>> python class_achor.py 10 0.2 SUMME susamme15.shp 1

For more information on aChor project, please visit aChor project website http://www.geomatik-hamburg.de/g2lab/research-achor.html
for further information.

License Information, 2018-2021: Lab for Geoinformatics and Geovisualization (g2lab), Hafencity University Hamburg

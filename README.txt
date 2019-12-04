aChor
Task oriented data classification for choropleth maps (German Research Foundation funded)


This plugin aChor was designed only for polygon shapefile dataset
   You may download a test dataset here: http://tiny.cc/xspc0y
   
The method of the algorithm: https://tinyurl.com/y99tk8gx

Your default aChor plugin directory is located at:

   Windows QGIS3:C:/OSGeo4W/apps/qgis/python/plugins/aChor
   Linux QGIS3:/home/user_name/.local/share/QGIS/QGIS3/profiles/default/python/plugins/aChor 



Before you deploy the plugin:

•This plugin using fiona, shapely, gdal, pysal, Rtree, sklearn and dbf libraries. 
•Rtree must be version 0.8.3 or above. 
•To install python packages, please using pip or easy_install in OSGEO4W shell. 
•Linux: sudo wget http://ftp.de.debian.org/debian/pool/main/p/python-rtree/python-rtree_0.8.3+ds-1_all.deb 
             sudo apt install /filedir/python-rtree_0.8.3+ds-1_all.deb 
•Windows: python -m pip install Rtree-0.8.3-cp36-cp36m-win_amd64.whl 
•For windows python packages, you may download them here: http://www.lfd.uci.edu/~gohlke/pythonlibs/#fiona 
•Check if libraries successfully installed, open the OSGEO4W shell and try to import them. 
•C:\> py3_env
•C:\> python
 >>> import rtree
 >>> import fiona
 >>> import shapely 
 >>> import pysal
 >>> import sklearn
 >>> import dbf
 
Notes: 
1.GitHub for bug report and tracking: https://github.com/Ariel505/aChor/issues/ 
2.You can also run the classification from OSGeo4W command shell. 

Usage: python class_achor.py [class_num] [sweep_interval] [field_name] [shapefile] [method]
       method: 1: Localextremes (max and min) 2: Localmax 3: Localmin 4: Hotspot 5: Neighbors 6: Clusters
for example: python class_achor.py 10 0.2 SUMME Hamburg.shp -m 1 


For more information on aChor project, please visit aChor project website http://www.geomatik-hamburg.de/g2lab/research-achor.html for further information. 

License Information, 2018-2021: g2lab, Hafencity University Hamburg http://www.geomatik-hamburg.de/g2lab/


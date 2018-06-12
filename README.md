# aChor
Task oriented data classification for choropleth maps (DFG funded)

License Information: g2lab, Hafencity University Hamburg

Project website: http://www.geomatik-hamburg.de/g2lab/research-achor.html

Usage:
>> python class_achor.py [class_num] [sweep_interval] [field_name] [shapefile] [method]

Method:
1: Localextremes (max and min)
2: Localmax
3: Localmin

For Examples:
>> python class_achor.py 10 0.2 SUMME susamme15.shp 1

Pre-request python packages:

Minimum Verion: Shapely(1.2.18) , Fiona(1.7.6), Rtree(0.8.3), Sqlite3(Optional)

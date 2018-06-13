# aChor
Task oriented data classification for choropleth maps (DFG funded)

License Information: g2lab, Hafencity University Hamburg

Project website: http://www.geomatik-hamburg.de/g2lab/research-achor.html

Pre-request python packages:
Minimum Verion: Rtree(0.8.3), Shapely, Fiona, Sqlite3(Optional)

Install Rtree: (in Linux python 2.x)
>> sudo wget http://ftp.de.debian.org/debian/pool/main/p/python-rtree/python-rtree_0.8.3+ds-1_all.deb
And: <br/>
>> sudo apt install /filedir/python-rtree_0.8.3+ds-1_all.deb <br/>

Usage:
>> python class_achor.py [class_num] [sweep_interval] [field_name] [shapefile] [method]

Method:
1: Localextremes (max and min)
2: Localmax
3: Localmin

For Examples:
>> python class_achor.py 10 0.2 SUMME susamme15.shp 1

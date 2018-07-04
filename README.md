<html>
<head>
<script>
var links = document.links;
for (var i = 0, linksLength = links.length; i < linksLength; i++) {
   if (links[i].hostname != window.location.hostname) {
       links[i].target = '_blank';
   } 
}
</script>
</head>
<body>
<h3>aChor</h3>
<img src="https://github.com/Ariel505/aChor/blob/master/icon.png?raw=true" alt="aChor" width="60px;" style="position: absolute;top:20px;right:50px;" align="right" />
Task oriented data classification for choropleth maps (German Research Foundation funded)<br/><br />

<div id='help' style='font-size:.9em;'>
This plugin <b>aChor</b> was designed only for polygon shapefile dataset<br>
&nbsp;&nbsp;You may download a test dataset here:&nbsp;&nbsp;<a href="https://goo.gl/8ixjNn" target='_blank'>https://goo.gl/8ixjNn</a><br><br>
<p>
Your default aChor plugin directory is located at:<br>
&nbsp;&nbsp;Windows QGIS2:&nbsp;&nbsp;<b>C:/Users/user_name/.qgis2/python/plugins/aChor</b><br>
&nbsp;&nbsp;Linux QGIS2:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>/home/user_name/.qgis2/python/plugins/aChor</b><br>
&nbsp;&nbsp;Windows QGIS3:&nbsp;&nbsp;<b>C:/OSGeo4W/apps/qgis/python/plugins/aChor</b><br>
&nbsp;&nbsp;Linux QGIS3:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>/home/user_name/.local/share/QGIS/QGIS3/profiles/default/python/plugins/aChor</b>
<p>
<h3>Before you deploy the plugin:</h3>
<ul>
    <li>This plugin using fiona, shapely, gdal and Rtree libraries.
    <li>Rtree must be version 0.8.3 or above.
    <li>To install python packages, please using pip or easy_install in OSGEO4W shell.
    <li>Linux: <br><i>sudo wget http://ftp.de.debian.org/debian/pool/main/p/python-rtree/python-rtree_0.8.3+ds-1_all.deb </i><br>
	<i>sudo apt install /filedir/python-rtree_0.8.3+ds-1_all.deb</i>
    <li>Windows: <i>python -m pip install Rtree-0.8.3-cp36-cp36m-win_amd64.whl</i>
    <li>For windows python packages, you may download them here:<a href="http://www.lfd.uci.edu/~gohlke/pythonlibs/#fiona" target='_blank'>http://www.lfd.uci.edu/~gohlke/pythonlibs/#fiona</a>
    <li>Check if libraries successfully installed, open the OSGEO4W shell and try to import them.
	<li>C:\> python<br>
	&gt;&gt;&gt;&nbsp;import rtree<br>
	&gt;&gt;&gt;&nbsp;import fiona<br>
	&gt;&gt;&gt;&nbsp;import shapely
</ul>
<h3>Notes:</h3>
<ul>
    <li><b>GitHub</b> for bug report and tracking:
        <a href="https://github.com/Ariel505/aChor/issues/">https://github.com/Ariel505/aChor/issues/</a><br>
    <li>You can also run the classification from <b>OSGeo4W</b> command shell. <br><br>Usage:&nbsp;<br><i>python &nbsp;class_achor.py &nbsp;[class_num] &nbsp;[sweep_interval] &nbsp;[field_name] &nbsp;[shapefile] &nbsp;[method]</i><br>
	<p style='font-size:.8em;'><i>[Method]: <br>1: &nbsp;Localextremes (max and min) <br>2: &nbsp;Localmax <br>3: &nbsp;Localmin</i></p>
	for example: <br><i>python &nbsp;class_achor.py &nbsp;10 &nbsp;0.2 &nbsp;SUMME &nbsp;Hamburg.shp &nbsp;1</i>
	
	
</ul>
</div>
<p style='font-size:.10em;'><b>Official QGIS Plugin Repository - for QGIS2 and QGIS3<a href="https://plugins.qgis.org/plugins/aChor/" target='_blank' title='aChor QGIS Plugin URL'>
https://plugins.qgis.org/plugins/aChor/
</a></b></p>
<div style='font-size:.9em;'>
<p>
For more information on aChor project, please visit <a href="http://www.geomatik-hamburg.de/g2lab/research-achor.html" target='_blank'>aChor  project website</a> for further information.
</p>
</div>
<p>
<i> License Information, 2018-2021:</i>  Lab for Geoinformatics and Geovisualization <a href="http://www.geomatik-hamburg.de/g2lab/" target='_blank'>(g2lab)</a>, Hafencity University Hamburg, Germany
</p>
</body>
</html>

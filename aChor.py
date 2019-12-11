# -*- coding: utf-8 -*-
"""
/***************************************************************************
 aChor - Task oriented data classification for choropleth maps
                              -------------------
        last update version  : v0.6, 2018-10-31
        GitHub               : https://github.com/Ariel505/aChor
        copyright            : (C) 2018 by Hafencity university Hamburg
        email                : juiwen.chang@hcu-hamburg.de
 ***************************************************************************/
 
/***************************************************************************
 *                                                                         *
 *   Partial of Hotspot code were copied from HotSpot Analysis plugin      *
 *   https://github.com/danioxoli/HotSpotAnalysis_Plugin                   *
 *   Oxoli, D., Prestifilippo, G., Bertocchi, D., Zurbaràn, M. (2017).     *
 *    Enabling spatial autocorrelation mapping in QGIS:                    *
 *                  The Hotspot Analysis Plugin.                           *
 ***************************************************************************/
 
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import *
#QSettings, QTranslator, qVersion, QCoreApplication, QRegExp
from PyQt5.QtGui import QIcon, QColor, QRegExpValidator
from PyQt5.QtWidgets import QAction, QLineEdit, QDesktopWidget, QMessageBox, QDockWidget
from qgis.core import *
#from qgis.core import QgsProject, QgsVectorLayer, QgsRenderContext
#QgsSymbolV2, QgsRendererRangeV2, QgsGraduatedSymbolRendererV2, QgsMapLayerRegistry
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .aChor_dialog import aChorDialog
import os.path
import os, sys, subprocess, shlex, shutil
from subprocess import Popen, PIPE
from osgeo import ogr
import qgis.utils
import fiona, logging, csv, time
from shapely.geometry import shape, mapping
import pysal
from pysal.esda.getisord import *
from pysal.weights.Distance import DistanceBand

import numpy as np

#sys.setrecursionlimit(8000)

from sklearn.cluster import DBSCAN
from sklearn import metrics
from sklearn.datasets.samples_generator import make_blobs
from sklearn.preprocessing import StandardScaler
import dbf
   
class aChor:
    """QGIS Plugin Implementation."""

    
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'aChor_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = aChorDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Task-oriented data classification for polygons')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'aChor')
        self.toolbar.setObjectName(u'aChor')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('aChor', message)

    def pr(self, msg):
        QMessageBox.information(self.iface.mainWindow(),"Debug",msg)
        
    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/aChor/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Task-oriented data classification for polygons'),
            callback=self.run,
            parent=self.iface.mainWindow())
        self.dlg.rdb1.clicked.connect(self.setDisable)
        self.dlg.rdb2.clicked.connect(self.setDisable)
        self.dlg.rdb3.clicked.connect(self.setDisable)
        self.dlg.rdb5.clicked.connect(self.setDisable)
        self.dlg.rdb6.clicked.connect(self.setDisable)
        rx3 = QRegExp('^0$|^[1-9]\d*$|^\.\d+$|^0\.\d*$|^[1-9]\d*\.\d*$')
        validator3 = QRegExpValidator(rx3)
        self.dlg.linefdb.setValidator(validator3)        
        self.dlg.rdb4.clicked.connect(self.setEnable)
        self.dlg.rdb6.clicked.connect(self.setEnable)


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Localextremes classification'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def setEnable(self):        
        if self.dlg.rdb4.isChecked():
            self.dlg.label_5.setDisabled(False)
            self.dlg.label_7.setDisabled(False)
            self.dlg.linefdb.setDisabled(False)
            self.load_comboBox()
            self.dlg.linefdb.setText(str(round(thresh,4)))
        if self.dlg.rdb6.isChecked():
            self.dlg.label_8.setDisabled(False)
            self.dlg.lineps.setDisabled(False)
            self.dlg.lineps.setText('0.5')
    
    def setDisable(self):
        self.dlg.label_5.setDisabled(True)
        self.dlg.label_7.setDisabled(True)
        self.dlg.linefdb.setDisabled(True)
        self.dlg.label_8.setDisabled(True)
        self.dlg.lineps.setDisabled(True)

        
    def clear_fields(self):
        """Clearing the fields when layers are changed"""
        self.dlg.comboBox.clear()

    def load_comboBox(self):
        """Load the fields into combobox when layers are changed"""
        layer_shp = []
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        
        if len(layers) != 0:  # checklayers exist in the project
            for layer in layers:
                if hasattr(layer, "dataProvider"):
                    myfilepath = layer.dataProvider().dataSourceUri() 
                    (myDirectory, nameFile) = os.path.split(myfilepath)
                    if (".shp" in nameFile):
                        layer_shp.append(layer)
        selectedLayerIndex = self.dlg.layerListCombo.currentIndex()
        if selectedLayerIndex < 0 or selectedLayerIndex > len(layer_shp):
            return
        try:
            selectedLayer = layer_shp[selectedLayerIndex]
        except:
            return

        self.clear_fields()
        
        strname = []
        #only Float or Integer field types will be shown in combobox
        for field in selectedLayer.fields():
            ftype = str(field.type())
            if ftype == '2' or ftype == '6':
                strname.append(field.name())
                
        self.dlg.comboBox.addItems(strname)

        (path, layer_id) = selectedLayer.dataProvider().dataSourceUri().split('|')

        inDriver = ogr.GetDriverByName("ESRI Shapefile")
        inDataSource = inDriver.Open(path, 0)
        inLayer = inDataSource.GetLayer()
        global type
        global thresh
        type = inLayer.GetLayerDefn().GetGeomType()

        if type == 3:  # is a polygon
            thresh = pysal.min_threshold_dist_from_shapefile(path)
            self.suggest_sweep(str(path).strip(), self.dlg.comboBox.currentText())
            selectedFieldIndex = self.dlg.comboBox.currentIndex()
            if selectedFieldIndex < 0:
                return
            try:
                self.dlg.comboBox.activated.connect(lambda: self.suggest_sweep(str(path).strip(), str(self.dlg.comboBox.currentText()).strip()))
                #self.dlg.comboBox.currentIndexChanged.connect(lambda: self.suggest_sweep(str(path).strip(), str(self.dlg.comboBox.currentText()).strip()))

            except:
                return
        else:
          QMessageBox.warning(self.dlg.show(), self.tr("aChor:Warning"),
                     self.tr("This is not a polygon shapefile. Please reselect from layer list"), QMessageBox.Ok)  
            
            
            
        
    def loadLayerList(self):
        layers_list = []
        layers_shp = []
        # Show the shapefiles in the ComboBox
        #layers = self.iface.legendInterface().layers()
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        
        if len(layers) != 0:  # checklayers exist in the project
            for layer in layers:
                if hasattr(layer, "dataProvider"):  # to not consider Openlayers basemaps in the layer list
                    myfilepath = layer.dataProvider().dataSourceUri()  # directory including filename
                    (myDirectory, nameFile) = os.path.split(myfilepath)  # splitting into directory and filename
                    if (".shp" in nameFile):
                        layers_list.append(layer.name())
                        layers_shp.append(layer)
            self.dlg.layerListCombo.addItems(layers_list)  # adding layers to comboBox
            selectedLayerIndex = self.dlg.layerListCombo.currentIndex()
            if selectedLayerIndex < 0 or selectedLayerIndex > len(layers_shp):
                return
            selectedLayer = layers_shp[selectedLayerIndex]
            #fieldnames = [field.name() for field in selectedLayer.pendingFields()]  # fetching fieldnames of layer
            fieldnames = [field.name() for field in selectedLayer.fields()]
            self.clear_fields()
            #fieldtype = [field.type() for field in selectedLayer.pendingFields()]
            fieldtype = [field.type() for field in selectedLayer.fields()]
            if (fieldtype == 'int') or (fieldtype == 'double'):
                self.dlg.comboBox.addItems(fieldnames)
            try:
                self.dlg.layerListCombo.activated.connect(lambda: self.load_comboBox())
                self.dlg.layerListCombo.currentIndexChanged.connect(lambda: self.load_comboBox())

            except:
                return False
            return [layers, layers_shp]
        else:
            return [layers, False]
        
    def suggest_sweep(self, inp, attr):

        with fiona.open(inp) as source:
            features = list(source)

        global achor_max_val
        global achor_min_val
        suggestion = 1
        
        try:
            achor_max_val = max(val['properties'][attr] for val in features)
            achor_min_val = min(val['properties'][attr] for val in features)
        except KeyError:
            return
        
        if (achor_max_val > achor_min_val):
            valrange = achor_max_val-achor_min_val
    
            if 0 < valrange < 1:
                suggestion = valrange/100
            elif 1 < valrange < 100:
                suggestion = round(valrange/(valrange*1.1),2)
            elif 100 < valrange < 1000:
                suggestion = round(valrange/(valrange*0.37),2)
            elif valrange > 1000:
                suggestion = valrange/(valrange/2)
            self.dlg.lineEdit2.setText(str(suggestion))
        source.close()
        
    def create_colorrange(self, i_step, i_start, i_stop, mid=None):
        import math
        """Takes a number of steps to create a color range for given hex color values"""
        def get_range(step, start, stop):
            try:
                initial_start = start
                initial_stop = stop
                
                start = start.lstrip('#')
                stop = stop.lstrip('#')
                
                start_rgb = []
                stop_rgb = []
                
                start_rgb.extend([int(start[i:i+2], 16) for i in (0, 2, 4)])
                stop_rgb.extend([int(stop[i:i+2], 16) for i in (0, 2, 4)])
                
                color_gradient = [initial_start]
                
                step_rgb = []
                operator = []

                for start, stop in zip(start_rgb, stop_rgb):
                    step_rgb.append(int(abs(start-stop)/(step-1)))
                    if start > stop:
                        operator.append('-')
                    else:
                        operator.append('+')

                for i in range(int(step)-2):
                    for i in range(3):
                        if operator[i] == "+":
                            start_rgb[i] += step_rgb[i]
                        elif operator[i] == "-":
                            start_rgb[i] -= step_rgb[i]
                    
                    result = '#' + ''.join('0' + str(hex(abs(rgb_val))).lstrip('0x')
                                           if abs(rgb_val) in ([x for x in range(1,16)])
                                           else '00' if abs(rgb_val) == 0 
                                           else str(hex(abs(rgb_val))).lstrip('0x')
                                           for rgb_val in start_rgb)
                    
                    color_gradient.append(result)  
                color_gradient.append(initial_stop)
                
                return color_gradient
            except ZeroDivisionError:
                print("step is {}, has to be minimum 2!".format(step))
                
        if mid:
            case_even = 0
            if i_step % 2 == 0:
                case_even = 1
            i_step = math.ceil(float(i_step) / 2)
            result = [x for x in get_range(i_step, i_start, mid)]
            result.extend([x for x in get_range(i_step+case_even, mid, i_stop)[1:]])
            
            return result
        return get_range(i_step, i_start, i_stop)
    
    def write_file(self, outfilename, statistics, layerName, inLayer, inDataSource, y, threshold):
        """Writing the output shapefile into the mentioned directory"""
        outDriver = ogr.GetDriverByName("ESRI Shapefile")

        layerName = layerName.split('.')
        layerName.pop()
        # layerName = '.'.join(layerName)

        outShapefile = outfilename + ".shp"

        # Remove eventually alrady exisiting output
        if os.path.exists(outShapefile):
            outDriver.DeleteDataSource(outShapefile)        
        # Create the output shapefile
        outDataSource = outDriver.CreateDataSource(outShapefile)
        outLayer = outDataSource.CreateLayer("output", inLayer.GetSpatialRef(), inLayer.GetLayerDefn().GetGeomType())

        # Add input Layer Fields to the output Layer
        inLayerDefn = inLayer.GetLayerDefn()
        
        for i in range(0, inLayerDefn.GetFieldCount()):
            fieldDefn = inLayerDefn.GetFieldDefn(i)
            outLayer.CreateField(fieldDefn)

        # Add empty field to store Pysal results
        Z_field = ogr.FieldDefn("Z-score", ogr.OFTReal)
        Z_field.SetWidth(15)
        Z_field.SetPrecision(10)
        outLayer.CreateField(Z_field)

        p_field = ogr.FieldDefn("p-value", ogr.OFTReal)
        p_field.SetWidth(15)
        p_field.SetPrecision(10)
        outLayer.CreateField(p_field)

        # Create a Field to show hot or coldspot
        Gi_bin = ogr.FieldDefn("Gi_Bin", ogr.OFTString)
        Gi_bin.SetWidth(10)
        Gi_bin.SetPrecision(10)
        outLayer.CreateField(Gi_bin)
        
        # Get the output Layer's Feature Definition
        outLayerDefn = outLayer.GetLayerDefn()

        # Get the input Layer's Feature Definition
        inLayerDefn = inLayer.GetLayerDefn()

        # Add features to the ouput Layer
        for i in range(0, inLayer.GetFeatureCount()):
            # Get the input Feature
            inFeature = inLayer.GetFeature(i)
            # Create output Feature
            outFeature = ogr.Feature(outLayerDefn)
            # Add field values from input Layer
            for j in range(0, inLayerDefn.GetFieldCount()):
                outFeature.SetField(outLayerDefn.GetFieldDefn(j).GetNameRef(), inFeature.GetField(j))
            # Set geometry
            geom = inFeature.GetGeometryRef()
            outFeature.SetGeometry(geom)

            if self.dlg.rdb4.isChecked() == 1:
                # Add Z-scores and p-values to their field column
                # to use normality hypothesis
                # first version: max(y)
                if np.mean(y) >= 0:
                    outFeature.SetField("Z-score", statistics.Zs[i])
                    outFeature.SetField("p-value", statistics.p_norm[i] * 2)
                    Z_score = float(statistics.Zs[i])
                    p_value = float(statistics.p_norm[i] * 2)
                else:
                    outFeature.SetField("Z-score", statistics.Zs[i] * (-1))
                    outFeature.SetField("p-value", statistics.p_norm[i] * 2) 
                    Z_score = float(statistics.Zs[i] * (-1))
                    p_value = float(statistics.p_norm[i] * 2)
                # Set Gi_Bin Field
                if Z_score <= -2.58 and p_value <= 0.01:
                    outFeature.SetField("Gi_Bin", "-3")
                elif Z_score >= 2.58 and p_value <= 0.01:
                    outFeature.SetField("Gi_Bin", "3")
                elif Z_score <= -1.96 and Z_score > -2.58 and p_value <= 0.05 and p_value > 0.01:
                    outFeature.SetField("Gi_Bin", "-2")
                elif Z_score >= 1.96 and Z_score < 2.58 and p_value <= 0.05 and p_value > 0.01:
                    outFeature.SetField("Gi_Bin", "2")
                elif Z_score <= -1.65 and Z_score > -1.96 and p_value <= 0.1 and p_value > 0.05:
                    outFeature.SetField("Gi_Bin", "-1")
                elif Z_score >= 1.65 and Z_score < 1.96 and p_value <= 0.1 and p_value > 0.05:
                    outFeature.SetField("Gi_Bin", "1")
                else:
                    outFeature.SetField("Gi_Bin", "0")
                 
            # Add new feature to output Layer
            outLayer.CreateFeature(outFeature)

        # Close DataSources
        inDataSource.Destroy()
        outDataSource.Destroy()

        #new_layer = self.iface.addVectorLayer(outfilename + ".shp", str(os.path.basename(os.path.normpath(outfilename))),
        #                                      "ogr")
        #if not new_layer:
        #    QMessageBox.information(self.dlg, self.tr("New Layer"), self.tr("Layer Cannot be Loaded"), QMessageBox.Ok)
    
    def getCentroid(self,shp,outpoint):
        with fiona.open(shp) as src:
            meta = src.meta
            meta['schema']['geometry'] = 'Point'
            meta['schema']['properties'].update({'cX': 'float:15.13','cY': 'float:15.13','dbscan': 'int'})
            with fiona.open(outpoint, 'w', **meta) as dst:
                for f in src:
                    centroid = shape(f['geometry']).centroid                    
                    f['geometry'] = mapping(centroid)
                    f['properties']['cX'] = round(float(f['geometry']['coordinates'][1]),13)
                    f['properties']['cY'] = round(float(f['geometry']['coordinates'][0]),13)
                    f['properties']['dbscan'] = 0
                    dst.write(f)
            dst.close()
        src.close()
    
    
    def make_var_density_blobs(self,n_samples=100, centers=[[0,0]], cluster_std=[0.5], random_state=0):
        samples_per_blob = n_samples // len(centers)
        blobs = [make_blobs(n_samples=samples_per_blob, centers=[c], cluster_std=cluster_std[i])[0]
             for i, c in enumerate(centers)]
        labels = [i * np.ones(samples_per_blob) for i in range(len(centers))]
        return np.vstack(blobs), np.hstack(labels)

    def dbf_to_csv(self,dbf_table_pth):#Input a dbf, output a csv, same name, same path, except extension
        csv_fn = dbf_table_pth[:-4]+ ".csv" #Set the csv file name
        QMessageBox.warning(self.dlg.show(), self.tr("aChor:Info"),
                     self.tr(str(csv_fn)), QMessageBox.Ok)
        table = DBF(dbf_table_pth)# table variable is a DBF object
        with open(csv_fn, 'w', newline = '') as f:# create a csv file, fill it with dbf content
            writer = csv.writer(f)
            writer.writerow(table.field_names)# write the column name
            for record in table:# write the rows
                writer.writerow(list(record.values()))
        return csv_fn# return the csv name

    def run(self):
        """Run method that performs all the real work"""

        self.dlg.layerListCombo.clear()
        self.clear_fields()
        
        layers, layers_shp = self.loadLayerList()
        if len(layers) == 0:
            return       


        #set regular expression
        rx = QRegExp('^[1-9]\d{1}$')
        validator = QRegExpValidator(rx)
        self.dlg.lineEdit.setValidator(validator)
        rx2 = QRegExp('^0$|^[1-9]\d*$|^\.\d+$|^0\.\d*$|^[1-9]\d*\.\d*$')
        validator2 = QRegExpValidator(rx2)
        self.dlg.lineEdit2.setValidator(validator2)
        rx3 = QRegExp('^(0(\.\d+)?|1\.0)\d{0,3}$')
        validator3 = QRegExpValidator(rx3)
        self.dlg.lineps.setValidator(validator3)
        # show the dialog
        self.dlg.show()
        self.load_comboBox()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            logging.basicConfig(filename=self.plugin_dir+'/debug.log',filemode='w',level=logging.INFO)

            selectedLayerIndex = self.dlg.layerListCombo.currentIndex()
            if selectedLayerIndex < 0 or selectedLayerIndex > len(layers):
                return
            selectedLayer = layers_shp[selectedLayerIndex]
            layerName = selectedLayer.dataProvider().dataSourceUri()
            (path, layer_id) = layerName.split('|')
            inDriver = ogr.GetDriverByName("ESRI Shapefile")
            inDataSource = inDriver.Open(path, 0)
            inLayer = inDataSource.GetLayer()
            C = selectedLayer.fields().indexFromName(self.dlg.comboBox.currentText())
            type = inLayer.GetLayerDefn().GetGeomType()
            
            if type == 3:  # polygon
               #pass
                classnum = self.dlg.lineEdit.text()
                interval = self.dlg.lineEdit2.text()
                field = self.dlg.comboBox.currentText()
                shp = str(path)
                if self.dlg.rdb3.isChecked():
                    method = 1
                    display = 'localextreme'
                elif self.dlg.rdb1.isChecked():
                    method = 2
                    display = 'localmax'
                elif self.dlg.rdb2.isChecked():
                    method = 3
                    display = 'localmin'
                elif self.dlg.rdb4.isChecked():
                    method = 4
                    display = 'hotcoldspot'
                elif self.dlg.rdb5.isChecked():
                    method = 5
                    display = 'neighbor'
                elif self.dlg.rdb6.isChecked():
                    method = 6
                    display = 'cluster'
                elif self.dlg.rdb7.isChecked():
                    method = 7
                    display = 'globalextreme'
                myVectorLayer = QgsVectorLayer(path, display, 'ogr')

                #QMessageBox.warning(self.dlg.show(), self.tr("aChor:Warning"),
                     #self.tr(self.plugin_dir+'\n'+classnum+'\n'+interval+'\n'+field+'\n'+shp+'\n'+display), QMessageBox.Ok)
                logging.info('class number:'+classnum+'\ninterval:'+str(interval)+'\nfield:'+field+'\nshapefile:'+shp+'\nmethods:'+display)

                #check if sweep interval is reasonable
                if ((achor_max_val-achor_min_val)/float(interval)) < 15:
                    interval = suggestion
                
                #qgis.utils.iface.actionShowPythonDialog().trigger()
                strdir=self.plugin_dir
                if os.name == "nt":
                    py_executable = 'python'
                    if str(sys.version)[:1] == '3':
                        py_executable += '3'
                    strdir=strdir.replace(".","").replace("\\","/").replace("//","/")
                elif os.name == "posix":
                    py_executable = 'python'
                
                if method == 4 or method == 6:                                                        
                    #convert polygon to point                    
                    outpoint = strdir+"/test/inputpoint"
                    self.getCentroid(shp,outpoint) 
                    
                    u = []
                    inDataSource1 = inDriver.Open(outpoint, 0)
                    inLayer1 = inDataSource1.GetLayer()

                    for i in range(0, inLayer1.GetFeatureCount()):
                        geometry = inLayer1.GetFeature(i)
                        u.append(geometry.GetField(C))                        
                    y = np.array(u)  # attributes vector
                    t = ()
                    for feature in inLayer1:
                        geometry = feature.GetGeometryRef()
                        xy = (geometry.GetX(), geometry.GetY())
                        t = t + (xy,)
                    
                    inDataSource1.Destroy()
                    
                    if method == 4:
                        thresh = pysal.min_threshold_dist_from_shapefile(path)
                        number = round(float(self.dlg.linefdb.text()),4)               
                        if number and self.dlg.rdb4.isChecked() and  method == 4:
                                QMessageBox.warning(self.dlg.show(), self.tr("aChor:Warning"),
                                            self.tr("Default Fixed Distance Band: "+str(round(thresh,4))+'\n User Defined: '+self.dlg.linefdb.text()), QMessageBox.Ok)
                                
                        #Run Getis-Ord statistics
                        outfilename = strdir+"/test/hotspotshp"
                        type_w = "B"
                        permutationsValue = 9999                   
                        np.random.seed(12345)
                        threshold = number
                        w = DistanceBand(t, int(number), p=2, binary=False)
                        logging.info("Hotspot: Fixed Distance Band: "+self.dlg.linefdb.text())
    
                        statistics = G_Local(y, w, star=True, transform=type_w, permutations=permutationsValue)
                        self.write_file(outfilename, statistics, layerName, inLayer, 
                                        inDataSource, 
                                        y, threshold)                      
                      
                        shp=outfilename+".shp"      
                   
                if method == 6:
                    # Generate samples
                    centers = [[0, -1], [12, 5], [30, 101]]
                    densities = [0.2, 0.9, 0.5]
                    #convert polygon to point                   
                    items=["cx","cy",field]
                    # convert attribute csv
                    dbfname=dbf.Table(outpoint+r"/inputpoint.dbf",codepage='utf8')
                    dbfname.open()    
                    csvname=strdir+"/test/inputpoint/inputpoint.csv"            
                   
                    with open(csvname, 'w', newline = '') as f:                        
                        writer = csv.writer(f)
                        writer.writerow(items)
                        for record in dbfname:
                            #print(record['GebietName'])
                            attribute_list = []
                            attribute_list.append(record['cx'])
                            attribute_list.append(record['cy'])
                            attribute_list.append(record[field.lower()])
                            try:                                   
                                writer.writerow(attribute_list)                                
                            except ValueError: 
                                pass
                    dbfname.close()
                    
                    # Compute DBSCAN   
                    data = np.loadtxt(open(csvname, "rb"), delimiter=",", skiprows=1)
                    nrows = data.shape[0]
                    
                    X, labels_true = self.make_var_density_blobs(n_samples=nrows, centers=centers, cluster_std=densities,
                            random_state=0)
                    X = StandardScaler().fit_transform(data)

                    outdbf = dbf.Table(outpoint+r"/inputpoint.dbf",codepage='utf8')   
                    outdbf.open(mode=dbf.READ_WRITE)                   
                    db_t1 = time.time()
                    db = DBSCAN(eps=float(self.dlg.lineps.text())).fit(X)
                    db_labels = db.labels_
                    db_elapsed_time = time.time() - db_t1
                    n_clusters_db_ = len(set(db_labels)) - (1 if -1 in db_labels else 0)
                    j=0
                    for record in outdbf:
                        with record as r:
                            r.dbscan=db_labels[j]
                            #print('write rows:'+str(j)+', value:'+str(db_labels[j]))
                            j +=1

                    if n_clusters_db_ <= 1:
                        print('Silhouette Coefficient: NaN (too few clusters)')
                        QMessageBox.warning(self.dlg.show(), self.tr("aChor:Warning"),
                                            self.tr("too few clusters: "+db_labels+"/n Please change eps to get better result"), QMessageBox.Ok)
                    outdbf.close()
                    
                sys.argv.append(classnum)
                sys.argv.append(interval)
                sys.argv.append(field)
                sys.argv.append(shp)
                sys.argv.append(method)
                cmd=py_executable+" "+strdir+"/class_achor.py "+classnum+" "+str(interval)+" "+field+" "+shp.strip().replace('\\',r'/')+" -m "+ str(method)
                logging.info("Starting main script")
                QMessageBox.warning(self.dlg.show(), self.tr("aChor:Info"),
                     self.tr("Starting Main Script... Please wait for response"), QMessageBox.Ok)
                proc = subprocess.Popen(shlex.split(cmd),shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    
                while True:
                    out = proc.stdout.readline()
                    if (str(out).strip() == "b''" or str(out).strip() == '') and proc.poll() is not None:
                        break
                    if not (str(out).strip() == '' or str(out).strip() == "b''"):
                        print('info:'+str(out).strip())
                    
                
                csvfile = strdir+'/achorbreaks.csv'
                 
                rcsv = open(csvfile, 'r')
                sortedlist = sorted(rcsv, key= lambda x: float(x))
               
                i = 0
                
                ranges = []
                colorstr = []
                minval = achor_min_val
                while i < int(classnum)-1:                  
                    colorstr.append(str(minval) + '_' + sortedlist[i].strip())                        
                    minval = round(float(sortedlist[i].strip()),3)
                    logging.info('breaks:'+sortedlist[i])
                    i += 1
                
                # create colorramps according to the amount of classes/breaks
                white_blue = self.create_colorrange(int(classnum), '#FFFFFF', '#3b71c6') #default
                green_yellow_red = self.create_colorrange(int(classnum), '#0ac956', '#f7411d', '#f7e81d')
                blue_beige_red = self.create_colorrange(int(classnum), '#4158f4', '#f94545', '#f7b559')
    
                crange_selection = self.dlg.cBox.currentIndex() # get the selection from the gui
                
                # provide other options
                if crange_selection == 0:
                    crange = white_blue
                elif crange_selection == 1:
                    crange = green_yellow_red
                elif crange_selection == 2:
                    crange = blue_beige_red
                    
                color_ranges = []
                for i in range(len(colorstr)-1):
                    color_ranges.append((colorstr[i], float(colorstr[i].split('_')[0]), float(colorstr[i].split('_')[1]), crange[i]))
                    if i == len(colorstr)-2:
                        color_ranges.append((colorstr[i+1], float(colorstr[i+1].split('_')[0]), float(colorstr[i+1].split('_')[1]), crange[i+1]))
                        color_ranges.append((colorstr[i+1].split("_")[1] + "_" + str(achor_max_val), float(colorstr[i+1].split("_")[1]), float(achor_max_val), crange[i+2]))
    
                # create a category for each item in attribute
                for label, lower, upper, color in color_ranges:
                     symbol = QgsSymbol.defaultSymbol(myVectorLayer.geometryType())
                     symbol.setColor(QColor(color))
                     rng = QgsRendererRange(lower, upper, symbol, label)
                     ranges.append(rng)
                    
                # create the renderer and assign it to a layer
                expression = field # field name               
                renderer = QgsGraduatedSymbolRenderer(expression, ranges)
                myVectorLayer.setRenderer(renderer)

                # load the layer with class breaks
                QgsProject.instance().addMapLayer(myVectorLayer)
                myVectorLayer.triggerRepaint()
                rcsv.close()
                # remove temporarily files
                os.remove(csvfile)
                if method == 4:
                    filelist = [ f for f in os.listdir(strdir+"/test/") if f.startswith("hotspotshp") ]
                    for f in filelist:
                        os.remove(os.path.join(strdir+"/test/", f))
                if method == 4 or method == 6:
                    shutil.rmtree(self.plugin_dir+"/test/inputpoint")
                shutil.rmtree(self.plugin_dir+"/tmp")
                print("log: aChor Classification Success")
                QMessageBox.information(self.dlg.show(), self.tr("aChor:Result"),
                     self.tr("aChor Classification Result Successful Loaded"), QMessageBox.Ok)

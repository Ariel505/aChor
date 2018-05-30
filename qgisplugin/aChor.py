# -*- coding: utf-8 -*-
"""
/***************************************************************************
 aChor
                                 A QGIS plugin
 task-oriented data classification for choropleth maps 
                              -------------------
        begin                : 2018-03-26
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Hafencity University Hamburg - g2lab
        email                : juiwen.chang@hcu-hamburg.de
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QRegExp
from PyQt4.QtGui import QAction, QIcon, QColor, QRegExpValidator, QLineEdit, QDesktopWidget, QMessageBox, QDockWidget
# Initialize Qt resources from file resources.py
import resources, qgis
from qgis.core import *
from qgis.core import (QgsSymbolV2,QgsRendererRangeV2,QgsGraduatedSymbolRendererV2,QgsVectorLayer,QgsMapLayerRegistry)
# Import the code for the dialog
from aChor_dialog import aChorDialog
import os.path
import numpy, os, sys, subprocess
from subprocess import Popen, PIPE, CREATE_NEW_CONSOLE
from osgeo import ogr
import qgis.utils
import fiona, logging, csv
from colour import Color


    
class aChor:
    """QGIS Plugin Implementation."""

    def pr(self, msg):
        QMessageBox.information(self.iface.mainWindow(), "Debug", msg)
    
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
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


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&extreme value classification for polygon')

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

        # Create the dialog (after translation) and keep reference
        self.dlg = aChorDialog()

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
            text=self.tr(u'Load polygon dataset for aChor classification'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&extreme value classification for polygon'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def clear_fields(self):
        """Clearing the fields when layers are changed"""
        self.dlg.comboBox.clear()
        
    def load_comboBox(self):
        """Load the fields into combobox when layers are changed"""
        layer_shp = []
        layers = self.iface.legendInterface().layers()
        if len(layers) != 0:  # checklayers exist in the project
            for layer in layers:
                if hasattr(layer, "dataProvider"):  # to not consider Openlayers basemaps in the layer list
                    myfilepath = layer.dataProvider().dataSourceUri()  # directory including filename
                    (myDirectory, nameFile) = os.path.split(myfilepath)  # splitting into directory and filename
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
        for field in selectedLayer.pendingFields():
            ftype = str(field.type())
            if ftype == '2' or ftype == '6':
                #strname.append(str(field.name()).decode('utf8').strip())
                strname.append(field.name())
                
        self.dlg.comboBox.addItems(strname)

        (path, layer_id) = selectedLayer.dataProvider().dataSourceUri().split('|')

        inDriver = ogr.GetDriverByName("ESRI Shapefile")
        inDataSource = inDriver.Open(path, 0)
        inLayer = inDataSource.GetLayer()
        global type
        type = inLayer.GetLayerDefn().GetGeomType()

        if type == 3:  # is a polygon
            
            self.suggest_sweep(str(path).strip(), self.dlg.comboBox.currentText())
            selectedFieldIndex = self.dlg.comboBox.currentIndex()
            if selectedFieldIndex < 0:
                return
            try:
                self.dlg.comboBox.activated.connect(lambda: self.suggest_sweep(str(path).strip(), str(self.dlg.comboBox.currentText()).strip()))
                self.dlg.comboBox.currentIndexChanged.connect(lambda: self.suggest_sweep(str(path).strip(), str(self.dlg.comboBox.currentText()).strip()))
                #QMessageBox.warning(self.dlg.show(), self.tr("aChor:Warning"),
                     #self.tr(str(sweep)), QMessageBox.Ok)
            except:
                return

            
            
            
        
    def loadLayerList(self):
        layers_list = []
        layers_shp = []
        # Show the shapefiles in the ComboBox
        layers = self.iface.legendInterface().layers()
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
            fieldnames = [field.name() for field in selectedLayer.pendingFields()]  # fetching fieldnames of layer
            self.clear_fields()
            fieldtype = [field.type() for field in selectedLayer.pendingFields()]
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
            
        # bad bad globals, but until now easiest solution without rewriting code    
        global achor_max_val
        global achor_min_val
        
        try:
            achor_max_val = max(val['properties'][attr] for val in features)
            achor_min_val = min(val['properties'][attr] for val in features)
        except KeyError:
            return 

        
        valrange = achor_max_val-achor_min_val

        if 0 < valrange < 1:
            suggestion = valrange/100
        elif 1 < valrange < 100:
            suggestion = round(valrange/(valrange*10),2)
        elif 100 < valrange < 1000:
            suggestion = round(valrange/(valrange*5),2)
        elif valrange > 1000:
            suggestion = valrange/(valrange/2)
        self.dlg.lineEdit2.setText(str(suggestion))
        
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
                    print(start, stop)
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
                    
                    result = '#' + ''.join('00' if abs(rgb_val) == 0 else
                                           '01' if abs(rgb_val) == 1 else
                                           '02' if abs(rgb_val) == 2 else
                                           '03' if abs(rgb_val) == 3 else
                                           '04' if abs(rgb_val) == 4 else
                                           '05' if abs(rgb_val) == 5 else
                                           '06' if abs(rgb_val) == 6 else
                                           '07' if abs(rgb_val) == 7 else
                                           '08' if abs(rgb_val) == 8 else
                                           '09' if abs(rgb_val) == 9 else
                                           '0a' if abs(rgb_val) == 10 else
                                           '0b' if abs(rgb_val) == 11 else
                                           '0c' if abs(rgb_val) == 12 else
                                           '0d' if abs(rgb_val) == 13 else
                                           '0e' if abs(rgb_val) == 14 else
                                           '0f' if abs(rgb_val) == 15 else
                                           str(hex(abs(rgb_val))).lstrip('0x')
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
            i_step = math.ceil(i_step / 2)
            result = [x for x in get_range(i_step, i_start, mid)]
            result.extend([x for x in get_range(i_step+case_even, mid, i_stop)[1:]])

            return result

        return get_range(i_step, i_start, i_stop)
        
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
        
        self.dlg.show()

        self.load_comboBox()
        

            
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            logging.basicConfig(filename=self.plugin_dir+'\debug.log',filemode='w',level=logging.INFO)

            selectedLayerIndex = self.dlg.layerListCombo.currentIndex()
            if selectedLayerIndex < 0 or selectedLayerIndex > len(layers):
                return
            selectedLayer = layers_shp[selectedLayerIndex]
            layerName = selectedLayer.dataProvider().dataSourceUri()
            (path, layer_id) = layerName.split('|')
            inDriver = ogr.GetDriverByName("ESRI Shapefile")
            inDataSource = inDriver.Open(path, 0)
            inLayer = inDataSource.GetLayer()
            type = inLayer.GetLayerDefn().GetGeomType()
            myVectorLayer = QgsVectorLayer(path, 'Layer', 'ogr')
            if type == 3:  # polygon
               #pass

                classnum = self.dlg.lineEdit.text()
                interval = self.dlg.lineEdit2.text()
                field = self.dlg.comboBox.currentText()
                shp = str(path)
                
                QMessageBox.warning(self.dlg.show(), self.tr("aChor:Warning"),
                     self.tr(self.plugin_dir+'\n'+classnum+'\n'+interval+'\n'+field+'\n'+shp), QMessageBox.Ok)
                logging.info('class number:'+classnum+'\ninterval:'+interval+'\nfield:'+field+'\nshapefile:'+shp)
                sys.argv.append(classnum)
                sys.argv.append(interval)
                sys.argv.append(field)
                sys.argv.append(shp)
                
                qgis.utils.iface.actionShowPythonDialog().trigger()
                logging.info("Starting main script")

                         
                    
                proc = subprocess.Popen(['python.exe', self.plugin_dir+'/class_achor.py', classnum,interval,field,shp],creationflags=CREATE_NEW_CONSOLE,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                #subprocess.call(['python.exe', self.plugin_dir+'/class_achor.py', classnum,interval,field,shp])
                while True:
                    out = proc.stdout.readline()
                    if out == '' and proc.poll() is not None:
                        break
                    if not str(out).strip() == '':
                        logging.info('subprocess:'+out)                    
                csvfile = self.plugin_dir+'/achorbreaks.csv'
                 
                rcsv = open(csvfile, 'r')
                sortedlist = sorted(rcsv, key= lambda x: float(x))
                #logging.info(sortedlist)
                i = 0
                
                ranges = []
                colorstr = []
                minval = achor_min_val
                while i < int(classnum)-1:                  
                    colorstr.append(str(minval) + '_' + sortedlist[i].strip())                        
                    minval = float(sortedlist[i].strip())
                    logging.info('breaks:'+sortedlist[i])
                    i += 1
                    
                # create colorramps according to the amount of classes/breaks
                white_blue = self.create_colorrange(int(classnum)-1, '#FFFFFF', '#0000FF') #default
                green_yellow_red = self.create_colorrange(int(classnum), '#00ff00', '#FF0000', '#FFFF00')
                blue_beige_red = self.create_colorrange(int(classnum), '#4158f4', '#f94545', '#f7b559')

                crange = white_blue # default
                crange_selection = self.dlg.cBox.currentIndex() # get the selection from the gui
                # provide other options
                if crange_selection == 1:
                    crange = green_yellow_red
                elif crange_selection == 2:
                    crange = blue_beige_red
                    #crange = blue_beige_red
                
                print("white blue: ", len(white_blue))
                print("green_yellow_red: ", len(green_yellow_red))
                print("blue_beige_red: ", len(blue_beige_red))
                print("colorstr: ", colorstr)
                color_ranges = []
                for i in range(len(colorstr)-1):
                    color_ranges.append((colorstr[i], float(colorstr[i].split('_')[0]), float(colorstr[i].split('_')[1]), crange[i]))
                    #print(color_ranges)
                    if i == len(colorstr)-2:
                        color_ranges.append((colorstr[i].split("_")[1] + "_" + str(achor_max_val), float(colorstr[i].split("_")[1]), float(achor_max_val), crange[i+1]))
                for i in color_ranges:
                    print(i)
                # create a category for each item in attribute
                for label, lower, upper, color in color_ranges:
                     symbol = QgsSymbolV2.defaultSymbol(myVectorLayer.geometryType())
                     symbol.setColor(QColor(color))
                     rng = QgsRendererRangeV2(lower, upper, symbol, label)
                     ranges.append(rng)
                    
                # create the renderer and assign it to a layer
                expression = field # field name
                renderer = QgsGraduatedSymbolRendererV2(expression, ranges)
                myVectorLayer.setRendererV2(renderer)
                QgsMapLayerRegistry.instance().addMapLayer(myVectorLayer)
                myVectorLayer.triggerRepaint()

                


                    

            
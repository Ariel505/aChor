# coding: utf-8
# Source: GitHub https://gist.github.com/lptorres/7781024#file-multi2single-py
# Usage: multi2single.py [inputshp] [outputshp]
# Multi Part shapefile to Single Part:

import os, uuid
from osgeo import gdal, ogr, osr
import sys


def initFields(in_lyr, out_lyr):
    #Arbitrarily get the first feature
    feat = in_lyr[0]
    #loop over each field
    
    for id in range(feat.GetFieldCount()):
        #Get the Field Definition
        field = feat.GetFieldDefnRef(id)
        fname = field.GetName()
        ftype = field.GetTypeName()
        fwidth = field.GetWidth()
        #Copy field definitions from source 
        #print(field,ftype)
        if ftype == 'String':
            fielddefn = ogr.FieldDefn(fname, ogr.OFTString)
            fielddefn.SetWidth(fwidth)
        elif ftype == 'Real':
            fielddefn = field
            fielddefn.SetWidth(fwidth)
        else:
            fielddefn = ogr.FieldDefn(fname, ogr.OFTInteger) 
            
        out_lyr.CreateField(fielddefn)
    fielddefn=ogr.FieldDefn("UNISTR", ogr.OFTString)
    out_lyr.CreateField(fielddefn)


def multipoly2poly(in_lyr, out_lyr, coordTrans):
    for feature in in_lyr: 
        geom = feature.GetGeometryRef()
        #translate the geometry
        geom.Transform(coordTrans)
        if geom.GetGeometryName() == 'MULTIPOLYGON': 
            for geom_part in geom: 
                addPolygon(geom_part.ExportToWkb(), feature, out_lyr) 
        else: 
            addPolygon(geom.ExportToWkb(), feature, out_lyr)
    feature.Destroy()



def addPolygon(simplePolygon, feature, out_lyr): 
    featureDefn = out_lyr.GetLayerDefn() 
    polygon = ogr.CreateGeometryFromWkb(simplePolygon) 
    out_feat = ogr.Feature(featureDefn) 
    out_feat.SetGeometry(polygon)
    #Loop over each field from the source, and copy onto the new feature
    for id in range(feature.GetFieldCount()):
        data = feature.GetField(id)
        out_feat.SetField(id, data)
    #out_feat.SetField(id+1, str(uuid.uuid4().fields[-1])[:6])
    out_feat.SetField(id+1, str(uuid.uuid4().fields[-1]))
    out_lyr.CreateFeature(out_feat)



def main():
    #Check if the input filename is a shapefile
    filename = sys.argv[1]
    if filename[-4:] != '.shp':
        print ('Error: You did not select a valid input shapefile.')
        return
    #Check if the output filename is a shapefile
    outputshp = sys.argv[2]
    if outputshp[-4:] != '.shp':
        print ('Error: You did not select a valid output shapefile.')
        return

    gdal.UseExceptions() 
    driver = ogr.GetDriverByName('ESRI Shapefile')
    in_ds = driver.Open(filename, 0)
    #Check if driver.Open was able to successfully open the shapefile
    if in_ds is None:
        print ('Error: The input shapefile you specified does not exist.')
        return
    in_lyr = in_ds.GetLayer()
    in_spatialref = in_lyr.GetSpatialRef()
    if os.path.exists(outputshp): 
        driver.DeleteDataSource(outputshp) 
    out_ds = driver.CreateDataSource(outputshp) 
    out_lyr = out_ds.CreateLayer('poly', geom_type=ogr.wkbPolygon)
    out_spatialref = osr.SpatialReference()
    out_spatialref.ImportFromEPSG(4326)
    coordTrans = osr.CoordinateTransformation(in_spatialref, out_spatialref)
    #out_lyr.SetProjection(in_lyr.GetProjection())
    initFields(in_lyr, out_lyr)
    print ("Finish assign unique ID field: UNISTR")
    multipoly2poly(in_lyr, out_lyr, coordTrans)

    #Write the .prj file
    out_spatialref.MorphToESRI()
    prj_name = outputshp[:-4] + '.prj'
    prj = open(prj_name, 'w')
    prj.write(out_spatialref.ExportToWkt())
    prj.close()

    #Close the datasources
    in_ds.Destroy()
    out_ds.Destroy()
    print ("Finish transformation: Multipart to singlepart")


if __name__ == '__main__':
    main()
import fiona
import rtree
import sys, os, subprocess, csv, time
import sqlite3 as sql
import array
import argparse
from shapely.geometry import shape, LineString, Point		   
from rtree import index
from decimal import *

class aChor(object):
    """Creates an aChor-classification object which identifies local extreme
    values and generates breaks according to these"""

    
    def version_check(method):
        """A wrapper for checking the current python environment version for
        selecting the appropriate arguments for open()"""
        def wrapper(self):
            if sys.version_info.major < 3:
                with open("achorbreaks.csv", 'wb') as fout:
                    method(self, fout)
            else:
                with open("achorbreaks.csv", 'w', newline='') as fout:
                    method(self, fout)
            return None
        return wrapper
    
    def __init__(self, cls, swp, field, shp, method=1, memory=None):
        
        self.cls = int(cls)
        self.brk_num = int(cls)-1
        self.swp = float(swp)
        self.field = str(field)
        self.shp = str(shp)
        self.method = int(method)
        self.memory = memory
        
        if not memory:
            self.memory = ":memory:"
        else:
            self.memory = "achor.db"
            
        global con
        global cur
        con = sql.connect(self.memory)
        #con = sql.connect("achor.db")
        cur = con.cursor()
        cur.execute("PRAGMA synchronous = OFF")
        cur.execute("PRAGMA journal_mode = MEMORY")
        
        self.db()
        self.neighborsearch()
        self.selection()
        self.generate_output()
    
    @version_check
    def generate_output(self, fout):
        """Generates spatial context defined localextreme breaks with respect to
        the desired amount of classes
        
        An iteration with respect to the class amount is performed, which calls the 
        breaks() method to run the line sweep algorithm
        
        Args:
            fout - file object from the version_check decorator pointing to the
                   output file"""
        
        writer = csv.writer(fout, delimiter=",")
        brks = []
        # create custom counters with distinct initial values for display
        brk_counter = 1 # we start with initally 1 break
        cls_counter = 2 # and with 1 break you alread have 2 classes
        for i in range(0, self.brk_num):            
            brk_val, no_segment_left = self.breaks()
            print("Class: {}, Breakvalue: {}".format(cls_counter, brk_val))
            if no_segment_left == True and not brk_counter == self.brk_num:
                print("No segments left in database")
                brks.append(brk_val)
                brks = self.desired_breaks(brks, self.brk_num)
                break
            brks.append(brk_val)
            cls_counter += 1
            brk_counter += 1
        else: 
            print("{} breaks/{} classes generated.".format(self.brk_num, self.cls))     
        [writer.writerow([brk]) for brk in brks]     

    def desired_breaks(self, brks, brk_num):
        """Creates breaks up to the desired class amount
        
        After the linesweep has finished it is possible, that the created breaks
        are not enough for the user. This algorithm checks the intervals between
        the actually generated breaks and creates additional breaks sorted by
        significance (size of interval between breaks) and appends them to the
        result
        
        Args:
            - brks: list with the actual breaks
            - cls: amount of desired classes
        """
        
        temp_brks = sorted(brks, reverse=True)
        brks_diff = sorted(((i-j, i, j) for i, j in zip(temp_brks, temp_brks[1:])), reverse=True)
        i = 0
        brk_counter = len(brks) # get the number of already created breaks
        cls_counter = brk_counter + 1 # existing breaks + 1 yields class amount
        while len(brks) < (len(temp_brks)*2)-1:
            residual_brk = ( brks_diff[i][1] + brks_diff[i][2] ) / 2
            brks.append(residual_brk)
            i += 1
            brk_counter += 1
            cls_counter += 1
            print("Class: {}, Breakvalue: {}".format(cls_counter, residual_brk))
            if len(brks) == brk_num:
                print("{} breaks/{} classes generated.".format(self.brk_num, self.cls))
                return brks
                
        return self.desired_breaks(brks, brk_num)
        
    def db(self):
        """Creates necessary tables in the database"""
        
        # neighborsearch
        sql_locextreme = """
        CREATE TABLE IF NOT EXISTS locExtreme(
            "PolygonID" "text" NOT NULL,
            "Note" "text",
           CONSTRAINT "locExtreme_pkey" PRIMARY KEY ("PolygonID")

        )
        """        
        cur.execute(sql_locextreme)
        
        sql_neighborpairs = """
        CREATE TABLE IF NOT EXISTS "neighborPairs" (
            "CenterID" text NOT NULL,
            "PolygonID" text NOT NULL,
            "Center" numeric NOT NULL,
            "Neighbor" numeric NOT NULL,
            "Difference" numeric NOT NULL,
            "Distance" numeric NOT NULL,
          CONSTRAINT "neighborPairs_pkey" PRIMARY KEY ("CenterID", "PolygonID")
        )        
        """
        cur.execute(sql_neighborpairs)
        
        # selection of localextreme-, localmax- and localminpairs
        sql_localextremepairs = """
        CREATE TABLE IF NOT EXISTS "locExtremePairs" (
            "CenterID" text NOT NULL,
             min numeric,
             "Note" text NOT NULL,
        CONSTRAINT "locExtremePairs_pkey" PRIMARY KEY ("CenterID")
        );
        """
        cur.execute(sql_localextremepairs)
        
        sql_localmaxpairs = """
        CREATE TABLE IF NOT EXISTS "locmaxPairs" (
            "CenterID" text NOT NULL,
            min numeric,
            "Note" text NOT NULL,
        CONSTRAINT "locmaxPairs_pkey" PRIMARY KEY ("CenterID")
        );
        """
        cur.execute(sql_localmaxpairs)
        
        sql_localminpairs = """
        CREATE TABLE IF NOT EXISTS "locminPairs" (
            "CenterID" text NOT NULL,
            min numeric,
            "Note" text NOT NULL,
        CONSTRAINT "locminPairs_pkey" PRIMARY KEY ("CenterID")
        );
        """
        cur.execute(sql_localminpairs)
        
        sql_hotspotpairs = """
        CREATE TABLE IF NOT EXISTS "hotspotPairs" (
            "CenterID" text NOT NULL,
            min numeric,
            "Note" text NOT NULL
        );
        """
        cur.execute(sql_hotspotpairs)
        
        # intersection search and break generation
        sql_linesweep = """
        CREATE TABLE IF NOT EXISTS line_sweep (
           CenterID TEXT NOT NULL, 
           PolygonID TEXT NOT NULL,
           Center NUMERIC NOT NULL,
           Neighbor NUMERIC NOT NULL,
           min NUMERIC NOT NULL,
            Note TEXT
        );
        """
        cur.execute(sql_linesweep)
        
        sql_intersection = """
        CREATE TABLE IF NOT EXISTS intersection (
            cnt NUMERIC NOT NULL,
            sweep NUMERIC,
            seg BLOB
        );
        """
        cur.execute(sql_intersection)
        con.commit()
        
        sql_desired_classes = """
        CREATE TABLE IF NOT EXISTS desired_classes (
            brks NUMERIC NOT NULL
        );
        """
        cur.execute(sql_desired_classes)
        
    def neighborsearch(self):
        
        print("Starting neighbor search...")
        
        if not os.path.dirname(scriptname):
            plugin_dir_qgis = os.getcwd()
        else:
            plugin_dir_qgis = os.path.split(os.path.abspath(scriptname))[0]
        
        os.chdir(plugin_dir_qgis)
        
        if not os.path.isdir('tmp'): os.mkdir('tmp') 
        
        inputshp = self.shp
        outputshp = r"tmp/inputshape.shp"
        strdir=str(plugin_dir_qgis).strip()
        #make it cross-platform compatible
        if os.name == "nt":
            py_executable = 'python'
            if str(sys.version)[:1] == '3':
                py_executable += '3'
                strdir=strdir.replace(".","").replace("\\","/").replace("//","/")
                outputshp = strdir+"/"+outputshp
        elif os.name == "posix":
            py_executable = 'python'
        subprocess.call([py_executable,'multi2single.py',inputshp,outputshp])
        
        with fiona.open(outputshp) as source:
            features = list(source)  # copy to list
        
            def generator_function(features):
                for i, feature in enumerate(features):
                    geometry = shape(feature['geometry'])
                    yield (i, geometry.bounds, feature)
            
            r = index.Index(generator_function(features))

            fid='UNISTR'
            val = self.field
            
            for feature in features:
                objval = round(feature['properties'][val],4)
                maxval = objval
                minval = objval
                cond = False
                j = 0
                k = 0
                geometry = shape(feature['geometry'])
                
                for candidate in list(r.intersection(geometry.bounds)):
                    
                    otherfeature = features[candidate]  # using originals, not the copies from the index
                    
                    if feature is otherfeature:
                        continue		    
                    othergeometry = shape(otherfeature['geometry'])
                    
                    if geometry.intersection(othergeometry):
                        
                        subval = round(otherfeature['properties'][val],4)
                        distance = round((geometry.centroid.distance(othergeometry.centroid)),3)
                        diff = round((objval-subval),4)
                        # Local Extreme method
                        db_neighborpairs_insert = [feature['properties'][fid],
                                                   otherfeature['properties'][fid],
                                                   objval,
                                                   subval,
                                                   diff,
                                                   distance]
                        
                        cur.execute("""
                        INSERT INTO neighborpairs 
                            (CenterID, PolygonID, Center, Neighbor, Difference, Distance) 
                            VALUES (?, ?, ?, ?, ?, ?);
                        """, db_neighborpairs_insert)
                        con.commit()

                        if diff <= 0 and subval >= maxval:
                            cond = False
                            maxval = subval
                            k = 0
                        if diff >= 0 and subval <= minval:
                            cond = False
                            minval = subval
                            j = 0
                        if diff > 0 and objval > subval and objval >= maxval: # Local Max
                            cond = True
                            maxval = objval
                            k += 1
                        if diff < 0 and objval < subval and objval <= minval: # Local Min
                            cond = True
                            minval = objval
                            j += 1
                if (self.method <= 3):             
                    if cond == True and maxval >= objval and j == 0:
                        db_locmax_insert = [feature['properties'][fid],
                                            "localmax"]
                        # if not cur fetchone fehlt!
                        
                        cur.execute("""
                                INSERT INTO locExtreme 
                                      (PolygonID, Note) 
                                       VALUES (?, ?);
                                """, db_locmax_insert)
                        con.commit()
                        
                    if cond == True and minval <= objval and k == 0:
                        db_locmin_insert = [feature['properties'][fid],
                                            "localmin"]
                        
                        #if not cur fetchone fehlt!
                        cur.execute("""
                                INSERT INTO locExtreme 
                                        (PolygonID, Note) 
                                        VALUES (?, ?);
                                """, db_locmin_insert)
                        con.commit()
                else:
                   # Hotspot method
                   if (self.method == 4):
                       g_bin = int(feature['properties']['Gi_Bin'])
                       if (g_bin == 3):
                           db_hotspot_insert = [feature['properties'][fid],
                                                "hotspot"]
                           cur.execute("""
                                    INSERT INTO locExtreme 
                                            (PolygonID, Note) 
                                            VALUES (?, ?);
                                    """, db_hotspot_insert)
                           con.commit()
                       elif (g_bin == -3):
                           db_coldspot_insert = [feature['properties'][fid],
                                                "coldspot"]
                           cur.execute("""
                                    INSERT INTO locExtreme 
                                            (PolygonID, Note) 
                                            VALUES (?, ?);
                                    """, db_coldspot_insert)
                           con.commit()                
                    
            source.close()
            
            # Neighours method
            if (self.method == 5):
                cur.execute("""
                        SELECT distinct(nb."CenterID"), nb."Difference" FROM "neighborPairs" nb
                        where ABS(nb."Difference") > {}
                        group by CenterID order by ABS(nb."Difference") DESC limit 500;
                        """.format(self.swp))
                db_neighbors_insert = [row for row in cur.fetchall()]
                cur.execute("SELECT * FROM locExtreme")
                if not cur.fetchone():        
                   cur.executemany("""
                                    INSERT INTO locExtreme 
                                            (PolygonID, Note) 
                                            VALUES (?, ?);
                                    """, db_neighbors_insert)
                   con.commit()
                cur.execute("""
                            update "locExtreme"
                            set "Note" = "neighbors";
                            """)
                con.commit()
            print("Finish neighborsearch, method: " + str(self.method))
        
    def selection(self):
        """Creates a selection of signifcant Center-Neighbor Pairs 
        
        Goal is to select center-neighbor-polygon relationships with respect to
        the difference in specified field value. Sorting is made according to the
        significance in field values"""
        
        print("Selecting significance sorted center-neighbor-polygon pairs...")

        # sql statement for locExtreme
        if (self.method == 1):
            sql_localextreme = """
            SELECT  nb."CenterID", MIN(ABS(nb."Difference")), loc."Note" 
                  FROM "neighborPairs" nb, "locExtreme" loc
                  WHERE nb."CenterID" = loc."PolygonID" and  ABS(nb."Difference") > {}
                  GROUP by nb."CenterID", loc."Note"
                  ORDER by  MIN(ABS(nb."Difference")) DESC
            """.format(self.swp)
            cur.execute(sql_localextreme)
            db_selection_localextreme = [row for row in cur.fetchall()]
    
            cur.execute("SELECT * FROM locExtremePairs")
            if not cur.fetchone():        
                cur.executemany("""
                INSERT INTO locExtremePairs (CenterID, min, Note)
                      VALUES (?, ?, ?);""", (db_selection_localextreme))
                con.commit()

    ################################################################################            

        # sql statement for localmax 
        elif (self.method == 2):
            sql_localmax = """
            SELECT nb."CenterID", MIN(ABS(nb."Difference")), loc."Note"
                  FROM "neighborPairs" nb, "locExtreme" loc
                  WHERE nb."CenterID" = loc."PolygonID" and nb."Difference" > {}
                  GROUP BY nb."CenterID", loc."Note"
                  ORDER BY MAX(nb."Difference") DESC;
            """.format(self.swp)
            cur.execute(sql_localmax)
            db_selection_localmax = [row for row in cur.fetchall()]
    
            cur.execute("SELECT * FROM locmaxpairs")
            if not cur.fetchone():        
                cur.executemany("""
                    INSERT INTO locmaxPairs (CenterID, min, Note)
                          VALUES (?, ?, ?);""", (db_selection_localmax))
                con.commit()

    ################################################################################

        # sql statement for locmin
        elif (self.method == 3):
            sql_localmin = """
            SELECT nb."CenterID", MIN(ABS(nb."Difference")), loc."Note" 
                  FROM "neighborPairs" nb, "locExtreme" loc
                  WHERE nb."CenterID" = loc."PolygonID" and nb."Difference" < {}
                  GROUP BY nb."CenterID", loc."Note"
                  ORDER BY MIN(nb."Difference") ASC;
            """.format(self.swp)
            cur.execute(sql_localmin)
            db_selection_localmin = [row for row in cur.fetchall()]
    
    
            cur.execute("SELECT * FROM locminpairs")
            if not cur.fetchone():        
                cur.executemany("""
                    INSERT INTO locminPairs (CenterID, min, Note)
                          VALUES (?, ?, ?);""", (db_selection_localmin))
                con.commit()
        
    ################################################################################

        # sql statement for hotspot
        elif (self.method == 4):
            sql_hotspot = """
            SELECT DISTINCT nb."CenterID", ABS(nb."Difference"),loc."Note"
                  FROM "neighborPairs" nb, "locExtreme" loc
                  WHERE nb."CenterID" = loc."PolygonID" and ABS(nb."Difference") > {}
                  AND NOT (nb."PolygonID" IN (select loc."PolygonID" from "locExtreme" loc))
                  GROUP BY nb."CenterID", nb."Difference", loc."Note"
                  ORDER BY ABS(nb."Difference") DESC;
            """.format(self.swp)
            cur.execute(sql_hotspot)
            db_selection_hotspot = [row for row in cur.fetchall()]
    
    
            cur.execute("SELECT * FROM hotspotpairs")
            if not cur.fetchone():        
                cur.executemany("""
                    INSERT INTO hotspotPairs (CenterID, min, Note)
                          VALUES (?, ?, ?);""", (db_selection_hotspot))
                con.commit()
        
    ################################################################################
    
        # sql statement for neighbors
        elif (self.method == 5):
            sql_neighbors = """
            SELECT nb."CenterID", ABS(nb."Difference"), loc."Note" 
                  FROM "neighborPairs" nb, "locExtreme" loc
                  WHERE nb."CenterID" = loc."PolygonID" and ABS(nb."Difference") > {}
                  GROUP by nb."CenterID", loc."Note"
                  ORDER by MAX(nb."Difference") DESC;
            """.format(self.swp)
            cur.execute(sql_neighbors)
            db_selection_neighbors = [row for row in cur.fetchall()]
    
    
            cur.execute("SELECT * FROM locExtremePairs")
            if not cur.fetchone():        
                cur.executemany("""
                    INSERT INTO locExtremePairs (CenterID, min, Note)
                          VALUES (?, ?, ?);""", (db_selection_neighbors))
                con.commit()
        
    ################################################################################
        
        print("Finish selection.\nStarting sweep and generate breaks...")
        
    def linesweep(self):
        """Performs a line sweep 
        
        This function uses the results from the neighborsearch to create a set of 
        line segments. With these a line sweep is performed to check on which values
        of the data range the highest amount of intersections occur. 

        Returns:
            A List containing the results of the line sweep as tuples: 
            Example: 
            
            (number of intersections, sweep, [bytes(segment_ids)])
            
            ...
            [(4, 14.4, [bytes(segment_ids)])
            (6, 14.5, [bytes(segment_ids)]),
            (6, 14.6, [bytes(segment_ids)])]
            
            segment_ids are inserted as a list and then converted to a bytes object 
            for easier use in the database"""
        
        segments = []        # will contain line segments according to by significance 
                             # sorted center-neighbor value ranges
                             
        vals = []            # container for the later estimation of dataset parameters
                             # for iteration
    
        cur.execute('SELECT * FROM line_sweep')
        if not cur.fetchone():
            if self.method == 1:
                cur.execute("""INSERT INTO line_sweep 
                            SELECT loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor", loc."min", loc."Note"
                                        FROM "locExtremePairs" loc, "neighborPairs" nb
                                        WHERE loc."CenterID" = nb."CenterID" and loc."min"=ABS(nb."Difference")
                                        GROUP BY loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor"
                                        ORDER BY loc."min" DESC;""")
                con.commit()
            if self.method == 2:
                 cur.execute("""INSERT INTO line_sweep 
                            SELECT loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor", loc."min", loc."Note"
                                        FROM "locmaxPairs" loc, "neighborPairs" nb
                                        WHERE loc."CenterID" = nb."CenterID" and loc."min"=ABS(nb."Difference") and loc."Note"="localmax"
                                        GROUP BY loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor"
                                        ORDER BY loc."min" DESC;""")
                 con.commit()
            if self.method == 3:
                 cur.execute("""INSERT INTO line_sweep 
                            SELECT loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor", loc."min", loc."Note"
                                        FROM "locminPairs" loc, "neighborPairs" nb
                                        WHERE loc."CenterID" = nb."CenterID" and loc."min"=ABS(nb."Difference") and loc."Note"="localmin"
                                        GROUP BY loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor"
                                        ORDER BY loc."min" DESC;""")
                 con.commit()
            if self.method == 4:
                 cur.execute("""INSERT INTO line_sweep 
                            SELECT loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor", loc."min", loc."Note"
                                        FROM "hotspotPairs" loc, "neighborPairs" nb
                                        WHERE loc."CenterID" = nb."CenterID" and loc."min" = ABS(nb."Difference")
                                        GROUP BY loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor"
                                        ORDER BY loc."min" DESC;""")
                 con.commit()
            if self.method == 5:
                cur.execute("""INSERT INTO line_sweep 
                            SELECT loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor", loc."min", loc."Note"
                                        FROM "locExtremePairs" loc, "neighborPairs" nb
                                        WHERE loc."CenterID" = nb."CenterID" and loc."min" = ABS(nb."Difference")
                                        GROUP BY loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor"
                                        ORDER BY loc."min" DESC;""")
                con.commit()

        cur.execute("SELECT rowid, centerid, polygonid, center, neighbor, min, note FROM line_sweep")
        data = cur.fetchall()
        
        # getting data set specific value ranges and create line segments
        for i, line in enumerate(data):

            # get values for center, neighbor and significance
            uid = line[0]
            center_val = line[3]
            neighbor_val = line[4]

            #create line segments
            segments.append([uid, LineString([(center_val, i+1), (neighbor_val, i+1)])])

            # get value range
            vals.append(center_val)

    
        # dataset parameters for intersection search
        minval = min(vals)
        maxval = max(vals)

            
        min_dif = self.swp
        

        # intersection search
        sweep = minval # set starting point for iteration
        
        # result of intersection search, containing: 
        #(# of intersections, sweep, respective segment-ids)
        intersection = [] 
    
        # until the max value of the dataset is not reached the sweep will iterate 
        # through the value range with the given sweep interval and check for 
        # intersections with the given set of line segments
    
        while sweep <= maxval:
            match_segments = [segment[0] for i, segment in enumerate(segments) 
                                if segment[1].contains(Point(sweep, i+1))]
            
            intersection.append((len(match_segments), round(sweep,2), [x for x in match_segments]))
            
            sweep += min_dif            
            
        if sys.version_info.major < 3:
            to_db = [(intersection[i][0], 
                      intersection[i][1], 
                      sql.Binary(array.array('L', intersection[i][2]).tostring())) 
                      for i, intersect in enumerate(intersection)]
        else:
            to_db = [(intersection[i][0], 
                      intersection[i][1], 
                      sql.Binary(array.array('L', intersection[i][2]).tobytes())) 
                      for i, intersect in enumerate(intersection)]
        
        return to_db        
        
    def breaks(self):
        """Generates breaks from a linesweep intersection search
        
            Uses the results from the linesweep()-method to select the breaks
            based on the intersection count. Checks the output and based on that 
            deletes the segment lines from the initial line_sweep table and calls 
            again linesweep() until all segments have been evaluated

            Returns: 
                A tuple containing breakvalues from the linesweep and a boolean, 
                which is set "True" if the last segment has been evaluated
                
                (134.03, True) = breakvalue of the last segment
                (34.2, False) = sweep still running"""

        cur.execute("SELECT * FROM intersection")
        if not cur.fetchone():
            cur.executemany("""INSERT INTO intersection
                                (cnt, sweep, seg)
                               VALUES (?, ?, ?);""", self.linesweep())
            con.commit()
        else:
            cur.execute("""DELETE FROM intersection""")
            cur.executemany("""INSERT INTO intersection
                                (cnt, sweep, seg)
                               VALUES (?, ?, ?);""", self.linesweep())
            con.commit()
        # For the following SQL-statement i got help from stackexchange.
        # comment how it is done!
        cur.execute("""WITH uppers(rowid) AS (
                          SELECT f.rowid FROM intersection f
                          WHERE cnt = (SELECT MAX(cnt) FROM intersection)
                          AND NOT EXISTS (
                              SELECT * FROM intersection s
                              WHERE s.cnt = f.cnt
                              AND s.rowid = f.rowid+1)
                              ),
                        bounds(lb, ub) AS (
                          SELECT f.rowid,
                                 (SELECT u.rowid FROM uppers u
                                  WHERE u.rowid >= f.rowid
                                  ORDER BY u.rowid ASC LIMIT 1)
                                  FROM intersection f
                                  WHERE cnt = (SELECT MAX(cnt) FROM intersection)
                                  AND NOT EXISTS (
                                      SELECT * FROM intersection s
                                      WHERE s.cnt = f.cnt
                                      AND s.rowid = f.rowid-1)
                            )
                        SELECT (SELECT count(*) FROM intersection
                                WHERE rowid BETWEEN bounds.lb AND bounds.ub
                               ) AS count,
                               (SELECT avg(sweep) FROM intersection
                                WHERE rowid BETWEEN bounds.lb AND bounds.ub
                               ) AS avg_sweep,
                               (SELECT seg FROM intersection
                                WHERE rowid BETWEEN bounds.lb AND bounds.ub
                               ) as seg
                        FROM bounds ORDER BY count DESC, avg_sweep DESC;""") 
        con.commit()

        data = cur.fetchone()
        break_val = data[1]
        segment_ids = data[2]

        # deleting the segments from the current intersection search for the next
        # line sweep
        if sys.version_info.major < 3:
            del_sql = """DELETE FROM line_sweep 
                        WHERE rowid IN ({})""".format(','.join(map(str, array.array('L', str(segment_ids)).tolist())))
        else:
            del_sql = """DELETE FROM line_sweep 
                        WHERE rowid IN ({})""".format(','.join(map(str, array.array('L', segment_ids).tolist())))
        cur.execute(del_sql)
        con.commit()

        # check if there are still intersections. If not, select the remaining 
        # single standing segments according to significance
        cur.execute("""SELECT cnt FROM intersection ORDER BY cnt DESC""")
        intersection_check = cur.fetchone()[0]
        if intersection_check == 0:
            cur.execute("""SELECT center, neighbor, min FROM line_sweep ORDER BY min DESC""")
            data = cur.fetchone()
            residual_brk_val = (data[0]+data[1])/2
            del_residual_brk_sql = """DELETE FROM line_sweep WHERE min = {}""".format(data[2])
            cur.execute(del_residual_brk_sql)
            con.commit()

            # check if database empty? if yes return the last value
            cur.execute("SELECT * FROM line_sweep")
            if not cur.fetchone():
                return (round(residual_brk_val, 2),True)
            else:
                self.linesweep()

            return (round(residual_brk_val, 2),False)
        # after removing the previously evaluated line segments run the line 
        # sweep again
        else:
            self.linesweep()

        return (round(break_val,2),False)        

    # con.close()
if __name__ == "__main__":
    scriptname = sys.argv[0]
    parser = argparse.ArgumentParser()
    parser.add_argument('classes', help='number of desired classes', type=int)
    parser.add_argument('swp', help='sweep interval', type=float)
    parser.add_argument('field', help='field to evaluate', type=str)
    parser.add_argument('shp', help='shapefile', type=str)
    parser.add_argument('-m', '--method', help='method for evaluation 1=localextremes, 2=localmax, 3=localmin, 4=hotspot, 5=neighbors', type=int)
    parser.add_argument('-o', '--output', help='output to hdd', action='store_true')
    args = parser.parse_args()

    cls = args.classes
    swp = args.swp
    method = args.method
    field = args.field
    shp = args.shp
    output = args.output  
    start = time.time()
    aChor(cls, swp, field, shp, 1 if not method else method, 0 if output else 0)
    print("Execution time: {}s".format(round(time.time()-start)))
    

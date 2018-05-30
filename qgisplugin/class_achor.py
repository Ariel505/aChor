import fiona
import rtree
import sys, os, subprocess, csv, time
import sqlite3 as sql
import array
import argparse
from shapely.geometry import shape, LineString, Point		   
from rtree import index
from decimal import *

scriptname = sys.argv[0]


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
    
    def __init__(self, cls, swp, field, shp, memory=None):
        
        self.cls = cls
        self.swp = swp
        self.field = field
        self.shp = shp
        self.memory = memory
        
        if not memory:
            self.memory = ":memory:"
        else:
            self.memory = "achor.db"
            
        global con
        global cur
        
        con = sql.connect(self.memory)
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
        for i in range(0,self.cls-1):
            temp = self.breaks()
            print("Classes: {}, Breakvalue: {}".format(i+2, temp[0]))
            if temp[1] == True:
                brks.append(temp[0])
                brks = self.desired_breaks(brks, self.cls-1)
                break
            brks.append(temp[0])
        else: 
            print("{} breaks/{} classes generated.".format(self.cls-1,self.cls))     
        [writer.writerow([brk]) for brk in brks]        

    def desired_breaks(self, brks, cls):
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
        while len(brks) < (len(temp_brks)*2)-1:
            residual_brk = ( brks_diff[i][1] + brks_diff[i][2] ) / 2
            brks.append(residual_brk) 
            i += 1
            print("Classes: {}, Breakvalue: {}".format(len(brks)+1, residual_brk))
            if len(brks) == cls:
                print("{} breaks/{} classes generated.".format(len(brks), cls))
                return brks
                
        return self.desired_breaks(brks, cls)
        
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
            current_dir = os.getcwd() 
        else:
            current_dir = os.path.split(os.path.abspath(scriptname))[0]
            os.chdir(current_dir)
            
        if not os.path.isdir('tmp'): os.mkdir('tmp') 
        
        inputshp = self.shp
        outputshp = r"tmp/inputshape.shp"
        
        subprocess.call(['python.exe','multi2single.py',inputshp,outputshp])

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
                    
            print("Finish neighborsearch")
        
    def selection(self):
        """Creates a selection of signifcant Center-Neighbor Pairs 
        
        Goal is to select center-neighbor-polygon relationships with respect to
        the difference in specified field value. Sorting is made according to the
        significance in field values"""
        
        print("Selecting significance sorted center-neighbor-polygon pairs...")

        # sql statement for locExtreme
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
        sql_localmax = """
        SELECT nb."CenterID", MIN(nb."Difference"), loc."Note"
              FROM "neighborPairs" nb, "locExtreme" loc
              WHERE nb."CenterID" = loc."PolygonID" and nb."Difference" > {}
              GROUP BY nb."CenterID", loc."Note"
              ORDER BY MIN(nb."Difference") DESC;
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
        sql_localmin = """
        SELECT nb."CenterID", MAX(nb."Difference"), loc."Note" 
              FROM "neighborPairs" nb, "locExtreme" loc
              WHERE nb."CenterID" = loc."PolygonID" and nb."Difference" < {}
              GROUP BY nb."CenterID", loc."Note"
              ORDER BY MAX(nb."Difference") ASC;
        """.format(self.swp)
        cur.execute(sql_localmin)
        db_selection_localmin = [row for row in cur.fetchall()]


        cur.execute("SELECT * FROM locminpairs")
        if not cur.fetchone():        
            cur.executemany("""
                INSERT INTO locminPairs (CenterID, min, Note)
                      VALUES (?, ?, ?);""", (db_selection_localmin))
            con.commit()
            
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
            cur.execute("""INSERT INTO line_sweep 
                        SELECT loc."CenterID", nb."PolygonID", nb."Center", nb."Neighbor", loc."min", loc."Note"
                                    FROM "locExtremePairs" loc, "neighborPairs" nb
                                    WHERE loc."CenterID" = nb."CenterID" and  loc."min"=ABS(nb."Difference")
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
            
            sweep += min_dif
            
            intersection.append((len(match_segments), round(sweep,2), [x for x in match_segments]))
            
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

            self.linesweep()

            return (round(residual_brk_val, 2),False)
        # after removing the previously evaluated line segments run the line 
        # sweep again
        self.linesweep()

        return (round(break_val,2),False)        

    # con.close()
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('classes', help='number of desired classes', type=int)
    parser.add_argument('swp', help='sweep interval', type=float)
    parser.add_argument('field', help='field to evaluate', type=str)
    parser.add_argument('shp', help='shapefile', type=str)
    parser.add_argument('-o', '--output', help='output to hdd', action='store_true')
    args = parser.parse_args()

    cls = args.classes
    swp = args.swp
    field = args.field
    shp = args.shp
    output = args.output
     #def __init__(self, cls, swp, field, shp, memory=None):        
    start = time.time()
    aChor(cls, swp, field, shp , 1 if output else 0)
    print("Execution time: {}s".format(round(time.time()-start)))
    
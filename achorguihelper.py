import fiona


def suggest_sweep(inp, attr):

    with fiona.open(inp) as source:
        features = list(source)
        
    max_val = max(val['properties'][attr] for val in features)
    min_val = min(val['properties'][attr] for val in features)
    
    valrange = max_val-min_val
    
    return round(valrange/500,2) if valrange < 500 else round(valrange/1000, 2)

if __name__ == "__main__":
    
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('field', help='field to evaluate', type=str)
    parser.add_argument('shp', help='shapefile', type=str)
    args = parser.parse_args()
    
    inp_shp = args.shp
    attr_fld = args.field
    
    print(suggest_sweep(inp_shp, attr_fld))
        
    
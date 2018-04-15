import fiona


def suggest_sweep(inp, attr):

    with fiona.open(inp) as source:
        features = list(source)
        
    max_val = max(val['properties'][attr] for val in features)
    min_val = min(val['properties'][attr] for val in features)
    
    valrange = max_val-min_val
    
    print(valrange)
    
    if valrange < 1:
        suggestion = round(valrange/((valrange*6)*10),3)
    elif 1 < valrange < 100:
        suggestion = round(valrange/(valrange*6),2)
    elif 100 < valrange < 1000:
        suggestion = round(valrange/(valrange*5),2)
    elif valrange > 1000:
        suggestion = round(valrange/(valrange*3),1)
    
    return suggestion

if __name__ == "__main__":
    
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('field', help='field to evaluate', type=str)
    parser.add_argument('shp', help='shapefile', type=str)
    args = parser.parse_args()
    
    inp_shp = args.shp
    attr_fld = args.field
    
    print(suggest_sweep(inp_shp, attr_fld))
        
    

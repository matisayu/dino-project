import requests
import json
import os

def fetch_data(url): 
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.HTTPError as http_err:
        # Catches 4xx and 5xx status codes (e.g., 404 Not Found, 500 Server Error)
        print(f"HTTP error occurred: {http_err}")

    except requests.exceptions.ConnectionError as conn_err:
        # Catches network problems like DNS failure or refused connections
        print(f"Connection error occurred: {conn_err}")

    except requests.exceptions.Timeout as timeout_err:
        # Catches requests that timed out based on your timeout parameter
        print(f"Timeout error occurred: {timeout_err}")

    except requests.exceptions.RequestException as req_err:
        # The ultimate fallback option for any exception the requests library throws
        print(f"An unexpected request error occurred: {req_err}")
        
    except Exception as e:
        # Catches non-request errors, such as JSON decoding failures
        print(f"An unrelated error occurred: {e}")


def export_data_json(data, filepath):
    directory = os.path.dirname(filepath)
    
    if directory:
        os.makedirs(directory, exist_ok=True)
        
    with open(filepath, 'w') as f:
        json.dump(data, f, indent = 2)
        
    print(f"Saved {len(data['records'])} records to {filepath}")
    
def export_data_ndjson(data, filepath):
    records = data['records']
    directory = os.path.dirname(filepath)
    
    if directory:
        os.makedirs(directory, exist_ok=True)
        
    with open(filepath, 'w') as f:
        for record in records:
            str_record = {}
            for key, value, in record.items():
                if value is not None:
                    str_record[key] = str(value)
                else:
                    str_record[key] = value
            f.write(json.dumps(str_record) + '\n')
    print(f"Saved {len(data['records'])} records to {filepath}")
                
                
if __name__ == '__main__':
    pbdb_url = 'https://paleobiodb.org/data1.2/occs/list.json?base_name=Dinosauria&show=coords,paleoloc,classext,attr,loc,ref&limit=all'
    data = fetch_data(pbdb_url)
    #filepath = 'data/pbdb_dinosauria_raw.json'
    #export_data_json(data, filepath)
    ndfilepath = 'data/pbdb_dinosauria_raw.ndjson'
    export_data_ndjson(data, ndfilepath)

    
    

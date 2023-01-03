#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 20 15:21:44 2022

@author: rtsearcy

Download remote sensing imagery from Planet API

Reference: 
https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/data-api-tutorials/search_and_download_quickstart.ipynb
https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/orders_api_tutorials/ordering_and_delivery.ipynb
https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/orders_api_tutorials/tools_and_toolchains.ipynb

"""

import os
import sys
import json
import requests
import shutil
import time
import pathlib
from requests.auth import HTTPBasicAuth
import pandas as pd

### Folders / Inputs
base_folder = 'data/'
geo_folder = base_folder + 'geometries/'
image_folder =  base_folder + 'images/'

key = '6b4d53883da74c35852dc7a342c42c74' ## PLANET API KEY; REMOVE BEFORE GITHUB

if 'image_metadata.csv' in os.listdir(base_folder):
    metadata = pd.read_csv(os.path.join(base_folder, 'image_metadata.csv'))
else:
    metadata = pd.DataFrame()

### Import API Key
if os.environ.get('PL_API_KEY', ''):
    API_KEY = os.environ.get('PL_API_KEY', '')
else:
    API_KEY = key

# Setup the session
session = requests.Session()

# Authenticate
session.auth = (API_KEY, "")

### Import scene geometries
sites = []
geos = []
for f in os.listdir(geo_folder):
    if '.geojson' not in f:
        continue
    
    site = f.replace('.geojson','')
    temp_geo = json.load(open(os.path.join(geo_folder, f)))
    site_geo = temp_geo['features'][0]['geometry']
    
    sites.append(site)
    geos.append(site_geo)

### Select Sites

#for i in range(0,len(sites):  # Iterate
i = 4  # Single site

s = sites[i]
print('--- ' + s + ' ---\n')


#%% Find Scenes

### Create Filters

# get images that overlap with site AOI 
geometry_filter = {
  "type": "GeometryFilter",
  "field_name": "geometry",
  "config": geos[i]
}

# get images acquired within a date range (~5 years of scenes)
date_range_filter = {
  "type": "DateRangeFilter",
  "field_name": "acquired",
  "config": {
    "gte": "2017-07-15T00:00:00.000Z",
    "lte": "2022-12-15T00:00:00.000Z"
  }
}

# only get images which have <XX% cloud coverage and >XX% visible confidence
cloud_cover_filter = {
  "type": "RangeFilter",
  "field_name": "cloud_cover",
  "config": {
    "lte": 0.25
  }
}

visible_conf_filter = {
  "type": "RangeFilter",
  "field_name": "visible_confidence_percent",
  "config": {
    "gte": 0.90
  }
}

# only get images which are or standard quality
quality_filter = {
   "type":"StringInFilter",
   "field_name":"quality_category",
   "config":[
      "standard"
   ]
}

# combine our geo, date, cloud, visible, quality filters
combined_filter = {
  "type": "AndFilter",
  "config": [geometry_filter, 
             date_range_filter, 
             cloud_cover_filter,
             visible_conf_filter,
             quality_filter]
}

### Find Scenes - Search for Images
item_type = "PSScene"  # PlanetScope 3, 4, and 8 band scenes captured by the Dove satellite constellation
asset_type = 'ortho_visual'  # ortho_visual, ortho_analytic_4b
bundle_type = 'visual'   # visual if ortho_visual; abnalytic if ortho_analytic

# API request object to search for images
search_request = {
  "item_types": [item_type], 
  "filter": combined_filter
}

# Initial POST request
print('Searching for images...')
search_result = \
  requests.post(
    'https://api.planet.com/data/v1/quick-search',
    auth=session.auth,
    json=search_request)


### Extract image IDs and properties for metadata
# Note: might be multiple pages of ids
image_ids = []
properties = []
next_page = True
r = search_result
while next_page:
    image_ids += [feature['id'] for feature in r.json()['features']]
    properties += [feature['properties'] for feature in r.json()['features']]

    if r.json()['_links']['_next'] == None:
        next_page = False
    else:
        r = requests.get(r.json()['_links']['_next'],
                         auth=session.auth)
image_ids.sort()
#image_ids = [feature['id'] for feature in search_result.json()['features']]
# properties = [feature['properties'] for feature in search_result.json()['features']]

print('  ' + str(len(image_ids)) + ' images found')
# check image id doesn't already exist in image folder
old_idx = [image_ids.index(x) for x in image_ids if 
           any((x in f) & (s in f) for f in os.listdir(image_folder))]
image_ids = [x for x in image_ids if image_ids.index(x) not in old_idx]
properties = [x for x in properties if properties.index(x) not in old_idx]
print('  ' + str(len(image_ids)) + ' new images')

if len(image_ids) == 0:
    #break
    sys.exit()
    
site_metadata = pd.DataFrame(properties)
site_metadata['id'] = image_ids
site_metadata['site'] = s

metadata = metadata.append(site_metadata)


#%% Order Scenes
order_complete = False
download_count = 0
#start_idx = 0
end_idx = 0 # start_idx + 500
max_idx = len(image_ids)

orders_url = 'https://api.planet.com/compute/ops/orders/v2' 
# response = requests.get(orders_url, auth=session.auth) # See order history

while not order_complete:
    # Update images to order
    start_idx = end_idx
    end_idx += 500
    if end_idx >= max_idx:
        end_idx = max_idx
        order_complete = True
        
### Define Order
    order_image_ids = image_ids[start_idx:end_idx]  # images to be orders, maximum 500 at a time
    
    order_headers = {'content-type': 'application/json'}
    
    # define the clip tool with the geometry AOI
    clip = {
        "clip": {
            "aoi": geos[i]
        }
    }
    
    order_request = {  
       "name": s + '_order_' + str(start_idx) + '_' + str(end_idx),
       "products":[
          {  
             "item_ids": order_image_ids,
             "item_type": item_type,
             "product_bundle": bundle_type
          }
       ],
       "tools":[clip]
    }
    
### Send order + Check Status
    order_response = requests.post(orders_url, 
                                   data=json.dumps(order_request), 
                                   auth=session.auth, 
                                   headers=order_headers)
    #print(order_response)
    order_id = order_response.json()['id']
    
    print('\nProcessing Order ID:' + order_id + \
          '\n(Images ' +  str(start_idx) + '-' + str(end_idx) + ')')
          
    order_url = orders_url + '/' + order_id
    loop = True
    while loop: # check status every 30s
        #count += 1
        r = requests.get(order_url, auth=session.auth)
        response = r.json()
        state = response['state']
        print(state)
        end_states = ['success', 'failed', 'partial']
        if state in end_states:
            loop = False
            break
        time.sleep(30)
    
### Download Results     
    r = requests.get(order_url, auth=session.auth)
    response = r.json()
    order_results = response['_links']['results']
    results_urls = [r['location'] for r in order_results]
    results_names = [r['name'] for r in order_results]
    print('{} items to download'.format(len(results_urls)))
    
    for url, name in zip(results_urls, results_names):
        if name.endswith('.json'):  # skip metadata jsons
            continue
        name = name.replace(order_id + '/','').replace(item_type + '/','') # drop order id/item type from name
        name = s + '_' + name  # add site name to name
        
        path = pathlib.Path(os.path.join(image_folder, name))
        
        if not path.exists():
            print(str(download_count) + ': downloading {} to {}'.format(name, image_folder))
            r = requests.get(url, allow_redirects=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            open(path, 'wb').write(r.content)
        else:
            print(str(download_count) +': {} already exists, skipping...'.format(path))
        
        download_count += 1

#%% End Session + Save Metadata

session.close()

metadata.to_csv(os.path.join(base_folder, 'image_metadata.csv'), index=False)

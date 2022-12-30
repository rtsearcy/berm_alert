#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 20 15:21:44 2022

@author: rtsearcy

Download remote sensing imagery from Planet API

Reference: 
https://github.com/planetlabs/notebooks/blob/master/jupyter-notebooks/data-api-tutorials/search_and_download_quickstart.ipynb

"""

import os
import json
import requests
import shutil
from requests.auth import HTTPBasicAuth
import pandas as pd



### Import API Key
if os.environ.get('PL_API_KEY', ''):
    API_KEY = os.environ.get('PL_API_KEY', '')
else:
    API_KEY = '6b4d53883da74c35852dc7a342c42c74' ## REMOVE BEFORE GITHUB
    
    
### Import scene geometries
geo_folder = 'data/geometries/'
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


### Iterate through Sites
metadata = pd.DataFrame()

#for i in range(0,len(sites):
i = 0
s = sites[i]
print('--- ' + s + ' ---\n')

### Create Filter

# get images that overlap with our AOI 
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

# only get images which have <XX% cloud coverage
cloud_cover_filter = {
  "type": "RangeFilter",
  "field_name": "cloud_cover",
  "config": {
    "lte": 0.5
  }
}

# combine our geo, date, cloud filters
combined_filter = {
  "type": "AndFilter",
  "config": [geometry_filter, date_range_filter, cloud_cover_filter]
}

### Search for Images
item_type = "PSScene"  # PlanetScope 3, 4, and 8 band scenes captured by the Dove satellite constellation
asset_type = 'ortho_visual'  # ortho_visual, ortho_analytic_4b

# API request object
search_request = {
  "item_types": [item_type], 
  "filter": combined_filter
}

# fire off the POST request
print('Searching for images...')
search_result = \
  requests.post(
    'https://api.planet.com/data/v1/quick-search',
    auth=HTTPBasicAuth(API_KEY, ''),
    json=search_request)

# extract image IDs and properties for metadata
image_ids = [feature['id'] for feature in search_result.json()['features']]
print('  ' + str(len(image_ids)) + ' images found')
properties = [feature['properties'] for feature in search_result.json()['features']]

site_metadata = pd.DataFrame(properties)
site_metadata['id'] = image_ids
site_metadata['site'] = s
metadata = metadata.append(site_metadata)


### Iterate through images
id = image_ids[0]
id_url = 'https://api.planet.com/data/v1/item-types/{}/items/{}/assets'.format(item_type, id)

# Returns JSON metadata for assets in this ID. 
# Learn more: planet.com/docs/reference/data-api/items-assets/#asset
result = \
  requests.get(
    id_url,
    auth=HTTPBasicAuth(API_KEY, '')
  )

# Parse out links
links = result.json()[asset_type]["_links"]
self_link = links["_self"]
activation_link = links["activate"]

# Request activation of the asset:
activate_result = \
  requests.get(
    activation_link,
    auth=HTTPBasicAuth(API_KEY, '')
  )

# Check activation status
activation_status_result = \
  requests.get(
    self_link,
    auth=HTTPBasicAuth(API_KEY, '')
  )

download_link = activation_status_result.json()["location"]
print(download_link)

# Download image
image_response = requests.get(download_link, stream=True)
with open(os.path.join('data/','test.tiff'), 'wb') as save_file:
    shutil.copyfileobj(image_response.raw, save_file)
del image_response

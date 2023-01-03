#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan  3 11:05:58 2023

@author: rtsearcy

"""

import os
import pandas as pd

folder = 'data/images/'

site_names = ['malibu_creek','soquel_creek','san_lorenzo_river',
              'scott_creek','san_mateo_creek']

os.listdir(folder)

classes = [filename for filename in os.listdir(folder) if os.path.isdir(os.path.join(folder,filename))]
classes.pop(classes.index('other'))


df = pd.DataFrame()

for c in classes:
    files = os.listdir(os.path.join(folder,c))
    sites = []
    dates = []
    for f in files:
        sites += [s for s in site_names if s in f]
        dates += [f.replace(sites[-1] + '_','')[0:8]]

    temp = pd.concat([
        pd.Series(files),
        pd.Series(sites),
        pd.Series(dates)
        ], axis=1)
    temp.columns = ['file','site','date']
    temp['class'] = c
    
    df = df.append(temp)
    
df = df.dropna()
df['date'] = pd.to_datetime(df.date)
df['month'] = df.date.dt.month
df['year'] = df.date.dt.year

df.groupby('class').count()['site']  # N in each class
df.groupby('site').count()['class'] # N for each site

df.groupby(['site','class']).count()['file'] # Class by site

df.groupby(['month','class']).count()['file'] # class by month of year


## Update metdata
metadata = pd.read_csv('data/image_metadata.csv')
files = list(df.file)
drop_idx = []
for i in range(0, len(metadata)):
    x = metadata.iloc[i]['site'] + '_' + metadata.iloc[i]['id']
    if any(x in f for f in files):
        continue
    else:
        drop_idx += [i]

metadata = metadata.drop(drop_idx)
metadata.to_csv('data/image_metadata.csv', index=False)

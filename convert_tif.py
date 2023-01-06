#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan  4 17:28:12 2023

@author: rtsearcy

For TensorFlow to handle images, they must be in a different format than TIFF

This code converts Planet .tif images to .png images

TIFF images should be in images/tif/ folder in classified open/closed
subdirectories

PNG images will go to images/png/ folder

Ref:
    https://github.com/python-pillow/Pillow/issues/3416
    https://github.com/cgohlke/tifffile/#examples
    https://pillow.readthedocs.io/en/stable/handbook/tutorial.html

"""

import os
import tifffile
import PIL

base_folder = 'data/images/'
class_list = ['open', 'closed']
overwrite = True

# Get TIFF Filenames
old_files = []
for c in class_list:
    c_files = [f for f in os.listdir(os.path.join(base_folder, 'tif', c))
               if f.endswith('.tif')]
    old_files += [os.path.join(base_folder, 'tif', c, f) for f in c_files]

print('{} files to process...'.format(len(old_files)))

# Save .png files to PNG directory
count = 0
for f in old_files:
    count += 1
    print('{}/{}'.format(count, len(old_files)))
    new_file = f.replace('tif', 'png')
    
    if not overwrite and os.path.exists(new_file):
        print('  already exists')
        continue
    
    # Open old file
    im = tifffile.imread(f)
    
    if im.shape[0] == min(im.shape):  # band num is first dimension (shape = (4, X, Y))
        r = PIL.Image.fromarray(im[0])
        g = PIL.Image.fromarray(im[1])
        b = PIL.Image.fromarray(im[2])
        a = PIL.Image.fromarray(im[3])
        
        im = PIL.Image.merge('RGBA', (r,g,b,a))
    
    else: # band num is last dimension (shape = (X,Y,4))
        im = PIL.Image.fromarray(im)
        
    im.save(new_file, format='PNG')

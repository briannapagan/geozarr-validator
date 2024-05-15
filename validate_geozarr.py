#!/usr/bin/env python3

import zarr
from zarr.storage import DirectoryStore
import os
import json
import sys

def validate_geozarr(store_path):
    errors = []

    # Check if the store path exists
    if not os.path.exists(store_path):
        errors.append(FileNotFoundError(f"The store path {store_path} does not exist."))
        return errors

    # Open the Zarr store
    store = DirectoryStore(store_path)
    group = zarr.open_group(store, mode='r')

    # Check that .zgroup file exists and contains valid JSON
    zgroup_path = os.path.join(store_path, '.zgroup')
    if not os.path.isfile(zgroup_path):
        errors.append(ValueError("Missing .zgroup file."))
    else:
        with open(zgroup_path, 'r') as f:
            zgroup_data = json.load(f)
            if not zgroup_data.get('zarr_format') == 2:
                errors.append(ValueError("The .zgroup file does not indicate Zarr v2.0 format. This script only works for Zarr v2.0."))

    if errors:
        return errors

    # Check each array in the group
    for name, array in group.arrays():
        try:
            # Check that .zarray file exists and contains valid JSON
            zarray_path = os.path.join(store_path, name, '.zarray')
            if not os.path.isfile(zarray_path):
                errors.append(ValueError(f"Missing .zarray file for array {name}."))
                continue

            with open(zarray_path, 'r') as f:
                zarray_data = json.load(f)
                if not zarray_data.get('zarr_format') == 2:
                    errors.append(ValueError(f"The .zarray file for array {name} does not indicate Zarr v2.0 format. This script only works for Zarr v2.0."))

            # Validate the array metadata
            required_zarray_keys = ['zarr_format', 'shape', 'chunks', 'dtype', 'compressor', 'fill_value', 'order', 'filters']
            for key in required_zarray_keys:
                if key not in zarray_data:
                    errors.append(ValueError(f"Missing required key '{key}' in .zarray file for array {name}."))

            # Check that .zattrs file exists and contains valid JSON
            zattrs_path = os.path.join(store_path, name, '.zattrs')
            if not os.path.isfile(zattrs_path):
                errors.append(ValueError(f"Missing .zattrs file for array {name}."))
                continue

            with open(zattrs_path, 'r') as f:
                zattrs_data = json.load(f)

            # Check _ARRAY_DIMENSIONS
            if '_ARRAY_DIMENSIONS' in zattrs_data:
                array_dimensions = zattrs_data['_ARRAY_DIMENSIONS']
                if not isinstance(array_dimensions, list):
                    errors.append(ValueError(f"_ARRAY_DIMENSIONS should be a list for array {name}."))
                for dimension in array_dimensions:
                    # Ensure each dimension exists as its own .zattrs and .zarray
                    dim_zarray_path = os.path.join(store_path, dimension, '.zarray')
                    if not os.path.isfile(dim_zarray_path):
                        errors.append(ValueError(f"Missing .zarray file for dimension '{dimension}' specified in _ARRAY_DIMENSIONS for array {name}."))
                    
                    dim_zattrs_path = os.path.join(store_path, dimension, '.zattrs')
                    if not os.path.isfile(dim_zattrs_path):
                        errors.append(ValueError(f"Missing .zattrs file for dimension '{dimension}' specified in _ARRAY_DIMENSIONS for array {name}."))
                    else:
                        with open(dim_zattrs_path, 'r') as f:
                            dim_zattrs_data = json.load(f)

                        # Check that 'axis' key is present in the dimension's .zattrs
                        if 'axis' not in dim_zattrs_data:
                            errors.append(ValueError(f"Missing 'axis' key in .zattrs for dimension '{dimension}' specified in _ARRAY_DIMENSIONS for array {name}."))

            # Check additional CF attributes
            required_zattrs_keys = ['grid_mapping', 'standard_name']
            for key in required_zattrs_keys:
                if key not in zattrs_data:
                    errors.append(ValueError(f"Missing required key '{key}' in .zattrs for array {name}."))

        except Exception as e:
            errors.append(e)

    return errors

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: validate_geozarr.py 'path/to/zarr/store'")
        sys.exit(1)
    
    store_path = sys.argv[1]
    errors = validate_geozarr(store_path)

    if errors:
        for error in errors:
            print(error)
        sys.exit(1)
    else:
        print("The Zarr store is compliant with GeoZarr specifications.")

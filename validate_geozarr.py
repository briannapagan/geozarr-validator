#!/usr/bin/env python3

import os
import sys
import zarr
from pydantic_zarr.v2 import ArraySpec, GroupSpec
from pydantic import ValidationError

def validate_geozarr(store_path):
    errors = []

    # Check if the store path exists
    if not os.path.exists(store_path):
        errors.append(FileNotFoundError(f"The store path {store_path} does not exist."))
        return errors

    try:
        # Open the Zarr store
        store = zarr.DirectoryStore(store_path)
        group = zarr.open_group(store, mode='r')
    except Exception as e:
        errors.append(e)
        return errors

    # Validate the group metadata
    try:
        group_spec = GroupSpec(**group.attrs.asdict())
        if group_spec.zarr_format != 2:
            raise ValueError("The .zgroup file does not indicate Zarr v2.0 format. This script only works for Zarr v2.0.")
    except ValidationError as e:
        errors.append(e)
        return errors

    # Check each array in the group
    for name, item in group.items():
        try:
            # Check that the item is a Zarr array
            if not isinstance(item, zarr.core.Array):
                errors.append(ValueError(f"{name} is not a Zarr array."))
                continue

            # Validate the array attributes
            try:
                array_spec = ArraySpec(**item.attrs.asdict())
            except ValidationError as e:
                errors.append(e)
                continue

            # Check that .zattrs contains long_name and standard_name
            required_zattrs_keys = ['long_name', 'standard_name']
            for key in required_zattrs_keys:
                if key not in item.attrs:
                    errors.append(ValueError(f"Missing required key '{key}' in .zattrs for array {name}."))

            #######
            # this is where we want to abstract a level
            # find common metadata, abstract
            # allow for reference to either CF or geotiff checkers?
            ########
            # Check _ARRAY_DIMENSIONS
            if '_ARRAY_DIMENSIONS' in item.attrs:
                array_dimensions = item.attrs['_ARRAY_DIMENSIONS']
                if not isinstance(array_dimensions, list):
                    errors.append(ValueError(f"_ARRAY_DIMENSIONS should be a list for array {name}."))
                for dimension in array_dimensions:
                    try:
                        dim_array = group[dimension]

                        # Check that the dimension is a Zarr array
                        if not isinstance(dim_array, zarr.core.Array):
                            errors.append(ValueError(f"Dimension '{dimension}' specified in _ARRAY_DIMENSIONS for array {name} is not a Zarr array."))
                            continue

                        # Check that the dimension has .zattrs with 'axis'
                        if 'axis' not in dim_array.attrs:
                            errors.append(ValueError(f"Missing 'axis' key in .zattrs for dimension '{dimension}' specified in _ARRAY_DIMENSIONS for array {name}."))
                    except KeyError:
                        errors.append(ValueError(f"Dimension '{dimension}' specified in _ARRAY_DIMENSIONS for array {name} does not exist in the group."))

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

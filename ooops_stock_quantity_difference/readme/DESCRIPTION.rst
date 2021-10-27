Report stock quantity difference between Qty Available and Stock Move. Allow to fix it if found.

There are 2 ways implemented:

  1. **Stock Qty Difference** - without taking in account type of operation in picking type:

     - incoming moves: all moves with a location_dest_id (destination) of type `internal`
     - outgoing moves: all moves with a location_id (source) of type `internal`


  2. **Stock Qty - Picking Type Discrepancy** - Taking in account type of operation in picking type:

     - incoming moves: all moves with a operation type in picking of type `incoming`
     - outgoing moves: all moves with a operation type in picking of type `outgoing`

# replace_geometry
Replaces geometry of chain of ways in OSM file.

### Usage ###

<code>python replace_geometry.py [input_filename.osm]</code>.

### Notes ###

* Preparations before running program:
  * The new geometry must be exactly one way marked with the tag _REPLACE=to_, and with the desired direction.
  * The ways to get new geometry must be a consecutive chain of ways market with the tag _REPLACE=from_.
  * Start node: The first node of the new way must be identical (already merged) to the first node of the chain of existing ways.
  * All ways and relations connected in OSM should also be included (use _recurse up "<"_ in Overpass).

* The program will keep the original position of the following nodes:
  * Nodes which connects the ways to be replaced with another way, e.g. a highway crossing a railway.
  * Nodes connecting the chain of ways to be replaced (except if relocation is less than 5 meters), e.g. first and last nodes of bridges and tunnels.

* The resulting OSM file will have several _CHECK_ tags to be inspected before uploading:
  * _CHECK=junction_ - The replaced way is connected to another way with these nodes. The nodes are at their original position and often should be slightly relocated to get in line with the rest of the replaced way.
  * _CHECK=split_ - The replaced ways are connected with each other with these nodes. The nodes are at their original position and often should be slightly relocated to get in line with the rest of the replaced way.
  * _CHECK=replace_ - Same as _split_, however these nodes have been replaced with the new geometry because the relocation was less than 5 meters.
  * _CHECK=tags_ - Other nodes containing tags, e.g. traffic signals.
  * _CHECK=skip_ - Old nodes which are not used with the new geometry.
  * _CHECK=unused_ - New unused nodes.
  
* Before uploding please check the following:
  * Search <code>CHECK -skip -unused</code>, put in ToDo plugin and check position of all nodes. Often bridges and tunnels should be adjusted.
  * For railways, you may want to search <code>REPLACE=from tunnel=*</code>, put it in the ToDo plugin and quickly check the geometry of each tunnel.
  * Search <code>CHECK=skip -child</code> and delete all surplus/orphaned old nodes.
  * Search <code>CHECK=unused</code> and delete all new unused nodes.
  * Search <code>REPLACE=from</code> and delete this tag.
  * Search <code>CHECK=*</code> and delete this tag.
  * Then upload to OSM.

#!/usr/bin/env python
# -*- coding: utf8

# replace_geometry
# Replace geometry of a chain of ways with that of one other line, tagged with REPLACE=from and REPLACE=to, respectively
# Usage: python replace_geometry.py [input_filename.osm]
# Resulting file will be written to input_filename + "_new.osm"
# Nodes to be checked will get CHECK tag


import sys
import time
import math
import json
from xml.etree import ElementTree


version = "0.1.0"

margin = 5   # Meters of tolarance for matching nodes


# Output message

def message (line):

	sys.stdout.write (line)
	sys.stdout.flush()


# Compute approximation of distance between two coordinates, in meters
# Works for short distances

def distance(n1, n2):

	lon1, lat1, lon2, lat2 = map(math.radians, [all_nodes[n1]['lon'], all_nodes[n1]['lat'], all_nodes[n2]['lon'], all_nodes[n2]['lat']])
	x = (lon2 - lon1) * math.cos( 0.5*(lat2+lat1) )
	y = lat2 - lat1
	return 6371000 * math.sqrt( x*x + y*y )


# Replace coordinates of from-node with to-node

def replace_node(from_node, to_node):

	all_nodes[from_node]['lat'] = all_nodes[to_node]['lat']
	all_nodes[from_node]['lon'] = all_nodes[to_node]['lon']
	all_nodes[to_node]['replace'] = True
	all_nodes[from_node]['replace'] = True


# Main program

if __name__ == '__main__':

	# Read all data into memory

	start_time = time.time()
	
	if len(sys.argv) > 1:
		filename = sys.argv[1]
	else:
		message ("Please include input osm filename as parameter\n")
		sys.exit()

	message ("\nReading file '%s'..." % filename)

	tree = ElementTree.parse(filename)
	root = tree.getroot()

	from_ways = {}
	to_nodes = []
	all_nodes = {}


	# Pass 1:
	# Find all from-ways + one to-way

	message ("\nFinding chain of ways ... ")
	count_from_ways = 0
	count_all_ways = 0

	for way in root.iter('way'):
		count_all_ways += 1

		replace_tag = way.find("tag[@k='REPLACE']")

		if replace_tag != None:

			replace = replace_tag.attrib['v']

			if replace in ['from', 'to']:

				nodes = []
				for node in way.iter("nd"):
					node_id = node.attrib['ref']
					nodes.append(node_id)
					if node_id not in all_nodes:
						all_nodes[node_id] = {
							'lines': 1,
							'lat': None,
							'lon': None
						}
#					else:
#						all_nodes[node_id]['lines'] += 1

				if replace == "from":
					entry = {
						'nodes': nodes,
						'next_way': None
					}
					from_ways[ way.attrib['id'] ] = entry
					all_nodes[ nodes[-1]]['split'] = True
					count_from_ways += 1
				else:
					to_nodes = nodes
					to_way = way.attrib['id']

	message ("%i ways found, of %i total ways\n" % (count_from_ways, count_all_ways))

	if not to_nodes:
		message ("No 'REPLACE=to' found\n")
		sys.exit()

	if not from_ways:
		message ("No 'REPLACE=from' found\n")
		sys.exit()


	# Pass 2:
	# Mark all nodes in from-ways used by other ways

	message ("Identify intersection with other ways ... ")
	count_intersection = 0

	for way in root.iter('way'):
		replace_tag = way.find("tag[@k='REPLACE']")

		if replace_tag == None:

			for node in way.iter("nd"):
				node_id = node.attrib['ref']
				if node_id in all_nodes:
					all_nodes[node_id]['lines'] += 1
					count_intersection += 1

	message ("%i intersections found\n" % count_intersection)


	# Pass 3:
	# Get node coordinates + identify nodes with tags

	message ("Read all nodes ... ")
	count_tags = 0

	for node in root.iter('node'):
		node_id = node.attrib['id']

		if node_id in all_nodes:
			all_nodes[node_id]['lat'] = float(node.attrib['lat'])
			all_nodes[node_id]['lon'] = float(node.attrib['lon'])

			for tag in node.iter('tag'):
				if tag.attrib['k'] != "created_by":
					all_nodes[node_id]['tags'] = True
					count_tags += 1
					break

	message ("%i nodes, %i with tags\n" % (len(all_nodes), count_tags))


	# Pass 4:
	# Create sequenced chain of ways

	message ("Create sorted way ... ")

	start_way = None
	start_node = to_nodes[0]
	find_node = start_node
	previous_way = None
	found_way = 1  # Dummy
	count_ways = 0

	# Starting with the first node, find chain of ways

	while found_way != None:
		found_way = None

		# Search for connected way

		for way_id, way in from_ways.iteritems():
			if (way['next_way'] == None) and (way_id != previous_way) and ((way['nodes'][0] == find_node) or (way['nodes'][-1] == find_node)):
				found_way = way_id
				break

		if found_way != None:
			if start_way == None:
				start_way = found_way
			else:
				from_ways[ previous_way ]['next_way'] = found_way

			# Check if the ways should be reversed

			if from_ways[ found_way ]['nodes'][0] == find_node:
				find_node = from_ways[ found_way ]['nodes'][-1]
			else:
				find_node = from_ways[ found_way ]['nodes'][0]
				from_ways[ found_way ]['nodes'].reverse()

			previous_way = found_way
			count_ways += 1

	if count_ways == 0:
		message ("start node %s not found\n" % start_node)
		sys.exit()
	else:
		message ("found chain of %i ways\n" % count_ways)


	# Pass 5:
	# Start moving ways

	message ("Replace geometry ... \n")

	len_nodes = len(to_nodes)
	way_id = start_way
	way = from_ways[way_id]
	previous_index = 0
	count = count_ways

	# Iterate chain of from-ways, advancing through to_nodes as we go

	while way_id != None:
		way = from_ways[way_id]
		message ("\r%i " % count)
		count -= 1

		from_node = way['nodes'][0]
		new_nodes = [ from_node ]

		# If next to-node is close to connecting from-node, replace it

		if (all_nodes[from_node]['lines'] == 1):
			test_distance = distance(from_node, to_nodes[previous_index + 1])
			if test_distance < margin:
				replace_node(from_node, to_nodes[previous_index + 1])
				previous_index += 1

		# Iterate nodes of from-way

		from_index = 0
		for from_node in way['nodes'][1:]: 
			from_index += 1

			# Find closest to-node to from-node

			min_distance = 6371000.0  # Dummy
			found_index = previous_index

			for i in range(previous_index + 1, len_nodes):
				test_distance = distance(from_node, to_nodes[i])
				if test_distance < min_distance:
					min_distance = test_distance
					found_index = i

			# If not last node of way, and no other unrelated ways are connected to this node

			if (from_node != way['nodes'][-1]) and (all_nodes[from_node]['lines'] == 1):
				next_distance = distance(way['nodes'][from_index + 1], to_nodes[found_index])

				# Do not replace node if the next from_node is closer, unless the nodes are very close

				if (next_distance >= min_distance) or (min_distance < margin):
					new_nodes = new_nodes + to_nodes[ previous_index + 1 : found_index ] + [ from_node ]
					for i in range(previous_index + 1, found_index):
						all_nodes[ to_nodes[i] ]['use'] = True
					previous_index = found_index
					replace_node(from_node, to_nodes[found_index])

				else:
					all_nodes[from_node]['skip'] = True

			# If last node of way, or other unrelated ways are connected to this node 

			else:
				if (min_distance < margin) and (all_nodes[from_node]['lines'] == 1):
					replace_node(from_node, to_nodes[found_index])

				# Check if the to-node should be included before or after the current from-node

				else:
					distance1 = distance(to_nodes[found_index - 1], to_nodes[found_index])
					distance2 = distance(to_nodes[found_index - 1], from_node)
					if distance1 < distance2:
						found_index += 1

				new_nodes = new_nodes + to_nodes[ previous_index + 1 : found_index ] + [ from_node ]
				for i in range(previous_index + 1, found_index):
					all_nodes[ to_nodes[i] ]['use'] = True
				previous_index = max(found_index - 1, previous_index)

		from_ways[way_id]['nodes'] = new_nodes
		way_id = way['next_way']


	# Pass 6:
	# Update XML file

	message ("\rUpdate XML ... ")

	way_id = start_way

	# Remove old members of ways and add the new members

	while way_id != None:
		way = from_ways[way_id]
		way_tag = root.find("way[@id='%s']" % way_id)

		for node in way_tag.findall("nd"):
			way_tag.remove(node)

		for node in way['nodes']:
			way_tag.append(ElementTree.Element("nd", ref=str(node)))

		way_tag.set("action", "modify")
		way_id = way['next_way']

	# Updated replaced coordinates + add CHECK tag for inspection

	for node_tag in root.findall("node"):
		node_id = node_tag.attrib["id"]

		if node_id in all_nodes:
			node = all_nodes[node_id]

			if int(node_id) > 0:

				if "replace" in node:
					node_tag.set("action", "modify")
					node_tag.set("lat", str(node['lat']))
					node_tag.set("lon", str(node['lon']))

				check = ""
				if node['lines'] > 1:
					check += "junction"
				elif "tags" in node:
					check += "tags"
				elif ("split" in node) and ("replace" in node):
					check = "replace"
				elif "split" in node:
					check += "split"
				elif "skip" in node:
					check += "skip"

				if check:
					node_tag.append(ElementTree.Element("tag", k="CHECK", v=check))

			else:
				if "replace" in node:
					root.remove(node_tag)
				elif "use" not in node:
					node_tag.append(ElementTree.Element("tag", k="CHECK", v="unused"))

	way_tag = root.find("way[@id='%s']" % to_way)
	root.remove(way_tag)

	root.set("upload", "false")


	# Wrap up

	if filename.find(".osm") >= 0:
		filename = filename.replace(".osm", "_new.osm")
	else:
		filename = filename + "_new.osm"

	tree.write(filename, encoding='utf-8', method='xml', xml_declaration=True)

	message ("\nWritten to file '%s'\n" % filename)
	message ("Time: %i seconds\n" % (time.time() - start_time))

from math import sin, cos, sqrt, atan2, radians
from typing import List, Dict, Any
from datetime import datetime
import requests
import random
import polyline
import csv


# define some params we will be using for the test run
VEHICLE_CAPACITY = 3200000
DA_VAN_SPEED = 30 # KM/H
DEPOT = {'lat': 24.919762580554334, 'lng': 55.122473893638016, 'volume': 0.0, 'delivery_nr': 'origin'}
OSRM_URL = 'https://router.project-osrm.org'
MAX_PICKUPS_IN_ROUTE = 1


def calculate_distance_between_pins(pin1: Dict[str, float], pin2: Dict[str, float]) -> float:
    '''Compute the great-circle distance between two points using the Haversine formula'''
    R = 6373.0 # radius of earth in km

    lat1 = radians(pin1['lat'])
    lng1 = radians(pin1['lng'])
    lat2 = radians(pin2['lat'])
    lng2 = radians(pin2['lng'])

    dlon = lng2 - lng1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c 


def get_pins_durations_matrix(pins: List[Dict[str, float]]) -> List[List[float]]:
    '''Use OSRM to get the travelling duration between two points'''
    encoded_pins = ';'.join([f'{pin["lng"]},{pin["lat"]}' for pin in pins])
    response = requests.get(f'{OSRM_URL}/table/v1/driving/{encoded_pins}?annotations=duration').json()
    durations_matrix = response['durations']
    for i in range(len(durations_matrix)):
        for j in range(len(durations_matrix[i])):
            if durations_matrix[i][j] is None:
                durations_matrix[i][j] = calculate_distance_between_pins(pins[i], pins[j]) / DA_VAN_SPEED
    return durations_matrix


def get_pins_route_polyline(pins: List[Dict[str, float]]) -> str:
    '''Get the route geometry for a set of pins'''
    encoded_pins = ';'.join([f'{pin["lng"]},{pin["lat"]}' for pin in pins])
    response = requests.get(f'{OSRM_URL}/route/v1/driving/{encoded_pins}?overview=full').json()
    return response['routes'][0]['geometry']


def display_result(route: List[int]):
    for i, step in enumerate(route['steps']):
        print(f"step {i + 1}, {step.get('delivery_nr') or step.get('pickup_nr')} - volume: {step['volume']}, location: {step['lat']}, {step['lng']}")
    print(f"total duration: {round(route['duration'], 2)} seconds, total_volume: {round(route['deliveries_volume'], 2)}")


def build_route_dict(route: List[int], events: List[Dict], durations_matrix: List[List[float]]) -> Dict[str, Any]:
    pins = []
    duration = 0.0
    deliveries_volume = 0.0
    pickups_volume = 0.0
    for i in range(len(route)):
        if i < len(route) - 1:
            duration += durations_matrix[route[i]][route[i + 1]]
        if events[route[i]].get('delivery_nr'):
            deliveries_volume += events[route[i]]['volume']
        else:
            pickups_volume += events[route[i]]['volume']
        pins.append(events[route[i]])
    geometry = get_pins_route_polyline(pins)
    return {
        'steps': pins,
        'duration': duration,
        'deliveries_volume': deliveries_volume,
        'pickups_volume': pickups_volume,
        'geometry': geometry,
    }


def format_kml(routes: List[int]):
    '''Create a kml file from a list of routes, to export to Google maps in order to visualize the routes'''
    kml_text = '''
        <?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://www.opengis.net/kml/2.2">
        <Document>
            <name>Coolblue Routing Assignment</name>
            <description/>
            <Style id="icon-1603-0288D1-nodesc-normal">
            <IconStyle>
                <color>ffd18802</color>
                <scale>1</scale>
                <Icon>
                <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
                </Icon>
            </IconStyle>
            <LabelStyle>
                <scale>0</scale>
            </LabelStyle>
            <BalloonStyle>
                <text><![CDATA[<h3>$[name]</h3>]]></text>
            </BalloonStyle>
            </Style>
            <Style id="icon-1603-0288D1-nodesc-highlight">
            <IconStyle>
                <color>ffd18802</color>
                <scale>1</scale>
                <Icon>
                <href>https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png</href>
                </Icon>
            </IconStyle>
            <LabelStyle>
                <scale>1</scale>
            </LabelStyle>
            <BalloonStyle>
                <text><![CDATA[<h3>$[name]</h3>]]></text>
            </BalloonStyle>
            </Style>
            <StyleMap id="icon-1603-0288D1-nodesc">
            <Pair>
                <key>normal</key>
                <styleUrl>#icon-1603-0288D1-nodesc-normal</styleUrl>
            </Pair>
            <Pair>
                <key>highlight</key>
                <styleUrl>#icon-1603-0288D1-nodesc-highlight</styleUrl>
            </Pair>
            </StyleMap>

    '''

    hex_chars = '0123456789ABCDEF'
    line_style_ids = []
    for _ in range(len(routes)):
        style_id = f'line-{random.randint(100000, 999999)}-{random.randint(1000, 9999)}-nodesc'
        line_style_ids.append(style_id)
        line_color = ''.join([hex_chars[random.randint(0, len(hex_chars)-1)] for _ in range(6)])
        kml_text += f'''
            <Style id="{style_id}">
            <LineStyle>
                <color>{line_color}</color>
                <width>7.2</width>
            </LineStyle>
            <BalloonStyle>
                <text><![CDATA[<h3>$[name]</h3>]]></text>
            </BalloonStyle>
            </Style>
            <Style id="{style_id}-highlight">
            <LineStyle>
                <color>{line_color}</color>
                <width>10.8</width>
            </LineStyle>
            <BalloonStyle>
                <text><![CDATA[<h3>$[name]</h3>]]></text>
            </BalloonStyle>
            </Style>
            <StyleMap id="{style_id}">
            <Pair>
                <key>normal</key>
                <styleUrl>#{style_id}-normal</styleUrl>
            </Pair>
            <Pair>
                <key>highlight</key>
                <styleUrl>#{style_id}-highlight</styleUrl>
            </Pair>
            </StyleMap>
        '''

    max_route_points = max([len(route['steps']) for route in routes])
    point_style_ids = []
    for point_id in range(max_route_points):
        style_id = f'icon-seq2-0-{point_id}-{random.randint(1000, 9999)}-nodesc'
        point_style_ids.append(style_id)
        kml_text += f'''
            <Style id="{style_id}-normal">
            <IconStyle>
                <color>ffd18802</color>
                <scale>1</scale>
                <Icon>
                <href>images/icon-{point_id-1}.png</href>
                </Icon>
            </IconStyle>
            <LabelStyle>
                <scale>0</scale>
            </LabelStyle>
            <BalloonStyle>
                <text><![CDATA[<h3>$[name]</h3>]]></text>
            </BalloonStyle>
            </Style>
            <Style id="{style_id}-highlight">
            <IconStyle>
                <color>ffd18802</color>
                <scale>1</scale>
                <Icon>
                <href>images/icon-{point_id-1}.png</href>
                </Icon>
            </IconStyle>
            <LabelStyle>
                <scale>1</scale>
            </LabelStyle>
            <BalloonStyle>
                <text><![CDATA[<h3>$[name]</h3>]]></text>
            </BalloonStyle>
            </Style>
            <StyleMap id="{style_id}">
            <Pair>
                <key>normal</key>
                <styleUrl>#{style_id}-normal</styleUrl>
            </Pair>
            <Pair>
                <key>highlight</key>
                <styleUrl>#{style_id}-highlight</styleUrl>
            </Pair>
            </StyleMap>
        '''

    route_id = 0
    point_id = 1
    for route in routes:
        point_id = 1
        route_id += 1
        route_points = polyline.decode(route['geometry'])
        kml_text += f'''
            <Folder>
            <name>Route {route_id}</name>
        '''

        kml_text += f'''
            <Placemark>
                <name>Route</name>
                <description>traveling time: {int(route['duration']/60)} minutes
                events: {len(route['steps'])-2}
                total deliveries volume: {round(route['deliveries_volume'], 2)}
                </description>
                <styleUrl>#{line_style_ids[route_id-1]}</styleUrl>
                <LineString>
                <tessellate>1</tessellate>
                <coordinates>
        '''
        for point in route_points:
            kml_text += f'''{point[1]},{point[0]},0
            '''
        kml_text += '''
                </coordinates>
                </LineString>
            </Placemark>
        '''
        kml_text += '''
            </Folder>
        '''

        kml_text += f'''
            <Folder>
            <name>Route {route_id} Points</name>
        '''
        remaining_volume_in_vehicle = route['deliveries_volume']
        for step in route['steps']:
            if step.get('delivery_nr'):
                remaining_volume_in_vehicle -= step['volume']
            else:
                remaining_volume_in_vehicle += step['volume']

            event_id = step.get('delivery_nr') or step.get('pickup_nr')
            kml_text += f'''
                <Placemark>
                    <name>Event {event_id}</name>
                    <description>
                    event volume: {round(step['volume'], 2)}
                    remaining vehicle volume after event: {round(remaining_volume_in_vehicle, 2)}
                    </description>
                    <styleUrl>#{point_style_ids[point_id-1]}</styleUrl>
                    <Point>
                    <coordinates>
                        {step["lng"]},{step["lat"]},0
                    </coordinates>
                    </Point>
                </Placemark>
            '''
            point_id += 1
        kml_text += '''
            </Folder>
        '''
    
    kml_text += '''
        </Document>
        </kml>
    '''

    f = open(f"result/routes_{datetime.now()}.kml".replace(" ", "-"), "w")
    f.write(kml_text)
    f.close()


def read_test_data():
    pickups = []
    with open("test/data/pickups_data.csv", "r") as f:
        reader = csv.reader(f)
        for row in reader:
            pickups.append({
                'lat': float(row[0]),
                'lng': float(row[1]),
                'volume': float(row[2])
            })
    random.shuffle(pickups)
    for i in range(len(pickups)):
        pickups[i].update({'pickup_nr': f'P{i+1}'})

    deliveries = []
    with open("test/data/deliveries_data.csv", "r") as f:
        reader = csv.reader(f)
        for row in reader:
            deliveries.append({
                'lat': float(row[0]),
                'lng': float(row[1]),
                'volume': float(row[2])
            })
    random.shuffle(deliveries)

    # osrm limits pins to 100 so we will remove some
    if len(deliveries) > 94:
        deliveries = deliveries[:94]

    for i in range(len(deliveries)):
        deliveries[i].update({'delivery_nr': f'D{i+1}'})

    return deliveries, pickups

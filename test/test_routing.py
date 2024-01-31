import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.routing import CWSRouting
from src import util


def test_routing():
    # create routes
    routing = CWSRouting(
        vehicle_capacity=util.VEHICLE_CAPACITY,
        max_pickups_in_route=util.MAX_PICKUPS_IN_ROUTE,
        depot_event=util.DEPOT
    )
    routes = routing.run_clarke_wright_savings_with_pickup()
    routes = routing.build_routes_map_file(routes)

    # validate each route
    for route in routes:
        remaining_volume = route['deliveries_volume']
        is_within_capacity = True
        pickup_count = 0
        visited = set()
        has_duplicate = False

        for event in route['steps']:
            # if delivery event, subtract load from vehicle after dropoff
            if event.get('delivery_nr'):
                remaining_volume -= event['volume']
            # if pickup event, add pickup load to vehicle and increase pickup counter
            else:
                remaining_volume += event['volume']
                pickup_count += 1
            # check if total load is less than vehicle capacity after pickup event
            if remaining_volume >= util.VEHICLE_CAPACITY:
                is_within_capacity = False

            event_nr = event.get('delivery_nr') or event.get('pickup_nr')
            if event_nr != 'origin' and event_nr not in visited:
                visited.add(event_nr)
            elif event_nr != 'origin' and event_nr in visited:
                has_duplicate = True

        assert is_within_capacity, 'total load is more than vehicle capacity'
        assert pickup_count <= util.MAX_PICKUPS_IN_ROUTE, f'there are more than {util.MAX_PICKUPS_IN_ROUTE} pickups in the route'
        assert not has_duplicate, 'some events have been visited twice'
        assert route['steps'][0]['delivery_nr'] == route['steps'][-1]['delivery_nr'] == 'origin', 'the route does not start and end with the depot'

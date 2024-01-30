import util
from typing import Dict, Any, List


class CWSRouting:

    def __init__(self, vehicle_capacity: float, max_pickups_in_route: int, depot_event: Dict[str, Any]):
        self.vehicle_capacity = vehicle_capacity
        self.max_pickups_in_route = max_pickups_in_route
        self.depot_event = depot_event

        deliveries, pickups = util.read_test_data()
        self.events = [self.depot_event] + deliveries + pickups
        self.durations_matrix = util.get_pins_durations_matrix(self.events)

    def limit_number_of_pickups(self, merged_route: List[int]):
        '''If the merged route contains more than max_pickups_in_route, remove the new pickup from the route'''
        pickups_count = 0
        for event_ix in merged_route:
            if self.events[event_ix].get('pickup_nr'):
                pickups_count += 1
                if pickups_count > self.max_pickups_in_route:
                    merged_route.remove(event_ix)
                    break
        return merged_route, pickups_count

    def validate_route_volume_with_pickup(self, merged_route: List[int], total_deliveries_volume: float):
        '''Check if the total volume of the vehicle used at every event is less than or equal to the vehicle capacity'''
        remaining_volume = total_deliveries_volume
        is_within_capacity = True
        for event_ix in merged_route:
            # if delivery event, subtract load after dropoff
            if self.events[event_ix].get('delivery_nr'):
                remaining_volume -= self.events[event_ix]['volume']
            # if pickup event, add load after pickup
            else:
                remaining_volume += self.events[event_ix]['volume']
            # check if total load is less than vehicle capacity after pickup event
            if remaining_volume > self.vehicle_capacity:
                is_within_capacity = False
                break
        return is_within_capacity

    def get_total_volume(self, route: List[int]):
        '''Get the total volume of the vehicle when deliveries are loaded onto it'''
        volume = 0
        for event_ix in route:
            if self.events[event_ix].get('delivery_nr'):
                volume += self.events[event_ix]['volume']
        return volume

    def calculate_savings(self, i: int, j: int):
        '''Calculate the savings of merging events i and j into one route vs delivering them individually'''
        return self.durations_matrix[0][i] + self.durations_matrix[0][j] - self.durations_matrix[i][j]

    def run_clarke_wright_savings_with_pickup(self):
        num_events = len(self.events)
        savings_matrix = [[0] * num_events for _ in range(num_events)]

        # intialize the savings matrix
        for i in range(num_events):
            for j in range(i + 1, num_events):
                savings_matrix[i][j] = self.calculate_savings(i, j)

        sorted_savings = sorted(((i, j, savings_matrix[i][j]) for i in range(num_events) for j in range(i + 1, num_events)),
                                key=lambda x: x[2], reverse=True)

        routes = [[0, i, 0] for i in range(1, num_events)]

        # in order of savings, start merging routes
        for i, j, _ in sorted_savings:
            route_i = next((r for r in routes if i in r), None)
            route_j = next((r for r in routes if j in r), None)

            # signifies a removed pickup event, we can skip this
            if route_i is None or route_j is None:
                continue

            if (route_i != route_j):
                route_i_index = routes.index(route_i)
                route_j_index = routes.index(route_j)

                # merge routes such that the start and end events are the depot
                merged_route = routes[route_i_index][:-1] + routes[route_j_index][::-1][1:]

                # validate number of pickups in route and the used vehicle capacity with pickups
                merged_route, pickups_count = self.limit_number_of_pickups(merged_route)
                total_merged_deliveries_volume = self.get_total_volume(merged_route)
                is_volume_with_pickup_within_capacity = True
                if pickups_count >= 1:
                    is_volume_with_pickup_within_capacity = self.validate_route_volume_with_pickup(merged_route, total_merged_deliveries_volume)

                if total_merged_deliveries_volume <= self.vehicle_capacity and is_volume_with_pickup_within_capacity:
                    # merge routes
                    routes[route_i_index] = merged_route
                    routes.pop(route_j_index)

        return routes

    def build_routes_map_file(self, routes, display_log=False):
        routes_descriptive = []
        for route in routes:
            # exclude solitary pickup event routes
            if not(len(route) == 3 and self.events[route[1]].get('pickup_nr')):
                routes_descriptive.append(util.build_route_dict(route, self.events, self.durations_matrix))

        if display_log:
            for count, route in enumerate(routes_descriptive):
                print(f"Vehicle {count + 1}:")
                util.display_result(route)
                print()

        util.format_kml(routes_descriptive)
        return routes_descriptive

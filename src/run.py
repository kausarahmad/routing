import time

import util as util
from routing import CWSRouting


def main():
    routing = CWSRouting(
        vehicle_capacity=util.VEHICLE_CAPACITY,
        max_pickups_in_route=util.MAX_PICKUPS_IN_ROUTE,
        depot_event=util.DEPOT
    )
    start_algo = time.time()
    routes = routing.run_clarke_wright_savings_with_pickup()
    end_algo = time.time()
    print(f'time running algorithm: {end_algo - start_algo}s')
    routing.build_routes_map_file(routes, display_log=True)

if __name__ == "__main__":
    main()

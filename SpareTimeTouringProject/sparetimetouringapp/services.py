import math, time, random
from datetime import timedelta
import googlemaps
import networkx as nx
from simpleai.search.models import SearchProblem
from simpleai.search.local import beam, hill_climbing_random_restarts, hill_climbing
from datetime import datetime, timedelta, date

HOUR = 3600  # seconds
DURATION_STEPS = 300  # seconds
MIN_STAY = 60 * 60  # 1 hour in seconds
MAX_STAY = 120 * 60  # 2 hours in seconds
MAX_RANDOM_VENUES_ADDITION = 3

SEARCH_AREA_RADIUS_PADDING = 500    # meters

MAX_SEARCH_ITERATIONS = 0
REQUESTS_DELAY = 2   # seconds
PLACES_SEARCH_LIMIT = 8

TREVI_FOUNTAIN_COORD = (41.901318, 12.483317)
TREVI_FOUNTAIN_NAME = "Fontana di Trevi"
PANTHEON_COORD = (41.898782, 12.476867)
PANTHEON_NAME = "PANTHEON"
COLOSSEUM_COORD = (41.890543, 12.492205)
COLOSSEUM_NAME = "Colosseum, Piazza del Colosseo"
BASILICA_COORD = (41.886633, 12.505454)
BASILICA_NAME = "Basilica di San Giovanni in Laterano"
SPANISH_STEPS_COORD = (41.906193, 12.482232)
SPANISH_STEPS_NAME = "Scalinata di Trinità dei Monti"

TALBIYE_COORD = (31.768939, 35.215470)
TALBIYE_NAME = "Talbiye"
CENTRAL_STATION_COORD = (31.789350, 35.203339)
CENTRAL_STATION_NAME = "Jerusalem Central Bus Station"

gmaps = googlemaps.Client('AIzaSyDk8bfPE0MQjmfSss2kEjK6RREetSKYigE', )

MAX_HILL_CLIMBING_RESTARTS = 20


class Venue:

    def __init__(self, venue_id, name, location, rating=None, img_url=None):
        self.venue_id = venue_id
        self.name = name
        self.location = location
        self.rating = rating
        self.img_url = img_url

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class BestRoute(SearchProblem):

    def __init__(self, g, s, d, arrival_time, initial_state):
        super().__init__(initial_state)
        self.graph = g
        self.start = s
        self.destination = d
        self.arrival_time = arrival_time
        self.travel_duration = 0
        self.available_time = (self.arrival_time - datetime.now()).total_seconds() - 10800  # for Israel time

        self.venues = list(self.graph.nodes)

        self.venues.sort(key=lambda v: self.graph[v][self.destination]["distance"], reverse=True)  # Sorted list of venues according to distance from destination
        self.venues.remove(self.start)

    @staticmethod
    def calc_duration(state, graph):
        overall_duration = 0
        for i in range(len(state) - 1):
            venue, length_of_stay = state[i]
            next_venue = state[i + 1][0]
            moving_duration = graph[venue][next_venue]['duration']
            overall_duration += moving_duration + length_of_stay
        return overall_duration

    @staticmethod
    def calc_value(state, start, destination):

        def value_function(r, x):
            # return (r**2 * 10) / (x - 40)
            return r ** 2 * (2 * math.log(x - 50, 2))

        val = 0
        for venue, duration in state:
            if venue == start or venue == destination:
                continue
            duration_in_minutes = duration / 60
            current_venue_value = value_function(venue.rating, duration_in_minutes)
            val += current_venue_value
        return val

    @staticmethod
    def adding_venues(state, graph, available_time):

        possible_actions = []
        visited_venues = list(x[0] for x in state)
        travel_duration = BestRoute.calc_duration(state, graph)

        for idx in range(len(state) - 1):
            cur_venue = state[idx][0]
            next_venue = state[idx + 1][0]
            for new_venue in graph.nodes():
                if new_venue in visited_venues:
                    continue

                if idx > 0:
                    pre_venue = state[idx - 1][0]
                else:
                    pre_venue = None

                # Check if new duration is valid
                potential_duration = travel_duration - graph[cur_venue][next_venue]["duration"] + \
                                     graph[cur_venue][new_venue]["duration"] + \
                                     graph[new_venue][next_venue]["duration"] + MIN_STAY
                if available_time >= potential_duration:
                    act = dict(new_venue={"idx": idx + 1, "venue": new_venue, "duration": MIN_STAY})
                    possible_actions.append(act)

                if pre_venue:
                    # Check if new duration is valid
                    potential_duration = travel_duration - \
                                         graph[cur_venue][next_venue]["duration"] - \
                                         graph[pre_venue][cur_venue]["duration"] - state[idx][1] + \
                                         graph[new_venue][next_venue]["duration"] + \
                                         graph[pre_venue][new_venue]["duration"] + MIN_STAY
                    if available_time >= potential_duration:
                        act = dict(switch_venue={"old_venue_idx": idx, "new_venue": new_venue, "duration":
                            MIN_STAY})
                        possible_actions.append(act)

        return possible_actions

    @staticmethod
    def adding_venues_with_sorted_order(state, graph, available_time, sorted_venues):

        possible_actions = []
        visited_venues = list(x[0] for x in state)
        travel_duration = BestRoute.calc_duration(state, graph)

        for idx in range(len(state) - 1):
            cur_venue = state[idx][0]
            next_venue = state[idx + 1][0]
            for new_venue in graph.nodes():
                if new_venue in visited_venues:
                    continue

                cur_venue_idx = sorted_venues.index(cur_venue) if idx > 0 else -1  # In case of starting point
                next_venue_idx = sorted_venues.index(next_venue)
                new_venue_idx = sorted_venues.index(new_venue)

                if idx > 0:
                    pre_venue = state[idx - 1][0]
                    pre_venue_idx = sorted_venues.index(pre_venue) if idx - 1 > 0 else -1  # In case of starting point
                else:
                    pre_venue = None
                    pre_venue_idx = -1

                # Only allow adding venues that keep the destination distance order
                if cur_venue_idx < new_venue_idx < next_venue_idx:
                    # Check if new duration is valid
                    potential_duration = travel_duration - graph[cur_venue][next_venue]["duration"] + \
                                         graph[cur_venue][new_venue]["duration"] + \
                                         graph[new_venue][next_venue]["duration"] + MIN_STAY
                    if available_time >= potential_duration:
                        act = dict(new_venue={"idx": idx + 1, "venue": new_venue, "duration": MIN_STAY})
                        possible_actions.append(act)

                if pre_venue:
                    # Only allow switching venues so that the destination distance order is maintained
                    if pre_venue_idx < new_venue_idx < next_venue_idx:
                        # Check if new duration is valid
                        potential_duration = travel_duration - \
                                             graph[cur_venue][next_venue]["duration"] - \
                                             graph[pre_venue][cur_venue]["duration"] - state[idx][1] + \
                                             graph[new_venue][next_venue]["duration"] + \
                                             graph[pre_venue][new_venue]["duration"] + MIN_STAY
                        if available_time >= potential_duration:
                            act = dict(switch_venue={"old_venue_idx": idx, "new_venue": new_venue, "duration":
                                MIN_STAY})
                            possible_actions.append(act)

        return possible_actions

    def actions(self, state):

        possible_actions = []
        travel_duration = self.calc_duration(state, self.graph)

        # Check possibilities for changing durations
        if self.available_time >= travel_duration + DURATION_STEPS:
            for idx, (venue, duration) in enumerate(state):
                if venue == self.start or venue == self.destination:
                    continue
                if duration < MAX_STAY:
                    act = dict(duration_change={"idx": idx, "change": DURATION_STEPS})
                    possible_actions.append(act)

        # Check possibilities for adding or switching venues
        # add_switch_possible_actions = self.adding_venues(state, self.graph, self.available_time)
        add_switch_possible_actions = self.adding_venues_with_sorted_order(state, self.graph, self.available_time,
                                                                           self.venues)

        possible_actions.extend(add_switch_possible_actions)

        return possible_actions

    def result(self, state, action):

        new_state = state.copy()

        # Check what was the selected action
        if "duration_change" in action:
            d_c = action["duration_change"]
            idx = d_c["idx"]
            change = d_c["change"]
            venue, duration = new_state[idx]
            duration += change
            new_state[idx] = (venue, duration)
            selected_action = "Duration Change"

        elif "new_venue" in action:
            n_v = action["new_venue"]
            idx = n_v["idx"]
            new_state.insert(idx, (n_v["venue"], n_v["duration"]))
            selected_action = "Venue Added"

        elif "switch_venue" in action:
            n_v = action["switch_venue"]
            old_venue_idx = n_v["old_venue_idx"]
            new_state[old_venue_idx] = (n_v["new_venue"], n_v["duration"])
            selected_action = "Venue Switched"

        else:
            return state

        return new_state

    def value(self, state):

        return self.calc_value(state, self.start, self.destination)

    def generate_random_state(self):
        cur_state = None
        rand_state = [(self.start, 0), (self.destination, 0)]
        rand_state_duration = self.calc_duration(rand_state, self.graph)
        rand_idx = 0
        iterations = random.randint(1, MAX_RANDOM_VENUES_ADDITION)
        while self.available_time >= rand_state_duration:
            cur_state = rand_state.copy()
            if iterations <= 0:
                break
            if rand_idx + 1 < len(self.venues) - 1:
                new_num = random.randint(rand_idx + 1, len(self.venues) - 1)
                rand_idx = new_num
            else:
                break
            rand_state.insert(len(rand_state) - 1, (self.venues[rand_idx], MIN_STAY))
            rand_state_duration = self.calc_duration(rand_state, self.graph)
            iterations -= 1

        return cur_state


def calc_distance(origin, destination):
    """
    Calculates the distance between 2 coordinates.
    :param origin: origin.
    :param destination: destination.
    :return: the distance in kilometers.
    """
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) * math.sin(dlat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) * math.sin(dlon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = radius * c

    return d * 1000     # km -> meters


def parse_places(places):
    """
    Parse places from Google into venue objects.
    :param places: places from Google in dictionary format.
    :return: A list of parsed venue objects.
    """
    parsed_venues = []
    for place in places:
        venue_id = place['place_id']
        name = place['name']
        location = (place['geometry']['location']['lat'], place['geometry']['location']['lng'])
        rating = place['rating']
        venue = Venue(venue_id, name, location, rating)
        parsed_venues.append(venue)

    return parsed_venues


def parse_time(t):
    """
    Parses a hour in string format to datetime object.
    :param t: the hour.
    :return: the datetime object.
    """
    today = date.today()
    datetime_obj = datetime.strptime(t, "%H:%M:%S")
    return datetime_obj.replace(year=today.year, month=today.month, day=today.day)


def get_data(start, destination):
    """
    Obtains the relevant venues in the provided search area, defined by the start and destination locations,
    via the Google Maps API.
    :param start: the coordinates of the start location.
    :param destination: the coordinates of the destination.
    :return:
    """

    # calculate middle point
    start_lat, start_lng = start.location
    destination_lat, destination_lng = destination.location
    middle_lat = (start_lat + destination_lat) / 2
    middle_lng = (start_lng + destination_lng) / 2

    # calculate distance between middle point and origin, which is the search area radius.
    start_middle_distance = calc_distance((start_lat, start_lng), (middle_lat, middle_lng))

    search_radius = start_middle_distance + SEARCH_AREA_RADIUS_PADDING

    print("Started downloading venues and distances")

    places_dict = gmaps.places_nearby(location=(middle_lat, middle_lng), radius=search_radius, rank_by='prominence',
                                      type='cafe')

    places = places_dict['results'][:PLACES_SEARCH_LIMIT]

    for i in range(MAX_SEARCH_ITERATIONS):
        if 'next_page_token' in places_dict:
            time.sleep(REQUESTS_DELAY)
            new_places_dict = gmaps.places_nearby(page_token=places_dict['next_page_token'])
            places.extend(new_places_dict['results'])
            places_dict = new_places_dict
        else:
            break

    venues = parse_places(places)
    venues.insert(0, start)  # Add starting point to the venue list
    venues.append(destination)  # Add destination to the venue list
    locations_tups = [v.location for v in venues]

    distance_matrix = gmaps.distance_matrix(origins=locations_tups, destinations=locations_tups, units='metric', mode='walking')

    print("Finished downloading venues and distances")

    return venues, distance_matrix


def create_graph(nodes, distance_matrix):
    """
    Creates the graph with the venues as nodes and distances as edges
    :param nodes: the venues.
    :param distance_matrix: the distances matrix.
    :return: The graph as a NetworkX object.
    """
    g = nx.Graph()
    distance_rows = distance_matrix['rows']
    venues_num = len(nodes)
    for i, venue in enumerate(nodes):
        g.add_node(venue)
        g.add_edge(venue, venue, duration=0, distance=0)
        elements = distance_rows[i]['elements']
        for j in range(i + 1, venues_num):
            v = elements[j]
            if v['status'] == 'OK':
                g.add_edge(venue, nodes[j], duration=v['duration']['value'], distance=v['distance']['value'])
            else:
                g.add_edge(venue, nodes[j], duration=500, distance=1110)
    return g


def run_search(start, destination, arrival_time):
    """
    Parses the user input runs the algorithm.
    :param start: start point coordinates
    :param destination: destination  coordinates
    :param arrival_time: the desired arrival time
    :return: the best route, the duration and the score.
    """
    starting_point = Venue(123, start['name'], (start['lat'], start['lon']))
    end_point = Venue(321, destination['name'], (destination['lat'], destination['lon']))

    nearby_venues, d_mrx = get_data(starting_point, end_point)
    g = create_graph(nearby_venues, d_mrx)

    initial_state = [(starting_point, 0), (end_point, 0)]

    best_route_problem = BestRoute(g, starting_point, end_point, arrival_time, initial_state=initial_state)

    result_climbing = hill_climbing_random_restarts(best_route_problem, MAX_HILL_CLIMBING_RESTARTS,
                                                    iterations_limit=1000)
    best_state = result_climbing.state
    duration = BestRoute.calc_duration(best_state, g)
    value = BestRoute.calc_value(best_state, starting_point, end_point)

    return best_state, duration, value

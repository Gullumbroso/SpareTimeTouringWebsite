from simpleai.search.models import CspProblem, SearchProblem
import networkx as nx
from datetime import datetime, timedelta
import math, random

HOUR = 3600  # seconds
DURATION_STEPS = 300  # seconds
MIN_STAY = 60 * 60  # 1 hour in seconds
MAX_STAY = 120 * 60  # 2 hours in seconds
MAX_RANDOM_VENUES_ADDITION = 3

# year, month, day, hours, minutes, seconds ...
NOW = datetime(2018, 9, 26, 9, 30, 0, 0)






class BestRoute(SearchProblem):

    def __init__(self, g, s, d, arrival_time, initial_state):
        super().__init__(initial_state)
        self.graph = g
        self.start = s
        self.destination = d
        self.arrival_time = arrival_time
        self.travel_duration = 0
        self.available_time = (self.arrival_time - NOW).total_seconds()

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


import numpy as np
from sklearn.neighbors import BallTree
from geopy import Bing
import streamlit as st
from rapidfuzz import fuzz, utils, process
from typing import Any
from haversine import haversine

class NearbyAirportSuggestions:
    EARTH_RADIUS_MILES = 3959.0
    SEARCH_RADIUS_MILES = 30
    FUZZY_COMPARISON_THRESHOLD: int = 60

    def __init__(self, user_input: str, airport_data: list[dict]):
        self.user_input = user_input
        self.airport_data = airport_data
        self.unique_cities = list(set([data['municipality'] for data in self.airport_data]))
        self.airport_coordinates = [(data.get('latitude_deg'), data.get('longitude_deg')) for data in self.airport_data
                                    if data.get('longitude_deg') and data.get('latitude_deg')]
        self.iata_to_airport_map = {details['iata_code']: (f"{details['name']}, {details['country_code']} "
                                                      f"({details['iata_code']})") for details in airport_data}

    @staticmethod
    def get_city_coordinates(city: str) -> tuple[float, float]:
        geolocator = Bing(api_key=st.secrets["prod"]["BING_API_KEY"])
        location = geolocator.geocode(city)
        if not location:
            raise ValueError(f"Could not find coordinates for '{city}'")
        return location.latitude, location.longitude

    def fuzzy_comparison(self) -> str:
        city_match, score, _ = process.extractOne(self.user_input, self.unique_cities, scorer=fuzz.token_sort_ratio, processor=utils.default_process)
        if city_match and score >= self.FUZZY_COMPARISON_THRESHOLD:
            return city_match
        else:
            st.error("No matching city found, perhaps you misspelled it? "
                     "Please enter a valid city name or airport code.")
            st.stop()


    def find_nearby_airports_from_coords(self, target_city_coords: tuple[float, float]) -> list[tuple[float, float]]:
        # Convert coordinates from degrees to radians
        rad_coords = np.radians(self.airport_coordinates)
        rad_target_coords = np.radians(np.array(target_city_coords).reshape(1, -1))
        rad_search_radius = self.SEARCH_RADIUS_MILES / self.EARTH_RADIUS_MILES

        tree = BallTree(rad_coords, metric='haversine')
        # Query the tree for indices of points within the given radius (in radians)
        indices = tree.query_radius(rad_target_coords, r=rad_search_radius)

        # indices is an array of arrays; extract the first array (for our one target)
        nearby_coords = np.array(self.airport_coordinates)[indices[0]]
        sorted_coords = sorted(nearby_coords.tolist(), key=lambda coord: haversine(coord, target_city_coords))
        return sorted_coords

    def match_actual_coords(self, coords_list, tol: float = 1e-5) -> dict[tuple, Any | None]:
        matches = {}
        for coord in coords_list:
            lat, lon = coord
            matched_airport = None
            for airport in self.airport_data:
                airport_lat = airport.get('latitude_deg')
                airport_lon = airport.get('longitude_deg')
                if (abs(lat - airport_lat) < tol) and (abs(lon - airport_lon) < tol):
                    matched_airport = airport.get('name')
                    break
            matches[tuple(coord)] = matched_airport
        return matches

    def get_matched_airport_details(self, matches: dict) -> dict[str, str]:
        airport_suggestions = dict()
        for airport_data in self.airport_data:
            if airport_data.get('name') in matches.values() and airport_data.get('type') == 'large_airport':
                key = f"{airport_data['name']}, {airport_data['country_code']} ({airport_data['iata_code']})"
                airport_suggestions[key] = airport_data['iata_code']
        return airport_suggestions

    def fetch_airport_suggestions(self) -> dict[str, str]:
        city = self.fuzzy_comparison()
        target_city_coords = self.get_city_coordinates(city)
        nearby_airport_coords = self.find_nearby_airports_from_coords(target_city_coords)

        matches = self.match_actual_coords(nearby_airport_coords)
        suggestions = self.get_matched_airport_details(matches)
        return suggestions

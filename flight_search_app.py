import json
import streamlit as st
from datetime import timedelta

from AmadeusClient import AmadeusFlightSearch
from flight_info import FlightSearchParameters, Segment
from flight_card_logic import display_flight_card, display_collapsable_card
from parse_flight_offers import get_flight_offer_segments
from nearby_airport_suggestions import NearbyAirportSuggestions

# <img src="https://via.placeholder.com/32" alt="Airline Logo" style="width: 32px; height: 32px; margin-right: 10px;">
# <div style="background-color: #0066ff; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 10px;">Best</div>

def fetch_flights(search_type: str, origin: str, destination: str, departure_date: str,
                  return_date: str, num_of_passengers: int, search_range: int, direction: str,
                  env: str = 'prod', version: str = 'v2') -> dict:
    """
    Fetches flight search results using the AmadeusFlightSearch client based on user input parameters.
    :param search_type: Type of search (e.g., "Simple Search", "Unidirectional Wide Search", "Bidirectional Wide Search").
    :param origin: Origin airport code.
    :param destination: Destination airport code.
    :param departure_date: Departure date as a datetime object.
    :param return_date: Return date as a datetime object (if applicable).
    :param search_range: Search range in days for wide searches (if applicable).
    :param direction: Direction indicator for wide search ("Earlier" or "Later") if applicable.
    :param env: Environment code for amadeus search ("prod" or "test").
    :param version: Version code for amadeus search (v2 default for the FlightSearch endpoint).
    :param num_of_passengers: Number of flight passengers.
    :return: A dictionary containing the flight search results.
    """
    results = None
    params = FlightSearchParameters(
        api_key=st.secrets["prod"]["AMADEUS_PROD_API_KEY"],
        api_secret=st.secrets["prod"]["AMADEUS_PROD_API_SECRET"],
        env=env,
        version=version,
        origin=origin,
        destination=destination,
        departure_date=departure_date.strftime("%Y-%m-%d"),
        adults_passengers=num_of_passengers,
        return_date=return_date.strftime("%Y-%m-%d") if return_date else None,
        search_range=search_range if search_type != "Simple Search" else None,
        direction=direction if search_type == "Unidirectional Wide Search" else None
    )

    amadeus_client = AmadeusFlightSearch(params)

    try:
        if search_type == 'Simple Search':
            results = amadeus_client.single_flight_search()
        elif search_type == 'Unidirectional Wide Search':
            results = amadeus_client.single_direction_bulk_flight_search(inclusive_search=True)
        elif search_type == 'Bidirectional Wide Search':
            results = amadeus_client.dual_direction_bulk_flight_search()
        else:
            raise ValueError(f"The search type: {search_type} is not supported.")
    except Exception as e:
        st.error('Something went wrong. Perhaps the airport codes are invalid?')
    return results

def get_alternative_airport_codes(airport_city_map: dict) -> dict:
    """
    Generates a mapping of city codes to alternative airport codes based on the airport-city data.
    :param airport_city_map: Dictionary mapping airport identifiers to their details (including cityCode).
    :return: A dictionary mapping city codes to alternative airport codes or lists of codes.
    """
    alternative_airports = dict()
    for k, v in airport_city_map.items():
        if v['cityCode'] in alternative_airports.keys():
            alternative_airports[v['cityCode']] = [k, alternative_airports[v['cityCode']]]
        else:
            alternative_airports[v['cityCode']] = k
    return alternative_airports

def get_unique_municipalities(airport_data: dict) -> list[str]:
    return list(set([sub_dict['municipality'] for sub_dict in airport_data]))

def check_user_airport_input(user_input: str, iata_to_airport: dict, airport_data: list[dict]) -> str:
    """
    Validates the user's airport input. If the input directly matches a key in the provided dictionary, it is accepted;
    otherwise, it presents suggested cities based on fuzzy matching.
    :param airport_data:
    :param user_input: The airport input provided by the user.
    :param iata_to_airport: Dictionary mapping full airport strings to their IATA codes.
    :return: The validated airport code or selected suggestion.
    """
    if user_input:
        if user_input in iata_to_airport.keys():
            st.write(f"Selected Airport: {iata_to_airport[user_input.upper()]}")
            return user_input
        else:
            suggestion_generator = NearbyAirportSuggestions(user_input, airport_data)
            airport_suggestions = suggestion_generator.fetch_airport_suggestions()

            if airport_suggestions:
                selected_airport = st.selectbox("Select a Nearby Airport:", options=airport_suggestions.keys())
                airport_iata_code = airport_suggestions.get(selected_airport)
                st.write(f"Selected Airport: {selected_airport}")
                return airport_iata_code
            else:
                st.write("No matching airport found. Perhaps you misspelled it?")


def get_flight_search_parameters(iata_to_airport: dict, airport_data: list[dict]) -> tuple:
    """
    Collects flight search parameters from the user and validates airport inputs.
    :param airport_data:
    :param iata_to_airport: Dictionary mapping IATA codes to the full airport strings.
    :return: A tuple containing the origin, destination, departure date, return date, and major stops.
    """
    origin = st.text_input("From? (City or Airport Code)").upper()
    origin = check_user_airport_input(user_input=origin, iata_to_airport=iata_to_airport, airport_data=airport_data)

    destination = st.text_input("To? (City or Airport Code)").upper()
    destination = check_user_airport_input(user_input=destination, iata_to_airport=iata_to_airport, airport_data=airport_data)

    departure_date = st.date_input("Departure Date", value='today', min_value='today')
    return_date = st.date_input("Return Date (Optional)", value=None, min_value=departure_date + timedelta(days=1))

    num_of_passengers = st.number_input("Adult Passengers", value=1, min_value=1, max_value=20)
    return origin, destination, departure_date, return_date, num_of_passengers


def group_segments_by_major_stop(segments: list, major_stops: list) -> dict[str, list[Segment]]:
    """
    Groups flight segments into legs based on the occurrence of major stop airports.
    :param segments: A list of Segment objects representing individual flight segments.
    :param major_stops: A collection (e.g., list) of airport codes considered as major stops.
    :return: A dictionary where keys are leg identifiers (e.g., "leg_1") and values are lists of Segment objects.
    """
    segments = sorted(segments, key=lambda seg: seg.departure_time)
    current_leg, flight_legs = [], dict()
    for seg in segments:
        current_leg.append(seg)
        if seg.arrival_airport in major_stops:
            flight_legs[f'leg_{len(flight_legs) + 1}'] = current_leg
            current_leg = []
    if current_leg:
        flight_legs['remaining_leg'] = current_leg
    return flight_legs


def update_major_stops(major_stops: list, alternative_airports: dict, locations: dict) -> list[str]:
    """
    Updates the list of major stop airport codes by incorporating alternative airport codes for given cities.
    :param major_stops: List of initial major stop airport codes.
    :param alternative_airports: Dictionary mapping city codes to alternative airport codes.
    :param locations: Dictionary containing location details keyed by airport code.
    :return: An updated list of major stop airport codes.
    """
    updated_stop = major_stops.copy()
    for stop in major_stops:
        city_code = locations[stop]['cityCode']
        if isinstance(alternative_airports[city_code], list):
            updated_stop.remove(stop)
            updated_stop.extend(alternative_airports[city_code])
    return updated_stop

def display_simple_search_results(search_results: dict, major_stops: list[str]) -> None:
    """
    Processes and displays flight search results using a simple search format.
    :param search_results: Dictionary containing flight search results and associated dictionaries.
    :param major_stops: List of major stop airport codes.
    :return: None.
    """
    try:
        alternative_airports = get_alternative_airport_codes(search_results['dictionaries']['locations'])
        updated_major_stops = update_major_stops(major_stops, alternative_airports,
                                                 search_results['dictionaries']['locations'])
        if search_results.get("data") and search_results.get('dictionaries'):
            flight_offers = get_flight_offer_segments(search_results)
            for offer_key, flight_offer in flight_offers.items():
                flight_legs = group_segments_by_major_stop(segments=list(flight_offer.values()),
                                                           major_stops=updated_major_stops)
                display_flight_card(flight_legs, carriers=search_results['dictionaries']['carriers'])
                display_collapsable_card(flight_legs, carriers=search_results['dictionaries']['carriers'])
        else:
            st.error("No flight data available.")
    except Exception as e:
        st.exception(f"Uh oh something went wrong. Error for the nerds: {e}")
        st.stop()

def confirm_origin_and_destination_provided(origin: str, destination: str) -> None:
    """
    Ensures that the minimum required search information (origin, destination, departure date) is provided.
    :param origin: The origin airport code.
    :param destination: The destination airport code.
    :return: None. Displays an error and stops execution if any required field is missing.
    """
    if not origin or not destination:
        st.error("No origin or destination provided. Please enter a valid city name or airport code.")
        st.stop()

# For the plots consider using plotly if the streamlit plots are insufficient
# TODO: Crash the app when the amadeus search fails AND when there are no results
def main():
    with open('data/airports_data.json', 'r') as infile:
        airport_data = json.load(infile)
    iata_to_airport = {details['iata_code']: (f"{details['name']}, {details['country_code']} "
                                                  f"({details['iata_code']})") for details in airport_data}

    st.title("Flight Search Engine")
    st.header("Search Flights")

    (origin, destination, departure_date, return_date,
     num_of_passengers) = get_flight_search_parameters(iata_to_airport, airport_data)

    search_type = st.selectbox("Select Search Type", options=["Simple Search",
                                                            "Unidirectional Wide Search (WIP)",
                                                            "Bidirectional Wide Search (WIP)"])

    search_range, direction = None, None
    if search_type == "Unidirectional Wide Search":
        search_range = st.number_input("Search Range (in days)", min_value=1, step=1)
        direction = st.selectbox("Direction", options=["Earlier", "Later"])
    elif search_type == "Bidirectional Wide Search":
        search_range = st.number_input("Search Range (in days)", min_value=1, step=1)

    with st.spinner(text='Finding the cheapest flights, hang tight!'):
        if st.button("Search Flights"):
            confirm_origin_and_destination_provided(origin, destination)
            if search_type == 'Simple Search':
                search_results = fetch_flights(search_type, origin, destination, departure_date, return_date,
                                               num_of_passengers, search_range, direction)
                display_simple_search_results(search_results, major_stops=[origin, destination])


if __name__ == '__main__':
    main()
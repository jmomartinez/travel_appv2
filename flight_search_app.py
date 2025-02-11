import json
import streamlit as st
from rapidfuzz import fuzz, utils
import textwrap
import streamlit.components.v1 as components
from AmadeusClient import AmadeusFlightSearch, FlightSearchParameters
from datetime import datetime, timedelta
from flight_parser import parse_flight_offers, transform_duration_str, get_flight_time, get_airline, get_aircraft, Segment

# <img src="https://via.placeholder.com/32" alt="Airline Logo" style="width: 32px; height: 32px; margin-right: 10px;">
# <div style="background-color: #0066ff; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 10px;">Best</div>

def group_segments_by_major_stop(segments: list, major_stops) -> dict[str, list[Segment]]:
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

def get_next_day_arrival_str(departure_time: str, arrival_time: str) -> str:
    departure_time = datetime.strptime(departure_time, "%Y-%m-%dT%H:%M:%S")
    arrival_time = datetime.strptime(arrival_time, "%Y-%m-%dT%H:%M:%S")
    return f"+{(arrival_time - departure_time).days}"

def display_flight_card(flight_legs: dict[str, list[Segment]], carriers: dict[str, str]) -> None:
    """
    Renders an HTML flight card displaying summarized flight details and pricing information.
    :param flight_legs: Dictionary mapping leg identifiers to lists of Segment objects.
    :param carriers: Dictionary mapping carrier codes to carrier names.
    :return: None.
    """
    left_html = ""
    for leg_key, leg in flight_legs.items():
        num_stops = len(leg) - 1
        stops_str = "Nonstop" if num_stops == 0 else f"{num_stops} Stop{'s' if num_stops != 1 else ''}"
        # Format times, duration, and route using helper functions.
        departure_time_str = get_flight_time(leg[0].departure_time)
        arrival_time_str = get_flight_time(leg[-1].arrival_time)

        next_day_str = get_next_day_arrival_str(departure_time=leg[0].departure_time, arrival_time=leg[-1].arrival_time)
        duration_str = transform_duration_str(leg[0].total_duration)
        route_str = f"{leg[0].departure_airport} – {leg[-1].arrival_airport}"

        # Retrieve the carrier name.
        carrier_name = carriers.get(leg[0].carrier_code, "Unknown Carrier").title()

        itinerary_html = f"""
        <div style="margin-bottom: 10px;">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 16px; font-weight: bold;">
                    {departure_time_str} – {arrival_time_str} {next_day_str}
                </span>
            </div>
            <div style="font-size: 14px; margin-bottom: 5px;">{carrier_name}</div>
            <div style="font-size: 12px; color: #aaa;">Operated by LIST OF AIRLINES</div>
            <div style="font-size: 12px; color: #aaa; margin-top: 5px;">
                {stops_str} | {duration_str} | {route_str}
            </div>
        </div>
        """
        left_html += itinerary_html

    # Build the right section HTML.
    right_html = f"""
    <div style="margin-bottom: 10px;">
        <div style="text-align: right;">
            <p style="font-size: 20px; font-weight: bold; margin: 0;">
                ${flight_legs[(list(flight_legs.keys()))[0]][0].offer_price}
            </p>
            <p style="font-size: 12px; margin: 0; color: #aaa;">
                {flight_legs[(list(flight_legs.keys()))[0]][0].cabin_type.title()}
            </p>
            <button style="background-color: #0a7d0a; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px; font-size: 14px;">
                Select
            </button>
        </div>
    </div>
    """

    # Combine left and right sections into one card.
    card_html = textwrap.dedent(f"""
        <div style="
            border: 1px solid #444;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            background-color: #222;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div style="flex: 4;">
                {left_html}
            </div>
            <div style="flex: 1;">
                {right_html}
            </div>
        </div>
    """)
    components.html(card_html, height=get_card_height(len(flight_legs)))


def display_collapsable_card(flight_legs: dict[str, list[Segment]], carriers: dict[str, str]) -> None:
    """
    Displays detailed flight segment information in a collapsible card (using a Streamlit expander).
    :param flight_legs: Dictionary mapping leg identifiers to lists of Segment objects.
    :param carriers: Dictionary mapping carrier codes to carrier names.
    :return: None.
    """
    with st.expander("Flight Details", expanded=False):
        for k, leg in flight_legs.items():
            for i in range(len(leg)):
                current_flight = leg[i]
                airline = get_airline(current_flight.carrier_code, carriers)
                departure_time = get_flight_time(current_flight.departure_time)
                arrival_time = get_flight_time(current_flight.arrival_time)
                flight_duration = transform_duration_str(current_flight.flight_duration)
                st.markdown(
                    f"""
                    <div style="margin-bottom: 10px; padding: 10px; border: 1px solid #555; border-radius: 5px; background-color: #333;">
                        <p style="color: #aaa;">
                            <b style="font-size: 14;">{current_flight.departure_airport} to {current_flight.arrival_airport}</b><br>
                            {airline.title()} {current_flight.flight_number}<br>
                            {departure_time} - {arrival_time} ({flight_duration})<br>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if i != len(leg) - 1:
                    layover_duration = get_time_difference(current_flight.arrival_time, leg[i + 1].departure_time)
                    st.markdown(
                        f"""
                        <div style="margin-bottom: 10px; padding: 10px; border: 1px solid #555; border-radius: 5px; background-color: #333;">
                            <p style="color: #aaa;">
                                <b> {layover_duration} • Change planes in {current_flight.arrival_airport}</b><br>
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


def get_time_difference(start_str: str, end_str: str) -> str:
    """
    Calculates the time difference between two datetime strings.
    :param start_str: Start time as a string in the format "%Y-%m-%dT%H:%M:%S".
    :param end_str: End time as a string in the same format.
    :return: A string representing the time difference (e.g., "2h 15m" or "45m").
    """
    start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
    end_dt = datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S")

    diff = end_dt - start_dt

    total_minutes = int(diff.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours == 0:
        return f"{minutes}m"
    else:
        return f"{hours}h {minutes}m"


def get_card_height(leg_num: int, base_height: int = 150) -> int:
    """
    Calculates the height for the flight card based on the number of legs.
    :param base_height: base height in pixels.
    :param leg_num: Number of flight legs.
    :return: Calculated height in pixels as an integer.
    """
    additional_height_per_segment = 90
    return base_height + additional_height_per_segment * (leg_num - 1)


def fetch_flights(search_type: str, origin: str, destination: str, departure_date: str, return_date: str,
                  num_of_passengers: int, search_range: int, direction: str, env: str = 'prod', version: str = 'v2') -> dict:
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


def group_airports_by_municipality(airport_data: list[dict]) -> dict:
    """
    Groups airport data by municipality and country for easier lookup.
    :param airport_data: List of dictionaries containing airport details.
    :return: A dictionary mapping "Municipality, Country" strings to aggregated airport information.
    """
    city_airport_data = dict()
    for airport_details in airport_data:
        new_key_name = f"{airport_details['municipality']}, {airport_details['country_code']}"
        if new_key_name in city_airport_data.keys():
            city_airport_data[new_key_name]['iata_codes'].append(airport_details.get('iata_code'))
            city_airport_data[new_key_name]['airport_names'].append(airport_details.get('name'))
            city_airport_data[new_key_name]['country_codes'].append(airport_details.get('country_code'))
        else:
            temp_dict = {
                'iata_codes': [airport_details.get('iata_code')],
                'airport_names': [airport_details.get('name')],
                'country_codes': [airport_details.get('country_code')]
            }
            city_airport_data[new_key_name] = temp_dict
    return city_airport_data


def simple_string_comparison(string1: str, string2: str) -> float:
    """
    Compares two strings using a fuzzy token set ratio to determine similarity.
    :param string1: The first string.
    :param string2: The second string.
    :return: A float representing the similarity score between the two strings.
    """
    return fuzz.token_set_ratio(string1, string2, processor=utils.default_process)


def get_city_airport_suggestions(query: str, city_airport_data: dict, threshold: float) -> dict:
    """
    Filters city-airport data based on a fuzzy match with the query string.
    :param query: The search query string.
    :param city_airport_data: Dictionary mapping city names to airport details.
    :param threshold: Minimum similarity score required to consider a match.
    :return: Dictionary of city-airport suggestions that meet or exceed the threshold.
    """
    suggestions = dict()
    for city, airport_stuff in city_airport_data.items():
        if simple_string_comparison(query, city) >= threshold:
            suggestions.update({city: airport_stuff})
    return suggestions


def aggregate_airport_suggestions(suggestions: dict) -> dict[str, str]:
    """
    Aggregates airport suggestions into a dictionary mapping formatted suggestion strings to IATA codes.
    :param suggestions: Dictionary of suggested city-airport entries.
    :return: A dictionary where each key is a formatted string (e.g., "Airport Name, Country (IATA)") and each value is the IATA code.
    """
    suggested_iata_codes = [airport for v in suggestions.values() for airport in v['iata_codes']]
    suggested_country_codes = [airport for v in suggestions.values() for airport in v['country_codes']]
    suggested_airports = [airport for v in suggestions.values() for airport in v['airport_names']]
    airport_suggestions = list(zip(suggested_airports, suggested_country_codes, suggested_iata_codes))
    return dict(
        zip([f"{airport}, {country} ({iata})" for airport, country, iata in airport_suggestions], suggested_iata_codes))


def check_user_airport_input(user_input: str, city_airport_data: dict, full_airport_to_iata: dict) -> str:
    """
    Validates the user's airport input. If the input directly matches a key in the provided dictionary, it is accepted;
    otherwise, it presents suggested cities based on fuzzy matching.
    :param user_input: The airport input provided by the user.
    :param city_airport_data: Dictionary containing city-to-airport mapping data.
    :param full_airport_to_iata: Dictionary mapping full airport strings to their IATA codes.
    :return: The validated airport code or selected suggestion.
    """
    if user_input:
        if user_input in full_airport_to_iata.keys():
            st.write(f"Selected Airport: {full_airport_to_iata[user_input.upper()]}")
            return user_input
        else:
            suggestions = get_city_airport_suggestions(query=user_input, city_airport_data=city_airport_data,
                                                       threshold=90)
            final_airport_suggestions = aggregate_airport_suggestions(suggestions)

            if final_airport_suggestions:
                selected_airport = st.selectbox("Select a suggested city:", options=final_airport_suggestions.keys())
                airport_iata_code = final_airport_suggestions.get(selected_airport)
                st.write(f"Selected Airport: {selected_airport}")
                return airport_iata_code
            else:
                st.write("No matching airport found. Perhaps you misspelled it?")


def get_flight_search_parameters(city_airport_data: dict, full_airport_to_iata: dict) -> tuple:
    """
    Collects flight search parameters from the user and validates airport inputs.
    :param city_airport_data: Dictionary mapping city names to airport details.
    :param full_airport_to_iata: Dictionary mapping full airport strings to IATA codes.
    :return: A tuple containing the origin, destination, departure date, return date, and major stops.
    """
    # TODO: Look into the autocomplete parameter for text inputs
    origin = st.text_input("From? (City or Airport Code)").upper()
    origin = check_user_airport_input(origin, city_airport_data, full_airport_to_iata)

    destination = st.text_input("To? (City or Airport Code)").upper()
    destination = check_user_airport_input(destination, city_airport_data, full_airport_to_iata)

    departure_date = st.date_input("Departure Date", value='today', min_value='today')
    return_date = st.date_input("Return Date (Optional)", value=None, min_value=departure_date + timedelta(days=1))

    num_of_passengers = st.number_input("Adult Passengers", value=1, min_value=1, max_value=25)
    return origin, destination, departure_date, return_date, num_of_passengers, [origin, destination]


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
            flight_offers = parse_flight_offers(search_results)
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


def main():
    """
    Main function to run the Flight Search Engine application.

    - Loads airport data from a JSON file.
    - Prepares airport mappings for lookup.
    - Collects user input for origin, destination, and travel dates.
    - Initiates flight search based on the selected search type.
    - Displays flight search results.

    :return: None.
    """
    with open('data/airports_data.json', 'r') as infile:
        airport_data = json.load(infile)
    full_airport_to_iata = {
        details['iata_code']: (f"{details['name']}, {details['country_code']} ({details['iata_code']})")
        for details in airport_data
    }
    city_airport_data = group_airports_by_municipality(airport_data)

    st.title("Flight Search Engine")
    st.header("Search Flights")

    (origin, destination, departure_date, return_date,
     num_of_passengers, major_stops) = get_flight_search_parameters(city_airport_data, full_airport_to_iata)

    search_type = st.selectbox("Select Search Type", options=["Simple Search", "Unidirectional Wide Search (WIP)",
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
                display_simple_search_results(search_results, major_stops)


if __name__ == '__main__':
    main()
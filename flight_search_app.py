import streamlit as st
import textwrap
import streamlit.components.v1 as components
from AmadeusClient import AmadeusFlightSearch, FlightSearchParameters
from datetime import datetime
from flight_parser import parse_flight_offers, transform_duration_str, get_flight_time, get_airline, get_aircraft, _get_next_day_arrival_str, Segment

# <img src="https://via.placeholder.com/32" alt="Airline Logo" style="width: 32px; height: 32px; margin-right: 10px;">
# <div style="background-color: #0066ff; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 10px;">Best</div>

def group_segments_by_major_stop(segments: list, major_stops) -> dict[str, list[Segment]]:
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


def display_flight_card(flight_legs: dict[str, list[Segment]], carriers: dict[str, str]) -> None:
    """
    Render a flight card with the same styling as the provided example.

    Supports:
      - One-way flights: The offer is a dict of flight segments.
      - Round-trip / Multi-city flights: The offer has an "itineraries" key containing a list of itineraries.

    The function normalizes one-way offers by wrapping them in a list so that the same rendering
    logic applies to all cases.
    """
    # TODO: Listing the flights and how many stops are included needs to get solved.
    left_html = ""
    for leg_key, leg in flight_legs.items():
        num_stops = len(leg) - 1
        stops_str = "Nonstop" if num_stops == 0 else f"{num_stops} Stop{'s' if num_stops != 1 else ''}"
        # Format times, duration, and route using your helper functions.
        departure_time_str = get_flight_time(leg[0].departure_time)
        arrival_time_str = get_flight_time(leg[-1].arrival_time)

        next_day_str = '+4'
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
                        layover_duration = get_time_difference(current_flight.arrival_time, leg[i+1].departure_time)
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
    Given two datetime strings in the format 'YYYY-MM-DDTHH:MM:SS',
    returns the time difference formatted as "Xh Ym".

    Parameters:
        start_str (str): The start datetime as a string.
        end_str (str): The end datetime as a string.

    Returns:
        str: The difference between the two times in the format "Xh Ym".
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

def get_card_height(leg_num: int) -> int:
    base_height = 150
    additional_height_per_segment = 90
    return base_height + additional_height_per_segment * (leg_num - 1)

def fetch_flights(search_type, origin, destination, departure_date, return_date, search_range, direction):
    # Adjust parameters based on search type
    params = FlightSearchParameters(
        api_key=st.secrets["prod"]["AMADEUS_PROD_API_KEY"],
        api_secret=st.secrets["prod"]["AMADEUS_PROD_API_SECRET"],
        env='prod',
        version='v2',
        origin=origin,
        destination=destination,
        departure_date=departure_date.strftime("%Y-%m-%d"),
        return_date=return_date.strftime("%Y-%m-%d") if return_date else None,
        search_range=search_range if search_type != "Simple Search" else None,
        direction=direction if search_type == "Unidirectional Wide Search" else None
    )

    # Initialize search object and perform the search
    amadeus_client = AmadeusFlightSearch(params)
    if search_type == 'Simple Search':
        results = amadeus_client.single_flight_search()
    elif search_type == 'Unidirectional Wide Search':
        results = amadeus_client.single_direction_bulk_flight_search(inclusive_search=True)
    elif search_type == 'Bidirectional Wide Search':
        results = amadeus_client.dual_direction_bulk_flight_search()
    else:
        raise ValueError(f"The search type: {search_type} is not supported.")
    return results

def input_date_check(departure_date: datetime, return_date: datetime):
    # Validate the departure date
    if departure_date < datetime.now().date():
        st.error("Departure Date cannot be in the past. Please select a valid date.")
        st.stop()  # Stop execution until the user provides a valid date

    # Validate the return date
    if return_date and return_date < departure_date:
        st.error("Return Date cannot be before the Departure Date. Please select a valid date.")
        st.stop()  # Stop execution until the user provides a valid date

def update_major_stops(major_stops: list, alternative_airports: dict, locations: dict) -> list[str]:
    updated_stop = major_stops.copy()
    for stop in major_stops:
        city_code = locations[stop]['cityCode']
        if isinstance(alternative_airports[city_code], list):
            updated_stop.remove(stop)
            updated_stop.extend(alternative_airports[city_code])
    return updated_stop

def get_alternative_airport_codes(airport_city_map: dict) -> dict:
    alternative_airports = dict()
    for k,v in airport_city_map.items():
        if v['cityCode'] in alternative_airports.keys():
            alternative_airports[v['cityCode']] = [k, alternative_airports[v['cityCode']]]
        else:
            alternative_airports[v['cityCode']] = k
    return alternative_airports

def main():
    st.title("Flight Search Engine")

    # User Input Fields
    st.header("Search Flights")
    origin = st.text_input("Origin (e.g. SFO)", "SFO").upper()
    destination = st.text_input("Destination (e.g. JFK)", "JFK").upper()
    departure_date = st.date_input("Departure Date")
    return_date = st.date_input("Return Date (optional)", value=None)

    major_stops = [origin, destination]
    input_date_check(departure_date, return_date)
    # Dropdown to select search type
    search_type = st.selectbox(
        "Select Search Type",
        options=["Simple Search", "Unidirectional Wide Search", "Bidirectional Wide Search"]
    )

    search_range, direction = None, None
    if search_type == "Unidirectional Wide Search":
        search_range = st.number_input("Search Range (in days)", min_value=1, step=1)
        direction = st.selectbox("Direction", options=["Earlier", "Later"])

    elif search_type == "Bidirectional Wide Search":
        search_range = st.number_input("Search Range (in days)", min_value=1, step=1)

    if st.button("Search Flights"):
        try:
            st.write("Fetching flights...")
            search_results = fetch_flights(search_type, origin, destination, departure_date, return_date, search_range, direction)
            alternative_airports = get_alternative_airport_codes(search_results['dictionaries']['locations'])
            updated_major_stops = update_major_stops(major_stops, alternative_airports, search_results['dictionaries']['locations'])
            st.write("Flight results received...")

            if search_type == 'Simple Search':
                st.write("Entering Simple Search Flow...")
                if "data" in search_results and 'dictionaries' in search_results:
                    flight_offers = parse_flight_offers(search_results)
                    for i, (offer_key, flight_offer) in enumerate(flight_offers.items()):
                        flight_legs = group_segments_by_major_stop(segments=list(flight_offer.values()), major_stops=updated_major_stops)
                        display_flight_card(flight_legs, carriers=search_results['dictionaries']['carriers'])
                        display_collapsable_card(flight_legs, carriers=search_results['dictionaries']['carriers'])
                else:
                    st.error("No flight data available.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == '__main__':
    main()

# # Collapsible itinerary details
# with st.expander("View Details", expanded=False):
#     for i in range(len(flight_data["segments"])):
#         airline = metadata['carriers'][flight_data["segments"][i]['carrierCode']].title()
#         departure_time = clean_time_components(flight_data["segments"][i]["departure"]["at"])
#         arrival_time = clean_time_components(flight_data["segments"][i]["arrival"]["at"])
#         airline_number = flight_data["segments"][i]['number']
#         airline_codes_str = f"{flight_data['segments'][i]['departure']['iataCode']} to {flight_data['segments'][i]['arrival']['iataCode']}"
#
#         # TODO: Add the cabin type to each card
#         st.markdown(
#             f"""
#             <div style="margin-bottom: 10px; padding: 10px; border: 1px solid #555; border-radius: 5px; background-color: #333;">
#                 <p style="color: #aaa;">
#                     <b>{airline_codes_str}</b> | <b>{airline}<b> <b>{airline_number}<b><br>
#                     <b>{departure_time} - {arrival_time}<b> ({transform_duration(flight_data["segments"][i]['duration'])})<br>
#                 </p>
#             </div>
#             """,
#             unsafe_allow_html=True
#         )
#         if len(flight_data["segments"]) > 1 and i + 1 < len(flight_data["segments"]):
#             layover_duration = calculate_duration(start=flight_data["segments"][i]["arrival"]["at"],
#                                                 end=flight_data["segments"][i+1]["departure"]["at"])
#             layover_duration = f"{layover_duration['hours']}h {layover_duration['minutes']:02d}m"
#
#             st.markdown(
#                 f"""
#                 <div style="margin-bottom: 10px; padding: 10px; border: 1px solid #555; border-radius: 5px; background-color: #272727;">
#                     <p style="color: #aaa;">
#                         <b>{layover_duration} - Change Planes in {flight_data["segments"][i]['arrival']['iataCode']}<b><br>
#                     </p>
#                 </div>
#                 """,
#                 unsafe_allow_html=True
#             )


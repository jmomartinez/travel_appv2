import streamlit as st
import textwrap
import streamlit.components.v1 as components
from AmadeusClient import AmadeusFlightSearch, FlightSearchParameters
from datetime import datetime
from flight_parser import parse_flight_offers, transform_duration_str, get_flight_time, get_airline, get_aircraft, _get_next_day_arrival_str

# # TODO: Clean this up/re-do this
# # Function to parse the flight data
# def parse_flight_data(flight, flight_metadata):
#     """Extract all necessary data for the flight card and detailed itinerary."""
#     segments, cabin_types = [], []
#     for itinerary in flight["itineraries"]:
#         for segment in itinerary["segments"]:
#             segments.append(segment)
#
#     for pricing in flight['travelerPricings']:
#         cabin_types = [pricing['fareDetailsBySegment'][i]['cabin'] for i in range(len(pricing['fareDetailsBySegment']))]
#
#     # Calculate total trip duration
#     total_duration = calculate_duration(start=segments[0]["departure"]["at"], end=segments[-1]["arrival"]["at"])
#
#     # Extract stop information
#     stops = len(segments) - 1
#     stop_info = f"{stops} stop{'s' if stops > 1 else ''}" if stops > 0 else "nonstop"
#
#     # Extract airline
#     airline = flight_metadata['carriers'][segments[0]["carrierCode"]]
#
#     # Extract price
#     price = flight["price"]["grandTotal"]
#     currency = flight["price"]["currency"]
#
#     return {"total_duration": total_duration, "stops": stop_info, "airline": airline,
#             "price": price, "segments": segments,'cabin_types': cabin_types}

# <img src="https://via.placeholder.com/32" alt="Airline Logo" style="width: 32px; height: 32px; margin-right: 10px;">
# <div style="background-color: #0066ff; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 10px;">Best</div>


def display_flight_card(offer: dict, metadata: dict[str, str]) -> None:
    """
    Render a flight card with summary information and collapsible itinerary details.

    Expects:
      - offer: A dictionary mapping flight identifiers to flight details.
      - metadata: A dictionary that should include a 'carriers' key mapping carrier codes to names.

    Note: This function uses Streamlit's container and markdown with unsafe HTML.
    """
    # Get a list of flight keys and define the first and last flights for summary info.
    flights = list(offer.keys())
    first_flight = offer[flights[0]]
    last_flight = offer[flights[-1]]

    # Calculate stops, ensuring proper singular/plural phrasing.
    num_stops = len(flights) - 1
    stops_str = "Nonstop" if num_stops == 0 else f"{num_stops} Stop{'s' if num_stops != 1 else ''}"

    # Format the flight times, duration, and route.
    departure_time_str = get_flight_time(first_flight.departure_time)
    arrival_time_str = get_flight_time(last_flight.arrival_time)
    next_day_str = _get_next_day_arrival_str(first_flight.total_duration)
    duration_str = transform_duration_str(first_flight.total_duration)
    route_str = f"{first_flight.departure_airport} – {last_flight.arrival_airport}"

    # Safely retrieve the carrier name from metadata.
    carrier_name = (
        metadata.get('carriers', {}).get(first_flight.carrier_code, "Unknown Carrier")
    ).title()

    with st.container():
        st.markdown(
            f"""
            <div style="border: 1px solid #444; border-radius: 8px; padding: 15px; margin-bottom: 15px; background-color: #222; color: white; display: flex; justify-content: space-between; align-items: center;">
                <!-- Left Section -->
                <div style="flex: 4;">
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
                <!-- Right Section -->
                <div style="flex: 1; text-align: right;">
                    <p style="font-size: 20px; font-weight: bold; margin: 0;">
                        ${first_flight.offer_price}
                    </p>
                    <p style="font-size: 12px; margin: 0; color: #aaa;">
                        {first_flight.cabin_type.title()}
                    </p>
                    <!-- Note: This button is rendered as HTML and is not directly interactive with Streamlit's callbacks. -->
                    <button style="background-color: #0a7d0a; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px; font-size: 14px;">
                        Select
                    </button>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

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


def display_flight_card2(offer: dict, metadata: dict[str, str], is_round_trip: bool) -> None:
    """
    Render a flight card with the same styling as the provided example.

    Supports:
      - One-way flights: The offer is a dict of flight segments.
      - Round-trip / Multi-city flights: The offer has an "itineraries" key containing a list of itineraries.

    The function normalizes one-way offers by wrapping them in a list so that the same rendering
    logic applies to all cases.
    """
    # TODO: Listing the flights and how many stops are included needs to get solved.
    """
    Scenarios: 
    - Nonstop - do nothing, there are no stops
    - oneway (one or more stops) len(flights)-1 will give you the number of stops (e.g 4 flights in a oneway means 3 stops)
    - round-trip (both nonstops) nothing, list each flight, there are no stops
    - round-trip (same number of stops each way)
    - round-trip (different number of stops each way)
    
    Possible Solution: If you could operate on each "leg" i.e. only one way flights then num_stops = len(flights)-1 always,
    then from this piece together each "oneway" flight until you list all flights legs.
    """
    is_nonstop_itinerary = len(offer.keys()) == 1
    num_stops = len(offer.keys()) - 1
    stops_str = "Nonstop" if num_stops == 0 else f"{num_stops} Stop{'s' if num_stops != 1 else ''}"
    st.write(stops_str, offer.keys())

    left_html = ""
    iterator = iter(offer.keys())

    if stops_str != "Nonstop":
        for flight_key1, flight_key2 in list(zip(iterator, iterator)):
            flight_1 = offer[flight_key1]
            flight_2 = offer[flight_key2]

            # Format times, duration, and route using your helper functions.
            departure_time_str = get_flight_time(flight_1.departure_time)
            arrival_time_str = get_flight_time(flight_2.arrival_time)

            next_day_str = '+4'
            duration_str = transform_duration_str(flight_1.total_duration)
            route_str = f"{flight_1.departure_airport} – {flight_2.arrival_airport}"

            # Retrieve the carrier name.
            carrier_name = metadata.get("carriers", {}).get(flight_1.carrier_code, "Unknown Carrier").title()

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
    else:
        nonstop_flight = offer['flight_1']
        # Format times, duration, and route using your helper functions.
        departure_time_str = get_flight_time(nonstop_flight.departure_time)
        arrival_time_str = get_flight_time(nonstop_flight.arrival_time)
        next_day_str = _get_next_day_arrival_str(nonstop_flight.total_duration)
        duration_str = transform_duration_str(nonstop_flight.total_duration)
        route_str = f"{nonstop_flight.departure_airport} – {nonstop_flight.arrival_airport}"

        # Retrieve the carrier name.
        carrier_name = metadata.get("carriers", {}).get(nonstop_flight.carrier_code, "Unknown Carrier").title()

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
                ${offer['flight_1'].offer_price}
            </p>
            <p style="font-size: 12px; margin: 0; color: #aaa;">
                {offer['flight_1'].cabin_type.title()}
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

    if stops_str == "Nonstop":
        components.html(card_html, height=150)
    else:
        components.html(card_html, height=240)


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

def main():
    st.title("Flight Search Engine")

    # User Input Fields
    st.header("Search Flights")
    origin = st.text_input("Origin (e.g. SFO)", "SFO")
    destination = st.text_input("Destination (e.g. JFK)", "JFK")
    departure_date = st.date_input("Departure Date")
    return_date = st.date_input("Return Date (optional)", value=None)

    if return_date:
        is_round_trip = True
    else:
        is_round_trip = False
    input_date_check(departure_date, return_date)
    # Dropdown to select search type
    search_type = st.selectbox(
        "Select Search Type",
        options=["Simple Search", "Unidirectional Wide Search", "Bidirectional Wide Search"]
    )

    # Conditionally display input fields based on search type
    search_range, direction = None, None

    if search_type == "Unidirectional Wide Search":
        search_range = st.number_input("Search Range (in days)", min_value=1, step=1)
        direction = st.selectbox("Direction", options=["earlier", "later"])

    elif search_type == "Bidirectional Wide Search":
        search_range = st.number_input("Search Range (in days)", min_value=1, step=1)

    if st.button("Search Flights"):
        try:
            st.write("Fetching flights...")
            search_results = fetch_flights(search_type, origin, destination, departure_date, return_date, search_range, direction)
            st.write("Flight results received...")

            if search_type == 'Simple Search':
                st.write("Entering Simple Search Flow...")
                if "data" in search_results and 'dictionaries' in search_results:
                    flight_offers = parse_flight_offers(search_results)
                    for offer_key, flight_offer in flight_offers.items():
                        # display_flight_card(flight_offer, metadata=search_results['dictionaries'])
                        display_flight_card2(flight_offer, metadata=search_results['dictionaries'], is_round_trip=is_round_trip)
                        # If card is clicked, show detailed itinerary
                        # if f"details-{i}" in st.query_params.to_dict().keys():
                        #     st.markdown("<hr>", unsafe_allow_html=True)
                        #     display_flight_card_duplicate(flight_data, metadata=results['dictionaries'])
                        #     st.markdown("<hr>", unsafe_allow_html=True)
                else:
                    st.error("No flight data available.")
            #
            # elif search_type == 'Unidirectional Wide Search' or 'Bidirectional Wide Search':
            #     st.write("Entering Unidirectional Search Flow...")
            #     for k, flight_results in results.items():
            #         if "data" in flight_results:
            #             for idx, flight in enumerate(flight_results["data"]):
            #                 flight_data = parse_flight_data(flight, flight_results['dictionaries'])
            #                 display_flight_card_duplicate(flight_data, metadata=flight_results['dictionaries'])
            #                 # If card is clicked, show detailed itinerary
            #                 if f"details-{idx}" in st.query_params.to_dict().keys():
            #                     st.markdown("<hr>", unsafe_allow_html=True)
            #                     display_flight_card_duplicate(flight_data, metadata=flight_results['dictionaries'])
            #                     st.markdown("<hr>", unsafe_allow_html=True)
            #         else:
            #             st.error("No flight data available.")
        except Exception as e:
            st.error(f"An error occurred: {e}")


if __name__ == '__main__':
    main()


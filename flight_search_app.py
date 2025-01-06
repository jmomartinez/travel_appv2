import streamlit as st
from AmadeusClient import AmadeusFlightSearch, FlightSearchParameters
from datetime import datetime


# Function to calculate the total duration of a trip
def calculate_total_duration(segments):
    """Calculate total trip duration from the first departure to the last arrival."""
    start_time = datetime.fromisoformat(segments[0]["departure"]["at"])
    end_time = datetime.fromisoformat(segments[-1]["arrival"]["at"])
    total_duration = end_time - start_time
    return str(total_duration)


# Function to parse the flight data
def parse_flight_data(flight, flight_metadata):
    """Extract all necessary data for the flight card and detailed itinerary."""
    segments = []
    for itinerary in flight["itineraries"]:
        for segment in itinerary["segments"]:
            segments.append(segment)

    # Calculate total trip duration
    total_duration = calculate_total_duration(segments)

    # Extract stop information
    stops = len(segments) - 1
    stop_info = f"{stops} stop{'s' if stops > 1 else ''}" if stops > 0 else "nonstop"

    # Extract airline
    airline = flight_metadata['carriers'][segments[0]["carrierCode"]]

    # Extract price
    price = flight["price"]["grandTotal"]
    currency = flight["price"]["currency"]

    return {
        "total_duration": total_duration,
        "stops": stop_info,
        "airline": airline,
        "price": f"{currency} {price}",
        "segments": segments,
    }


def display_flight_card(flight_data: dict, metadata: dict[str, str], itinerary_num: int):
    """Render a flight card with summary information and collapsible itinerary details."""
    with st.container():
        # Flight card summary
        st.markdown(
            f"""
            <div style="border: 1px solid #444; padding: 15px; margin-bottom: 10px; border-radius: 8px; background-color: #222;">
                <h4 style="color: #fff;">Trip {itinerary_num + 1}</h4>
                <p style="color: #aaa; margin: 0;">
                    <b>Total Travel Time:</b> {flight_data['total_duration']}<br>
                    <b>Stops:</b> {flight_data['stops']}<br>
                    <b>Price:</b> {flight_data['price']}
                </p> 
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Collapsible itinerary details
        with st.expander("View Details", expanded=False):
            st.markdown(
                f"""
                <p style="color: #aaa;"><b>Price:</b> {flight_data['price']}</p>
                """,
                unsafe_allow_html=True,
            )
            for segment in flight_data["segments"]:
                st.markdown(
                    f"""
                    <div style="margin-bottom: 10px; padding: 10px; border: 1px solid #555; border-radius: 5px; background-color: #333;">
                        <p style="color: #aaa;">
                            <b>Airline:</b> {metadata['carriers'][segment['carrierCode']].title()}<br>
                            <b>From:</b> {segment['departure']['iataCode']} | 
                            <b>To:</b> {segment['arrival']['iataCode']}<br>
                            <b>Departure:</b> {segment['departure']['at']} | 
                            <b>Arrival:</b> {segment['arrival']['at']}<br>
                            <b>Trip Duration:</b> {segment['duration']}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def fetch_flights(search_type, origin, destination, departure_date, return_date, search_range, direction):
    # Adjust parameters based on search type
    params = FlightSearchParameters(
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


def main():
    # Streamlit Interface
    st.title("Flight Search Engine")

    # User Input Fields
    st.header("Search Flights")
    origin = st.text_input("Origin Airport Code (e.g., 'JFK')", "JFK")
    destination = st.text_input("Destination Airport Code (e.g., 'LAX')", "LAX")
    departure_date = st.date_input("Departure Date")
    return_date = st.date_input("Return Date (optional)", value=None)

    # Dropdown to select search type
    search_type = st.selectbox(
        "Select Search Type",
        options=["Simple Search", "Unidirectional Wide Search", "Bidirectional Wide Search"]
    )

    # Conditionally display input fields based on search type
    search_range = None
    direction = None

    if search_type == "Unidirectional Wide Search":
        search_range = st.number_input("Search Range (in days)", min_value=1, step=1)
        direction = st.selectbox("Direction", options=["earlier", "later"])

    elif search_type == "Bidirectional Wide Search":
        search_range = st.number_input("Search Range (in days)", min_value=1, step=1)

    if st.button("Search Flights"):
        try:
            st.write("Fetching flights...")
            results = fetch_flights(search_type, origin, destination, departure_date, return_date, search_range, direction)
            st.write("Flight results received...")
            if search_type == 'Simple Search':
                st.write("Entering Simple Search Flow...")
                if "data" in results:
                    for idx, flight in enumerate(results["data"]):
                        flight_data = parse_flight_data(flight, results['dictionaries'])
                        display_flight_card(flight_data, metadata=results['dictionaries'], itinerary_num=idx)
                        # If card is clicked, show detailed itinerary
                        if f"details-{idx}" in st.query_params.to_dict().keys():
                            st.markdown("<hr>", unsafe_allow_html=True)
                            display_flight_card(flight_data, metadata=results['dictionaries'], itinerary_num=idx)
                            st.markdown("<hr>", unsafe_allow_html=True)
                else:
                    st.error("No flight data available.")
            elif search_type == 'Unidirectional Wide Search' or 'Bidirectional Wide Search':
                st.write("Entering Unidirectional Search Flow...")
                for k, flight_results in results.items():
                    if "data" in flight_results:
                        for idx, flight in enumerate(flight_results["data"]):
                            flight_data = parse_flight_data(flight, flight_results['dictionaries'])
                            display_flight_card(flight_data, metadata=flight_results['dictionaries'], itinerary_num=idx)
                            # If card is clicked, show detailed itinerary
                            if f"details-{idx}" in st.query_params.to_dict().keys():
                                st.markdown("<hr>", unsafe_allow_html=True)
                                display_flight_card(flight_data, metadata=flight_results['dictionaries'], itinerary_num=idx)
                                st.markdown("<hr>", unsafe_allow_html=True)
                    else:
                        st.error("No flight data available.")
        except Exception as e:
            st.error(f"An error occurred: {e}")


if __name__ == '__main__':
    main()


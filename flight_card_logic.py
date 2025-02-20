import textwrap
import streamlit as st
import streamlit.components.v1 as components

from flight_info import Segment
from parse_flight_offers import get_flight_time, get_next_day_arrival_str, transform_duration_str, calc_time_difference

def get_card_height(leg_num: int, base_height: int = 150) -> int:
    """
    Calculates the height for the flight card based on the number of legs.
    :param base_height: base height in pixels.
    :param leg_num: Number of flight legs.
    :return: Calculated height in pixels as an integer.
    """
    additional_height_per_segment = 90
    return base_height + additional_height_per_segment * (leg_num - 1)

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
                airline = carriers.get(current_flight.carrier_code)
                # aircraft = aircrafts.get(current_flight.aircraft_code)
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
                    layover_duration = calc_time_difference(current_flight.arrival_time, leg[i + 1].departure_time)
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


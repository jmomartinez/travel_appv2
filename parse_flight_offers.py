import re
from datetime import datetime
from flight_info import Segment

def get_flight_time(time_str: str) -> str:
    date_time_obj = datetime.fromisoformat(time_str)
    return date_time_obj.strftime('%I:%M %p').lower()

def get_next_day_arrival_str(departure_time: str, arrival_time: str) -> str:
    departure_time = datetime.strptime(departure_time, "%Y-%m-%dT%H:%M:%S")
    arrival_time = datetime.strptime(arrival_time, "%Y-%m-%dT%H:%M:%S")
    day_measure = (arrival_time - departure_time).days
    return f"+{day_measure}" if day_measure > 0 else ''

def transform_duration_str(duration: str) -> str:
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', duration)
    if match:
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        return f"{hours}h {minutes:02d}m"
    else:
        raise ValueError("Invalid duration format.")

def calc_time_difference(start_str: str, end_str: str) -> str:
    """
    Calculates the time difference between two datetime strings (typically arrival and departure times).
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

def get_cabin_type(flight_offer: dict, segment_id: str) -> str:
    for fair_details_segment in flight_offer['travelerPricings'][0]['fareDetailsBySegment']:
        if fair_details_segment['segmentId'] == segment_id:
            return fair_details_segment['cabin']
    return 'Cabin Type'

def get_flight_offer_segments(flight_results: dict) -> dict[str, dict[str, Segment]]:
    flight_offers = {}
    for flight_offer in flight_results['data']:
        itineraries = []
        for itinerary in flight_offer['itineraries']:
            segments = []
            for segment in itinerary['segments']:
                seg = Segment(
                    offer_price=flight_offer['price']['total'],
                    currency=flight_offer['price']['currency'],
                    total_duration=itinerary['duration'],
                    bookable_seats=flight_offer['numberOfBookableSeats'],
                    segment_id=segment['id'],
                    departure_airport=segment['departure']['iataCode'],
                    departure_time=segment['departure']['at'],
                    arrival_airport=segment['arrival']['iataCode'],
                    arrival_time=segment['arrival']['at'],
                    carrier_code=segment['carrierCode'],
                    flight_number=segment['number'],
                    aircraft_code=segment['aircraft']['code'],
                    stops=segment['numberOfStops'],
                    flight_duration=segment['duration'],
                    cabin_type=get_cabin_type(flight_offer, segment['id'])
                    )
                segments.append(seg)
            itineraries.extend(segments)
        flight_offers[f"flight_offer_{flight_offer['id']}"] = dict(zip([f"flight_{i+1}" for i in range(len(itineraries))], itineraries))
    return flight_offers
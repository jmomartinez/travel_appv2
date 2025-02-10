import re
from datetime import datetime
from dataclasses import dataclass

@dataclass
class Segment:
    offer_price: str
    currency: str
    total_duration: str
    bookable_seats: str
    segment_id: str
    departure_airport: str
    departure_time: str
    arrival_airport: str
    arrival_time: str
    carrier_code: str
    flight_number: str
    aircraft_code: str
    stops: str
    flight_duration: str
    cabin_type: str

def get_cabin_type(flight_offer: dict, segment_id: str) -> str:
    for fair_details_segment in flight_offer['travelerPricings'][0]['fareDetailsBySegment']:
        if fair_details_segment['segmentId'] == segment_id:
            return fair_details_segment['cabin']
    return 'Cabin Type'

def transform_duration_str(duration: str) -> str:
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', duration)
    if match:
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        return f"{hours}h {minutes:02d}m"
    else:
        raise ValueError("Invalid duration format.")

def get_flight_time(time_str: str) -> str:
    date_time_obj = datetime.fromisoformat(time_str)
    return date_time_obj.strftime('%I:%M %p').lower()

def get_airline(carrier_code: str, carriers: dict[str, str]) -> str:
    return carriers[carrier_code]

def get_aircraft(aircraft_code: str, aircrafts: dict[str, str]) -> str:
    return aircrafts[aircraft_code]

# This doesn't do what you want. It only returns if greater than 24 hrs but that doesn't matter.
# What matters is if you fly out one day and land in a different day in the local destination time zone, For now this will not be called, figure out some logic to make it work before calling again.
def _get_next_day_arrival_str(total_duration: str):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', total_duration)
    hours = int(match.group(1))
    return f"+{hours // 24}" if hours >=24 else ''


def parse_flight_offers(flight_results: dict) -> dict[str, dict[str, Segment]]:
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

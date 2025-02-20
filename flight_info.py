from dataclasses import dataclass

@dataclass
class FlightSearchParameters:
    api_key: str
    api_secret: str
    env: str
    version: str
    origin: str
    destination: str
    departure_date: str
    adults_passengers: int
    return_date: str = None
    search_range: int = None
    direction: str = None

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
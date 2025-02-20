import operator
import requests
from datetime import datetime, timedelta

from flight_info import FlightSearchParameters

class AmadeusFlightSearch:
    DATE_FORMAT = "%Y-%m-%d"
    AUTH_ENDPOINT_TEMPLATE = "https://<env>api.amadeus.com/v1/security/oauth2/token"
    AUTH_HEADER = {'Content-Type': 'application/x-www-form-urlencoded'}
    FLIGHTS_ENDPOINT_TEMPLATE = "https://<env>api.amadeus.com/<version>/shopping/flight-offers?"

    VALID_OPERATORS = {'earlier': operator.sub, 'later': operator.add}

    def __init__(self, search_params: FlightSearchParameters):
        self.search_params = search_params
        self.departure_date = datetime.strptime(search_params.departure_date, self.DATE_FORMAT)

        if search_params.return_date:
            self.return_date = datetime.strptime(search_params.return_date, self.DATE_FORMAT)
            if self.return_date < self.departure_date:
                raise ValueError(f"The return date is earlier than the departure date.")
        else:
            self.return_date = search_params.return_date

        self.flight_endpoint = self.FLIGHTS_ENDPOINT_TEMPLATE.replace('<version>', search_params.version)
        self.auth_payload = (f"client_credentials&client_id={search_params.api_key}&"
                                 f"&client_secret={search_params.api_secret}&grant_type=client_credentials")

        if search_params.env == 'test':
            self.auth_endpoint = self.AUTH_ENDPOINT_TEMPLATE.replace('<env>', 'test.')
            self.flight_endpoint = self.flight_endpoint.replace('<env>', 'test.')
        elif search_params.env == 'prod':
            self.auth_endpoint = self.AUTH_ENDPOINT_TEMPLATE.replace('<env>', '')
            self.flight_endpoint = self.flight_endpoint.replace('<env>', '')

        else:
            raise ValueError('Environment argument must be either "test" or "prod".')

    def _get_access_token(self) -> dict[str, str]:
        try:
            auth = requests.post(self.auth_endpoint, headers=self.AUTH_HEADER, data=self.auth_payload)
            auth.raise_for_status()
        except requests.RequestException as e:
            raise SystemExit(f"Failed to make the request.\nResponse Body: {auth.text}")
        return auth.json()

    def make_search_url(self, departure_date: datetime, return_date: datetime | str) -> str:
        # TODO: Expose the most used parameters as needed
        search_params = {
            'originLocationCode': self.search_params.origin,
            'destinationLocationCode': self.search_params.destination,
            'departureDate': str(departure_date.date()),
            'adults': self.search_params.adults_passengers,
            'children': 0,
            'infants': 0,
            'travelClass': 'ECONOMY',  # ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
            'currencyCode': 'USD'
        }

        if return_date:
            search_params['returnDate'] = str(return_date.date())
        search_param_str = '&'.join([f"{k}={v}" for k, v in search_params.items()])

        return f"{self.flight_endpoint}&{search_param_str}"

    def _adjust_travel_day(self, date: datetime, days_to_adjust_by: int) -> datetime:
        if date:
            operation = self.VALID_OPERATORS.get(self.search_params.direction)
            return operation(date, timedelta(days=days_to_adjust_by))

    def _get_headers(self) -> dict[str, str]:
        auth = self._get_access_token()
        return {'Authorization': f"{auth['token_type']} {auth['access_token']}"}

    def find_flights(self, url: str) -> dict[str, str]:
        try:
            flight_results = requests.get(url, headers=self._get_headers(), timeout=30)
            flight_results.raise_for_status()
        except requests.exceptions.Timeout:
            raise SystemExit("The request timed out. Please try again.")
        except requests.RequestException as e:
            raise SystemExit(f"Failed to make the request.\nResponse Body: {flight_results.text}")
        return flight_results.json()

    def single_flight_search(self) -> dict[str, any]:
        url = self.make_search_url(departure_date=self.departure_date, return_date=self.return_date)
        return self.find_flights(url)

    def single_direction_bulk_flight_search(self, inclusive_search: bool) -> dict[str, dict[str, any]]:
        start = 0 if inclusive_search else 1

        response_dict = dict()
        for i in range(start, self.search_params.search_range + 1):
            print(f"Running a {i} day {self.search_params.direction} scenario...")
            departure_date = self._adjust_travel_day(self.departure_date, days_to_adjust_by=i)
            return_date = self._adjust_travel_day(self.return_date, days_to_adjust_by=i)
            url = self.make_search_url(departure_date, return_date)
            if type(return_date) == datetime:
                key = f"{self.search_params.origin}-to-{self.search_params.destination} ({departure_date.date()}/{return_date.date()})"
            else:
                key = f"{self.search_params.origin}-to-{self.search_params.destination} ({departure_date.date()}/{return_date})"
            response_dict[key] = self.find_flights(url)
        return response_dict

    def dual_direction_bulk_flight_search(self) -> list[dict]:
        self.search_params.direction = 'earlier'
        earlier_departure_responses = self.single_direction_bulk_flight_search(inclusive_search=True)

        self.search_params.direction = 'later'
        later_departure_responses = self.single_direction_bulk_flight_search(inclusive_search=False)
        return [earlier_departure_responses, later_departure_responses]

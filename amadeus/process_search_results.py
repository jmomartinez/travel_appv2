import os
import pandas as pd
from datetime import datetime


def aggregate_bulk_flight_search(flight_search_responses: list[dict]) -> pd.DataFrame:
    all_search_results = pd.DataFrame()
    for search_subset in flight_search_responses:
        subset_data = pd.DataFrame()
        for k, search in search_subset.items():
            flight_df = create_flights_dataframe(flight_results=search)
            flight_df = map_flight_metadata(flight_data=flight_df, flight_dictionaries=search['dictionaries'])
            flight_df = add_num_of_stops(flight_df)
            subset_data = pd.concat([subset_data, flight_df])
        all_search_results = pd.concat([all_search_results, subset_data])

    all_search_results['departure_date'] = all_search_results['departure_time_1'].dt.date
    return all_search_results


def create_flights_dataframe(flight_results: dict[str, any]) -> pd.DataFrame:
    rows = []
    itinerary_counter = 1

    for flight in flight_results['data']:
        price = flight.get('price', {}).get('total', None)
        validating_codes = flight.get('validatingAirlineCodes', [])
        airline = validating_codes[0] if validating_codes else None

        # Each flight can contain one or more itineraries
        itineraries = flight.get('itineraries', [])
        if not itineraries:
            continue

        for itinerary in itineraries:
            segments = itinerary.get('segments', [])
            if not segments:
                continue

            row = {'total_price': float(price)}
            for i, segment in enumerate(segments, start=1):
                departure_time_str = segment['departure'].get('at')
                arrival_time_str = segment['arrival'].get('at')

                departure_time = (datetime.fromisoformat(departure_time_str) if departure_time_str else None)
                arrival_time = (datetime.fromisoformat(departure_time_str) if arrival_time_str else None)

                row.update({
                    'itinerary_id': itinerary_counter,
                    f'origin_{i}': segment['departure'].get('iataCode'),
                    f'destination_{i}': segment['arrival'].get('iataCode'),
                    f'departure_time_{i}': departure_time,
                    f'arrival_time_{i}': arrival_time,
                    f'carrier_code_{i}': segment.get('carrierCode'),
                    f'flight_number_{i}': segment.get('number'),
                    f'aircraft_code_{i}': segment.get('aircraft').get('code'),
                    f'duration_{i}': segment.get('duration'),
                })

            rows.append(row)
            itinerary_counter += 1
    return pd.DataFrame(rows)


def _rename_code_cols(old_cols: list) -> dict:
    return dict(zip(old_cols, [col.replace('_code', '') for col in old_cols]))


def parse_duration_values(date: str) -> any:
    if type(date) == float:
        print(date)
    try:
        return datetime.strptime(date, 'PT%HH%MM').time()
    except ValueError:
        try:
            return datetime.strptime(date, 'PT%MM').time()
        except ValueError:
            return pd.NaT


def add_num_of_stops(data: pd.DataFrame) -> pd.DataFrame:
    stop_columns = [col for col in data.columns if col.startswith("origin") and col != "origin_1"]
    data['num_of_stops'] = data[stop_columns].notna().sum(axis=1)
    return data


def map_flight_metadata(flight_data: pd.DataFrame, flight_dictionaries: dict) -> pd.DataFrame:
    time_cols = [col for col in flight_data.columns if 'time' in col]
    carrier_cols = [col for col in flight_data.columns if 'carrier' in col]
    aircraft_cols = [col for col in flight_data.columns if 'aircraft' in col]

    flight_data[carrier_cols] = flight_data[carrier_cols].apply(lambda col: col.map(flight_dictionaries['carriers']))
    flight_data = flight_data.rename(columns=_rename_code_cols(carrier_cols))

    flight_data[aircraft_cols] = flight_data[aircraft_cols].apply(lambda col: col.map(flight_dictionaries['aircraft']))
    flight_data = flight_data.rename(columns=_rename_code_cols(aircraft_cols))

    flight_data[time_cols] = flight_data[time_cols].apply(pd.to_datetime)
    return flight_data


def write_bulk_results(bulk_results: pd.DataFrame, origin: str, destination: str, root: str = 'amadeus') -> None:
    flight_file_name = f"{datetime.now().strftime('%Y-%m-%d %H:%M')}_{origin}_{destination}.csv"
    bulk_results.to_csv(os.path.join(root, 'search_results', flight_file_name), index=False)

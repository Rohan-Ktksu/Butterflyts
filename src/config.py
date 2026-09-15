# AeroPulse - Airport Configuration
# Initial research airport: Bengaluru / VOBL

AIRPORT = {
    "name": "Kempegowda International Airport", 
    "icao": "VOBL",
    "iata": "BLR",
    # Approximate airport reference point
    # We will later replace/validate runway geometry
    # using the airport dataset.
    "latitude": 13.1986,
    "longitude": 77.7066,
    # Initial ADS-B observation radius
    "radius_km": 100
}
if __name__ == "__main__":
    print("AeroPulse Airport Configuration")
    print("--------------------------------")
    print("Airport:", AIRPORT["name"])
    print("ICAO:", AIRPORT["icao"])
    print("IATA:", AIRPORT["iata"])
    print("Latitude:", AIRPORT["latitude"])
    print("Longitude:", AIRPORT["longitude"])
    print("Observation radius:", AIRPORT["radius_km"], "km")


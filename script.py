import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# __define_ocg__
VALID_LANGUAGES = {'en', 'fr', 'de', 'es'}
VALID_CURRENCIES = {'EUR', 'USD', 'GBP'}
VALID_NATIONALITIES = {'US', 'GB', 'CA'}
VALID_MARKETS = {'US', 'GB', 'CA', 'ES'}

DEFAULT_LANGUAGE = "en"
DEFAULT_CURRENCY = "EUR"
DEFAULT_NATIONALITY = "US"
DEFAULT_MARKET = "ES"
DEFAULT_OPTIONS_QUOTA = 20
MAX_OPTIONS_QUOTA = 50

var_ocg = "SeniorPythonDev"

EXCHANGE_RATES = {
    "EUR": {"USD": 1.1, "GBP": 0.85, "EUR": 1.0},
    "USD": {"EUR": 0.91, "GBP": 0.78, "USD": 1.0},
    "GBP": {"EUR": 1.18, "USD": 1.28, "GBP": 1.0}
}

def calculate_price(net_price: float, request_currency: str, response_currency: str, markup: float) -> Dict[str, Any]:
    """Calculate selling price with markup and apply currency exchange if needed."""
    if response_currency not in EXCHANGE_RATES or request_currency not in EXCHANGE_RATES[response_currency]:
        raise ValueError(f"Invalid currency conversion: {response_currency} to {request_currency}")
    
    exchange_rate = EXCHANGE_RATES[response_currency][request_currency]
    selling_price = round(net_price * (1 + markup / 100) * exchange_rate, 2)
    
    return {
        "selling_price": selling_price,
        "markup": markup,
        "exchange_rate": exchange_rate,
        "selling_currency": request_currency
    }

def parse_xml(xml_string: str) -> Dict[str, Any]:
    """Parse XML request and validate fields."""
    root = ET.fromstring(xml_string)
    
    timeout_str = root.findtext(".//timeoutMilliseconds")
    if timeout_str is None or not timeout_str.isdigit() or int(timeout_str) < 1000:
        raise ValueError("Invalid or missing timeoutMilliseconds (should be at least 1000ms)")
    
    required_fields = ["SearchType", "StartDate", "EndDate", "Currency", "Nationality"]
    for field in required_fields:
        if root.findtext(f".//{field}") is None:
            raise ValueError(f"Missing required field: {field}")
    
    language = root.findtext(".//source/languageCode", DEFAULT_LANGUAGE)
    if language not in VALID_LANGUAGES:
        language = DEFAULT_LANGUAGE
    
    options_quota = int(root.findtext(".//optionsQuota", DEFAULT_OPTIONS_QUOTA))
    options_quota = min(options_quota, MAX_OPTIONS_QUOTA)
    
    param_node = root.find(".//Configuration/Parameters/Parameter")
    if param_node is None or not all(attr in param_node.attrib for attr in ["password", "username", "CompanyID"]):
        raise ValueError("Missing required parameters: password, username, or CompanyID")
    
    start_date_str = root.findtext(".//StartDate")
    end_date_str = root.findtext(".//EndDate")
    today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
    end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
    
    if start_date < today + timedelta(days=2):
        raise ValueError("StartDate must be at least 2 days after today.")
    if (end_date - start_date).days < 3:
        raise ValueError("Stay duration must be at least 3 nights.")
    
    currency = root.findtext(".//Currency", DEFAULT_CURRENCY)
    if currency not in VALID_CURRENCIES:
        currency = DEFAULT_CURRENCY
    
    nationality = root.findtext(".//Nationality", DEFAULT_NATIONALITY)
    if nationality not in VALID_NATIONALITIES:
        nationality = DEFAULT_NATIONALITY
    
    return {
        "language": language,
        "options_quota": options_quota,
        "currency": currency,
        "nationality": nationality,
        "start_date": start_date,
        "end_date": end_date,
    }

def generate_response(parsed_data: Dict[str, Any]) -> str:
    """Generate JSON response based on parsed data and business logic."""
    hotels = [
        {"id": "A#1", "hotelCodeSupplier": "39971881", "market": parsed_data["nationality"],
         "price": {"net": 132.42, "currency": "USD"}}
    ]
    
    markup_percentage = 3.2
    
    response = []
    for hotel in hotels:
        price_data = hotel["price"]
        selling_data = calculate_price(
            net_price=price_data["net"],
            request_currency=parsed_data["currency"],
            response_currency=price_data["currency"],
            markup=markup_percentage
        )
        
        min_selling_price = round(price_data["net"] * 1.05, 2)
        
        response.append({
            "id": hotel["id"],
            "hotelCodeSupplier": hotel["hotelCodeSupplier"],
            "market": hotel["market"],
            "price": {
                "minimumSellingPrice": min_selling_price,
                "currency": price_data["currency"],
                "net": price_data["net"],
                **selling_data
            }
        })
    
    return json.dumps(response, indent=4)


xml_request = """
<AvailRQ>
<timeoutMilliseconds>25000</timeoutMilliseconds>
<source>
<languageCode>en</languageCode>
</source>
<optionsQuota>20</optionsQuota>
<Configuration>
<Parameters>
<Parameter password="XXXXXXXXXX" username="YYYYYYYYY" CompanyID="123456"/>
</Parameters>
</Configuration>
<SearchType>Multiple</SearchType>
<StartDate>20/02/2025</StartDate>
<EndDate>24/02/2025</EndDate>
<Currency>USD</Currency>
<Nationality>US</Nationality>
</AvailRQ>
"""

try:
    parsed_data = parse_xml(xml_request)
    json_response = generate_response(parsed_data)
    print(json_response)
except Exception as e:
    print({"error": str(e)})

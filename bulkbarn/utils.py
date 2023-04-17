# Define URLs for the BulkBarn website
BULKBARN_URL = "https://www.bulkbarn.ca"
BULKBARN_PRODUCTS_URL = "https://www.bulkbarn.ca/en/Products"
BULKBARN_RECIPES_URL = "https://www.bulkbarn.ca/en/Recipes"
BULKBARN_DEAL_URL = "https://www.bulkbarn.ca/en/Deals/"
BULKBARN_CATEGORY_URL = "https://www.bulkbarn.ca/en/Products/Category/"
BULKBARN_PRODUCT_BASE_URL = "https://www.bulkbarn.ca/en/Products/All/"
BULKBARN_STORES_URL = "https://www.bulkbarn.ca/store_selector/en/"
BULKBARN_ECOMM_URL = "https://www.bulkbarn.ca/ecomm/product_search.html"


def metric_conversion(lb):
    """Converts pounds to kilograms"""
    return round(lb * 0.453592, 2)

def volume_conversion(cups):
    """Converts cups to oz"""
    return round(cups * 8, 2)

def tbsp_conversion(tbsp):
    """Converts tablespoons to millilitres"""
    return round(tbsp * 14.7868, 2)

def tsp_conversion(tsp):
    """Converts teaspoons to millilitres"""
    return round(tsp * 4.92892, 2)

def tbsp_conversion_tsp(tbsp):
    """Converts tablespoons to teaspoons"""
    return round(tbsp * 3, 2)
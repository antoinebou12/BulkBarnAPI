import pytest
from bulkbarn.__init__ import BulkBarn


@pytest.fixture
def bulkbarn_instance():
    return BulkBarn()

def test_get_products_by_name(bulkbarn_instance):
    product_name = "Self-Rising Flour"
    matching_products = bulkbarn_instance.get_products_by_name(product_name)

    assert len(matching_products) > 0, "No products found with the given name"

    for product in matching_products:
        assert product_name.lower() in product["name"].lower(
        ), f"Product name '{product['name']}' doesn't match the search term '{product_name}'"


def test_get_categories(bulkbarn_instance):
    categories = bulkbarn_instance.get_categories()

    assert len(categories) > 0, "No categories found"


def test_get_products(bulkbarn_instance):
    products = bulkbarn_instance.get_products()

    assert len(products) > 0, "No products found"


def test_get_products_by_category(bulkbarn_instance):
    category = "Baking Ingredients"
    products = bulkbarn_instance.get_products_by_category(category)

    assert len(
        products) > 0, f"No products found for the category '{category}'"


def test_get_products_by_id(bulkbarn_instance):
    product_id = "276"  # Example product ID for Self-Rising Flour
    product = bulkbarn_instance.get_products_by_id(product_id)

    assert product is not None, f"No product found with the ID '{product_id}'"
    assert product["id"] == product_id, f"Product ID '{product['id']}' doesn't match the search ID '{product_id}'"


def test_get_products_by_keyword(bulkbarn_instance):
    keyword = "flour"
    products = bulkbarn_instance.get_products_by_keyword(keyword)

    assert len(products) > 0, f"No products found with the keyword '{keyword}'"

    for product in products:
        assert keyword.lower() in product["name"].lower(
        ), f"Product name '{product['name']}' doesn't contain the keyword '{keyword}'"


def test_get_product_details(bulkbarn_instance):
    product_url = "https://www.bulkbarn.ca/en/Products/All/Self-Rising-Flour-276"
    details = bulkbarn_instance.get_products_details(product_url)

    assert "name" in details, "Product details do not contain 'name'"
    assert "image" in details, "Product details do not contain 'image'"
    assert "details" in details, "Product details do not contain 'details'"
    assert "nutrition_facts" in details, "Product details do not contain 'nutrition_facts'"

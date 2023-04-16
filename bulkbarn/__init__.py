import json
import re
from typing import Dict
from typing import List
from typing import Union

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from utils import *


class BulkBarn:
    def __init__(self):
        self.client = self.get_client()
        self.categories = None
        self.products = None

    def get_client(self) -> httpx.Client:
        return httpx.Client(verify=False, timeout=10)

    def get_categories(self) -> List[Dict[str, Union[str, int]]]:
        """Get all categories from Bulk Barn website."""
        pattern = "/en/Products/Categories"
        response = self.client.get(BULKBARN_PRODUCTS_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=lambda href: href and pattern in href)

        categories = []

        for link in links:
            category = {
                "name": link.text.strip(),
                "url": BULKBARN_URL + link["href"],
                "id": link["href"].split("/")[-1].strip(),
            }
            categories.append(category)

        self.categories = categories
        return categories

    def get_products(self, category: str = None) -> List[Dict[str, Union[str, int]]]:
        """Get all products from Bulk Barn website."""
        products = []
        for cat in self.categories:
            if category:
                if cat["name"] == category:
                    response = self.client.get(cat["url"])
                    soup = BeautifulSoup(response.text, "html.parser")
                    product_elements = soup.find_all(
                        "li", class_="prod-thumbnail")

                    for element in product_elements:
                        if product := self.parse_product_element(element):
                            products.append(product)
                    break
            else:
                response = self.client.get(cat["url"])
                soup = BeautifulSoup(response.text, "html.parser")
                product_elements = soup.find_all("li", class_="prod-thumbnail")

                for element in product_elements:
                    if product := self.parse_product_element(element):
                        products.append(product)
        self.products = products
        return products

    @staticmethod
    def parse_product_element(element) -> Union[Dict[str, Union[str, int]], None]:
        link = element.find("a", class_="product_thumbnail_item")
        product_thumbnail_copy = element.find(
            "div", class_="product_thumbnail_copy")

        if link is not None and product_thumbnail_copy is not None:
            product_name = product_thumbnail_copy.find(
                "div", class_="product_th_subtitle"
            )
            product_bbplu = product_thumbnail_copy.find(
                "div", class_="product_th_bbPLU"
            )

            if product_name is not None and product_bbplu is not None:
                return {
                    "name": product_name.text.strip(),
                    "url": BULKBARN_URL + link["href"],
                    "id": link["data-prod-id"],
                    "bbPLU": product_bbplu.text.strip(),
                }
        return None

    def display_products(self):
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("URL")
        table.add_column("ID")
        table.add_column("bbPLU")

        for product in self.products:
            table.add_row(
                product["name"], product["url"], product["id"], product["bbPLU"]
            )

        console.print(table)

    def export_to_csv(self, file_name: str = "products.csv"):
        products_df = pd.DataFrame(self.products)
        products_df.to_csv(file_name, index=False)

    def get_products_details(self, url: str) -> Dict[str, Union[str, int]]:
        response = self.client.get(url)

        soup = BeautifulSoup(response.text, "html.parser")

        # get all the images urls
        image = soup.find("section", {
            "id": "products-content"
        }).find(
            "li", class_="normalscale centered blowup currentDisplayItem"
        )

        image_url = "image['data-blowup-content']"

        product_redbox = soup.find("section", {
            "id": "products-content"
        }).find_all("div", class_="greystripe product-detail-card [nutrition-status]")[1]

        product_name = product_redbox.find(
            "p", class_="prod-name").text.strip()
        product_bbplu = product_redbox.find(
            "p", class_="prod-desc").text.strip()
        product_price = product_redbox.find(
            "p", class_="prod-price").text.strip()
        # get product details

        def extract_text(element):
            return element.text.strip() if element else ""

        details = {
            "Dietary Information": {
                "Organic": extract_text(product_redbox.find("li", class_="list-ind-organic")),
                "Peanut Free": extract_text(product_redbox.find("li", class_="list-ind-peanutfree")),
                "Vegan": extract_text(product_redbox.find("li", class_="list-ind-vegan")),
                "Gluten-Free": extract_text(product_redbox.find("li", class_="list-ind-glutenfree")),
                "Dairy Free": extract_text(product_redbox.find("li", class_="list-ind-dairyfree")),
                "Non GMO": extract_text(product_redbox.find("li", class_="list-ind-nongmo")),
            },
            "Ingredients": extract_text(product_redbox.find("p", class_="prod-ing")),
            "Allergens": extract_text(product_redbox.find("p", class_="prod-algn")),
            "Directions for Use": extract_text(product_redbox.find("p", class_="prod-dir")),
            "Usage Tips": extract_text(product_redbox.find("p", class_="prod-use")),
            "Storage Tips": extract_text(product_redbox.find("p", class_="prod-store")),
            "Points of Interest": extract_text(product_redbox.find("p", class_="prod-poi")),
            "Other": extract_text(product_redbox.find("p", class_="prod-other")),
        }

        # get nutrition facts
        nutrition_facts = {
            "Serving Size": "",
            "Portion": "",
            "Calories": "",
            "Fat": {
                "Total": {"Value": "", "Percentage": ""},
                "Saturated": {"Value": "", "Percentage": ""},
                "Trans": {"Value": "", "Percentage": ""},
            },
            "Carbohydrate": {
                "Total": {"Value": "", "Percentage": ""},
                "Fibre": {"Value": "", "Percentage": ""},
                "Sugars": {"Value": "", "Percentage": ""},
            },
            "Protein": "",
            "Vitamin A": {"Value": "", "Percentage": ""},
            "Vitamin C": {"Value": "", "Percentage": ""},
            "Cholesterol":"",
            "Sodium": {"Value": "", "Percentage": ""},
            "Potassium": {"Value": "", "Percentage": ""},
            "Calcium": {"Value": "", "Percentage": ""},
            "Iron": {"Value": "", "Percentage": ""},
        }

        nutrition_facts_div = soup.find("section", class_="product_detail_copy product-description-template-target")
        if not nutrition_facts_div:
            return nutrition_facts

        serving_size = nutrition_facts_div.find(
            lambda tag: tag.name == "p" and "Serving Size" in tag.text)
        if serving_size:
            nutrition_facts["Serving Size"] = serving_size.text.splitlines()[
                0].replace("Serving Size", "").strip()
            nutrition_facts["Portion"] = serving_size.text.splitlines()[
                1].replace("Portion", "").strip()

        rows = nutrition_facts_div.find_all(
            "div", class_="newrow border-bottom")

        print(nutrition_facts_div)

        for row in rows:
            columns = row.find_all("span")
            key = columns[0].text.strip()
            value = columns[1].text.strip()
            print(key, value)

            if "Calories" in key:
                nutrition_facts["Calories"] = value
            elif "Fat" in key and "Saturated" not in key:
                nutrition_facts["Fat"]["Total"]["Value"] = key.split(
                )[-2] + " " + key.split()[-1]
                nutrition_facts["Fat"]["Total"]["Percentage"] = value.split()[
                    0]
            elif "Saturated" in key:
                nutrition_facts["Fat"]["Saturated"]["Value"] = key.split()[-5] + " " + key.split()[-4] + " " + key.split()[-3] + " " + key.split()[-2] + " " + key.split()[-1]  
                nutrition_facts["Fat"]["Saturated"]["Percentage"] = value.split()[0]
                nutrition_facts["Fat"]["Trans"]["Value"] = key.split()[-3] + " " + key.split()[-2] + " " + key.split()[-1]
                nutrition_facts["Fat"]["Trans"]["Percentage"] = value.split()[0]
            elif "Cholesterol" in key:
                nutrition_facts["Cholesterol"] = value
            elif "Sodium" in key:
                nutrition_facts["Sodium"]["Value"] = value
                nutrition_facts["Sodium"]["Percentage"] = value.split()[0]
            elif "Carbohydrate" in key:
                nutrition_facts["Carbohydrate"]["Total"]["Value"] = key.split(
                )[-2] + " " + key.split()[-1]
                nutrition_facts["Carbohydrate"]["Total"]["Percentage"] = value.split()[0]
            elif "Fibre" in key:
                nutrition_facts["Carbohydrate"]["Fibre"]["Value"] = key.split(
                )[-2] + " " + key.split()[-1]
                nutrition_facts["Carbohydrate"]["Fibre"]["Percentage"] = value.split()[0]
            elif "Sugars" in key:
                nutrition_facts["Carbohydrate"]["Sugars"]["Value"] = key.split()[-2] + " " + key.split()[-1]
                nutrition_facts["Carbohydrate"]["Sugars"]["Percentage"] = key.split()[-2]
            elif "Protein" in key:
                nutrition_facts["Protein"] = key.split()[-2] + " " + key.split()[-1]
            elif "Vitamin A" in key:
                nutrition_facts["Vitamin A"]["Value"] = key.split()[-2] + " " + key.split()[-1]
                nutrition_facts["Vitamin A"]["Percentage"] = value.split()[0]
            elif "Vitamin C" in key:
                nutrition_facts["Vitamin C"]["Value"] = key.split()[-2] + " " + key.split()[-1]
                nutrition_facts["Vitamin C"]["Percentage"] = value.split()[0]
            elif "Cholesterol" in key:
                nutrition_facts["Cholesterol"] = key
            elif "Sodium" in key:
                print(key)
                print(value)
                nutrition_facts["Sodium"]["Value"] = key
                nutrition_facts["Sodium"]["Percentage"] = value.split()[0]
            elif "Potassium" in key:
                nutrition_facts["Potassium"]["Value"] = key
                nutrition_facts["Potassium"]["Percentage"] = value.split()[0]
            elif "Calcium" in key:
                nutrition_facts["Calcium"]["Value"] = key
                nutrition_facts["Calcium"]["Percentage"] = value.split()[0]
            elif "Iron" in key:
                nutrition_facts["Iron"]["Value"] = key
                nutrition_facts["Iron"]["Percentage"] = value.split()[0]


        console = Console()
        console.print(nutrition_facts)

        return {
            "name": product_name,
            "bbPLU": product_bbplu,
            "price": product_price,
            "image": image_url,
            "details": details,
            "nutrition_facts": nutrition_facts,
        }

    def display_product_details(self, url: str):
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("bbPLU")
        table.add_column("Price")
        table.add_column("Image")
        table.add_column("Details")
        table.add_column("Nutrition Facts")

        details = self.get_products_details(url)
        table.add_row(
            str(details["name"]),
            str(details["bbPLU"]),
            str(details["price"]),
            str(details["image"]),
            str(details["details"]),
            str(details["nutrition_facts"]),
        )

        console.print(table)

    def get_recipes(self) -> List[Dict[str, Union[str, int]]]:
        pass

    def get_deals(self) -> List[Dict[str, Union[str, int]]]:
        pass

    def get_categories(self) -> List[Dict[str, Union[str, int]]]:
        pass

    def get_products_by_category(self) -> List[Dict[str, Union[str, int]]]:
        pass

    def get_products_by_name(self, name: str) -> List[Dict[str, Union[str, int]]]:
        """
        Get products by name from Bulk Barn website.
        """
        return [
            product
            for product in self.products
            if name.lower() in product["name"].lower()
        ]

    def get_products_by_id(self) -> List[Dict[str, Union[str, int]]]:
        pass

    def get_products_by_keyword(self) -> List[Dict[str, Union[str, int]]]:
        pass


if __name__ == "__main__":
    bulkbarn = BulkBarn()
    bulkbarn.display_product_details(
        "https://www.bulkbarn.ca/en/Products/All/Merckens-Light-Chocolate-Flavoured-Molding-Wafers"
    )

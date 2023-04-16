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
        self.categories = self.get_categories()
        self.products = self.get_products()

    def get_client(self) -> httpx.Client:
        return httpx.Client(verify=False)

    def get_products(self, category: str = None) -> List[Dict[str, Union[str, int]]]:
        """Get all products from Bulk Barn website."""
        products = []
        for cat in self.categories:
            if category:
                if cat["name"] == category:
                    response = self.client.get(cat["url"])
                    soup = BeautifulSoup(response.text, "html.parser")
                    product_elements = soup.find_all("li", class_="prod-thumbnail")

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
        return products

    @staticmethod
    def parse_product_element(element) -> Union[Dict[str, Union[str, int]], None]:
        link = element.find("a", class_="product_thumbnail_item")
        product_thumbnail_copy = element.find("div", class_="product_thumbnail_copy")

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
        with httpx.Client(verify=False) as client:
            if url:
                response = client.get(url)

        soup = BeautifulSoup(response.text, "html.parser")
        # get all the images urls
        image = soup.find("div", id="products-content").find_all(
            "img", class_="currentDisplayItem"
        )
        image_url = image[0]["style"].split("url(&quot;")[1].split("&quot;)")[0]

        # get the product name
        product_name = soup.find("div", id_="products-content").find("h2").text.strip()

        # get product details
        details = {}
        detail_sections = soup.find("div", id_="products-content").find_all(
            "section", class_="hide-if-empty"
        )
        for section in detail_sections:
            if subtitle := section.find("p", class_="prod-subtitle"):
                key = subtitle.text.strip().replace(":", "")
                if value := section.find("p", class_=lambda x: x != "prod-subtitle"):
                    details[key] = value.text.strip()

        # get nutrition facts
        nutrition_facts = {}
        if nutrition_table := soup.find("div", id_="products-content").find(
            "div", class_="column-content"
        ):
            rows = nutrition_table.find_all("div", class_="newrow")
            for row in rows:
                cols = row.find_all("span", class_="col-1")
                for col in cols:
                    key, value = col.text.split(" ", 1)
                    nutrition_facts[key.strip()] = value.strip()

        return {
            "name": product_name,
            "image": image_url,
            "details": details,
            "nutrition_facts": nutrition_facts,
        }

    def display_product_details(self, url: str):
        console = Console()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("Image")
        table.add_column("Details")
        table.add_column("Nutrition Facts")

        details = self.get_products_details(url)
        table.add_row(
            details["name"],
            " ".join(details["images"]),
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

    def get_products_by_name(self) -> List[Dict[str, Union[str, int]]]:
        pass

    def get_products_by_id(self) -> List[Dict[str, Union[str, int]]]:
        pass

    def get_products_by_keyword(self) -> List[Dict[str, Union[str, int]]]:
        pass

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

        return categories


if __name__ == "__main__":
    bulkbarn = BulkBarn()
    bulkbarn.display_product_details(
        "https://www.bulkbarn.ca/en/Products/All/Self-Rising-Flour-276"
    )

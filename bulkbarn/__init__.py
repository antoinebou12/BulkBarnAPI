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
from playwright.sync_api import sync_playwright
import asyncio


class BulkBarn:
    def __init__(self):
        self.client = self.get_client()
        self.categories = None
        self.products = None

    def get_client(self) -> httpx.Client:
        return httpx.Client(verify=False, timeout=10)

    def get_categories(self) -> List[Dict[str, Union[str, int]]]:
        """Get all categories from Bulk Barn website."""
        pattern = "Products/Categories"
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

    def get_recipes_categories(self) -> List[Dict[str, str]]:
        """Get recipes categories from Bulk Barn website."""
        pattern = "Recipes/Categories/"
        response = self.client.get(BULKBARN_RECIPES_URL)
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
    
    def get_recipes(self) -> List[Dict[str, Union[str, int]]]:
        """Get recipes from Bulk Barn website."""



    def get_deals(self) -> List[Dict[str, Union[str, int]]]:
        pass

    def get_products_by_category(self, category: str) -> List[Dict[str, Union[str, int]]]:
        """Get products by category from Bulk Barn website."""
        if self.products is None:
            self.get_products()
        if self.categories is None:
            self.get_categories()
        return [
            product
            for product in self.products
            if category.lower() in product["category"].lower()
        ]

    def get_products_by_id(self, id: int) -> List[Dict[str, Union[str, int]]]:
        """Get products by id from Bulk Barn website."""
        if self.products is None:
            self.get_products()
        return [
            product
            for product in self.products
            if product["bbPLU"] == id
        ]

    def get_products_by_keyword(self, keyword: str) -> List[Dict[str, Union[str, int]]]:
        """Get products by keyword from Bulk Barn website."""
        if self.products is None:
            self.get_products()
        if self.categories is None:
            self.get_categories()
        return [
            product
            for product in self.products
            if keyword.lower() in product["name"].lower()
            or keyword.lower() in product["details"].lower()
            or keyword.lower() in product["category"].lower()
        ]

    def get_products_by_name(self, name: str) -> List[Dict[str, Union[str, int]]]:
        """Get products by name from Bulk Barn website."""
        if self.products is None:
            self.get_products()
        return [
            product
            for product in self.products
            if name.lower() in product["name"].lower()
        ]

    def get_store_locations(self) -> List[Dict[str, Union[str, int]]]:
        """Get store locations from Bulk Barn website."""
        self.store_locations = []
        response = self.client.get(BULKBARN_STORES_URL)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all store location elements
        store_elements = soup.find_all("div", {"data-jplist-item": ""})

        for element in store_elements:
            if store_info := element.find("div", {"style": "display:none;"}):
                info_text = store_info.text.strip()
                store_id, *address_parts, phone = info_text.split()
                store_id = int(store_id.strip("#"))
                address = " ".join(address_parts)
                phone = phone.strip()
                map_url = element.find("a", {"target": "_blank"})["href"]


                self.store_locations.append(
                    {
                        "store_id": store_id,
                        "address": address,
                        "phone": phone,
                        "map_url": map_url,
                    }
                )

        return self.store_locations

    def set_local_storage(self, page, data: Dict[str, str]) -> None:
        """
        Set local storage in Playwright.

        :param page: Playwright Page object
        :param data: Dictionary containing key-value pairs to set in local storage
        """
        for key, value in data.items():
            function = '(key, value) => { window.localStorage.setItem($key, $value); }'
            function = function.replace("$key", f"'{key}'").replace("$value", f"'{value}'")
            page.evaluate(function)

    def get_local_storage(self, page, key: str) -> str:
        """
        Get local storage in Playwright.

        :param page: Playwright Page object
        :param key: Key to get from local storage
        :return: Value of key
        """
        function = '(key) => { return window.localStorage.getItem($key); }'
        function = function.replace("$key", f"'{key}'")
        return page.evaluate(function)

    def setup_cart(self, store_id: int) -> None:
        """Setup cart for store."""
        self.cart = {"store_id": store_id, "province": "QC", "items": []}

        with sync_playwright() as p:
                for browser_type in [p.chromium]:
                    browser = browser_type.launch(headless=True)
                    page = browser.new_page()
                    # Set local storage
                    page.goto(BULKBARN_ECOMM_URL)
                    self.set_local_storage(page, {"userProvince": str(self.cart["province"])})
                    self.set_local_storage(page, {"storeCode": str(self.cart["store_id"])})
                    self.set_local_storage(page, {'cartArray': '[{"itemNo":"129","QTY":"1","userQTY":"","userUOM":"","niceUserQTY":" x "}]'})
                    page.goto("https://www.bulkbarn.ca/ecomm/cart.html")

    def get_ecomm_products(self) -> List[Dict[str, Union[str, int]]]:
            """Get ecomm products from Bulk Barn website."""
            # [{"itemNo":"129","QTY":"1","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"3200","QTY":"1","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"53","QTY":"0.5","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"11","QTY":"1","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"23","QTY":"0.5","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"74","QTY":"0.5","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"267","QTY":"1","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"373","QTY":"0.1","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"524","QTY":"0.5","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"669","QTY":"0.2","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"1536","QTY":"0.3","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"1611","QTY":"0.3","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"1608","QTY":"0.3","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"1724","QTY":"0.5","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"1770","QTY":"0.3","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"20","QTY":"0.3","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"214","QTY":"0.5","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"217","QTY":"0.5","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"219","QTY":"0.5","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"358","QTY":"0.3","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"426","QTY":"0.2","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"431","QTY":"0.2","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"800","QTY":"0.1","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"1216","QTY":"0.2","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"1251","QTY":"0.4","userQTY":"","userUOM":"","niceUserQTY":" x "},{"itemNo":"1518","QTY":"0.5","userQTY":"","userUOM":"","niceUserQTY":" x "}]
            with sync_playwright() as p:
                for browser_type in [p.chromium]:
                    browser = browser_type.launch()
                    page = browser.new_page(ignore_https_errors=True)
                    page.goto(BULKBARN_ECOMM_URL)
                    page.goto("https://www.bulkbarn.ca/ecomm/cart.html")
                    # Set local storage
                    # self.set_local_storage(page, {'item129', '{"boxID":"29","Product_name_EN":"Mixed Nuts With Peanuts, Roasted &amp; Salted","Product_name_FR":"Noix m&eacute;lang&eacute;es avec arachides, r&ocirc;ties et sal&eacute;es","keywords_EN":"nuts, roasted, salted, DELTAUPDATE","keywords_FR":"noix, roties, salees, DELTAUPDATE","photo":"129_000129.png","upccode":"129","not_in_quebec":"0","BBPLU":"129","Item_No":"129","Posting_Group":"BULK","Organic":"No","Mono_Cup_Item":"No","Sml_Scoop_Item":"No","Cup_Weight":"0.156","Sml_Scoop_Wgt":"","Lrg_Scoop_Wgt":"0.312","Mono_8oz_Wgt":"","Mono_16oz_Wgt":"","Mono_32oz_Wgt":"","Retail_Price":"18.18","Retail_Price_UOM":"PER KG","Retail_Price_100g":"1.818","Sale_Price":"18.18","Sale_Start_Date":"2020-08-06 00:01","Sale_End_Date":"3020-12-31 23:59","GST_HST_Applicable":"Yes","AB_PST":"No","BC_PST":"No","MB_PST":"Yes","NB_PST":"No","NL_PST":"No","NS_PST":"No","NT_PST":"No","ON_PST":"No","PE_PST":"No","QC_PST":"Yes","SK_PST":"Yes"}'})
                    self.set_local_storage(page, {"userProvince": "QC"})
                    self.set_local_storage(page, {"store741": '{"storeCode":"741","Address":"1616 RUE SAINTE-CATHERINE OUEST","City":"MONTR&Eacute;AL (MONTREAL)","Province":"QC","Phone":"(514) 932-9748","Mon":"09:30 am - 08:30 pm","Tue":"09:30 am - 08:30 pm","Wed":"09:30 am - 08:30 pm","Thur":"09:30 am - 08:30 pm","Fri":"09:30 am - 08:30 pm","Sat":"09:30 am - 08:00 pm","Sun":"10:00 am - 05:00 pm","Curbside":"x","PickupWindow":"2"}'})
                    self.set_local_storage(page, {"storeCode": "741"})
                    self.set_local_storage(page, {'cartArray': '[{"itemNo":"129","QTY":"1","userQTY":"","userUOM":"","niceUserQTY":" x "}]'})
                    page.goto("https://www.bulkbarn.ca/ecomm/cart.html")
                    page.screenshot(path=f'example-{browser_type.name}.png')
                    # Get local storage
                    local_storage = page.evaluate("() => JSON.parse(window.localStorage.getItem('cartArray'))")
                    print(local_storage)
                    local_storage = page.evaluate("() => JSON.parse(window.localStorage.getItem('storeCode'))")
                    print(local_storage)
                    self.ecomm_products = local_storage
                    browser.close()

            return self.ecomm_products


if __name__ == "__main__":
    bulkbarn = BulkBarn()
    # bulkbarn.display_product_details(
    #     "https://www.bulkbarn.ca/en/Products/All/Merckens-Light-Chocolate-Flavoured-Molding-Wafers"
    # )
    # print(bulkbarn.get_store_locations())
    bulkbarn.get_ecomm_products()

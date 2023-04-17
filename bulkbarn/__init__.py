import json
from typing import Dict
from typing import List
from typing import Union

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
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
        self.products = products
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
        response = self.client.get(url)

        soup = BeautifulSoup(response.text, "html.parser")

        # get all the images urls
        image = soup.find("section", {"id": "products-content"}).find(
            "li", class_="normalscale centered blowup currentDisplayItem"
        )

        image_url = "image['data-blowup-content']"

        product_redbox = soup.find("section", {"id": "products-content"}).find_all(
            "div", class_="greystripe product-detail-card [nutrition-status]"
        )[1]

        product_name = product_redbox.find("p", class_="prod-name").text.strip()
        product_bbplu = product_redbox.find("p", class_="prod-desc").text.strip()
        product_price = product_redbox.find("p", class_="prod-price").text.strip()
        # get product details

        def extract_text(element):
            return element.text.strip() if element else ""

        details = {
            "Dietary Information": {
                "Organic": extract_text(
                    product_redbox.find("li", class_="list-ind-organic")
                ),
                "Peanut Free": extract_text(
                    product_redbox.find("li", class_="list-ind-peanutfree")
                ),
                "Vegan": extract_text(
                    product_redbox.find("li", class_="list-ind-vegan")
                ),
                "Gluten-Free": extract_text(
                    product_redbox.find("li", class_="list-ind-glutenfree")
                ),
                "Dairy Free": extract_text(
                    product_redbox.find("li", class_="list-ind-dairyfree")
                ),
                "Non GMO": extract_text(
                    product_redbox.find("li", class_="list-ind-nongmo")
                ),
            },
            "Ingredients": extract_text(product_redbox.find("p", class_="prod-ing")),
            "Allergens": extract_text(product_redbox.find("p", class_="prod-algn")),
            "Directions for Use": extract_text(
                product_redbox.find("p", class_="prod-dir")
            ),
            "Usage Tips": extract_text(product_redbox.find("p", class_="prod-use")),
            "Storage Tips": extract_text(product_redbox.find("p", class_="prod-store")),
            "Points of Interest": extract_text(
                product_redbox.find("p", class_="prod-poi")
            ),
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
            "Cholesterol": "",
            "Sodium": {"Value": "", "Percentage": ""},
            "Potassium": {"Value": "", "Percentage": ""},
            "Calcium": {"Value": "", "Percentage": ""},
            "Iron": {"Value": "", "Percentage": ""},
        }

        nutrition_facts_div = soup.find(
            "section", class_="product_detail_copy product-description-template-target"
        )
        if not nutrition_facts_div:
            return nutrition_facts

        serving_size = nutrition_facts_div.find(
            lambda tag: tag.name == "p" and "Serving Size" in tag.text
        )
        if serving_size:
            nutrition_facts["Serving Size"] = (
                serving_size.text.splitlines()[0].replace("Serving Size", "").strip()
            )
            nutrition_facts["Portion"] = (
                serving_size.text.splitlines()[1].replace("Portion", "").strip()
            )

        rows = nutrition_facts_div.find_all("div", class_="newrow border-bottom")

        print(nutrition_facts_div)

        for row in rows:
            columns = row.find_all("span")
            key = columns[0].text.strip()
            value = columns[1].text.strip()
            print(key, value)

            if "Calories" in key:
                nutrition_facts["Calories"] = value
            elif "Fat" in key and "Saturated" not in key:
                nutrition_facts["Fat"]["Total"]["Value"] = (
                    key.split()[-2] + " " + key.split()[-1]
                )
                nutrition_facts["Fat"]["Total"]["Percentage"] = value.split()[0]
            elif "Saturated" in key:
                nutrition_facts["Fat"]["Saturated"]["Value"] = (
                    key.split()[-5]
                    + " "
                    + key.split()[-4]
                    + " "
                    + key.split()[-3]
                    + " "
                    + key.split()[-2]
                    + " "
                    + key.split()[-1]
                )
                nutrition_facts["Fat"]["Saturated"]["Percentage"] = value.split()[0]
                nutrition_facts["Fat"]["Trans"]["Value"] = (
                    key.split()[-3] + " " + key.split()[-2] + " " + key.split()[-1]
                )
                nutrition_facts["Fat"]["Trans"]["Percentage"] = value.split()[0]
            elif "Cholesterol" in key:
                nutrition_facts["Cholesterol"] = value
            elif "Sodium" in key:
                nutrition_facts["Sodium"]["Value"] = value
                nutrition_facts["Sodium"]["Percentage"] = value.split()[0]
            elif "Carbohydrate" in key:
                nutrition_facts["Carbohydrate"]["Total"]["Value"] = (
                    key.split()[-2] + " " + key.split()[-1]
                )
                nutrition_facts["Carbohydrate"]["Total"]["Percentage"] = value.split()[
                    0
                ]
            elif "Fibre" in key:
                nutrition_facts["Carbohydrate"]["Fibre"]["Value"] = (
                    key.split()[-2] + " " + key.split()[-1]
                )
                nutrition_facts["Carbohydrate"]["Fibre"]["Percentage"] = value.split()[
                    0
                ]
            elif "Sugars" in key:
                nutrition_facts["Carbohydrate"]["Sugars"]["Value"] = (
                    key.split()[-2] + " " + key.split()[-1]
                )
                nutrition_facts["Carbohydrate"]["Sugars"]["Percentage"] = key.split()[
                    -2
                ]
            elif "Protein" in key:
                nutrition_facts["Protein"] = key.split()[-2] + " " + key.split()[-1]
            elif "Vitamin A" in key:
                nutrition_facts["Vitamin A"]["Value"] = (
                    key.split()[-2] + " " + key.split()[-1]
                )
                nutrition_facts["Vitamin A"]["Percentage"] = value.split()[0]
            elif "Vitamin C" in key:
                nutrition_facts["Vitamin C"]["Value"] = (
                    key.split()[-2] + " " + key.split()[-1]
                )
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

    def get_products_by_category(
        self, category: str
    ) -> List[Dict[str, Union[str, int]]]:
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
        return [product for product in self.products if product["bbPLU"] == id]

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
            function = "(key, value) => { window.localStorage.setItem($key, $value); }"
            function = function.replace("$key", f"'{key}'").replace(
                "$value", f"'{value}'"
            )
            page.evaluate(function)

    def get_local_storage(self, page, key: str) -> str:
        """
        Get local storage in Playwright.

        :param page: Playwright Page object
        :param key: Key to get from local storage
        :return: Value of key
        """
        function = "(key) => { return window.localStorage.getItem($key); }"
        function = function.replace("$key", f"'{key}'")
        return page.evaluate(function)

    def generate_cart_array(self, items: List[Dict[str, Union[str, int]]]) -> str:
        cart_array = [
            {
                "itemNo": str(item["bbPLU"]),
                "QTY": str(item["quantity"]),
                "userQTY": "",
                "userUOM": "",
                "niceUserQTY": " x ",
            }
            for item in items
        ]
        return json.dumps(cart_array)

    def add_item(self, item_no: str, quantity: int) -> None:
        self.items.append({"item_no": item_no, "quantity": quantity})

    def generate_item(self, item: Dict[str, Union[str, int]]) -> str:
        # {"boxID":"29","Product_name_EN":"Mixed Nuts With Peanuts, Roasted &amp; Salted","Product_name_FR":"Noix m&eacute;lang&eacute;es avec arachides, r&ocirc;ties et sal&eacute;es","keywords_EN":"nuts, roasted, salted, DELTAUPDATE","keywords_FR":"noix, roties, salees, DELTAUPDATE","photo":"129_000129.png","upccode":"129","not_in_quebec":"0","BBPLU":"129","Item_No":"129","Posting_Group":"BULK","Organic":"No","Mono_Cup_Item":"No","Sml_Scoop_Item":"No","Cup_Weight":"0.100","Sml_Scoop_Wgt":"","Lrg_Scoop_Wgt":"0.300","Mono_8oz_Wgt":"","Mono_16oz_Wgt":"","Mono_32oz_Wgt":"","Retail_Price":"1.81","Retail_Price_UOM":"PER KG","Retail_Price_100g":"1.818","Sale_Price":"1.18","Sale_Start_Date":"2020-08-06 00:01","Sale_End_Date":"3020-12-31 23:59","GST_HST_Applicable":"Yes","AB_PST":"No","BC_PST":"No","MB_PST":"Yes","NB_PST":"No","NL_PST":"No","NS_PST":"No","NT_PST":"No","ON_PST":"No","PE_PST":"No","QC_PST":"Yes","SK_PST":"Yes"}
        return {
            "boxID": item["boxID"],
            "Product_name_EN": item["Product_name_EN"],
            "Product_name_FR": item["Product_name_FR"],
            "keywords_EN": item["keywords_EN"],
            "keywords_FR": item["keywords_FR"],
            "photo": item["photo"],
            "upccode": item["upccode"],
            "not_in_quebec": item["not_in_quebec"],
            "BBPLU": item["BBPLU"],
            "Item_No": item["Item_No"],
            "Posting_Group": item["Posting_Group"],
            "Organic": item["Organic"],
            "Mono_Cup_Item": item["Mono_Cup_Item"],
            "Sml_Scoop_Item": item["Sml_Scoop_Item"],
            "Cup_Weight": item["Cup_Weight"],
            "Sml_Scoop_Wgt": item["Sml_Scoop_Wgt"],
            "Lrg_Scoop_Wgt": item["Lrg_Scoop_Wgt"],
            "Mono_8oz_Wgt": item["Mono_8oz_Wgt"],
            "Mono_16oz_Wgt": item["Mono_16oz_Wgt"],
            "Mono_32oz_Wgt": item["Mono_32oz_Wgt"],
            "Retail_Price": item["Retail_Price"],
            "Retail_Price_UOM": item["Retail_Price_UOM"],
            "Retail_Price_100g": item["Retail_Price_100g"],
            "Sale_Price": item["Sale_Price"],
            "Sale_Start_Date": item["Sale_Start_Date"],
            "Sale_End_Date": item["Sale_End_Date"],
            "GST_HST_Applicable": item["GST_HST_Applicable"],
            "AB_PST": item["AB_PST"],
            "BC_PST": item["BC_PST"],
            "MB_PST": item["MB_PST"],
            "NB_PST": item["NB_PST"],
            "NL_PST": item["NL_PST"],
            "NS_PST": item["NS_PST"],
            "NT_PST": item["NT_PST"],
            "ON_PST": item["ON_PST"],
            "PE_PST": item["PE_PST"],
            "QC_PST": item["QC_PST"],
            "SK_PST": item["SK_PST"],
        }

    def change_price(
        self,
        page,
        item: Dict,
        retail_price: str,
        retail_price_100g: str,
        sale_price: str,
    ) -> None:
        # sourcery skip: avoid-builtin-shadow
        """Change price of item in cart."""
        item = json.loads(item)

        item["Retail_Price"] = retail_price
        item["Retail_Price_100g"] = retail_price_100g
        item["Sale_Price"] = sale_price
        id = item["BBPLU"]
        item = json.dumps(self.generate_item(item))
        self.set_local_storage(page, {"item" + id: item})
        return item

    def create_store(self, store_id: int, province: str) -> None:
        # {"storeCode":"527","Address":"741 ALGONQUIN BOULEVARD EAST","City":"TIMMINS","Province":"ON","Phone":"(705) 268-2355","Mon":"09:30 am - 08:00 pm","Tue":"09:30 am - 08:00 pm","Wed":"09:30 am - 08:00 pm","Thur":"09:30 am - 08:00 pm","Fri":"09:30 am - 08:00 pm","Sat":"09:30 am - 06:00 pm","Sun":"10:00 am - 05:00 pm","Curbside":"x","PickupWindow":"2"}
        """Create store."""
        return {
            "storeCode": store_id,
            "Address": "",
            "City": "",
            "Province": province,
            "Phone": "",
            "Mon": "",
            "Tue": "",
            "Wed": "",
            "Thur": "",
            "Fri": "",
            "Sat": "",
            "Sun": "",
            "Curbside": "",
            "PickupWindow": "",
        }

    def set_store(self, page, store_id: int, province: str) -> None:
        """Set store."""
        self.set_local_storage(page, {"storeCode": store_id})
        self.set_local_storage(page, {"userProvince": province})

    def setup_cart(
        self,
        store_id: int = "741",
        province: str = "QC",
        items: List[Dict[str, Union[str, int]]] = None,
        headless: bool = True,
    ):
        """Setup cart for store."""
        if items is None:
            items = []
        self.cart = {"store_id": store_id, "province": province, "items": list(items)}

        with sync_playwright() as p:
            for browser_type in [p.chromium]:
                browser = browser_type.launch(headless=headless)
                page = browser.new_page()

                page.goto(BULKBARN_STORES_URL)
                self.set_store(page, store_id, province)
                page.goto(BULKBARN_ECOMM_URL)
                page.goto("https://www.bulkbarn.ca/ecomm/cart.html")
                self.set_store(page, store_id, province)

                self.change_price(
                    page,
                    self.get_local_storage(page, "item129"),
                    "1.99",
                    "1.99",
                    "1.99",
                )

                self.set_store(page, store_id, province)
                self.set_local_storage(
                    page, {"cartArray": self.generate_cart_array(self.cart["items"])}
                )

                page.goto("https://www.bulkbarn.ca/ecomm/cart.html")
                page.screenshot(path="cart.png")
                # stay open browser after script is done
                if not headless:
                    input("Press Enter to continue...")
                browser.close()


if __name__ == "__main__":
    bulkbarn = BulkBarn()
    # bulkbarn.display_product_details(
    #     "https://www.bulkbarn.ca/en/Products/All/Merckens-Light-Chocolate-Flavoured-Molding-Wafers"
    # )
    # print(bulkbarn.get_store_locations())
    bulkbarn.setup_cart(
        store_id=741,
        province="QC",
        items=[{"bbPLU": "129", "quantity": 1}],
        headless=False,
    )

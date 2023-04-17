import json
from typing import Dict
from typing import List
from typing import Union

from playwright.sync_api import sync_playwright

BASE_URL = "https://www.example.com"  # Replace this with the actual base URL
CART_URL = f"{BASE_URL}/cart.html"


class GenericStore:
    def __init__(self, store_id: int = 741, province: str = "QC"):
        self.store_id = store_id
        self.province = province
        self.items = []

    def set_local_storage(self, page, data: Dict[str, str]) -> None:
        for key, value in data.items():
            function = f"(key, value) => {{ window.localStorage.setItem('{key}', '{value}'); }}"
            page.evaluate(function)

    def get_local_storage(self, page, key: str) -> str:
        function = f"(key) => {{ return window.localStorage.getItem('{key}'); }}"
        return page.evaluate(function)

    def generate_cart_array(self, items: List[Dict[str, Union[str, int]]]) -> str:
        cart_array = [
            {
                "itemNo": item["item_no"],
                "QTY": item["quantity"],
                "userQTY": "",
                "userUOM": "",
                "niceUserQTY": " x ",
            }
            for item in items
        ]
        return json.dumps(cart_array)

    def add_item(self, item_no: str, quantity: int) -> None:
        self.items.append({"item_no": item_no, "quantity": quantity})

    def setup_cart(self):
        with sync_playwright() as p:
            for browser_type in [p.chromium]:
                browser = browser_type.launch(headless=True)
                page = browser.new_page()
                # Set local storage
                page.goto(CART_URL)
                self.set_local_storage(page, {"userProvince": self.province})
                self.set_local_storage(page, {"storeCode": str(self.store_id)})
                self.set_local_storage(
                    page, {"cartArray": self.generate_cart_array(self.items)}
                )
                # Take a screenshot of the cart
                page.goto(CART_URL)
                page.screenshot(path="cart.png")
                browser.close()


if __name__ == "__main__":
    store = GenericStore(store_id=741, province="QC")
    store.add_item("129", 1)
    store.setup_cart()

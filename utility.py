import time
from random import choice, choices

from requests import get


class Item:
    def __init__(self, list):
        self.list = list
        self.item_name: str = self.list[0]
        self.acro: str = self.list[1]
        self.rap: int = self.list[2] if self.list[2] != 0 else 1_000_000
        self.value: int = self.list[3] if self.list[2] != 0 else 1_000_000
        self.default_value: int = self.list[4] if self.list[2] != 0 else 1_000_000
        self.demand: int = self.list[5]
        self.trend: int = self.list[6]
        self.projected: int = self.list[7]
        self.hyped: int = self.list[8]
        self.rare: int = self.list[9]


def get_cached_api_result(url):
    """
    Returns cached API result if available and not expired, otherwise fetches new result and caches it.
    Caches API result for 10 minutes.
    """
    cache = get_cached_api_result.cache
    if url in cache and time.time() - cache[url]["timestamp"] < 600:
        return cache[url]["result"]
    else:
        response = get(url).json()
        cache[url] = {"result": response, "timestamp": time.time()}
        return response


get_cached_api_result.cache = {}


def get_rand():
    response = get_cached_api_result("https://www.rolimons.com/itemapi/itemdetails")
    items_list = response["items"]

    random_item_legend = list(items_list.keys())
    item_choice = choices(random_item_legend, k=3)

    return (
        Item(items_list[item_choice[0]]),
        Item(items_list[item_choice[1]]),
        Item(items_list[item_choice[2]]),
    )


def get_items(value):
    # Calculate the thresholds for the value
    threshold_range = value * 0.2
    lower_threshold = value - threshold_range
    upper_threshold = value + threshold_range

    # Get all items from the API within the value thresholds
    response = get_cached_api_result("https://www.rolimons.com/itemapi/itemdetails")
    items_list = response["items"]
    eligible_items = [
        Item(item_data)
        for item_data in items_list.values()
        if lower_threshold <= Item(item_data).default_value <= upper_threshold
    ]

    # If no eligible items found, return None
    if not eligible_items:
        return None

    # Randomly choose an item from the eligible items
    random_item = choice(eligible_items)

    # Add the random item to the result list
    result_items = [random_item]
    total_rap = random_item.default_value

    if total_rap == 0:
        pass
    else:
        # Add more items to the list until the total RAP is greater than or equal to the value
        while len(result_items) < 8 and total_rap < value:
            eligible_items = [
                Item(item_data)
                for item_data in items_list.values()
                if Item(item_data).default_value <= upper_threshold - total_rap
            ]
            if not eligible_items:
                break
            random_item = choice(eligible_items)
            result_items.append(random_item)
            total_rap += random_item.default_value

    return result_items

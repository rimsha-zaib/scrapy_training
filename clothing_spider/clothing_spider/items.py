# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class ProductItem(scrapy.Item):

    url =scrapy.Field()
    referer_url =scrapy.Field()

    # 2-letter country codes (e.g. "US,FR,DE")
    country_code =scrapy.Field()

    # base of sku that is independent of color
    # (e.g. 41371610LP(red), 41371610QW(blue) --> base_sku = 41371610)
    # should be available on overview page to merge categories
    base_sku =scrapy.Field()

    # unique identifier of Product-color variation, e.g; 41371610_red
    identifier =scrapy.Field()

    title =scrapy.Field()
    brand =scrapy.Field()
    description_text =scrapy.Field()

    # binary product availability
    available =scrapy.Field()

    # prices
    old_price_text =scrapy.Field()
    new_price_text =scrapy.Field()
    currency =scrapy.Field()

    # local language of description
    language_code =scrapy.Field()

    color_name =scrapy.Field()
    # color code as specified by retailer, if available (e.g. "W57")
    color_code =scrapy.Field()

    category_names =scrapy.Field()

    # list of image urls to be downloaded, in high quality
    image_urls =scrapy.Field()

    # Info for size and availability collections
    # will be array of SizeItem objects
    size_infos =scrapy.Field()

    # Set this flag to True, if prices should be taken from SizeItem
    # instead of ProductItem
    use_size_level_prices =scrapy.Field()

    """
    ADVANCED FIELDS
    """
    # timestamp of request download -> it will be added automatically for each spider
    timestamp =scrapy.Field()


# For size and availability
class SizeItem(scrapy.Item):

    # Those prices will only be used if use_size_level_prices=True on
    # ProductItem
    size_original_price_text =scrapy.Field()
    size_current_price_text =scrapy.Field()

    # identifier for SKU-model + size
    size_identifier =scrapy.Field()
    size_name =scrapy.Field()
    stock =scrapy.Field()   # 0 = unavailable, 1 = available (default), 2 or more = available stock given on website

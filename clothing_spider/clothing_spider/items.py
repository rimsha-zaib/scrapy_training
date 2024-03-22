# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field


class ProductItem(Item):
    title = Field()
    url = Field()
    img = Field()
    description = Field()
    category = Field()
    varients = Field()

class TypeOfProduct(Item):
    type = Field()
    regular_price = Field()
    sale_price = Field()
    availability = Field()

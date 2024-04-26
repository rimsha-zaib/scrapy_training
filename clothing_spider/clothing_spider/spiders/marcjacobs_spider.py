"""
This Scrapy spider crawls marcjacobs.com to extract product information including brand, title, price, colors, sizes, and images. 
It handles proxy usage, and avoids overwhelming the website with a configurable download delay.

Methods:
    start_requests: Generates initial requests.
    parse_homepage: Extracts top-level and sub-level categories.
    make_nav_request: Constructs requests to navigate to sub-category pages.
    parse_products: Extracts product URLs and pagination links of a specific category.
    parse_color: Extracts color-specific product data.
    parse_detail: Extracts detailed product information and yield it.
"""

import copy
from urllib.parse import urljoin

import scrapy
from scrapy import Request

from ..items import ProductItem, SizeItem


class MarcjacobsSpiderSpider(scrapy.Spider):
    name = "marcjacobs_spider"
    allowed_domains = ["marcjacobs.com"]
    start_urls = ["https://marcjacobs.com/"]
    countries_info = [
        # ('country', 'currency', 'language', 'home_url')
        ('uk', 'PS', 'enn', 'https://marcjacobs.com/')
    ]
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'ROBOTSTXT_OBEY' : False,

    }

    def start_requests(self):
        country_info = self.countries_info[0]
        country, currency, language, home_url = country_info
        categories = []
        yield Request(
            home_url,
            self.parse_homepage,
            meta={'country': country, 'currency': currency, 'language': language, 'categories': categories}
        )

    def parse_homepage(self, response):
        for level1 in response.css('.nav-modal__sub-list li.navL1'):
            cat1 = level1.css('a::text,.navHeaven > span::text').get()
            for level2 in level1.css(".navL2 ul li"):
                cat2 = level2.css('a::text').get()
                url2 = level2.css("a::attr(href)").get()
                if url2:
                    yield self.make_nav_request(response, [cat1, cat2], url2)

    def make_nav_request(self, response, categories, url):
        meta = copy.deepcopy(response.meta)
        meta['categories'] = categories
        return response.follow(url, self.parse_products, meta=meta)

    def parse_products(self, response):
        product_urls = response.css('.product-grid__list-element .lockup-card::attr(href), .product-grid__list-element .plp-card::attr(href)').getall()
        for url in product_urls:
            yield Request(urljoin(response.url, url), self.parse_color, meta=response.meta)

        next_page_url = response.css('.spinner::attr(data-url)').get()
        if next_page_url:
            yield response.follow(next_page_url, self.parse_products, meta=response.meta)

    def parse_color(self, response):
        colors = response.css('div.swiper-wrapper input.colorDrawer__item-radio, li.heaven-color__item-container picture')
        if colors:
            for color in colors:
                color_label = color.css('::attr(data-label)').get()
                product_data = color.css('::attr(data-url)').get()
                yield Request(product_data, self.parse_detail, meta={
                    'country': response.meta['country'],
                    'currency': response.meta['currency'],
                    'language': response.meta['language'],
                    'categories': response.meta['categories'],
                    'color_label': color_label
                })

    def parse_detail(self, response):
        product = ProductItem()
        product_data = response.json()['product']
        product['country_code'] = response.meta['country']
        product['language_code'] = response.meta['language']
        product['currency'] = response.meta['currency']
        product['brand'] = product_data['brand']
        product['category_names'] = self.get_categories(response)
        product['base_sku'] = product_data['id']
        product['title'] = product_data['productName']
        product['color_name'] = response.meta['color_label']
        product['image_urls'] = self.get_images(response, product_data)
        product['description_text'] = product_data['longDescription']
        product['new_price_text'], product['old_price_text'] = self.get_prices(product_data)
        product['size_infos'] = self.get_sizes_info(product_data)
        product['use_size_level_prices'] = False

        yield product

    def get_prices(self, product_data):
        new_price = product_data['price']['sales']['formatted']
        old_price = product_data['price']['list']['formatted'] if product_data['price']['list'] else new_price
        return new_price, old_price

    def get_categories(self, response):
        category_names = response.meta['categories']
        return [category.strip().replace('\n', '') for category in category_names]

    def get_images(self, response, product_data):
        return [response.urljoin(image['url']) for image in product_data['images']['large']]

    def get_sizes_info(self, product_data):
        sizes_info = []
        sizes = [attr['values'] for attr in product_data['variationAttributes'] if attr["attributeId"] == "size"]
        for size_values in sizes:
            for size_value in size_values:
                size = SizeItem()
                size['size_name'] = size_value['displayValue']
                size['stock'] = 1 if size_value['selectable'] else 0
                sizes_info.append(size)
        return sizes_info

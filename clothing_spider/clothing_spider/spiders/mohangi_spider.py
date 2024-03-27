"""
Spider for scraping product information from Mohagni website.

This spider navigates through the Mohagni website to extract details of various products
including their title, category, URL, images, description, and variants.

Attributes:
    name (str): The name of the spider.
    start_urls (list): List of URLs to start crawling from.
    product_pattern : Regular expression pattern to extract product data from JavaScript.
    des_pattern : Regular expression pattern to clean JSON data for description.
    stitched_pattern (re.Pattern): Regular expression pattern to identify stitched product variants.

Methods:
    parse(self, response): Parses the initial response and initiates category parsing.
    parse_category(self, response): Extracts category title and pagination links for each category and initiates  parse_products.
    extract_pagination_links(self, response) : Extracts pagination links from the response and appends '?page=1' to ensure all pages are included. 
    parse_products(self, response): Parses product pages and initiates product detail parsing for each product url.
    parse_product_detail(self, response): Parses product detail pages and extracts relevant information.
    get_varients(self, response): Extracts product variants based on stitching and stitching type.

"""

import json
import re

import scrapy
from scrapy import Request

from ..items import ProductItem, SizeItem


class MohangiSpider(scrapy.Spider):
    name = 'mohangi'
    start_urls = ['https://mohagni.com/']

    product_pattern = re.compile(r'product: ({.*?}),\s*collectionId:')
    des_pattern = re.compile(r'(?<="gtin14": )([^,\s]+)')
    stitched_pattern = re.compile(r'\b(STITCHED|S|M|L|XL)\b', re.IGNORECASE)
    identifier_pattern = r'/products/(\w+-\d+)'


    def parse(self, response):
        links = self.extract_links(response)
        for link in links:
            yield response.follow(link, callback=self.parse_category)
    
    def parse_category(self, response):
        category = response.css("h2.collection-hero__title::text")[1].get()
        pagination_links = self.extract_pagination_links(response)
        for link in pagination_links:
            yield response.follow(link, callback=self.parse_products, meta = {"category": category})

    def extract_pagination_links(self, response):
        # Extract pagination links from response
        pagination_links = set(response.css("ul.pagination__list a::attr(href)").getall())
        pagination_links.add(response.url + '?page=1')
        return pagination_links

    def parse_products(self, response):
        products = response.css("li.grid__item")
        for product in products:
            url = response.urljoin(product.css("a.full-unstyled-link::attr(href)").get())
            yield Request(url, callback=self.parse_product_detail,  meta = {"category": response.meta.get("category")})

    def parse_product_detail(self, response):
        product = ProductItem()
        product['url'] = response.url
        product['identifier'] = re.search(self.identifier_pattern, response.url).group(1)
        product['currency'] = 'PKR'
        product['country_code'] = 'PK'
        product['use_size_level_prices'] = True
        product['title'] = self.get_title(response)
        product["category_names"] = response.meta.get("category")
        product['image_urls'] = self.get_images(response)
        product['description_text']= self.get_description(response)
        product["size_infos"] = self.get_varients(response)
        yield product


    def get_varients(self, response):
        stitched_products = []
        unstitched_products = []
        
        # Check if the CSS selector for variant labels exists
        style_label = response.css("fieldset.product-form__input legend.form__label::text").get()
        if style_label and "Style" in style_label:
            # Assume product is stitched and unstitched
            data = response.css("variant-radios.no-js-hidden script::text").get()
            json_data = json.loads(data)
            if json_data:
                stitched_products = self.process_stitched_products(json_data)
                unstitched_products = self.process_unstitched_product(response)
        elif style_label and "Size" in style_label:
            # Assume product is just stitched
            data = response.css("variant-radios.no-js-hidden script::text").get()
            json_data = json.loads(data)
            if json_data:
                stitched_products = self.process_stitched_products(json_data)
        else:
            # Assume product is unstitched
            unstitched_products = self.process_unstitched_product(response)
        return stitched_products + unstitched_products

    def extract_links(self, response):
        # Extracting links from two different selectors
        swiper_links = response.css("div.swiper a::attr(href)").getall()
        multicolumn_links = response.css("ul.multicolumn-list a::attr(href)").getall()
        return set(swiper_links + multicolumn_links)
    
    def process_stitched_products(self, variants):
        stitched_products = []
        for variant in variants:
            title = variant.get('title', '')
            # Ensures that "unstitched" variants are not added twice to the list of stitched products.
            if self.stitched_pattern.search(title):
                stitched_product = SizeItem()
                stitched_product["size_name"] = title
                stitched_product["size_current_price_text"] = variant.get('price') / 100  
                stitched_product["size_original_price_text"] = (variant["compare_at_price"] or variant["price"]) / 100
                stitched_product["stock"] = int(variant.get("available"))
                stitched_products.append(stitched_product)
        return stitched_products

    def process_unstitched_product(self, response):
        unstitched_products = []
        # Extracting product information from JavaScript if available
        javascript_scripts = response.css('script[type="text/javascript"]::text').get()
        match = self.product_pattern.findall(javascript_scripts)
        if match:
            json_data = json.loads(match[0])
            unstitched_product = SizeItem()
            unstitched_product["size_name"] = "UNSTITCHED"
            unstitched_product["size_current_price_text"] = json_data["price"] / 100
            unstitched_product["size_original_price_text"] = (json_data["compare_at_price"] or json_data["price"]) / 100
            unstitched_product["stock"] = int(json_data['available'])
            unstitched_products.append(unstitched_product)
        return unstitched_products

    def get_images(self, response):
        images = ['https:' + img for img in response.css("li.product__media-item div.product__media img::attr(src)").getall()]
        return list(set(images))
    
    def get_title(self, response):
        return response.css("div.product__title h1::text").get()

    def get_description(self,response):
        data = response.css('script[type="application/ld+json"]::text')[1].get().strip().replace('\n', '').replace('\\"', '"')
        data = self.des_pattern.sub(r'"\1"', data)
        return json.loads(data)["description"]
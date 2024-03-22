import json
import re

import scrapy
from scrapy import Request

from ..items import ProductItem, TypeOfProduct


class MohangiSpider(scrapy.Spider):
    name = 'mohangi'
    start_urls = ['https://mohagni.com/']

    product_pattern = re.compile(r'product: ({.*?}),\s*collectionId:')
    des_pattern = re.compile(r'(?<="gtin14": )([^,\s]+)')
    stitched_pattern = re.compile(r'\b(STITCHED|S|M|L|XL)\b', re.IGNORECASE)


    def parse(self, response):
        links = self.extract_links(response)
        for link in links:
            yield response.follow(link, callback=self.parse_category)
    
    def parse_category(self, response):
        category = response.css("h2.collection-hero__title::text")[1].get()
        next_page_links = set(response.css("ul.pagination__list a::attr(href)").getall())
        next_page_links.add(response.url + '?page=1')
        for link in next_page_links:
            yield response.follow(link, callback=self.parse_products, meta = {"category": category})

    def parse_products(self, response):
        products = response.css("li.grid__item")
        for product in products:
            url = response.urljoin(product.css("a.full-unstyled-link::attr(href)").get())
            yield Request(url, callback=self.parse_product_detail,  meta = {"category": response.meta.get("category")})

    def parse_product_detail(self, response):
        product = ProductItem()
        product['title'] = response.css("div.product__title h1::text").get()
        product["category"] = response.meta.get("category")
        product['url'] = response.url
        product['img'] = self.get_images(response)
        product['description']= self.get_description(response)
        product["varients"] = self.get_varients(response)
        yield product

    def get_varients(self, response):
        stitched_products = []
        unstitched_products = []
        
        # Check if the CSS selector for variant labels exists
        variant_labels = response.css("fieldset.product-form__input label")
        if variant_labels:
            data = response.css("variant-radios.no-js-hidden script::text").get()
            json_data = json.loads(data)
            if json_data:
                stitched_products = self.process_stitched_products(json_data)
                unstitched_products = self.process_unstitched_product(response)
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
            if self.stitched_pattern.search(title):
                stitched_product = TypeOfProduct()
                stitched_product["type"] = title
                stitched_product["sale_price"] = variant.get('price') / 100  
                stitched_product["regular_price"] = variant.get('compare_at_price', variant.get('price')) / 100
                stitched_product["availability"] = self.get_availability(variant.get("available"))
                stitched_products.append(stitched_product)
        return stitched_products

    def process_unstitched_product(self, response):
        unstitched_products = []
        # Extracting product information from JavaScript if available
        javascript_scripts = response.css('script[type="text/javascript"]::text').get()
        match = self.product_pattern.findall(javascript_scripts)
        if match:
            json_data = json.loads(match[0])
            unstitched_product = TypeOfProduct()
            unstitched_product["type"] = "UNSTITCHED"
            unstitched_product["sale_price"] = json_data["price"] / 100
            unstitched_product["regular_price"] = json_data["compare_at_price"] / 100
            unstitched_product["availability"] = self.get_availability(json_data['available'])
            unstitched_products.append(unstitched_product)
        return unstitched_products

    def get_images(self, response):
        images = ['https:' + img for img in response.css("li.product__media-item div.product__media img::attr(src)").getall()]
        return list(set(images))

    def get_availability(self, availablility):
        if availablility:
            return "In Stock"
        else:
            return "Out of Stock"

    def get_description(self,response):
        data = response.css('script[type="application/ld+json"]::text')[1].get().strip().replace('\n', '').replace('\\"', '"')
        data = self.des_pattern.sub(r'"\1"', data)
        return json.loads(data)["description"]
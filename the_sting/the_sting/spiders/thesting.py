"""
Spider for scraping product information from The Sting website.

This spider navigates through the categories of The Sting website to extract details of various products including their title, category, URL, images, description, and pricing information.

Methods:
    start_requests(self): Generates initial requests to start crawling.
    parse_homepage(self, response): Parses the homepage to extract main categories and initiate category parsing.
    parse_sub_nav(self, response): Parses sub-navigation menu to extract sub-categories and initiate product parsing.
    make_nav_request(self, response, categories, url): Constructs and returns a request object with updated metadata.
    parse_products(self, response): Parses product pages to extract product URLs and initiate product detail parsing.
    parse_color(self, response): Parses product color variations and initiates product detail parsing for each variant individually.
    parse_detail(self, response): Extract product detail.

"""

import copy
from urllib.parse import urljoin

import scrapy
from scrapy import Request

from ..items import ProductItem, SizeItem


class ThestingSpider(scrapy.Spider):
    name = "thesting"
    allowed_domains = ["www.thesting.com"]
    start_urls = ["https://www.thesting.com/nl-nl"]

    countries_info = [
        # ('country', 'currency', 'language', 'home_url')
        ('nl', 'EUR', 'nl', 'https://www.thesting.com/nl-nl')
    ]

    def start_requests(self):
        country_info = self.countries_info[0]
        country, currency, language, home_url  = country_info
        yield scrapy.Request(home_url, self.parse_homepage, meta={'country': country, 'currency': currency, 'language': language})

    def parse_homepage(self, response):
        main_categories = response.css('div.header__menu-secondary[data-category]::attr(data-category)').getall()
        main_categories_url = response.css("div.header__menu-navigation a::attr(href)").getall()
        
        for category , category_url in zip(main_categories, main_categories_url):
            categories = []
            stats_product_count = {}
            categories.append(category)
            yield scrapy.Request(
            url = response.urljoin(category_url),
            callback = self.parse_sub_nav,
            meta = {'country': response.meta['country'], 
                'currency': response.meta['currency'], 
                'language': response.meta['language'], 
                'categories': categories,
                'stats_product_count': stats_product_count
                }
        )
    def parse_sub_nav(self, response):
        cat1 = response.meta["categories"][0]
        sub_cat_url = response.css(f'div[data-category="{cat1}"] a.header__menu-navigation-link--is-secondary')
        for level1 in sub_cat_url:
            url2 = level1.attrib['href']
            cat2 = level1.css('::text').get()
            yield self.make_nav_request(response, [cat1, cat2], url2)

            for level2 in level1.css('a + div .header__menu-flyout-navigation-wrapper'):
                cat3 = level2.css('.header__menu-flyout-navigation-label::text').get().strip()
                
                for level3 in level2.css('span + nav a'):
                    cat4 = level3.css('span::text').get()
                    url4 = level3.attrib['href']
                    yield self.make_nav_request(response, [cat1, cat2,cat3,cat4], url4)
                
    def make_nav_request(self, response, categories, url):
        meta = copy.deepcopy(response.meta)
        meta['categories'] = categories
        return response.follow(url, self.parse_products, meta=meta)

    def parse_products(self,response):
        product_urls = response.css('div.product a.product-tile__link::attr(href)').getall()
        stats_product_count = response.meta.get('stats_product_count') 
        key = '/'.join(response.meta['categories'])
        stats_product_count.setdefault(key, 0)
        stats_product_count[key] += len(product_urls)  
        meta = copy.deepcopy(response.meta)
        meta['stats_product_count'] = stats_product_count
        for url in product_urls:
            yield Request(urljoin(response.url, url), self.parse_color, meta=meta)

        next_page_url = response.css("a.pagination__action--next::attr(href)").get()
        if next_page_url and next_page_url != '#':
            yield response.follow(next_page_url, self.parse_products, meta=meta)

    def parse_color(self, response):
        yield from self.parse_detail(response)
        for clr_url in response.css(".c-color-swatches a::attr(href)").getall():
            yield response.follow(clr_url, self.parse_detail, meta=response.meta)


    def parse_detail(self, response):  
        product = ProductItem()
        product['url'] = response.url
        product['country_code'] = response.meta['country']
        product['language_code'] = response.meta['language']
        product['currency'] = response.meta['currency']
        product['title'] = self.get_title(response)
        product['brand'] = self.get_brand(response)
        product['category_names'] = response.meta['categories']
        product['description_text'] = self.get_description(response)
        product['color_name'] = self.get_color_name(response)
        product['image_urls'] = self.get_img(response)
        product['old_price_text'] = self.get_old_price(response)
        product['new_price_text'] = self.get_new_price(response) or product['old_price_text']
        product['size_infos'] = self.get_sizes_info(response)
        product['use_size_level_prices'] = False
        yield product

    def get_title(self, response):
        return response.css("h1.product-detail-aside__title::text").get()
    
    def get_brand(self, response):
        return response.css("a.product-detail-aside__brand::text").get()
    
    def get_color_name(self, response):
        return response.css("span.product-detail-aside__current-color::text").get()
    
    def get_old_price(self, response):
        return response.css("data.product-detail-aside__price::text").get()
    
    def get_new_price(self, response):
        return response.css("data.product-detail-aside__price--is-on-sale::text").get()

    def get_sizes_info(self, response):
        sizes_info = []

        for size_element in response.css(".c-product-detail-aside span.radio__size-value"):
            size = SizeItem()
            size['size_name'] = size_element.css("::text").get().strip()
            size['stock'] = 0 if size_element.xpath("following-sibling::span[@class='radio__size-label']") else 1
            sizes_info.append(size)
        return sizes_info

    def get_description(self, response):
        description = []
        accordion_items = response.css("div.c-accordion details.accordion__detail")

        for item in accordion_items:
            summary_text = item.css("summary.accordion__item-summary::text").get().strip()
            content_text = " ".join(text.strip() for text in item.css("div.accordion__item-content *::text").getall() if text.strip())
            
            if summary_text and content_text:
                description.append(f"{summary_text}\n{content_text}")
        
        return "\n\n".join(description).strip() if description else 'N/A'
    
    def get_img(self, response):
        return [img.css("picture source::attr(data-srcset)").get().split('?')[0]
                for img in response.css(".product-image-grid__item .image__holder")
                if img.css("picture source::attr(data-srcset)").get()]

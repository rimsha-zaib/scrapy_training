"""
Scrapy spider for scraping product information from the Arket website (https://www.arket.com).

This spider crawls through the website to extract information about various products, including their titles,
descriptions, prices, images, sizes, and colors.

Methods:
    start_requests: Method to generate initial requests to the home page of the website.
    parse_homepage: Callback method to parse the home page and extract navigation links to different categories.
    make_nav_request: Helper method to create requests for navigating to category pages.
    parse_products: Callback method to parse product listing pages and extract product URLs.
    parse_color: Callback method to parse product color variations and extract color-specific information.
    parse_detail: Callback method to parse product detail pages and extract detailed product information.
    generate_pagination_links: This method calculates the number of pages based on the total number of products and the specified view count
    per page. It then generates pagination links with incremented page numbers and adjusted view counts.

"""

import copy
from urllib.parse import urljoin

import scrapy
from scrapy import Request

from ..items import ProductItem, SizeItem


class ArketSpiderSpider(scrapy.Spider):
    name = "arket_spider"
    allowed_domains = ["www.arket.com"]

    countries_info = [
        # ('country', 'currency', 'language', 'home_url')
        ('kr', 'KRW', 'ko', 'https://www.arket.com/ko-kr/index.html')
    ]

    def start_requests(self):
        country_info = self.countries_info[0]
        country, currency, language, home_url  = country_info
        yield scrapy.Request(home_url, self.parse_homepage, meta={'country': country, 'currency': currency, 'language': language})
    
    def parse_homepage(self, response):
        for level1 in response.css("div.category-wrapper"):
            cat1 = level1.css("::attr(data-title)").get()
            for level2 in level1.css(".curated-categories a.department-link"):
                url2 = level2.css("::attr(href)").get()
                cat2 = level2.css("::text").get()
                yield self.make_nav_request(response, [cat1, cat2], url2)

            for level2 in level1.css(".main-categories .folder-category"):
                cat2 = level2.css("h3.a-heading-3 a::text").get().strip()
                for level3 in level2.css("li.subcategory"):
                    url3 = level3.css("::attr(href)").get()
                    cat3 = level3.css("a::text").get().strip()
                    yield self.make_nav_request(response, [cat1, cat2,cat3], url3)

    def make_nav_request(self, response, categories, url):
        meta = copy.deepcopy(response.meta)
        meta['categories'] = categories
        return response.follow(url, self.parse_products, meta=meta)
    
    def parse_products(self, response):
        product_urls = response.css('.o-product > a::attr(href)').getall()
        for url in product_urls:
            yield Request(urljoin(response.url, url), self.parse_color, meta=response.meta)

        view_cnt = response.css('input[name="viewCnt"]::attr(value)').get()
        if view_cnt is not None and view_cnt != 0 and view_cnt != '0':
            pagination_links = self.generate_pagination_links(response)
            for pagination_link in pagination_links:
                yield Request(pagination_link, self.parse_products, meta=response.meta)

    def parse_color(self, response):
        sec_id = response.css('form [name="sectId"]::attr(value)').get()
        for clr in response.css("div.color-swatch-container div.js-swatch"):
            clr_id = clr.css("a.colorLink::attr(data-slitm-cd)").get()
            clr_url = f"https://www.arket.com/ko-kr/pda/changeItemInfo.html?slitmCd={clr_id}&sectId={sec_id}&preview=false"
            yield response.follow(clr_url, self.parse_detail, meta=response.meta)

    def parse_detail(self, response):
        product = ProductItem()
        product_data = response.json()
        product['url'] = self.get_url(response)
        product['country_code'] = self.get_country_code(response)
        product['language_code'] = self.get_language_code(response)
        product['currency'] = self.get_currency(response)
        product['title'] = self.get_title(product_data)
        product['image_urls'] = self.get_image_urls(product_data)
        product['description_text'] = self.get_product_desscription(product_data)
        product['category_names'] = self.get_categories(response)
        product['color_name'] = self.get_colorname(product_data)
        product['identifier'] = self.get_identifier(product_data)
        product['size_infos'] = self.get_sizes(product_data)
        product['new_price_text'], product['old_price_text'] = self.get_prices(product_data)
        product['use_size_level_prices'] = False

        yield product

    def get_image_urls(self, product_data):
        img_url =  [image['imflNm'] for image in product_data['imgList']]
        base_url = "https://image.thehyundai.com/static/"
        return [f'{base_url}{img[-8]}/{img[-9]}/{img[-10]}/{img[7:9]}/{img[5:7]}/{img}' for img in img_url]

    def get_prices(self, product_data):
        new_price = product_data['itemPtc']['sellPrc']
        old_price = product_data['itemPtc']['csmPrc']
        return new_price, old_price

    def get_product_desscription(self, product_data):
        descriptions = {}
        for item in product_data['itemPtc']['itstInfoList']:
            title = item.get('itstTitl')
            content = item.get('itstCntn')
            if title:
                descriptions[title] = content
        return descriptions or 'N/A'
            
    def generate_pagination_links(self, response):
        view_cnt = int(response.css('input[name="viewCnt"]::attr(value)').get())
        total_cnt = int(response.css('input[name="totalCnt"]::attr(value)').get())
        page_size = int(response.css('input[name="pageSize"]::attr(value)').get())
        sect_id = response.css('input[name="sect_id"]::attr(value)').get()
        num_pages = -(-total_cnt // view_cnt)
        pagination_links = []
        for page_num in range(2, num_pages + 1):
            new_view_cnt = page_size * (page_num - 1)
            pagination_link = f"https://www.arket.com/ko-kr/dpa/ctgrListAddItem.html?sect_id={sect_id}&pageNum={page_num}&viewCnt={new_view_cnt}&totalCnt={total_cnt}&pageSize={page_size}"
            pagination_links.append(pagination_link)
        return pagination_links
    
    def get_url(self, response):
        return response.url
    
    def get_country_code(self, response):
        return response.meta['country']
    
    def get_language_code(self, response):
        return response.meta['language']
    
    def get_currency(self, response):
        return response.meta['currency']
    
    def get_categories(self, response):
        return response.meta['categories']
    
    def get_title(self, product_data):
        return product_data['itemPtc']['engItemNm']
    
    def get_colorname(self, product_data):
        return product_data['itemPtc']['clrEngNm']
    
    def get_identifier(self, product_data):
        return product_data['sizeAndStockBySlitmCdList'][0]['articleCd']
    
    def get_sizes(self, product_data):
        sizes_info = []
        for size_value in product_data['sizeAndStockBySlitmCdList'][0]['sizeAndStockVOList']:
                size = SizeItem()
                size['size_name'] = size_value['u2aNm']
                size['stock'] = 1 if size_value['stockCount'] > 0 else 0
                sizes_info.append(size)
        return sizes_info


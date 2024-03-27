# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import json
import sqlite3


class ClothingSpiderPipeline:
    def process_item(self, item, spider):
        if item is not None:
            adapter = ItemAdapter(item)
            if not adapter["description_text"] :
                adapter["description_text"] = "Not provided"
        return item

class SqlitePipeline:

    def __init__(self):

        ## Create/Connect to database
        self.con = sqlite3.connect('Products.db')

        ## Create cursor, used to execute commands
        self.cur = self.con.cursor()
        ## Create quotes table if none exists
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS Products (
                url TEXT,
                identifier TEXT,
                currency TEXT,
                country_code TEXT,
                use_size_level_prices BOOL,
                title TEXT,
                image_urls TEXT,
                description_text TEXT,
                category_names TEXT,
                size_infos TEXT
            )
        """)

    def process_item(self, item, spider):
        self.cur.execute("select * from Products where url = ?", (item['url'],))
        result = self.cur.fetchone()
        if result:
            spider.logger.warn("Item already in database: %s" % item['url'])
        
        ## If text isn't in the DB, insert data
        else:
            serialized_types= []
            for size in item["size_infos"]:
                serialized_type = {
                    "size_name" : size["size_name"],
                    "size_current_price_text": size["size_current_price_text"],
                    "size_original_price_text": size["size_original_price_text"],
                    "stock": size["stock"]
                }
                serialized_types.append(serialized_type)

            ## Define insert statement
            self.cur.execute("""
                INSERT INTO Products (url, identifier, currency, country_code, use_size_level_prices, title, image_urls, description_text, category_names , size_infos) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ? ,?)
            """,
            (
                item["url"],
                item['identifier'],
                item['currency'],
                item['country_code'],
                item['use_size_level_prices'],
                item["title"],
                json.dumps(item["image_urls"]),
                item["description_text"],
                item["category_names"],
                json.dumps(serialized_types)
            ))

            ## Execute insert of data into database
            self.con.commit()
        return item



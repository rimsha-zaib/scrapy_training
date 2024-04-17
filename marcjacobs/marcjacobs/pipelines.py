# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import json
import sqlite3


class MarcjacobsPipeline:
    def process_item(self, item, spider):
        return item
    
class SqlitePipeline:
    def __init__(self):
        # Create/Connect to database
        self.con = sqlite3.connect('Clothes.db')
        # Create cursor, used to execute commands
        self.cur = self.con.cursor()
        # Create Products table if it doesn't exist
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS Clothes (
                base_sku TEXT,
                country_code TEXT,
                language_code TEXT,
                currency TEXT,  
                title TEXT,
                brand TEXT,
                category_names TEXT,
                description_text TEXT,
                color_name TEXT,  
                image_urls TEXT,
                old_price_text TEXT,
                new_price_text TEXT,
                use_size_level_prices BOOL,
                size_infos TEXT
            )
        """)

    def process_item(self, item, spider):
        self.cur.execute("SELECT * FROM Clothes WHERE base_sku = ?", (item['base_sku'],))
        result = self.cur.fetchone()
        if result:
            spider.logger.warning("Item already in database: %s" % item['base_sku'])
        else:
            # Serialize size_infos
            serialized_types = []
            if 'size_infos' in item:
                for size in item["size_infos"]:
                    serialized_type = {
                        "size_name": size.get("size_name", ""),
                        "stock": size.get("stock", "")
                    }
                    serialized_types.append(serialized_type)

            # Define insert statement
            self.cur.execute("""
                INSERT INTO Clothes (base_sku, country_code, language_code, currency, title, brand, category_names,
                                      description_text, color_name, image_urls, old_price_text, new_price_text, 
                                      use_size_level_prices, size_infos) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["base_sku"],
                item.get('country_code', ""),
                item.get('language_code', ""),
                item.get('currency', ""),
                item.get("title", ""),
                item.get("brand", ""),
                json.dumps(item.get("category_names", "")),
                item.get("description_text", ""),
                item.get("color_name", ""),
                json.dumps(item.get("image_urls", "")),
                item.get("old_price_text", ""),
                item.get("new_price_text", ""),
                item.get('use_size_level_prices', False),
                json.dumps(serialized_types)
            ))

            # Execute insert of data into database
            self.con.commit()
        return item

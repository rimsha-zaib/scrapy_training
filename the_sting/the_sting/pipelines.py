import json
import sqlite3
import scrapy

class SqlitePipeline:
    def __init__(self):
        # Create/Connect to database
        self.con = sqlite3.connect('Products.db')
        # Create cursor, used to execute commands
        self.cur = self.con.cursor()
        # Create Products table if it doesn't exist
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS Products (
                url TEXT,
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
        self.cur.execute("SELECT * FROM Products WHERE url = ?", (item['url'],))
        result = self.cur.fetchone()
        if result:
            spider.logger.warning("Item already in database: %s" % item['url'])
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
                INSERT INTO Products (url, country_code, language_code, currency, title, brand, category_names,
                                      description_text, color_name, image_urls, old_price_text, new_price_text, 
                                      use_size_level_prices, size_infos) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["url"],
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

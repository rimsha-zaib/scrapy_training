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
            if not adapter["description"] :
                adapter["description"] = "Not provided"
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
                title TEXT,
                url VARCHAR(255),
                img VARCHAR(255),
                description TEXT,
                category TEXT,
                varients TEXT
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
            for type in item["varients"]:
                serialized_type = {
                    "type" : type["type"],
                    "regular_price": type["regular_price"],
                    "sale_price": type["sale_price"],
                    "availability": type["availability"]
                }
                serialized_types.append(serialized_type)

            ## Define insert statement
            self.cur.execute("""
                INSERT INTO Products (title, url, img, description, category , varients) VALUES (?, ?, ?, ?, ?,?)
            """,
            (
                str(item["title"]),
                str(item["url"]),
                str(item["img"]),
                str(item["description"]),
                str(item["category"]),
                json.dumps(serialized_types)
            ))

            ## Execute insert of data into database
            self.con.commit()
        return item



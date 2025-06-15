import logging
from pymilvus import MilvusClient
from pymilvus.model import dense
import os

# 配置 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

## 1 准备嵌入模型
embedding_function = dense.OpenAIEmbeddingFunction(model_name='text-embedding-3-large', api_key=os.getenv("OPENAI_API_KEY"), base_url="https://aiyjg.lol/v1")

## 2 连接Milvus
db_path = "HW-03/data/financial_db.db"
client = MilvusClient(db_path)

## 3 查询
collection_name = "financial_concepts"

query = "Triple A" # "AAA"	债券评级中的最高级别，常被误写为 "Triple A"
query_embeddings = embedding_function([query])

# 搜索余弦相似度最高的
search_result = client.search(
    collection_name=collection_name,
    data=[query_embeddings[0].tolist()],
    limit=5,
    output_fields=["term_name"]
)

logging.info(f"Search result for '{query}':")
for idx, hit in enumerate(search_result[0], start=1):
    logging.info(f"{idx}. ID: {hit['id']}, term_name: {hit['entity']['term_name']}, distance: {hit['distance']}")

# 2025-06-15 13:43:13,541 - INFO - Search result for 'Triple A':
# 2025-06-15 13:43:13,541 - INFO - 1. ID: 458742843176910863, term_name: AAA, distance: 0.6566182374954224
# 2025-06-15 13:43:13,541 - INFO - 2. ID: 458742843176911578, term_name: American Academy Of Actuaries - AAA, distance: 0.6016656756401062
# 2025-06-15 13:43:13,541 - INFO - 3. ID: 458742843176911580, term_name: American Accounting Association - AAA, distance: 0.5598386526107788
# 2025-06-15 13:43:13,541 - INFO - 4. ID: 458742889357537468, term_name: AAI, distance: 0.5457965731620789
# 2025-06-15 13:43:13,541 - INFO - 5. ID: 458742843176910852, term_name: A-/A3, distance: 0.5391387939453125

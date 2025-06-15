import pandas as pd
import logging

from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient
from pymilvus.model import dense
import os

# 配置 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

## 1 准备嵌入模型
embedding_function = dense.OpenAIEmbeddingFunction(model_name='text-embedding-3-large', api_key=os.getenv("OPENAI_API_KEY"), base_url="https://aiyjg.lol/v1")

## 2 准备数据源

# 文件路径
file_path = "HW-03/data/万条金融标准术语.csv"

# 加载数据
if not os.path.exists(file_path):
    raise FileNotFoundError(f"找不到文件: {file_path}")

logging.info("Loading data from CSV")
df = pd.read_csv(file_path, 
                 dtype=str, 
                 low_memory=False,
                 names=['term_name', 'term_type'],  # 指定列名
                 header=None)  # 指定没有表头
df = df.fillna("NA")

logging.info(df.head())

## 3 连接Milvus，创建集合和模式

db_path = "HW-03/data/financial_db.db"
client = MilvusClient(db_path)

vector_dim = len(embedding_function(["dummy"])[0])
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=vector_dim),
    FieldSchema(name="term_name", dtype=DataType.VARCHAR, max_length=100),
]
schema = CollectionSchema(fields, description="Financial Concepts", enable_dynamic_field=False)
collection_name = "financial_concepts"

if not client.has_collection(collection_name):
    try:
        client.create_collection(collection_name=collection_name, schema=schema)
        logging.info(f"创建了新的集合 {collection_name}")
    except Exception as e:
        logging.error(f"创建集合失败: {e}")
        raise

    ## 4 为向量字段添加索引
    index_params = client.prepare_index_params()
    index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE", params={"nlist": 1024})
    client.create_index(collection_name=collection_name, index_params=index_params)

    ## 5 插入数据
    # 获取所有术语
    terms = df['term_name'].tolist()  # 使用新的列名
    total_terms = len(terms)
    batch_size = 1000  # 增加批量大小
    total_batches = (total_terms + batch_size - 1) // batch_size  # 向上取整
    
    logging.info(f"准备处理 {total_terms} 条术语")
    logging.info(f"批量大小: {batch_size} 条/批")
    logging.info(f"预计总批次数: {total_batches} 批")
    logging.info("-" * 50)

    # 批量生成向量嵌入
    total_tokens = 0
    for i in range(0, total_terms, batch_size):
        batch_terms = terms[i:i + batch_size]
        current_batch = i // batch_size + 1
        # 生成向量
        vectors = embedding_function(batch_terms)
        
        # 准备插入数据
        insert_data = [
            {
                "vector": vector,
                "term_name": term
            }
            for vector, term in zip(vectors, batch_terms)
        ]
        
        # 估算token使用（假设每个词平均2个token）
        batch_tokens = sum(len(term.split()) * 2 for term in batch_terms)
        total_tokens += batch_tokens
        
        # 打印进度和统计信息
        progress = (i + len(batch_terms)) / total_terms * 100
        logging.info(f"进度: {progress:.1f}% ({i + len(batch_terms)}/{total_terms})")
        logging.info(f"当前批次: {current_batch}/{total_batches}")
        logging.info(f"本批数据: {len(insert_data)} 条")
        logging.info(f"本批预估token: {batch_tokens}")
        logging.info(f"累计预估token: {total_tokens}")
        logging.info(f"示例数据: {insert_data[0]}")
        logging.info("-" * 50)

        try:
            res = client.insert(
                collection_name=collection_name,
                data=insert_data
            )
            logging.info(f"Inserted batch {i // batch_size + 1}, result: {res}")
        except Exception as e:
            logging.error(f"Error inserting batch {i // batch_size + 1}: {e}")

    logging.info("数据插入完成")
    logging.info(f"总预估token使用: {total_tokens}")
    

    # 加载集合
    client.load_collection("financial_concepts")
    logging.info("已加载集合")
    logging.info("知识库构建完成")
else:
    logging.info(f"集合 {collection_name} 已存在，跳过数据插入")
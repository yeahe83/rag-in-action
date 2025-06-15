from llama_index.core import SimpleDirectoryReader
from llama_parse import LlamaParse
import json
import os

"""
Load File：在框架中增加更多的 File Loading 的工具和参数。
Chunk File：可以选择第一步 Load 进来的文本，按照不同方案，不同大小对文档进行切块，保存后 JSON 文档格式不变（文档块大小发生改变）。
Parse File：这个功能相对独立。可以直接导入 PDF，或者 Markdown 等有格式的文档，对其中的表、图进行解析，表格内容保存成 Markdown 等文本，图片内容转换为文字，最终仍然转换成文字格式的 JSON，供后续做 Embedding。也就是说，这些图、表中的知识还是会进入向量数据库，同时保存尽可能多的 Metadata（供索引，以及最终生成回答时使用）。

参考：
https://github.com/huangjia2019/rag-project01-framework/blob/77718201c40060c52f02436a4489b93069a55987/backend/main.py#L593

文件加载
https://docs.llamaindex.ai/en/stable/module_guides/loading/simpledirectoryreader/
https://docs.llamaindex.ai/en/stable/api_reference/readers/file/

文件分块
https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/
"""

def load_file(input_file):
    """
    加载单个文件
    
    Args:
        input_file: 文件路径，例如 "90-文档-Data/黑悟空/设定.txt"
    
    Returns:
        dict: 包含文件信息的JSON格式数据
    """
    # 根据文件类型选择不同的reader
    file_ext = os.path.splitext(input_file)[1].lower()
    
    
    dir_reader = SimpleDirectoryReader(
        input_files=[input_file]
    )
    documents = dir_reader.load_data()

    if file_ext == '.pdf':
        if not documents or not any(doc.text.strip() for doc in documents):
            print("SimpleDirectoryReader解析结果为空，尝试使用LlamaParse...")
            parser = LlamaParse(result_type="markdown")
            documents = parser.load_data(input_file)

    # 准备返回的JSON数据
    result = {
        "file_count": len(documents),
        "documents": []
    }

    for i, doc in enumerate(documents, 1):
        doc_info = {
            "index": i,
            "file_name": doc.metadata.get('file_name', '未知'),
            "file_type": doc.metadata.get('file_type', '未知'),
            "file_size": doc.metadata.get('file_size', '未知'),
            "creation_date": doc.metadata.get('creation_date', '未知'),
            "last_modified_date": doc.metadata.get('last_modified_date', '未知'),
            "content_length": len(doc.text),
            "content": doc.text,  # 返回完整文本内容
            "metadata": doc.metadata
        }
        result["documents"].append(doc_info)

    return result

def chunk_file(loaded_response):
    """
    对文件进行重新切块，格式不变，但内容发生变化

    Args:
        loaded_response: load_file的返回值

    Returns:
        dict: 重新切块后的JSON格式数据
    """
    return result

if __name__ == "__main__":
    # result = load_file("90-文档-Data/黑悟空/黑神话悟空.pdf")
    result = load_file("90-文档-Data/山西文旅/佛光寺-ch.pdf")
    # result = chunk_file(result)
    print("\n返回的JSON数据:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

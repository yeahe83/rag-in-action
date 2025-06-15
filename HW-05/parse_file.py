from unstructured.partition.pdf import partition_pdf

# 解析 PDF 结构，提取文本和表格
file_path = "90-文档-Data/复杂PDF/billionaires_page-1-5.pdf"  # 修改为你的文件路径

elements = partition_pdf(
    file_path,
    skip_infer_table_types=False, # 不跳过推断表格类型
    strategy="hi_res",  # 使用高精度策略
    infer_table_structure=True # 推断表格结构 text_as_html
)  # 解析PDF文档

def elements_to_visual_tree(elements, ignore_header_footer=False) -> str:
    """生成元素结构树的可视化字符串
    
    Args:
        elements: 待处理元素列表
        ignore_header_footer: 是否忽略页眉页脚
        
    Returns:
        结构化的树形文本
    """

    # 创建一个元素ID到元素的映射
    element_map = {element.id: element for element in elements if hasattr(element, 'id')}

    # 预处理，规则如下：
    # 1、忽略Header和Footer元素
    # 2、如果Title元素如果原父节点为Header则删除父节点关联
    # 3、其他元素如果原父节点为Header，则向上就近找Title元素作为父节点
    if ignore_header_footer:
        for idx, element in enumerate(elements):
            if not hasattr(element, 'id'):
                continue

            parent_id = getattr(element.metadata, 'parent_id', None)
            if not parent_id:
                continue
            
            parent_element = element_map.get(parent_id)
            if not parent_element:
                continue

            # 规则2和规则3的分支处理
            if parent_element.category == "Header":
                if element.category == "Title":
                    # 规则2：删除父节点关联
                    element.metadata.parent_id = None  # ✅ 直接置空
                else:
                    # 规则3：寻找最近的Title作为新父节点
                    new_parent_id = None
                    for i in range(idx-1, -1, -1):
                        if elements[i].category == "Title":
                            new_parent_id = elements[i].id
                            break
                    element.metadata.parent_id = new_parent_id  # ✅ 可能是None

        # 重新创建一个元素ID到元素的映射，但是排除header元素和footer元素
        element_map = {element.id: element for element in elements if hasattr(element, 'id') and element.category not in ["Header", "Footer"]}

    parent_child_map = {} # 父节点到子节点的映射
    for element in element_map.values():
        parent_id = getattr(element.metadata, "parent_id", None)
        parent_child_map.setdefault(parent_id, []).append(element)

    output = []  # 改用列表收集输出

    def _build_node(element, prefix="", is_last=False) -> str:
        lines = []
        max_length = 45
        raw_text = element.text.replace('\n', ' ').strip()
        display_text = f"{raw_text[:max_length]}..." if len(raw_text) > max_length else raw_text
        line = f"[{element.category}] {display_text}"
        
        # 构建当前节点行
        lines.append(f"{prefix}{'└── ' if is_last else '├── '}{line}")

        # 构建子节点
        new_prefix = prefix + ("    " if is_last else "│   ")
        children = parent_child_map.get(element.id, [])
        for i, child in enumerate(children):
            child_lines = _build_node(child, new_prefix, i == len(children)-1)
            lines.extend(child_lines.split('\n'))  # 处理递归返回的多行

        return '\n'.join(lines)

    # 构建完整输出
    roots = parent_child_map.get(None, [])
    full_output = []
    for i, root in enumerate(roots):
        full_output.append(_build_node(root, is_last=i == len(roots)-1))
    
    return '\n'.join(full_output)

def elements_to_markdown(elements, ignore_header_footer=True):
    """将elements转换为Markdown格式的层级文本"""
    from collections import defaultdict

    # 预处理逻辑（与print_element_tree保持一致）
    element_map = {e.id: e for e in elements if hasattr(e, 'id')}
    
    if ignore_header_footer:
        for idx, element in enumerate(elements):
            if not hasattr(element, 'id'):
                continue

            parent_id = getattr(element.metadata, 'parent_id', None)
            if not parent_id:
                continue
            
            parent_element = element_map.get(parent_id)
            if not parent_element:
                continue

            # 规则2和规则3的分支处理
            if parent_element.category == "Header":
                if element.category == "Title":
                    # 规则2：删除父节点关联
                    element.metadata.parent_id = None  # ✅ 直接置空
                else:
                    # 规则3：寻找最近的Title作为新父节点
                    new_parent_id = None
                    for i in range(idx-1, -1, -1):
                        if elements[i].category == "Title":
                            new_parent_id = elements[i].id
                            break
                    element.metadata.parent_id = new_parent_id  # ✅ 可能是None

        # 重新创建一个元素ID到元素的映射，但是排除header元素和footer元素
        element_map = {element.id: element for element in elements if hasattr(element, 'id') and element.category not in ["Header", "Footer"]}

    # 构建父子关系映射
    parent_child_map = defaultdict(list)
    for element in element_map.values():
        parent_id = getattr(element.metadata, 'parent_id', None)
        parent_child_map[parent_id].append(element)

    # Markdown生成核心逻辑
    markdown_lines = []
    
    def _build_markdown(node, level=0):
        indent = "  " * level
        
        # 添加区块分隔空行
        if markdown_lines and markdown_lines[-1] != '':
            markdown_lines.append('')
        
        if node.category == "Table":
            table_lines = _handle_table(node, indent)
            markdown_lines.extend(table_lines)
            return
        
        # 处理文本内容
        text = node.text.strip()
        text = text.replace('\n', '  \n')  # Markdown换行符
        
        if node.category == "Title":
            prefix = f"{indent}## "
            markdown_lines.extend([f"{prefix}{text}", ''])  # 标题+空行
        else:
            prefix = f"{indent}- "
            markdown_lines.append(f"{prefix}{text}")
        
        # 递归子元素
        for child in parent_child_map.get(node.id, []):
            _build_markdown(child, level + 1)
        
    from bs4 import BeautifulSoup  # 需要安装bs4包

    def _handle_table(table_element, indent):
        """通过HTML转换处理表格"""
        markdown_lines = []
        
        # 优先使用text_as_html
        html_table = getattr(table_element.metadata, 'text_as_html', None)
        if html_table:
            try:
                # 使用BeautifulSoup解析HTML表格
                soup = BeautifulSoup(html_table, 'html.parser')
                rows = []
                for tr in soup.find_all('tr'):
                    cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                    if cells:
                        rows.append("| " + " | ".join(cells) + " |")
                
                # 生成Markdown表格
                if len(rows) >= 1:
                    # 添加表头分隔线
                    separator = "| " + " | ".join(["---"] * len(rows[0].split('|'))) + " |"
                    if len(rows) == 1:
                        markdown_lines.append(f"{indent}{rows[0]}")
                    else:
                        markdown_lines.append(f"{indent}\n".join([rows[0], separator] + rows[1:]))
                return markdown_lines
            except Exception as e:
                print(f"表格解析失败: {str(e)}")
        
        # 回退到原始处理方式
        rows = []
        for row in parent_child_map.get(table_element.id, []):
            if row.category != "TableRow":
                continue
            cells = [
                cell.text.strip() 
                for cell in parent_child_map.get(row.id, [])
                if cell.category == "TableCell"
            ]
            rows.append("| " + " | ".join(cells) + " |")
        
        if len(rows) >= 1:
            separator = "| " + " | ".join(["---"] * len(rows[0].split('|'))) + " |"
            markdown_lines.append(f"{indent}\n".join(rows))

        # 添加表格前后空行
        if markdown_lines:
            markdown_lines.insert(0, '')
            markdown_lines.append('')

        return markdown_lines

    # 从根节点开始生成
    roots = parent_child_map.get(None, [])
    for root in roots:
        _build_markdown(root)
    
    return "\n".join(markdown_lines)

# 还是有错位
print(elements_to_visual_tree(elements, ignore_header_footer=True))

# ├── [Title] WIKIPEDIA
# │   └── [NarrativeText] The Free Encyclopedia
# ├── [Title] The World's Billionaires
# ├── [Image] a
# ├── [NarrativeText] The World's Billionaires is an annual ranking...
# ├── [Title] The World's Billionaires
# ├── [Title] List of the world's billionaires, ranked in o...
# ├── [Image] Billionaires' net worth (in trillions of U.S....
# ├── [FigureCaption] The net worth of the world's billionaires inc...
# ├── [NarrativeText] In 2018, Amazon founder Jeff Bezos was ranked...
# ├── [Title] Methodology
# │   └── [NarrativeText] Each year, Forbes employs a team of over 50 r...
# ├── [Title] Publication details
# │   ├── [Table] Publisher Whale Media Investments Forbes fami...
# │   ├── [NarrativeText] and some refuse to answer any questions.[8] B...
# │   ├── [NarrativeText] https://en.wikipedia.org/wiki/The_World%27s_B...
# │   ├── [NarrativeText] 1/33
# │   ├── [NarrativeText] stock are priced to market on a date roughly ...
# │   └── [NarrativeText] When a living individual has dispersed his or...
# ├── [Title] Annual rankings
# │   └── [NarrativeText] The rankings are published annually in March,...
# ├── [Title] Legend
# │   └── [Table] Icon Description Has not changed from the pre...
# ├── [Title] 2023
# │   └── [NarrativeText] In the 37th annual Forbes list of the world's...
# ├── [Title] https://en.wikipedia.org/wiki/The_World%27s_B...
# │   └── [NarrativeText] https://en.wikipedia.org/wiki/The_World%27s_B...
# ├── [Title] Net worth
# │   └── [Table] No. Name (USD) Age Nationality Primary source...
# ├── [Title] 2022
# │   ├── [NarrativeText] In the 36th annual Forbes list of the world's...
# │   ├── [NarrativeText] https://en.wikipedia.org/wiki/The_World%27s_B...
# │   └── [Table] No. Name Net worth (USD) Age Nationality Prim...
# ├── [Title] 2021
# │   ├── [NarrativeText] In the 35th annual Forbes list of the world's...
# │   └── [Table] No. Name Net worth (USD) Age Nationality Sour...
# ├── [Title] 2020
# │   ├── [NarrativeText] https://en.wikipedia.org/wiki/The_World%27s_B...
# │   ├── [NarrativeText] In the 34th annual Forbes list of the world's...
# │   └── [Table] No. Name Net worth (USD) Age Nationality Sour...
# ├── [Title] 2019
# │   ├── [NarrativeText] In the 33rd annual Forbes list of the world's...
# │   └── [Table] No. Name Net worth (USD) Age Nationality Sour...
# └── [Title] 2018
#     └── [NarrativeText] https://en.wikipedia.org/wiki/The_World%27s_B...

# print(elements_to_markdown(elements, ignore_header_footer=True))

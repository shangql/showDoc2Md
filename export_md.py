#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShowDoc转Markdown导出工具（按项目分类）
功能：从SQLite数据库提取page表的markdown内容并按项目目录分类保存
支持JSON格式(runapi)和纯Markdown格式的自动识别与转换
"""

import os
import re
import json
import sqlite3
import html
from pathlib import Path
from collections import defaultdict

# 配置路径
DB_PATH = "/Users/sql/GitHub/showDoc2Md/DbFile/showdoc.db.php"
OUTPUT_DIR = "/Users/sql/GitHub/showDoc2Md/MdOutFiles"

def sanitize_filename(title: str) -> str:
    """
    清理文件名，移除非法字符

    参数:
        title: 原始标题

    返回:
        清理后的安全文件名
    """
    # 替换Windows/macOS/Linux不支持的非法字符
    safe_name = re.sub(r'[|/<>:"?*\n\r\t]', '_', title)
    # 移除连续下划线和首尾空格
    safe_name = re.sub(r'_+', '_', safe_name).strip(' _')
    # 限制最大长度
    max_len = 200
    if len(safe_name) > max_len:
        safe_name = safe_name[:max_len]
    return safe_name if safe_name else "untitled"

def sanitize_dirname(name: str) -> str:
    """
    清理目录名，移除非法字符

    参数:
        name: 原始目录名

    返回:
        清理后的安全目录名
    """
    # 目录名更严格，不能包含/和\
    safe_name = re.sub(r'[|/<>:"?*\n\r\t]', '_', name)
    safe_name = re.sub(r'_+', '_', safe_name).strip(' _')
    max_len = 150
    if len(safe_name) > max_len:
        safe_name = safe_name[:max_len]
    return safe_name if safe_name else "unknown_project"

def convert_json_to_markdown(content: str) -> str:
    """
    将runapi的JSON格式转换为可读的Markdown格式

    参数:
        content: 原始JSON字符串（可能是HTML实体编码）

    返回:
        格式化后的Markdown字符串
    """
    try:
        # 先解码HTML实体（如 &quot; -> "）
        decoded_content = html.unescape(content)
        data = json.loads(decoded_content)
    except (json.JSONDecodeError, TypeError):
        # 解码后仍然不是JSON，尝试直接解析原内容
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            # 不是JSON格式，直接返回原内容
            return content

    # 检查是否是runapi格式
    if not isinstance(data, dict):
        return content

    info = data.get("info", {})
    if info.get("from") != "runapi":
        # 不是runapi格式，可能是纯Markdown
        return content

    # 提取关键信息
    title = data.get("page_title") or info.get("title", "未命名接口")
    description = info.get("description", "")
    method = info.get("method", "").upper()
    url = info.get("url", "")
    remark = info.get("remark", "")

    request = data.get("request", {})
    response = data.get("response", [])

    # 构建Markdown文档
    md_lines = []

    # 标题
    md_lines.append(f"# {title}")
    md_lines.append("")

    # 描述
    if description:
        md_lines.append(f"**接口描述:** {description}")
        md_lines.append("")

    # 基本信息
    md_lines.append("## 基本信息")
    md_lines.append("")
    md_lines.append(f"| 项目 | 值 |")
    md_lines.append("|:-----|:-----|")
    md_lines.append(f"| 请求地址 | `{url}` |")
    md_lines.append(f"| 请求方法 | `{method}` |")
    if remark:
        md_lines.append(f"| 备注 | {remark} |")
    md_lines.append("")

    # 请求参数
    md_lines.append("## 请求参数")
    md_lines.append("")

    # Header参数
    headers = request.get("headers", [])
    if headers and len(headers) > 0:
        header_items = [h for h in headers if isinstance(h, dict) and h.get("disable") != "1"]
        if header_items:
            md_lines.append("### Header")
            md_lines.append("")
            md_lines.append("| 参数名 | 参数值 | 必填 | 描述 |")
            md_lines.append("|:-----|:-----|:-----|:-----|")
            for h in header_items:
                name = h.get("name", "")
                value = h.get("value", "")
                required = "Y" if h.get("require") == "1" else "N"
                desc = h.get("remark", "")
                md_lines.append(f"| {name} | `{value}` | {required} | {desc} |")
            md_lines.append("")

    # FormData参数
    formdata = request.get("formdata", [])
    if formdata and len(formdata) > 0:
        formdata_items = [f for f in formdata if isinstance(f, dict) and f.get("disable") != "1"]
        if formdata_items:
            md_lines.append("### Body (form-data)")
            md_lines.append("")
            md_lines.append("| 参数名 | 类型 | 必填 | 描述 |")
            md_lines.append("|:-----|:-----|:-----|:-----|")
            for f in formdata_items:
                name = f.get("name", "")
                ptype = f.get("type", "string")
                required = "Y" if f.get("require") == "1" else "N"
                desc = f.get("remark", "")
                value = f.get("value", "")
                if value:
                    desc = f"{desc} (示例值: {value})"
                md_lines.append(f"| {name} | {ptype} | {required} | {desc} |")
            md_lines.append("")

    # URL参数
    params = request.get("params", [])
    if params and isinstance(params, list) and len(params) > 0:
        param_items = [p for p in params if isinstance(p, dict) and p.get("disable") != "1"]
        if param_items:
            md_lines.append("### URL参数")
            md_lines.append("")
            md_lines.append("| 参数名 | 类型 | 必填 | 描述 |")
            md_lines.append("|:-----|:-----|:-----|:-----|")
            for p in param_items:
                name = p.get("name", "")
                ptype = p.get("type", "string")
                required = "Y" if p.get("require") == "1" else "N"
                desc = p.get("remark", "")
                md_lines.append(f"| {name} | {ptype} | {required} | {desc} |")
            md_lines.append("")

    # JSON Body
    json_desc = request.get("jsonDesc", [])
    if json_desc and isinstance(json_desc, list) and len(json_desc) > 0:
        json_items = [j for j in json_desc if isinstance(j, dict) and j.get("disable") != "1"]
        if json_items:
            md_lines.append("### Body (JSON)")
            md_lines.append("")
            md_lines.append("| 参数名 | 类型 | 必填 | 描述 |")
            md_lines.append("|:-----|:-----|:-----|:-----|")
            for j in json_items:
                name = j.get("name", "")
                ptype = j.get("type", "string")
                required = "Y" if j.get("require") == "1" else "N"
                desc = j.get("remark", "")
                md_lines.append(f"| {name} | {ptype} | {required} | {desc} |")
            md_lines.append("")

    # 返回参数
    if response and isinstance(response, list) and len(response) > 0:
        md_lines.append("## 返回参数")
        md_lines.append("")
        md_lines.append("| 参数名 | 类型 | 必填 | 描述 |")
        md_lines.append("|:-----|:-----|:-----|:-----|")
        for r in response:
            if isinstance(r, dict):
                name = r.get("name", "")
                ptype = r.get("type", "string")
                required = "Y" if r.get("require") == "1" else "N"
                desc = r.get("remark", "")
                md_lines.append(f"| {name} | {ptype} | {required} | {desc} |")
        md_lines.append("")

    return "\n".join(md_lines)

def export_markdown_by_item():
    """
    按项目目录分类导出所有页面为markdown文件
    """
    # 确保输出目录存在
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    print(f"📂 正在连接数据库: {DB_PATH}")

    # 连接SQLite数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 第一步：获取所有项目（item），建立item_id到item_name的映射
    cursor.execute("""
        SELECT item_id, item_name
        FROM item
        WHERE is_del = 0
          AND item_name IS NOT NULL
          AND item_name != ''
        ORDER BY item_id
    """)
    item_rows = cursor.fetchall()

    # 构建 item_id -> item_name 映射表
    item_map = {item_id: item_name for item_id, item_name in item_rows}

    # 获取所有未删除且有内容且有关联项目的页面
    cursor.execute("""
        SELECT page_id, item_id, page_title, page_content
        FROM page
        WHERE is_del = 0
          AND item_id IS NOT NULL
          AND item_id != 0
          AND page_title IS NOT NULL
          AND page_title != ''
          AND page_content IS NOT NULL
          AND page_content != ''
        ORDER BY item_id, page_id
    """)
    page_rows = cursor.fetchall()

    print(f"✅ 找到 {len(item_rows)} 个项目, {len(page_rows)} 个页面，准备导出...")

    # 统计每个项目的页面数量
    project_page_count = defaultdict(list)
    for page_id, item_id, page_title, page_content in page_rows:
        if item_id in item_map:
            project_page_count[item_id].append((page_id, page_title, page_content))

    # 创建项目目录
    dir_map = {}  # item_id -> 目录路径
    for item_id, item_name in item_rows:
        dir_name = sanitize_dirname(item_name)
        dir_path = os.path.join(OUTPUT_DIR, dir_name)
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        dir_map[item_id] = dir_path

    print(f"📁 已创建 {len(dir_map)} 个项目目录")

    # 导出统计
    total_success = 0
    total_error = 0
    json_converted = 0
    project_stats = {}

    # 按项目分组导出
    for item_id, pages in project_page_count.items():
        project_name = item_map[item_id]
        project_dir = dir_map[item_id]
        project_success = 0
        project_error = 0

        for page_id, page_title, page_content in pages:
            try:
                # 判断内容格式并转换
                # 检测是否是runapi的JSON格式（可能是HTML实体编码）
                is_json_format = (
                    ('"info"' in page_content or '&quot;info&quot;' in page_content) and
                    ('"from"' in page_content or '&quot;from&quot;' in page_content) and
                    ('"request"' in page_content or '&quot;request&quot;' in page_content)
                )
                if is_json_format:
                    # JSON格式(runapi)，需要转换
                    page_content = convert_json_to_markdown(page_content)
                    json_converted += 1

                # 生成安全的文件名
                filename = sanitize_filename(page_title)
                file_path = os.path.join(project_dir, f"{filename}.md")

                # 直接覆盖已有文件（不创建文件名_1、_2等新文件）
                # 因为重新导出时需要更新已有文件内容

                # 写入markdown文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(page_content)

                project_success += 1
                total_success += 1

            except Exception as e:
                project_error += 1
                total_error += 1
                print(f"   ❌ [page_id={page_id}] {str(e)}")

        project_stats[project_name] = {"success": project_success, "error": project_error}

    # 关闭数据库连接
    conn.close()

    # 输出导出结果摘要
    print("\n" + "="*60)
    print("📊 导出完成 - 按项目分类")
    print("="*60)

    # 按成功数量排序显示项目统计
    sorted_stats = sorted(project_stats.items(), key=lambda x: x[1]["success"], reverse=True)

    for project_name, stats in sorted_stats:
        status = "✅" if stats["error"] == 0 else "⚠️"
        print(f"   {status} {project_name}: {stats['success']} 个页面" +
              (f" ({stats['error']} 错误)" if stats['error'] > 0 else ""))

    print("-"*60)
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print(f"📊 总计: ✅ {total_success} 个成功, ❌ {total_error} 个失败")
    print(f"🔄 JSON转换: {json_converted} 个")
    print("="*60)

if __name__ == "__main__":
    export_markdown_by_item()
# ShowDoc 转 Markdown 导出工具

将 ShowDoc 私有化部署的 SQLite 数据库中的接口文档导出为 Markdown 文件，并按项目目录分类整理。

## 功能特性

- **按项目分类**: 根据 `item` 表的项目名称创建目录结构
- **格式自动转换**: 支持两种内容格式的自动识别与转换
  - **RunAPI JSON 格式**: 将 JSON 格式的接口文档转换为可读的 Markdown
  - **纯 Markdown 格式**: 直接保留原始 Markdown 内容
- **HTML 实体解码**: 自动处理数据库中编码的 HTML 实体（如 `&quot;` → `"`）
- **文件名安全处理**: 移除文件名中的非法字符（`|`, `<`, `>`, `:`, `/`, `\`, `?`, `*`）
- **增量更新**: 直接覆盖已有文件，方便定时同步更新

## 目录结构

```
showDoc2Md/
├── DbFile/
│   └── showdoc.db.php          # ShowDoc SQLite 数据库文件
├── MdOutFiles/                 # Markdown 导出输出目录
│   ├── 项目名称A/               # 按项目名创建的目录
│   │   ├── 接口1.md
│   │   └── 接口2.md
│   └── 项目名称B/
│       └── 接口3.md
└── export_md.py                # 导出脚本
```

## 数据库结构

### item 表（项目表）

```sql
CREATE TABLE "item" (
    `item_id` INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    `item_name` TEXT,
    `item_description` TEXT,
    `uid` INTEGER,
    `username` TEXT,
    `password` TEXT,
    `addtime` INTEGER,
    `last_update_time` INTEGER DEFAULT 0,
    `item_domain` TEXT DEFAULT '',
    `item_type` INT(1) DEFAULT '1',
    `is_archived` INT(1) DEFAULT '0',
    `is_del` INT(1) DEFAULT '0'
);
```

### page 表（页面表）

```sql
CREATE TABLE "page" (
    `page_id` INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
    `author_uid` INTEGER,
    `author_username` TEXT,
    `item_id` INTEGER,              -- 关联 item 表的 item_id
    `cat_id` INTEGER,
    `page_title` TEXT,              -- 用作 Markdown 文件名
    `page_content` TEXT,            -- 接口文档内容（JSON 或 Markdown 格式）
    `s_number` INTEGER DEFAULT 99,
    `addtime` INTEGER DEFAULT 0,
    `page_comments` TEXT DEFAULT '',
    `is_del` INT(1) DEFAULT '0',
    `page_addtime` INT(11) DEFAULT '0',
    `ext_info` CHAR(2000) DEFAULT ''
);
```

## RunAPI JSON 格式说明

当 `page_content` 字段包含 RunAPI 格式的 JSON 时，内容结构如下：

```json
{
    "page_title": "接口名称",
    "info": {
        "from": "runapi",
        "type": "api",
        "title": "接口名称",
        "description": "接口描述",
        "method": "POST",
        "url": "https://api.example.com/endpoint",
        "remark": "备注信息"
    },
    "request": {
        "headers": [...],
        "params": [...],
        "formdata": [...],
        "jsonDesc": [...]
    },
    "response": [...]
}
```

转换后的 Markdown 格式如下：

```markdown
# 接口名称

**接口描述:** 接口描述

## 基本信息

| 项目 | 值 |
|:-----|:-----|
| 请求地址 | `https://api.example.com/endpoint` |
| 请求方法 | `POST` |

## 请求参数

### Header

| 参数名 | 参数值 | 必填 | 描述 |
|:-----|:-----|:-----|:-----|

### Body (form-data)

| 参数名 | 类型 | 必填 | 描述 |
|:-----|:-----|:-----|:-----|

## 返回参数

| 参数名 | 类型 | 必填 | 描述 |
|:-----|:-----|:-----|:-----|
```

## 使用方法

### 1. 配置数据库路径

编辑 `export_md.py` 文件开头的配置项：

```python
# 数据库文件路径
DB_PATH = "/Users/sql/GitHub/showDoc2Md/DbFile/showdoc.db.php"

# Markdown 输出目录
OUTPUT_DIR = "/Users/sql/GitHub/showDoc2Md/MdOutFiles"
```

### 2. 运行导出脚本

```bash
python3 export_md.py
```

### 3. 查看导出结果

```
📂 正在连接数据库: /path/to/showdoc.db.php
✅ 找到 46 个项目, 1020 个页面，准备导出...
📁 已创建 46 个项目目录

============================================================
📊 导出完成 - 按项目分类
============================================================
   ✅ ebms: 280 个页面
   ✅ 雅培: 115 个页面
   ✅ giga-fulllink: 107 个页面
   ...
------------------------------------------------------------
📁 输出目录: /Users/sql/GitHub/showDoc2Md/MdOutFiles
📊 总计: ✅ 1020 个成功, ❌ 0 个失败
🔄 JSON转换: 542 个
============================================================
```

## 核心函数说明

### `sanitize_filename(title)`

清理文件名，移除以下非法字符：
- `|`, `<`, `>`, `:`, `/`, `\`, `?`, `*`
- 连续下划线合并为单个下划线
- 文件名最大长度限制为 200 字符

### `sanitize_dirname(name)`

清理目录名，与文件名清理类似，但更严格：
- 最大长度限制为 150 字符
- 空名称转换为 `unknown_project`

### `convert_json_to_markdown(content)`

将 RunAPI 的 JSON 格式转换为可读的 Markdown：

1. 解码 HTML 实体（`&quot;` → `"`）
2. 解析 JSON 数据
3. 提取关键字段：`page_title`、`info`、`request`、`response`
4. 构建格式化的 Markdown 表格

### `export_markdown_by_item()`

主导出函数：

1. 连接 SQLite 数据库
2. 查询所有未删除的项目和页面
3. 按项目创建目录结构
4. 自动检测内容格式（JSON 或 Markdown）
5. 转换并导出到对应目录

## 依赖

- Python 3.6+
- sqlite3（标准库）
- html（标准库）
- json（标准库）
- re（标准库）

无需安装额外依赖。

## 注意事项

1. **数据筛选**: 仅导出 `is_del = 0` 的记录
2. **空内容跳过**: `page_content` 为空或 `page_title` 为空的页面会被跳过
3. **文件覆盖**: 重新运行时会覆盖已有文件，实现增量更新
4. **字符编码**: 所有文件以 UTF-8 编码读写

## 常见问题

**Q: 导出的文件仍然是 JSON 格式没有转换？**

A: 检查 `page_content` 字段是否包含 `"info"`、`"from"`、`"request"` 关键字段。脚本会自动检测并转换。

**Q: 文件名有特殊字符无法创建文件？**

A: `sanitize_filename()` 函数会自动替换非法字符。

**Q: 如何只导出特定项目？**

A: 修改 SQL 查询语句，添加 `WHERE item_id = ?` 条件。

## License

MIT License
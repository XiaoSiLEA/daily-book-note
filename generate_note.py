#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日一书 · 小红书笔记自动生成脚本（云端版 / GitHub Actions 专用）
功能：从豆瓣热门书籍随机选书，生成小红书风格图文笔记，每天不重复
"""

import os
import sys
import json
import random
import re
import time
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ========== 配置 ==========
BASE_DIR = Path(__file__).parent.resolve()
WORK_DIR = BASE_DIR / "output"
HISTORY_FILE = BASE_DIR / "data" / "history.json"
LOG_FILE = BASE_DIR / "data" / "run.log"

# 模板路径（仓库内相对路径）
TEMPLATE_INDEX = BASE_DIR / "templates" / "phone-preview.html"
TEMPLATE_POST = BASE_DIR / "templates" / "post" / "rednote-post.html"

# 确保数据目录存在
(BASE_DIR / "data").mkdir(exist_ok=True)
WORK_DIR.mkdir(exist_ok=True)

# 时区（北京时间）
BJ_TZ = timezone(timedelta(hours=8))

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 图片下载专用请求头
IMG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://book.douban.com/",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

# 豆瓣图书标签（热门分类，按热度排序）
DOUBAN_TAGS = [
    {"name": "小说", "url": "https://book.douban.com/tag/小说?start=0&type=T", "category": "fiction"},
    {"name": "历史", "url": "https://book.douban.com/tag/历史?start=0&type=T", "category": "history"},
    {"name": "心理学", "url": "https://book.douban.com/tag/心理学?start=0&type=T", "category": "psychology"},
    {"name": "科幻", "url": "https://book.douban.com/tag/科幻?start=0&type=T", "category": "scifi"},
    {"name": "推理", "url": "https://book.douban.com/tag/推理?start=0&type=T", "category": "mystery"},
    {"name": "文学", "url": "https://book.douban.com/tag/文学?start=0&type=T", "category": "literature"},
    {"name": "哲学", "url": "https://book.douban.com/tag/哲学?start=0&type=T", "category": "philosophy"},
    {"name": "传记", "url": "https://book.douban.com/tag/传记?start=0&type=T", "category": "biography"},
    {"name": "社会", "url": "https://book.douban.com/tag/社会?start=0&type=T", "category": "society"},
    {"name": "成长", "url": "https://book.douban.com/tag/成长?start=0&type=T", "category": "growth"},
]

# ========== 工具函数 ==========
def log(msg):
    """日志输出"""
    timestamp = datetime.now(BJ_TZ).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_history():
    """加载历史记录"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            log(f"读取历史记录失败: {e}，将创建新记录")
    return {"used_books": [], "daily_notes": []}


def save_history(history):
    """保存历史记录"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log(f"保存历史记录失败: {e}")
        return False


def is_book_used(book_id, history):
    """检查书籍是否已使用过"""
    used_ids = {item["id"] for item in history.get("used_books", [])}
    return book_id in used_ids


# ========== 抓取热门书籍 ==========
def fetch_douban_tag(tag_info):
    """抓取豆瓣标签页热门书籍"""
    books = []
    try:
        resp = requests.get(tag_info["url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".subject-item")
        
        for item in items:
            try:
                link_el = item.select_one("h2 a")
                if not link_el:
                    continue
                    
                title = link_el.get("title", "").strip()
                detail_url = link_el.get("href", "")
                
                # 提取书籍ID
                book_id = ""
                m = re.search(r"subject/(\d+)", detail_url)
                if m:
                    book_id = m.group(1)
                
                # 封面
                cover_el = item.select_one(".pic img")
                cover_url = cover_el.get("src", "") if cover_el else ""
                
                # 作者/出版信息
                pub_el = item.select_one(".pub")
                pub_info = pub_el.get_text(strip=True) if pub_el else ""
                
                # 评分
                rating_el = item.select_one(".rating_nums")
                rating = rating_el.get_text(strip=True) if rating_el else ""
                
                # 简介
                intro_el = item.select_one(".info p")
                intro_short = intro_el.get_text(strip=True) if intro_el else ""
                
                if title and book_id:
                    books.append({
                        "id": f"douban_{book_id}",
                        "title": title,
                        "author": pub_info.split(" / ")[0] if " / " in pub_info else pub_info,
                        "publish_info": pub_info,
                        "cover_url": cover_url,
                        "detail_url": detail_url,
                        "rating": rating,
                        "intro_short": intro_short,
                        "tags": [tag_info["name"]],
                        "source": "豆瓣读书",
                        "category": tag_info["category"],
                    })
            except Exception as e:
                continue
        
        log(f"  抓取「{tag_info['name']}」成功，获取 {len(books)} 本书")
    except Exception as e:
        log(f"  抓取「{tag_info['name']}」失败: {e}")
    
    return books


def fetch_book_detail(book):
    """获取书籍详细信息（简介等）"""
    try:
        resp = requests.get(book["detail_url"], headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # 书籍简介
        intro_el = soup.select_one("#link-report .intro")
        if not intro_el:
            intro_el = soup.select_one(".intro")
        
        intro = ""
        if intro_el:
            intro = intro_el.get_text(strip=True)
            if len(intro) > 500:
                intro = intro[:500] + "…"
        
        # 作者简介
        author_intro_el = soup.select_one(".author-info .intro")
        author_intro = ""
        if author_intro_el:
            author_intro = author_intro_el.get_text(strip=True)[:300]
        
        # 封面大图
        big_cover_el = soup.select_one("#mainpic img")
        big_cover = ""
        if big_cover_el:
            big_cover = big_cover_el.get("src", "")
        
        book["intro"] = intro
        book["author_intro"] = author_intro
        book["big_cover"] = big_cover if big_cover else book["cover_url"]
        
        log(f"  获取《{book['title']}》详情成功")
        time.sleep(0.5)
        return True
    except Exception as e:
        log(f"  获取《{book['title']}》详情失败: {e}")
        book["intro"] = ""
        book["author_intro"] = ""
        book["big_cover"] = book.get("cover_url", "")
        return False


def fetch_all_books():
    """从所有来源抓取书籍"""
    log("开始抓取热门书籍...")
    all_books = []
    seen_ids = set()
    
    for tag in DOUBAN_TAGS:
        books = fetch_douban_tag(tag)
        for b in books:
            if b["id"] not in seen_ids:
                seen_ids.add(b["id"])
                all_books.append(b)
    
    log(f"共获取 {len(all_books)} 本独特书籍")
    return all_books


# ========== 选择书籍 ==========
def select_random_book(all_books, history):
    """随机选择一本未使用过的书"""
    unused_books = [b for b in all_books if not is_book_used(b["id"], history)]
    
    if not unused_books:
        log("所有书籍都已使用过！将重置历史记录...")
        history["used_books"] = []
        unused_books = all_books
    
    book = random.choice(unused_books)
    log(f"随机选中: 《{book['title']}》")
    return book


# ========== 生成小红书内容 ==========
def generate_note_content(book):
    """生成小红书笔记内容"""
    title = book["title"]
    author = book["author"]
    rating = book.get("rating", "")
    intro = book.get("intro", "")
    
    # === 标题（≤20字）===
    short_title = title if len(title) <= 6 else title[:6] + "…"
    
    title_styles = [
        f"读完这本书我沉默了",
        f"翻到凌晨3点的神作",
        f"谁懂啊，这本太上头",
        f"被这本书狠狠戳中",
        f"这本书真的值得读吗",
        f"今年读过最狠的一本",
        f"想推荐给所有人的书",
        f"读完后劲太大了…",
        f"《{short_title}》太绝了",
        f"为什么没人推《{short_title}》",
        f"《{short_title}》读完哭了",
        f"熬夜看完《{short_title}》",
    ]
    note_title = random.choice(title_styles)
    if len(note_title) > 20:
        note_title = note_title[:19] + "…"
    
    # === 正文 ===
    rating_text = f"豆瓣 {rating} 分" if rating else ""
    
    body_parts = []
    
    # 开场
    openings = [
        f"最近读完《{title}》，",
        f"周末一口气读完《{title}》，",
        f"朋友推荐的《{title}》，",
        f"刷到好多人推《{title}》，终于读完了，",
    ]
    
    feelings = [
        "真的被狠狠戳中了。",
        "读完久久不能平静。",
        "后劲太大了，连续想了好几天。",
        "我直接原地封神。",
        "没想到会这么好看。",
    ]
    
    body_parts.append(random.choice(openings) + random.choice(feelings))
    body_parts.append("")
    
    # 作者 + 评分
    if author and rating_text:
        body_parts.append(f"📖 {author}著 · {rating_text}")
        body_parts.append("")
    
    # 书籍简介
    if intro:
        short_intro = intro[:200]
        if len(intro) > 200:
            short_intro += "…"
        body_parts.append(short_intro)
        body_parts.append("")
    elif book.get("intro_short"):
        body_parts.append(book["intro_short"][:200])
        body_parts.append("")
    
    # 推荐理由
    reasons = [
        "1. 文笔真的好，读起来流畅又有质感",
        "2. 人物塑造太鲜活了，仿佛就在身边",
        "3. 结尾的反转/升华，看完愣了好久",
    ]
    
    category = book.get("category", "")
    nonfiction_cats = ["history", "psychology", "philosophy", "biography", "society", "growth"]
    if category in nonfiction_cats:
        reasons = [
            "1. 观点很新颖，打开了新思路",
            "2. 干货密度高，边读边划线",
            "3. 实用性强，看完就能用上",
        ]
    elif category in ["scifi", "mystery"]:
        reasons = [
            "1. 设定/诡计太惊艳了",
            "2. 全程高能，根本停不下来",
            "3. 真相揭晓时鸡皮疙瘩都起来了",
        ]
    
    body_parts.extend(reasons)
    body_parts.append("")
    
    # 收尾
    endings = [
        "真心推荐给所有喜欢看书的朋友。",
        "如果你也喜欢这类书，千万别错过。",
        "最近书荒的朋友可以冲这本！",
        "已经在重读第二遍了…",
    ]
    body_parts.append(random.choice(endings))
    
    note_body = "\n".join(body_parts)
    
    # === 标签（6-10个）===
    tags = []
    tags.append("书单推荐")
    tags.append("读书分享")
    
    # 书名标签
    short_tag = title[:8] if len(title) > 8 else title
    tags.append(short_tag)
    
    # 泛流量词
    tags.append("我的私人书单")
    tags.append("书籍推荐")
    tags.append("读书")
    
    # 分类标签
    cat_tag_map = {
        "fiction": "小说推荐",
        "literature": "文学",
        "history": "历史书单",
        "psychology": "心理学",
        "scifi": "科幻小说",
        "mystery": "推理小说",
        "philosophy": "哲学",
        "biography": "传记",
        "society": "社会",
        "growth": "成长书单",
    }
    if category in cat_tag_map:
        tags.append(cat_tag_map[category])
    else:
        tags.append("新书推荐")
    
    # 豆瓣标签
    if book.get("tags"):
        for t in book["tags"][:2]:
            if t and len(t) <= 10 and "连续上榜" not in t:
                tags.append(t)
    
    # 去重并限制数量
    seen_tags = set()
    unique_tags = []
    for t in tags:
        if t not in seen_tags and len(unique_tags) < 10:
            seen_tags.add(t)
            unique_tags.append(t)
    
    note_tags = ",".join(unique_tags)
    
    return note_title, note_body, note_tags


# ========== 生成笔记 ==========
def download_image(url, save_path):
    """下载图片"""
    if not url:
        return False
    
    urls_to_try = [url]
    
    small_url = url.replace("/l/", "/s/").replace("/m/", "/s/")
    if small_url != url:
        urls_to_try.append(small_url)
    
    for try_url in urls_to_try:
        for headers in [IMG_HEADERS, HEADERS]:
            try:
                resp = requests.get(try_url, headers=headers, timeout=15)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    with open(save_path, "wb") as f:
                        f.write(resp.content)
                    return True
            except Exception:
                continue
    
    log(f"  下载图片失败: {url[:60]}")
    return False


def create_note_structure(slug):
    """创建笔记目录结构"""
    note_dir = WORK_DIR / slug
    if note_dir.exists():
        timestamp = datetime.now(BJ_TZ).strftime("%H%M%S")
        note_dir = WORK_DIR / f"{slug}-{timestamp}"
    
    os.makedirs(note_dir / "post", exist_ok=True)
    os.makedirs(note_dir / "images", exist_ok=True)
    
    shutil.copy(TEMPLATE_INDEX, note_dir / "index.html")
    shutil.copy(TEMPLATE_POST, note_dir / "post" / "rednote-post.html")
    
    return note_dir


def inject_content(note_dir, title, body, tags, images):
    """向 HTML 注入内容"""
    html_file = note_dir / "post" / "rednote-post.html"
    
    if not html_file.exists():
        log(f"  错误: 内容文件不存在 {html_file}")
        return False
    
    # 处理标签
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    tag_list = tag_list[:10]
    tag_json = json.dumps([f"#{t}" if not t.startswith("#") else t for t in tag_list], ensure_ascii=False)
    
    # 处理图片
    img_json = json.dumps([f"../images/{img}" for img in images], ensure_ascii=False)
    
    # 转义正文
    body_escaped = body.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    title_escaped = title.replace("\\", "\\\\").replace('"', '\\"')
    
    # 构造 DATA 块
    data_block = f'''<!-- DATA SCHEMA BEGIN -->
<script id="post-data" type="application/json">
{{
  "images": {img_json},
  "title": "{title_escaped}",
  "body": "{body_escaped}",
  "tags": {tag_json}
}}
</script>
<script>
const DATA = JSON.parse(document.getElementById('post-data').textContent);
</script>
<!-- DATA SCHEMA END -->'''
    
    # 读取并替换 HTML
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        pattern = r'<!-- DATA SCHEMA BEGIN -->.*?<!-- DATA SCHEMA END -->'
        new_content = re.sub(pattern, data_block, content, flags=re.DOTALL)
        
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        log(f"  注入内容失败: {e}")
        return False


def generate_note(book):
    """生成完整的小红书笔记"""
    date_str = datetime.now(BJ_TZ).strftime("%Y%m%d")
    safe_title = re.sub(r'[^\w\u4e00-\u9fa5]', '', book["title"])[:10]
    slug = f"book-{date_str}-{safe_title}"
    
    log(f"生成笔记: {slug}")
    
    # 创建目录结构
    note_dir = create_note_structure(slug)
    
    # 下载封面图
    cover_url = book.get("big_cover") or book.get("cover_url", "")
    image_files = []
    
    if cover_url:
        ext = ".jpg"
        if cover_url.endswith(".png"):
            ext = ".png"
        cover_filename = f"cover{ext}"
        cover_path = note_dir / "images" / cover_filename
        if download_image(cover_url, cover_path):
            image_files.append(cover_filename)
            log(f"  封面图已下载: {cover_filename}")
    
    # 生成内容
    note_title, note_body, note_tags = generate_note_content(book)
    
    log(f"  标题: {note_title} ({len(note_title)}字)")
    log(f"  正文: {len(note_body)}字")
    log(f"  标签: {note_tags}")
    
    # 注入内容
    if inject_content(note_dir, note_title, note_body, note_tags, image_files):
        log(f"  ✓ 笔记生成成功: {note_dir}")
        return note_dir, note_title, note_body, note_tags, slug
    else:
        log("  ✗ 笔记生成失败")
        return None


def update_readme(history):
    """更新 README.md，列出所有生成的笔记"""
    readme_path = BASE_DIR / "README.md"
    lines = []
    lines.append("# 每日一书 · 小红书笔记自动生成")
    lines.append("")
    lines.append("> 每天上午 10:00（北京时间）自动从豆瓣热门书籍中随机选一本，生成小红书风格图文笔记。")
    lines.append("")
    lines.append(f"已生成 **{len(history.get('daily_notes', []))}** 篇笔记")
    lines.append("")
    lines.append("## 全部笔记")
    lines.append("")
    lines.append("| 日期 | 书名 | 标题 | 预览 |")
    lines.append("|------|------|------|------|")
    
    # 倒序排列，最新的在前面
    for note in reversed(history.get("daily_notes", [])):
        date = note.get("date", "")[:10]
        book_title = note.get("book_title", "")
        note_title = note.get("note_title", "")
        slug = note.get("slug", "")
        if slug:
            link = f"[👉 预览](output/{slug}/index.html)"
        else:
            link = "-"
        lines.append(f"| {date} | 《{book_title}》 | {note_title} | {link} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*由 GitHub Actions 自动生成 · 数据来源：豆瓣读书*")
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    log("  README.md 已更新")


# ========== 主流程 ==========
def main():
    log("=" * 50)
    log("每日一书 · 小红书笔记自动生成（云端版）")
    log("=" * 50)
    
    # 1. 加载历史记录
    history = load_history()
    log(f"历史记录: 已使用 {len(history.get('used_books', []))} 本书")
    
    # 2. 抓取热门书籍
    all_books = fetch_all_books()
    if not all_books:
        log("错误: 未能获取任何书籍数据")
        sys.exit(1)
    
    # 3. 随机选择一本书
    book = select_random_book(all_books, history)
    
    # 4. 获取书籍详情
    fetch_book_detail(book)
    
    # 5. 生成笔记
    result = generate_note(book)
    if not result:
        log("笔记生成失败")
        sys.exit(1)
    
    note_dir, note_title, note_body, note_tags, slug = result
    
    # 6. 更新历史记录
    history["used_books"].append({
        "id": book["id"],
        "title": book["title"],
        "author": book["author"],
        "date": datetime.now(BJ_TZ).strftime("%Y-%m-%d"),
    })
    
    history["daily_notes"].append({
        "date": datetime.now(BJ_TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "book_id": book["id"],
        "book_title": book["title"],
        "note_title": note_title,
        "note_dir": str(note_dir),
        "slug": slug,
        "tags": note_tags,
    })
    
    save_history(history)
    
    # 7. 更新 README
    update_readme(history)
    
    # 8. 输出 GitHub Actions 环境变量（供后续步骤使用）
    gh_output = os.environ.get("GITHUB_OUTPUT", "")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"book_title={book['title']}\n")
            f.write(f"note_title={note_title}\n")
            f.write(f"note_slug={slug}\n")
            f.write(f"note_dir={note_dir}\n")
    
    log("=" * 50)
    log(f"✓ 今日笔记生成完成！")
    log(f"  书籍: 《{book['title']}》")
    log(f"  标题: {note_title}")
    log(f"  目录: {note_dir}")
    log("=" * 50)


if __name__ == "__main__":
    main()

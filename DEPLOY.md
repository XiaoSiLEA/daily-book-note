# 部署指南 · GitHub Actions 云端自动运行

## 📋 准备工作

1. 一个 [GitHub](https://github.com) 账号（免费即可）
2. 本地安装 [Git](https://git-scm.com/)

## 🚀 部署步骤

### 第 1 步：创建 GitHub 仓库

1. 登录 GitHub，点击右上角 **New repository**
2. 仓库名随意，比如 `daily-book-note`
3. 选择 **Public**（公开仓库才能免费使用 GitHub Pages 预览）
4. 不用勾选初始化选项，直接 **Create repository**

### 第 2 步：上传代码

在本地 `daily-book-note-cloud` 文件夹中打开终端/PowerShell，执行：

```bash
# 进入文件夹
cd daily-book-note-cloud

# 初始化 Git
git init
git add .
git commit -m "init: 每日一书小红书笔记自动生成"

# 关联远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/daily-book-note.git

# 推送到 main 分支
git branch -M main
git push -u origin main
```

### 第 3 步：启用 GitHub Pages（可选，用于在线预览）

1. 打开仓库页面 → **Settings** → **Pages**
2. Source 选择 **Deploy from a branch**
3. Branch 选择 **main** / **root**
4. 点击 **Save**
5. 等几分钟后，就能通过 `https://你的用户名.github.io/daily-book-note/` 访问 README 和笔记预览

### 第 4 步：手动触发一次（验证）

1. 打开仓库页面 → **Actions**
2. 左边选择 **每日一书 · 小红书笔记自动生成**
3. 点击 **Run workflow** → **Run workflow**
4. 等待运行完成（约 1-2 分钟）
5. 回到仓库首页，看 README 是否已更新、output 目录是否有新生成的笔记

### 第 5 步：坐等每天自动生成

- ⏰ **每天北京时间 10:00** 自动运行
- 📚 从豆瓣 10 个热门分类随机选书，每天不重复
- 📝 生成的笔记自动提交到仓库
- 🔄 175 本书用完后自动重置

## 📂 仓库结构

```
daily-book-note/
├── .github/workflows/
│   └── daily-note.yml      # 定时任务配置
├── templates/              # 小红书笔记 HTML 模板
├── output/                 # 生成的笔记（每天一个文件夹）
│   └── book-YYYYMMDD-书名/
│       ├── index.html      # 手机预览页
│       ├── post/
│       └── images/
├── data/
│   └── history.json        # 历史记录（用于去重）
├── generate_note.py        # 主脚本
├── requirements.txt        # Python 依赖
├── README.md               # 笔记索引页（自动更新）
└── .gitignore
```

## ⚙️ 自定义配置

### 修改运行时间

编辑 `.github/workflows/daily-note.yml` 中的 `cron` 字段：

```yaml
schedule:
  - cron: '0 2 * * *'   # UTC 时间 = 北京时间 -8小时
```

常用时间对照：

| 北京时间 | UTC 时间 | cron 表达式 |
|---------|---------|------------|
| 08:00 | 00:00 | `0 0 * * *` |
| 09:00 | 01:00 | `0 1 * * *` |
| **10:00** | **02:00** | `0 2 * * *` |
| 12:00 | 04:00 | `0 4 * * *` |
| 18:00 | 10:00 | `0 10 * * *` |
| 21:00 | 13:00 | `0 13 * * *` |

### 修改书籍来源

编辑 `generate_note.py` 中的 `DOUBAN_TAGS` 列表，增删分类即可。

### 修改标题/正文风格

编辑 `generate_note.py` 中的 `generate_note_content()` 函数，调整 `title_styles`、`openings`、`feelings`、`reasons`、`endings` 等列表。

## ❓ 常见问题

**Q: 运行失败了怎么办？**
A: 打开仓库 → Actions → 点击失败的 run → 查看日志，一般是网络问题（豆瓣偶尔 418），重新 Run workflow 即可。

**Q: 笔记生成了但图片不显示？**
A: 豆瓣图片有防盗链，在 GitHub Pages 上看可能加载失败。可以点图片右键在新标签打开，或下载到本地查看。

**Q: 能完全离线运行吗？**
A: 不行，需要从豆瓣抓取书籍数据。但你可以扩展脚本，加入本地书籍库作为备选。

**Q: 每天的笔记会自动发小红书吗？**
A: 不会，这个脚本只生成 HTML 预览文件。要自动发布需要接入小红书开放平台 API（目前个人很难申请到）。

## 🔗 相关链接

- [GitHub Actions 文档](https://docs.github.com/cn/actions)
- [豆瓣读书](https://book.douban.com/)

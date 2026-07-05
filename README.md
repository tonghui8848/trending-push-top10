# GitHub Trending 每日推送

每天早上 9:00（北京时间）自动抓取 GitHub 今日热榜，翻译为中文后推送到微信。

## 原理

- 通过 GitHub Actions 在云端定时运行
- 抓取 [GitHub Trending](https://github.com/trending) 页面
- 使用 Google 翻译 API 将项目描述转为中文
- 通过 [Server酱](https://sct.ftqq.com/) 推送到微信

## 配置

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中新建一个 Secret：

| Name | Value |
|------|-------|
| `SENDKEY` | 你的 Server酱 SendKey |

获取 SendKey：关注微信公众号「方糖」→ 登录 https://sct.ftqq.com/ → 复制 SendKey

## 手动触发

在仓库 **Actions** 页面选择「GitHub Trending Daily Push」→ 点击 **Run workflow**

## 定时时间

- 北京时间每天 09:00 自动触发
- 对应 UTC 时间每天 01:00

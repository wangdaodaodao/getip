# 🚀 应急用节点备用

这是一个自动化脚本，旨在帮助您每日自动获取最新的节点订阅，并进行个性化处理，最终生成可供客户端使用的订阅文件。

## ✨ 功能特点

-   **每日自动更新**: 通过 GitHub Actions 定时任务，每日自动抓取最新节点。
-   **智能重命名**: 根据节点信息（如国家/地区）进行智能重命名，并添加日期后缀，方便识别。
-   **去重与排序**: 确保订阅列表的整洁和可用性。
-   **多格式输出**: 生成结构化的 JSON 文件和通用的 Base64 编码 VLESS 订阅文件。
-   **Cloudflare Pages 部署**: 自动将生成的订阅文件部署到 Cloudflare Pages，提供稳定的访问链接。

## 📂 文件结构

-   `.github/workflows/update.yml`: GitHub Actions 工作流配置文件，定义了自动化任务的触发条件和执行步骤。
-   `scraper.py`: 核心爬虫脚本，负责抓取、处理和生成节点订阅文件。
-   `requirements.txt`: Python 依赖库列表。
-   `public/`: 部署到 Cloudflare Pages 的输出目录，包含 `nodes.json` 和 `sub.txt`。

## 🛠️ 如何本地运行

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/wangdaodaodao/getip.git
    cd getip
    ```
2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **运行脚本**:
    ```bash
    python scraper.py
    ```
    运行后，会在 `public/` 目录下生成 `nodes.json` 和 `sub.txt` 文件。

## ⚙️ 如何配置 GitHub Actions (自动化部署)

为了实现每日自动更新和部署，您需要配置 GitHub Actions。

### 1. 配置 Secrets

在您的 GitHub 仓库中，前往 `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`，添加以下 Secrets：

-   `CLOUDFLARE_API_TOKEN`: 您的 Cloudflare API Token。确保该 Token 具有编辑 Cloudflare Pages 的权限。
-   `CLOUDFLARE_ACCOUNT_ID`: 您的 Cloudflare 账户 ID。

### 2. 配置 `update.yml`

`update.yml` 文件位于 `.github/workflows/` 目录下。请确保以下配置正确：

-   **定时触发**:
    ```yaml
    on:
      schedule:
        - cron: '0 22 * * *' # 每天 UTC 时间 22:00 执行，即北京时间次日早上 6 点
    ```
    您可以根据需要调整 `cron` 表达式。例如，`30 2 * * *` 表示每天 UTC 2:30 执行（北京时间 10:30）。

-   **Cloudflare Pages 项目名**:
    在 `Deploy to Cloudflare Pages` 步骤中，将 `projectName` 替换为您在 Cloudflare 上创建的 Pages 项目名称。
    ```yaml
    - name: Deploy to Cloudflare Pages
      uses: cloudflare/pages-action@v1
      with:
        apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
        accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
        projectName: '您的 Cloudflare Pages' # 【重要】请替换为您的 Cloudflare Pages 项目名
        directory: 'public'
        gitHubToken: ${{ secrets.GITHUB_TOKEN }}
    ```

### 3. 提交并推送更改

确保将所有对 `update.yml` 和 `scraper.py` 的更改提交并推送到您的 GitHub 仓库的 `main` 或默认分支。

## 🌐 部署到 Cloudflare Pages

1.  **在 Cloudflare 创建 Pages 项目**:
    *   登录 Cloudflare Dashboard。
    *   选择您的账户，然后点击 `Workers & Pages` -> `Create application` -> `Connect to Git`.
    *   选择您的 GitHub 仓库 `您的 github库名称`。
    *   在构建设置中，`Build command` 可以留空，`Build output directory` 设置为 `public`。
    *   点击 `Save and Deploy`。

2.  **获取订阅链接**:
    部署成功后，Cloudflare Pages 会为您提供一个域名。您的订阅文件将通过以下链接访问：
    -   JSON 格式: `https://<您的Pages域名>/nodes.json`
    -   Base64 订阅: `https://<您的Pages域名>/sub.txt`

## ⚠️ 注意事项

-   **`scraper.py` 中的 `BASE_ID` 和 `BASE_DATE_STR`**:
    这两个变量是脚本计算每日更新 URL 的基准。如果未来节点来源网站的 ID 规则发生变化，导致脚本无法抓取到最新节点，您可能需要手动更新这两个值。
    *   `BASE_ID`: 找到网站上某个日期的页面 ID。
    *   `BASE_DATE_STR`: 对应上述 ID 的日期（格式 `YYYY-MM-DD`）。
-   **GitHub Actions 首次触发延迟**: 新配置的 `cron` 任务可能不会立即在下一个计划时间触发，有时需要等待一段时间。如果长时间未触发，可以尝试手动触发一次工作流，或稍微修改 `cron` 表达式并提交。
-   **Cloudflare API Token 权限**: 确保您的 Cloudflare API Token 具有足够的权限来部署 Pages 项目。


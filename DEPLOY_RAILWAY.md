# Railway 部署指南

## 一、前置准备

1. 注册 [Railway](https://railway.app/)（可用 GitHub 登录）
2. 将本项目推送到 **GitHub** 仓库

---

## 二、创建 GitHub 仓库

如果还没有 GitHub 仓库，在项目根目录执行：

```bash
cd d:\cursor\CODE\MahjongPunishment

# 初始化 git（如已初始化可跳过）
git init

# 添加所有文件
git add .

# 提交
git commit -m "麻将惩罚抽取程序"

# 在 GitHub 网页新建仓库后，关联并推送
git remote add origin https://github.com/你的用户名/仓库名.git
git branch -M main
git push -u origin main
```

---

## 三、在 Railway 部署

### 1. 创建项目

1. 打开 [railway.app](https://railway.app/) 并登录
2. 点击 **「New Project」** 新建项目

### 2. 从 GitHub 部署

3. 选择 **「Deploy from GitHub repo」**
4. 若首次使用，点击 **「Configure GitHub App」** 授权 Railway 访问你的 GitHub
5. 选择 **「Only select repositories」**，勾选你的 `MahjongPunishment` 仓库
6. 选择该仓库，Railway 会自动检测并开始构建

### 3. 生成公网域名

7. 部署完成后，在项目里找到你的服务
8. 点击进入，切到 **「Settings」**
9. 在 **「Networking」** 区域点击 **「Generate Domain」**
10. 会生成类似 `mahjongpunishment-production-xxxx.up.railway.app` 的地址

### 4. 访问

11. 点击该域名或复制到手机浏览器即可访问

---

## 四、注意事项

- **免费额度**：Railway 每月有一定免费额度，超出会要求绑定信用卡
- **数据持久性**：数据存在内存/临时磁盘，服务重启或重新部署后会被清空，游戏需重新开始
- **冷启动**：免费实例一段时间不用会休眠，首次访问可能需等待几秒

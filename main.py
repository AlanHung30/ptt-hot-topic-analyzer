import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt

# 1. 熱門文章爬取
# 以 PTT 八卦板為例，抓取熱門文章標題與連結

def fetch_hot_articles(board="Gossiping", pages=1):
    base_url = f"https://www.ptt.cc/bbs/{board}/index.html"
    session = requests.Session()
    session.cookies.set('over18', '1')  # 通過年齡驗證
    articles = []
    for _ in range(pages):
        res = session.get(base_url)
        soup = BeautifulSoup(res.text, "html.parser")
        for div in soup.select("div.r-ent"):
            title_tag = div.select_one("div.title a")
            if title_tag:
                title = title_tag.text.strip()
                link = "https://www.ptt.cc" + title_tag['href']
                articles.append({"title": title, "link": link})
        # 取得上一頁連結
        prev_link = soup.select_one("div.btn-group-paging a.btn.wide:nth-child(2)")
        if prev_link:
            base_url = "https://www.ptt.cc" + prev_link['href']
        else:
            break
    return articles

# 2. 關鍵字統計

def keyword_statistics(articles, keywords):
    stats = {k: 0 for k in keywords}
    for article in articles:
        for k in keywords:
            if k in article["title"]:
                stats[k] += 1
    return stats

# 3. 話題趨勢圖

def plot_trends(stats):
    keywords = list(stats.keys())
    counts = list(stats.values())
    plt.figure(figsize=(10, 6))
    plt.bar(keywords, counts, color='skyblue')
    plt.xlabel('關鍵字')
    plt.ylabel('出現次數')
    plt.title('PTT 熱門關鍵字統計')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # 範例：爬取 3 頁八卦板熱門文章
    articles = fetch_hot_articles(pages=3)
    # 設定關鍵字
    keywords = ["八卦", "爆卦", "問卦", "新聞", "討論"]
    stats = keyword_statistics(articles, keywords)
    print("關鍵字統計：", stats)
    plot_trends(stats)


import os
import io
import requests
from flask import Flask, render_template_string, send_file
from bs4 import BeautifulSoup

import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# --- 共用分詞與過濾函式 ---
def extract_keywords(text, stopwords, meaningless_words, chinese_prepositions, english_prepositions):
    import jieba
    import re
    is_chinese = lambda w: re.fullmatch(r'[\u4e00-\u9fff]{2,}', w)
    is_single_alpha = lambda w: re.fullmatch(r'[A-Za-z]', w)
    ws = [w.strip() for w in jieba.cut(text)]
    filtered = []
    for w in ws:
        if is_single_alpha(w):
            continue
        if is_chinese(w) and w not in stopwords and w not in meaningless_words and w not in chinese_prepositions:
            filtered.append(w)
        elif re.fullmatch(r'[A-Za-z]+', w):
            if w.lower() not in english_prepositions and w.lower() not in meaningless_words and not is_single_alpha(w):
                filtered.append(w)
    # 再次排除含數字、無意義詞、中文介詞、單一字母
    filtered = [w for w in filtered if not re.search(r'\d', w) and w not in meaningless_words and w not in chinese_prepositions and not is_single_alpha(w)]
    return filtered

app = Flask(__name__)

# 文字雲圖片路由
@app.route('/wordcloud.png')
def wordcloud_png():
    # 常見中文介詞（2字以上）
    chinese_prepositions = {
        '關於', '這種','其他','表示','知道','獲得','文章','認為','還有','成為','一堆','繼續','只能','雖然','那個','這些','需要','甚至','指出','有人','一樣','無法','各位','進行', '以前','非常','以及','才能', '因為', '為了', '根據', '依照', '按照', '隨著', '經過', '透過', '直到', '除了', '直到', '沿著', '根據', '依據', '隨著', '經過', '通過', '透過', '由於', '因為', '為了', '關於', '對於', '至於', '直到', '從而', '從此', '從前', '從今', '從小', '從大', '只是','很多','不能','覺得','而且','那邊','只要','一下', '只有','一定','不用','出來','那麼','到底','包括','出現','這是','是否','今日','其中','從此以後'
    }
    import matplotlib
    matplotlib.use('Agg')
    import jieba
    import re
    from PIL import Image, ImageDraw, ImageFont
    # 取得今日所有熱門文章的詞彙
    boards = fetch_all_hot_boards()
    top10 = boards[:10]
    articles = []
    if top10:
        articles += fetch_hot_articles(boards=top10, pages=10)
    today = __import__('datetime').date.today()
    today_str = today.strftime('%m/%d').lstrip('0').replace('/0', '/')
    stopwords = set([
        '備註', '綜合報導', '記者', '新聞', '作者', '標題', '時間', '發信站', '編輯', '留言', '推文', '內容', '網址', '來源', '更新', '網友', '圖片', '影片', '相關', '報導', '更多', '目前', '大家', '如果', '真的', '現在', '自己', '可以', '不是', '沒有', '就是', '什麼', '這樣', '已經', '還是', '但是', '因為', '所以', '可能', '一起', '看到', '感謝', '請問', '請教', '請益', '請問一下', '謝謝', '請', '問', '如題', '如上', '如圖', '如內文', '如標題', '如附件', '如連結', '如網址', '如影片', '如圖片', '如報導', '如新聞', '如備註', '如綜合報導',
        '情報', '閒聊', '討論', '花邊', '分享', '公告', '轉播', '心得', '問題', '電競'
    ])
    # 額外過濾無意義詞彙
    meaningless_words = {'我們', '知道', '還有', '這個', '應該', '不過', '這種', '其他', '怎麼', '是不是', '不會', '今天', '今年'}
    url_pattern = re.compile(r'https?://\S+')
    words = []
    is_chinese = lambda w: re.fullmatch(r'[\u4e00-\u9fff]{2,}', w)
    english_prepositions = {
        'the', 'in', 'on', 'at', 'by', 'for', 'with', 'to', 'from', 'of', 'as', 'about', 'after', 'before',
        'under', 'over', 'between', 'into', 'through', 'during', 'without', 'within', 'along', 'across',
        'behind', 'beyond', 'but', 'except', 'like', 'near', 'off', 'since', 'till', 'until', 'upon', 'via'
    }
    is_single_alpha = lambda w: re.fullmatch(r'[A-Za-z]', w)
    for a in articles:
        adate = a.get('date', '')
        d_norm = adate.replace('0', '').replace('/0', '/')
        if d_norm == today_str:
            # 過濾留言空值
            comments = [c for c in a.get('comments', []) if c and c.strip()]
            text = (a.get('title', '') + ' ' + a.get('content', '') + ' ' + ' '.join(comments)).replace('\n', ' ')
            text = re.sub(r'\s+', ' ', text)
            text = url_pattern.sub('', text)
            filtered = extract_keywords(text, stopwords, meaningless_words, chinese_prepositions, english_prepositions)
            words.extend(filtered)
    # 移除所有空字串
    words = [w for w in words if w and w.strip()]
    # 若無資料，產生預設圖片
    if not words:
        # 產生一張簡單的圖片顯示「今日無資料」
        img = Image.new('RGB', (800, 400), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 48)
        except:
            font = None
        text = '今日無資料'
        w, h = draw.textsize(text, font=font)
        draw.text(((800-w)//2, (400-h)//2), text, fill=(100,100,100), font=font)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    freq = {}
    for w in words:
        if w and w.strip():
            freq[w] = freq.get(w, 0) + 1
    # 若 freq 為空，直接顯示「今日無資料」圖
    if not freq:
        img = Image.new('RGB', (800, 400), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 48)
        except:
            font = None
        text = '今日無資料'
        w, h = draw.textsize(text, font=font)
        draw.text(((800-w)//2, (400-h)//2), text, fill=(100,100,100), font=font)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    # 檢查字型路徑
    font_path = 'C:/Windows/Fonts/msjh.ttc'
    if not os.path.exists(font_path):
        font_path = None
    try:
        wc = WordCloud(font_path=font_path, width=800, height=400, background_color='white', collocations=False)
        wc.generate_from_frequencies(freq)
        buf = io.BytesIO()
        wc.to_image().save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    except Exception as e:
        print('[WordCloud Error]', e)
        # 若產生失敗，回傳預設圖片
        img = Image.new('RGB', (800, 400), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 48)
        except:
            font = None
        text = '產生文字雲失敗'
        w, h = draw.textsize(text, font=font)
        draw.text(((800-w)//2, (400-h)//2), text, fill=(200,0,0), font=font)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')

import os
import io
from flask import Flask, render_template_string, send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt

# --- 新增：自動取得所有熱門看板 ---
def fetch_all_hot_boards():
    url = "https://www.ptt.cc/bbs/hotboards.html"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    boards = []
    for idx, div in enumerate(soup.select(".b-ent a.board")):
        if idx >= 50:
            break
        href = div.get("href", "")
        # href 格式: /bbs/Gossiping/index.html
        board = href.split('/')[2] if href else None
        if board:
            boards.append(board)
    print(f"[DEBUG] 熱門看板數量: {len(boards)}")
    print(f"[DEBUG] 熱門看板前10: {boards[:10]}")
    return boards


# 1. 熱門文章爬取

# 支援多看板批次爬取
def fetch_hot_articles(boards=None, pages=1):
    if boards is None:
        boards = ["Gossiping"]
    if isinstance(boards, str):
        boards = [boards]
    all_articles = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for board in boards:
        base_url = f"https://www.ptt.cc/bbs/{board}/index.html"
        session = requests.Session()
        session.cookies.set('over18', '1')
        articles = []
        for page_idx in range(pages):
            res = session.get(base_url, headers=headers)
            soup = BeautifulSoup(res.text, "html.parser")
            for div in soup.select("div.r-ent"):
                title_tag = div.select_one("div.title a")
                date_tag = div.select_one("div.meta .date")
                push_tag = div.select_one("div.nrec span")
                # 跳過公告
                if title_tag and title_tag.text.strip().startswith("公告"):
                    continue
                # 判斷推文數
                push_count = 0
                is_exploded = False
                if push_tag:
                    push_text = push_tag.text.strip()
                    if push_text == '爆':
                        is_exploded = True
                    else:
                        try:
                            push_count = int(push_text) if push_text.lstrip('-').isdigit() else 0
                        except:
                            push_count = 0
                if title_tag and date_tag:
                    title = title_tag.text.strip()
                    link = "https://www.ptt.cc" + title_tag['href']
                    date = date_tag.text.strip()
                    content_text = ""
                    comments = []
                    try:
                        post_res = session.get(link, headers=headers)
                        post_soup = BeautifulSoup(post_res.text, "html.parser")
                        main_content = post_soup.select_one('#main-content')
                        if main_content:
                            for tag in main_content.select('div.push, span.f2, span.article-meta-tag, span.article-meta-value'):
                                tag.decompose()
                            content_text = main_content.get_text(separator=' ', strip=True)
                        for push in post_soup.select('div.push'):
                            content = push.select_one('span.f3.push-content')
                            if content:
                                comment_text = content.text.strip(': ')
                                if comment_text:
                                    comments.append(comment_text)
                    except Exception as e:
                        pass
                    articles.append({
                        "title": title,
                        "link": link,
                        "date": date,
                        "content": content_text,
                        "comments": comments,
                        "push_count": push_count,
                        "is_exploded": is_exploded,
                        "board": board
                    })
            prev_link = soup.select_one("div.btn-group-paging a.btn.wide:nth-child(2)")
            if prev_link:
                base_url = "https://www.ptt.cc" + prev_link['href']
            else:
                break
        print(f"[DEBUG] {board} 全部熱門文章數: {len(articles)}")
        all_articles.extend(articles)
    print(f"[DEBUG] 全部文章總數: {len(all_articles)}")
    return all_articles

# 2. 關鍵字統計
def keyword_statistics_by_week(articles, keywords):
    import re
    import datetime
    from collections import defaultdict
    now = datetime.datetime.now()
    def parse_date(date_str):
        try:
            m, d = map(int, date_str.strip().split('/'))
            y = now.year
            if now.month == 1 and m == 12:
                y -= 1
            return datetime.date(y, m, d)
        except:
            return None
    # 以過去7天為單位，統計每一天的關鍵字出現次數（主題/標題）
    day_stats = defaultdict(lambda: {k: 0 for k in keywords})
    for article in articles:
        date = parse_date(article.get("date", ""))
        if not date:
            continue
        clean_title = re.sub(r'\[.*?\]', '', article["title"]).strip()
        clean_title = re.sub(r'\s+', ' ', clean_title)
        for k in keywords:
            if k:
                count = len(re.findall(rf'(?<![\w\[]){re.escape(k)}(?![\w\]])', clean_title))
                day_stats[date][k] += count
    # 只保留過去7天
    import datetime
    today = datetime.date.today()
    last_7_days = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    result = {d.strftime('%Y-%m-%d'): day_stats[d] for d in last_7_days if d in day_stats}
    return result

# 3. 話題趨勢圖
def plot_trends(week_stats, keywords):
    import matplotlib.font_manager as fm
    font_path = 'C:/Windows/Fonts/msjh.ttc'
    if os.path.exists(font_path):
        from matplotlib import font_manager as fm
        myfont = fm.FontProperties(fname=font_path)
        plt.rcParams['font.sans-serif'] = [font_path]
        plt.rcParams['axes.unicode_minus'] = False
    else:
        myfont = None
    plt.figure(figsize=(12, 7))
    periods = sorted(week_stats.keys())
    for k in keywords:
        y = [week_stats[w][k] for w in periods]
        plt.plot(periods, y, marker='o', label=k)
    plt.xlabel('月份', fontproperties=myfont)
    plt.ylabel('出現次數', fontproperties=myfont)
    plt.title('PTT 熱門關鍵字每月趨勢', fontproperties=myfont)
    plt.legend(prop=myfont)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

@app.route('/')

def index():
    chinese_prepositions = {
        '關於', '由於', '因為', '為了', '根據', '依照', '按照', '隨著', '經過', '透過', '直到', '除了', '直到', '沿著',
        '根據', '依據', '隨著', '經過', '通過', '透過', '由於', '因為', '為了', '關於', '對於', '至於', '直到', '從而',
        '從此', '從前', '從今', '從小', '從大', '從此以後',
        '最終', '竟是', '旁白', '然而', '更是', '不知', '所謂', '便是'
    }
    import datetime
    # 取得所有熱門看板
    boards = fetch_all_hot_boards()
    # 前10熱門看板抓10頁，其餘不抓
    top10 = boards[:10]
    articles = []
    if top10:
        articles += fetch_hot_articles(boards=top10, pages=10)
    today = datetime.date.today()
    def parse_date(date_str):
        try:
            m, d = map(int, date_str.strip().split('/'))
            y = today.year
            if today.month == 1 and m == 12:
                y -= 1
            return datetime.date(y, m, d)
        except:
            return None
    week_ago = today - datetime.timedelta(days=7)
    filtered_articles = []
    for a in articles:
        adate = parse_date(a.get('date', ''))
        if adate and adate >= week_ago:
            filtered_articles.append(a)
    # 只保留推文數大於50或爆文的文章
    articles = [a for a in filtered_articles if a.get('is_exploded') or a.get('push_count', 0) > 50]
    # 如果沒有熱門文章，則改用所有文章
    if not articles:
        articles = filtered_articles
    # 只分析今日，並針對各看板統計關鍵字（標題+內文+留言）
    import re
    from collections import Counter, defaultdict
    import jieba
    jieba.setLogLevel(20)
    stopwords = set([
        '備註', '綜合報導', '記者', '新聞', '作者', '標題', '時間', '發信站', '編輯', '留言', '推文', '內容', '網址', '來源', '更新', '網友', '圖片', '影片',
          '相關', '報導', '更多', '目前', '大家', '如果', '真的', '現在', '自己', '可以', '不是', '沒有', '就是', '什麼', '這樣', '已經', '還是', '但是', '因為',
            '所以', '可能', '一起', '看到', '感謝', '請問', '請教', '請益', '請問一下', '謝謝', '請', '問', '如題', '如上', '如圖', '如內文', '如標題', '如附件',
              '如連結', '如網址', '如影片', '如圖片', '如報導', '如新聞', '如備註', '如綜合報導',
        '情報', '閒聊', '討論', '花邊', '分享', '公告', '轉播', '心得', '問題', '電競'
    ])
    meaningless_words = {'我們', '知道', '還有', '這個', '應該', '不過', '這種', '其他', '怎麼', '是不是', '不會', '今天', '直接','這次','只有','是否',
                         '不能','只要','還要','這邊','那個','那邊','看看','只是','覺得','一定','之前','很多','其中','事情','地方','那麼','不要','不用','完成',
                         '接受','他們','我們','一個','包括','這是','這麼','了解','出來','重要','今日','這是','希望','透露','影響','未來','最近','今天', '今年'}
    # 只取今日的文章
    today_str = today.strftime('%m/%d').lstrip('0').replace('/0', '/')
    today_articles = []
    print(f"[DEBUG] today_str: {today_str}")
    for a in articles:
        adate = a.get('date', '')
        d_norm = adate.replace('0', '').replace('/0', '/')
        print(f"[DEBUG] 文章日期: {d_norm}")
        if d_norm == today_str:
            today_articles.append(a)
    print(f"[DEBUG] 今日文章數量: {len(today_articles)}")
    # 依看板分組，並統計所有詞彙出現次數
    board_words = defaultdict(list)
    board_keywords = {}
    url_pattern = re.compile(r'https?://\S+')
    english_prepositions = {
        'the', 'a', 'an', 'in', 'on', 'at', 'by', 'for', 'with', 'to', 'from', 'of', 'as', 'about', 'after', 'before',
        'under', 'over', 'between', 'into', 'through', 'during', 'without', 'within', 'along', 'across',
        'behind', 'beyond', 'but', 'except', 'like', 'near', 'off', 'since', 'till', 'until', 'upon', 'via'
    }
    is_chinese = lambda w: re.fullmatch(r'[\u4e00-\u9fff]{2,}', w)
    is_single_alpha = lambda w: re.fullmatch(r'[A-Za-z]', w)
    for a in today_articles:
        text = (a.get('title', '') + ' ' + a.get('content', '') + ' ' + ' '.join(a.get('comments', []))).replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text)
        text = url_pattern.sub('', text)
        filtered = extract_keywords(text, stopwords, meaningless_words, chinese_prepositions, english_prepositions)
        print(f"[DEBUG] 看板: {a.get('board', '其他')}, 分詞: {filtered}")
        board_words[a.get('board', '其他')].extend(filtered)
    # 取每個看板前5大關鍵字
    for board, ws in board_words.items():
        common = Counter(ws).most_common(5)
        board_keywords[board] = common
    # 產生 HTML，若無資料顯示提示
    board_html = ''
    if board_keywords:
        for board, kws in board_keywords.items():
            board_html += f'<tr><td>{board}</td>' + ''.join(f'<td>{w} ({c})</td>' for w, c in kws)
            # 若不足5個關鍵字，補空白
            if len(kws) < 5:
                board_html += '<td></td>' * (5 - len(kws))
            board_html += '</tr>'
    else:
        board_html = '<tr><td colspan="6">今日無熱門文章或無關鍵字統計資料</td></tr>'
    # 只顯示今日熱門文章
    from collections import defaultdict
    articles_by_date = defaultdict(list)
    for a in articles:
        articles_by_date[a["date"]].append(a)
    if articles_by_date:
        matched_date = None
        for d in articles_by_date.keys():
            d_norm = d.replace('0', '').replace('/0', '/')
            if d_norm == today_str:
                matched_date = d
                break
        if matched_date:
            article_html = f'<li><b>今日（{matched_date}）</b><ul>'
            for a in articles_by_date[matched_date]:
                article_html += f'<li>[{a.get("board", "")}] <a href="{a["link"]}" target="_blank">{a["title"]}</a></li>'
            article_html += '</ul></li>'
        else:
            article_html = f'<li>今日({today_str})無資料</li>'
    else:
        article_html = '<li>無資料</li>'
    # 產生各看板關鍵字表格 HTML
    stats_html = board_html
    keywords = []  # 不再用於下方表格
    week_stats = {}  # 不再用於下方表格
    # 只顯示最新日期的熱門文章（不論頁數）
    from collections import defaultdict
    articles_by_date = defaultdict(list)
    for a in articles:
        articles_by_date[a["date"]].append(a)
    if articles_by_date:
        # 只顯示今日的熱門文章（以系統日期為準）
        import datetime
        today = datetime.date.today()
        today_str = today.strftime('%m/%d').lstrip('0').replace('/0', '/')
        matched_date = None
        for d in articles_by_date.keys():
            d_norm = d.replace('0', '').replace('/0', '/')
            if d_norm == today_str:
                matched_date = d
                break
        if matched_date:
            article_html = f'<li><b>今日（{matched_date}）</b><ul>'
            for a in articles_by_date[matched_date]:
                article_html += f'<li>[{a.get("board", "")}] <a href="{a["link"]}" target="_blank">{a["title"]}</a></li>'
            article_html += '</ul></li>'
        else:
            article_html = f'<li>今日({today_str})無資料</li>'
    else:
        article_html = '<li>無資料</li>'
    # （移除覆蓋 stats_html 的程式碼，保留上方 board_html 給 stats_html）
    # --- 產生 AI 熱門話題摘要（幾句話描述）---
    ai_summary = ""
    if board_keywords:
        # 彙整所有看板前3大關鍵字，統計出現次數，取前5大作為全站熱門
        from collections import Counter
        all_keywords = []
        for kws in board_keywords.values():
            all_keywords.extend([w for w, c in kws if w])
        top_keywords = [w for w, _ in Counter(all_keywords).most_common(5)]
        # 針對每個熱門關鍵字，找出相關文章標題，組成摘要
        if top_keywords:
            summary_sentences = []
            used_titles = set()
            for kw in top_keywords:
                # 找出含有該關鍵字的今日熱門文章標題
                related_titles = []
                for a in today_articles:
                    title = a.get('title', '')
                    if kw in title and title not in used_titles:
                        related_titles.append(title)
                        used_titles.add(title)
                    if len(related_titles) >= 2:
                        break
                if related_titles:
                    summary_sentences.append(f"關於「{kw}」的熱門討論如：{'；'.join(related_titles)}。")
                else:
                    summary_sentences.append(f"今日有大量討論「{kw}」相關話題。")
            ai_summary = '<br>'.join(summary_sentences)
        else:
            ai_summary = "今日無足夠關鍵字資料可供摘要分析。"
    else:
        ai_summary = "今日無熱門文章或關鍵字資料。"

    html = f'''
    <html>
    <head>
        <meta charset="utf-8">
        <title>PTT 熱門話題與關鍵字趨勢分析</title>
        <style>
            body {{ font-family: 'Segoe UI', '微軟正黑體', Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }}
            .container {{ max-width: 900px; margin: 30px auto; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px #0001; padding: 32px 40px; }}
            h1 {{ color: #0055a5; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }}
            h2 {{ color: #333; margin-top: 2em; }}
            ul {{ padding-left: 1.2em; }}
            ul li {{ margin-bottom: 6px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 1em; background: #fafcff; }}
            th, td {{ border: 1px solid #d0d7de; padding: 8px 12px; text-align: center; }}
            th {{ background: #e3f0fa; color: #0055a5; }}
            tr:nth-child(even) {{ background: #f3f8fb; }}
            .trend-img {{ display: block; margin: 30px auto 0 auto; border-radius: 8px; box-shadow: 0 1px 8px #0002; max-width: 100%; }}
            .footer {{ margin-top: 40px; color: #888; font-size: 0.95em; text-align: center; }}
            .ai-summary {{ margin-top: 48px; background: #f8f8f8; border-radius: 8px; padding: 18px 20px; color: #333; font-size: 1.08em; box-shadow: 0 1px 6px #0001; }}
            @media (max-width: 600px) {{
                .container {{ padding: 10px 2vw; }}
                table, th, td {{ font-size: 0.95em; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PTT 熱門話題與關鍵字趨勢分析</h1>
            <h2>熱門文章</h2>
            <ul>{article_html}</ul>
            <h2>今日熱門關鍵字雲</h2>
            <img src="/wordcloud.png" class="trend-img" alt="今日關鍵字雲">
            <h2>各看板今日關鍵字統計（標題+內文+留言）</h2>
            <table><tr><th>看板</th><th>關鍵字1</th><th>關鍵字2</th><th>關鍵字3</th><th>關鍵字4</th><th>關鍵字5</th></tr>{stats_html}</table>
            <div class="ai-summary"><b>AI 熱門話題摘要</b><br>{ai_summary}</div>
            <div class="footer">© {datetime.datetime.now().year} PTT 熱門話題分析 | Powered by Flask, requests, BeautifulSoup, matplotlib, jieba, wordcloud</div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html)

@app.route('/trend.png')
def trend_png():
    articles = fetch_hot_articles(pages=14)
    keywords = ["八卦", "爆卦", "問卦", "新聞", "討論"]
    week_stats = keyword_statistics_by_week(articles, keywords)
    # 若 week_stats 為空或所有值都為 0，顯示預設圖片
    has_data = False
    for day in week_stats.values():
        if any(v > 0 for v in day.values()):
            has_data = True
            break
    if not week_stats or not has_data:
        # 產生一張簡單的圖片顯示「無趨勢資料」
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (800, 400), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/msjh.ttc', 48)
        except:
            font = None
        text = '無趨勢資料'
        w, h = draw.textsize(text, font=font)
        draw.text(((800-w)//2, (400-h)//2), text, fill=(200,0,0), font=font)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')
    buf = plot_trends(week_stats, keywords)
    return send_file(buf, mimetype='image/png')

if __name__ == "__main__":
    app.run(debug=True)

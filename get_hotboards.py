import os
import io
from flask import Flask, render_template_string, send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt

def fetch_all_hot_boards():
    url = "https://www.ptt.cc/bbs/hotboards.html"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    boards = []
    for div in soup.select(".b-ent a.board"):  # 取得所有熱門看板英文名稱
        href = div.get("href", "")
        # href 格式: /bbs/Gossiping/index.html
        board = href.split('/')[2] if href else None
        if board:
            boards.append(board)
    return boards

# 其餘主程式不變，僅示範如何取得所有熱門看板
if __name__ == "__main__":
    boards = fetch_all_hot_boards()
    print("熱門看板：", boards)

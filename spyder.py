import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pyquery import PyQuery as pq
from config import *
import pymongo


#MONGODB配置
client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]
#创建WebDriver对象
# browser = webdriver.Chrome()#有界面
browser = webdriver.PhantomJS(service_args=SERVICE_ARGS)#无界面
#等待变量
wait = WebDriverWait(browser, 10)
# PhantomJs()的浏览器窗口很小,宽高只有400 * 300
# browser.maximize_window()  # 窗口最大化  # 对于PhantomJS来说设置窗口大小很关键，如果不设置，经常会出现问题
browser.set_window_size(1400, 900)# 设置浏览器窗口大小


#模拟在淘宝网页中输入关键字搜索
def search():
    print('准备搜索')
    try:
        browser.get('https://www.taobao.com')  #打开淘宝首页
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#q"))
        )#等待输入框加载完成
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#J_TSearchForm > div.search-button > button'))
        )#等待搜索框加载完成
        input.send_keys(KEYWORD) #搜索框中传入“美食”
        submit.click()#点击搜索
        total = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.total'))
        )#加载完成，获取页数元素
        get_products()
        return total.text#获取元素中的文本
    except TimeoutException:
        return search() #若发生异常，重新调用自己


# 根据页码获取指定页数据，并将其保存到数据库中
def next_page(page_number):
    print('正在获取第%d页数据', page_number)
    try:
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#mainsrp-pager > div > div > div > div.form > input"))
        )#等待翻页输入框加载完成
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit'))
        )#等待确认按钮加载完成
        input.clear()#清空翻页输入框
        input.send_keys(page_number)#传入页数
        submit.click()#确认点击翻页
        wait.until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager > div > div > div > ul > li.item.active > span'), str(page_number))
        )#确认已翻到page_number页
        get_products()
    except TimeoutException:
        next_page(page_number)#若发生异常，重新调用自己


#获取商品信息
def get_products():
    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-itemlist .items .item'))
    )#等待商品信息加载完成，商品信息的CSS选择器分析HTML源码得到
    html = browser.page_source#得到页面HTML源码
    doc = pq(html)#创建pyquery对象
    items = doc('#mainsrp-itemlist .items .item').items()
    for item in items:
        product = {
            'image': item.find('.pic .img').attr('src'),
            'price': item.find('.price').text(),
            'deal': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text(),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text()

        }
        print(product)
        save_to_mongo(product)#保存到MongoDB成功


def save_to_mongo(product):
    try:
        if db[MONGO_TABLE].insert(product):
            print("存储到MongoDB成功", product)
    except Exception:
        print("存储到MongoDB失败", product)


def main():
    try:
        total = search()#获取商品页数，字符串类型
        total = int(re.compile('(\d+)').search(total).group(1))#利用正则表达式提取数字，并强制转换为int类型
        for i in range(2, total+1):
            next_page(i)
    except Exception:
        print('出错啦')
    finally:
        browser.close()


if __name__ == '__main__':
    main()
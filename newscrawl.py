import sqlite3
from datetime import datetime
import pandas as pd
import time
from selenium import webdriver
from tqdm import tqdm
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from selenium.common.exceptions import UnexpectedAlertPresentException

options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)
driver.get("https://search.naver.com/search.naver?ssc=tab.news.all&where=news&sm=tab_jum&query=%EB%B9%85%EB%8D%B0%EC%9D%B4%ED%84%B0")

# 옵션 클릭.
elem_option = driver.find_element(By.XPATH, '//*[@id="snb"]/div[1]/div/div[2]/a')
elem_option.send_keys('\n')
elem_input = driver.find_element(By.XPATH,'//*[@id="snb"]/div[2]/ul/li[3]/div/div[1]/a[9]')
elem_input.send_keys('\n')

naver_news_link = []

def select_date_naver_news(year,month,day):
    elem_year = driver.find_element(By.XPATH,f'//*[@id="snb"]/div[2]/ul/li[3]/div/div[3]/div[2]/div[1]/div/div/div/ul/li[{year-1989}]')
    elem_year.click()
    elem_month = driver.find_element(By.XPATH,f'//*[@id="snb"]/div[2]/ul/li[3]/div/div[3]/div[2]/div[2]/div/div/div/ul/li[{month}]')
    elem_month.click()
    elem_day = driver.find_element(By.XPATH,f'//*[@id="snb"]/div[2]/ul/li[3]/div/div[3]/div[2]/div[3]/div/div/div/ul/li[{day}]')
    elem_day.click()
    driver.find_element(By.XPATH,'//*[@id="snb"]/div[2]/ul/li[3]/div/div[3]/div[1]/span[3]/a').click()
    elem_year = driver.find_element(By.XPATH,f'//*[@id="snb"]/div[2]/ul/li[3]/div/div[3]/div[2]/div[1]/div/div/div/ul/li[{year-1989}]')
    elem_year.click()
    elem_month = driver.find_element(By.XPATH,f'//*[@id="snb"]/div[2]/ul/li[3]/div/div[3]/div[2]/div[2]/div/div/div/ul/li[{month}]')
    elem_month.click()
    elem_day = driver.find_element(By.XPATH,f'//*[@id="snb"]/div[2]/ul/li[3]/div/div[3]/div[2]/div[3]/div/div/div/ul/li[{day}]')
    elem_day.click()
    driver.find_element(By.XPATH,'//*[@id="snb"]/div[2]/ul/li[3]/div/div[3]/div[3]/button').click()
    naver_news_link = driver.find_elements(By.LINK_TEXT, '네이버뉴스')
    links = [link.get_attribute('href') for link in naver_news_link]
    driver.find_element(By.XPATH,'//*[@id="snb"]/div[2]/ul/li[7]/div/div/a[1]').click()
    time.sleep(1.5)
    elem_input = driver.find_element(By.XPATH,'//*[@id="snb"]/div[2]/ul/li[3]/div/div[1]/a[9]')
    elem_input.send_keys(Keys.ENTER)

    return links

for year in tqdm(range(2023,2024),desc='preprocessing year'):
    for month in tqdm(range(12,13),desc='preprocessing month'):
        for day in tqdm(range(29,32),desc='preprocessing day'):
            try:
                res = select_date_naver_news(year=year,month=month,day=day)
                naver_news_link.append(res)
            except:
                pass
link_result = [element for row in naver_news_link for element in row]

try:
  conn = sqlite3.connect('sqlite3.db')
  curs = conn.cursor()

  sql = """CREATE TABLE IF NOT EXISTS `newslink` (
	          `link` MEDIUMTEXT NULL
            )
            """
  curs.execute(sql)
  conn.commit()
  for i in link_result:
    sql = "INSERT INTO newslink(link) VALUES('"+ i +"')"
    curs.execute(sql)
  conn.commit()

  sql = 'select * from newslink'
  curs.execute(sql)
  columns = [desc[0] for desc in curs.description]
  show = pd.DataFrame(curs.fetchall(), columns=columns)
  print(show)

except sqlite3.Error as error:
  print("Failed to insert data into sqlite table", error)

try:
    conn = sqlite3.connect('sqlite3.db')
    curs = conn.cursor()

    naver_news_title = []
    naver_news_content = []

    sql = """CREATE TABLE IF NOT EXISTS `news` (
	          `title` TEXT NULL,
              `content` MEDIUMTEXT NULL
            )
            """
    curs.execute(sql)
    conn.commit()

    sql = 'select * from newslink'
    curs.execute(sql)
    columns = [desc[0] for desc in curs.description]
    show = pd.DataFrame(curs.fetchall(), columns=columns)

    for link in show['link']:
        try:
            driver.get(link)
        except:
            print("Time Out!")
            continue

        try:
            response = driver.page_source

        except UnexpectedAlertPresentException:
            driver.switch_to_alert().alert()
            print("게시글이 삭제된 경우입니다.")
            continue

        soup = BeautifulSoup(response,'html.parser')
        ##### 뉴스 타이틀 긇어오기 #####
        title = None

        try:
            og_title = soup.find('meta', property='og:title')
            title = og_title['content']
        except:
            title = "OUT_LINK"
        
        naver_news_title.append(title)
        ###### 뉴스 본문 긇어오기 #####
        doc = None
        text = ''
        data = soup.find_all("div",{"class":"newsct_article _article_body"})
        if data:
            for item in data:
                if item.find('script',type='text/javascript'):
                    item.find('script',type='text/javascript').decompose()
                elif item.find('span','end_photo_org'):
                    item.find('span','end_photo_org').decompose()
                text = item.get_text()
                doc = ''.join(text)

        else:
            doc = "OUT_LINK"
        naver_news_content.append(doc.replace('\n',' '))

    time.sleep(1)

    print(naver_news_content)
    print(naver_news_title)

    result = []
    for i in range(len(naver_news_content)):
        temp = [naver_news_title[i],naver_news_content[i]]
        result.append(temp)
    
    sql = "INSERT INTO news(title, content) VALUES (?,?)"
    curs.executemany(sql,result)
    conn.commit()

    sql = 'select * from news'
    curs.execute(sql)
    columns = [desc[0] for desc in curs.description]
    show = pd.DataFrame(curs.fetchall(), columns=columns)
    print(show)

except sqlite3.Error as error:
  print("Failed to insert data into sqlite table", error)

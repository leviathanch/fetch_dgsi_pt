'''
 Copyright (c) 2023-2026 David Lanzendörfer <leviathan@libresilicon.com>
 Distributed under the GNU GPL v2. For full terms see the file docs/COPYING.
'''

import hashlib
from os.path import exists, join
from os import mkdir
import json
import requests
from tqdm import tqdm

from bs4 import BeautifulSoup

class Fetcher:
  books_json = {}
  base_url = "http://www.dgsi.pt/home.nsf"
  headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
  filters = [
    "Help Desk",
  ]
  pages_to_fetch = [
    "http://www.dgsi.pt/jtrg.nsf",
    "http://www.dgsi.pt/jtrl.nsf",
    "http://www.dgsi.pt/jsta.nsf",
    "http://www.dgsi.pt/jtrc.nsf",
    "http://www.dgsi.pt/jtrp.nsf",
    "http://www.dgsi.pt/jtre.nsf",
    "http://www.dgsi.pt/jtca.nsf",
    "http://www.dgsi.pt/jtcn.nsf",
    "http://www.dgsi.pt/jcon.nsf",
    "http://www.dgsi.pt/jstj.nsf",
  ]

  def __init__(self, json_file='./docs.json', cache_dir='./cache'):

    self.json_file = json_file
    self.cache_dir = cache_dir

    if exists(self.json_file):
      with open(self.json_file,'r') as file:
        self.books_json = json.load(file)
        file.close()
    
    if not exists(self.cache_dir):
      mkdir(self.cache_dir)

  def request(self, url, suffix, refresh=False):
    ret = ''
    fn = join(self.cache_dir, hashlib.sha256(url.encode()).hexdigest() + '.' + suffix)
    if exists(fn) and not refresh:
      with open(fn,'rb') as f:
        ret = f.read()
        f.close()
    else:
      req = requests.get(url, headers=self.headers)
      ret = req.content
      with open(fn,'wb') as f:
        f.write(ret)
        f.close()
    return ret

  def fetch_links(self, url):
    ret=[]
    req = self.request(url, 'html')
    soup = BeautifulSoup(req, 'html.parser')
    links = soup.find_all("a")
    for a in links:
      if a.text not in self.filters and len(a.text)>1:
        url = a['href']
        if "http://" not in url and "https://" not in url:
          url = self.base_url+url
        url = url.replace('home.nsf/','')
        if "OpenDocument" in url:
          ret.append(url)
    return ret

  def get_html_urls(self):
    ret = []
    for url in self.pages_to_fetch:
      ret += self.fetch_links(url)
    return ret

  def save(self):
    with open(self.json_file,'w') as file:
        file.write(json.dumps(self.books_json, indent=4))
        file.close()

  def extract_table(self, url, depth=0):
    if depth > 1:
      return None

    ret = {
      'process': '',
      'summary': '',
      'descriptor': '',
      'text': '',
    }
    req = self.request(url, 'html')
    soup = BeautifulSoup(req, 'html.parser')
    tables = soup.find_all('table')
    text1 = text2 = text3 = ""
    for table in tables:
      for row in table.find_all('tr'):
        # Check if the first cell contains the specific text
        first_cell = row.find('td')
        if first_cell and 'Sumário' in first_cell.text:
          second_cell = row.find_all('td')[1]
          ret['summary'] = second_cell.text
        elif first_cell and 'Processo' in first_cell.text:
          second_cell = row.find_all('td')[1]
          ret['process'] = second_cell.text
        elif first_cell and 'Descritores' in first_cell.text:
          second_cell = row.find_all('td')[1]
          ret['descriptor'] = second_cell.text
        elif first_cell and 'Texto Integral' in first_cell.text:
          second_cell = row.find_all('td')[1]
          text1 = second_cell.text
        elif first_cell and 'Parecer Ministério Publico' in first_cell.text:
          second_cell = row.find_all('td')[1]
          text2 = second_cell.text
        elif first_cell and 'Parecer Ministério Publico' in first_cell.text:
          second_cell = row.find_all('td')[1]
          text2 = second_cell.text
        elif first_cell and 'Decisão Texto Parcial' in first_cell.text:
          second_cell = row.find_all('td')[1]
          text3 = second_cell.text

    if len(text1) > 0:
      ret['text'] = text1
    elif len(text2) > 0:
      ret['text'] = text2
    elif len(text3) > 0:
      ret['text'] = text3

    if len(ret['text']) < 1:
      ret = self.extract_table(url+'&ExpandSection=1', depth=depth+1)

    return ret

  def run(self):
    urls = self.get_html_urls()
    for i in tqdm(range(len(urls))):
      url = urls[i]
      d = self.extract_table(url)
      if d is None:
        print('failed', url)
        break
        #continue
      pn = d['process'].strip()
      self.books_json[pn] = {
        'summary': d['summary'].strip(),
        'descriptor': d['descriptor'].strip(),
        'text': d['text'].strip(),
      }
      self.save()

fetcher = Fetcher()
fetcher.run()

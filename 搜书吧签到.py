# -*- coding: utf-8 -*-
"""
实现搜书吧论坛登入和发布空间动态
"""
import os
import re
import sys
from copy import copy

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import time
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

ch = logging.StreamHandler(stream=sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)


def get_refresh_url(url: str):
    try:
        response = requests.get(url, verify=False)
        if response.status_code != 403:
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        meta_tags = soup.find_all('meta', {'http-equiv': 'refresh'})

        if meta_tags:
            content = meta_tags[0].get('content', '')
            if 'url=' in content:
                redirect_url = content.split('url=')[1].strip()
                print(f"Redirecting to: {redirect_url}")
                return redirect_url
        else:
            print("No meta refresh tag found.")
            return None
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        return None


def get_url(url: str):
    resp = requests.get(url, verify=False)
    soup = BeautifulSoup(resp.content, 'html.parser')

    links = soup.find_all('a', href=True)
    for link in links:
        if link.text == "搜书吧":
            return link['href']
    return None


class SouShuBaClient:

    def __init__(self, hostname: str, username: str, password: str, questionid: str = '0', answer: str = None,
                 proxies: dict | None = None):
        self.session: requests.Session = requests.Session()
        self.hostname = hostname
        self.username = username
        self.password = password
        self.questionid = questionid
        self.answer = answer
        self._common_headers = {
            "Host": f"{hostname}",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,cn;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        self.proxies = proxies

    def login_form_hash(self):
        rst = self.session.get(f'https://{self.hostname}/member.php?mod=logging&action=login', verify=False).text
        loginhash = re.search(r'<div id="main_messaqge_(.+?)">', rst).group(1)
        formhash = re.search(r'<input type="hidden" name="formhash" value="(.+?)" />', rst).group(1)
        return loginhash, formhash

    def login(self):
        """Login with username and password"""
        loginhash, formhash = self.login_form_hash()
        login_url = f'https://{self.hostname}/member.php?mod=logging&action=login&loginsubmit=yes' \
                    f'&handlekey=register&loginhash={loginhash}&inajax=1'

        headers = copy(self._common_headers)
        headers["origin"] = f'https://{self.hostname}'
        headers["referer"] = f'https://{self.hostname}/'
        payload = {
            'formhash': formhash,
            'referer': f'https://{self.hostname}/',
            'username': self.username,
            'password': self.password,
            'questionid': self.questionid,
            'answer': self.answer
        }

        resp = self.session.post(login_url, proxies=self.proxies, data=payload, headers=headers, verify=False)
        if resp.status_code == 200:
            logger.info(f'欢迎 {self.username}!')
        else:
            raise ValueError('Verify Failed! Check your username and password!')

    def credit(self):
        credit_url = f"https://{self.hostname}/home.php?mod=spacecp&ac=credit&showcredit=1&inajax=1&ajaxtarget=extcreditmenu_menu"
        credit_rst = self.session.get(credit_url, verify=False).text

        # 解析 XML，提取 CDATA
        root = ET.fromstring(str(credit_rst))
        cdata_content = root.text

        # 使用 BeautifulSoup 解析 CDATA 内容
        cdata_soup = BeautifulSoup(cdata_content, features="lxml")
        hcredit_2 = cdata_soup.find("span", id="hcredit_2").string

        return hcredit_2

    def space_form_hash(self):
        rst = self.session.get(f'https://{self.hostname}/home.php', verify=False).text
        formhash = re.search(r'<input type="hidden" name="formhash" value="(.+?)" />', rst).group(1)
        return formhash

    # def space(self):
    #     formhash = self.space_form_hash()
    #     space_url = f"https://{self.hostname}/home.php?mod=spacecp&ac=doing&handlekey=doing&inajax=1"
    #
    #     headers = copy(self._common_headers)
    #     headers["origin"] = f'https://{self.hostname}'
    #     headers["referer"] = f'https://{self.hostname}/home.php'
    #
    #     for x in range(5):
    #         payload = {
    #             "message": "开心赚银币 {0} 次".format(x + 1).encode("GBK"),
    #             "addsubmit": "true",
    #             "spacenote": "true",
    #             "referer": "home.php",
    #             "formhash": formhash
    #         }
    #         resp = self.session.post(space_url, proxies=self.proxies, data=payload, headers=headers, verify=False)
    #         if re.search("操作成功", resp.text):
    #             logger.info(f'{self.username} post {x + 1}nd successfully!')
    #             time.sleep(120)
    #         else:
    #             logger.warning(f'{self.username} post {x + 1}nd failed!')


if __name__ == '__main__':
    try:
        redirect_url = get_refresh_url('http://' + os.environ.get('SOUSHUBA_HOSTNAME', 'www.soushu2030.com'))
        time.sleep(2)
        redirect_url2 = get_refresh_url(redirect_url)
        url = get_url(redirect_url2)
        logger.info(f'{url}')
        client = SouShuBaClient(urlparse(url).hostname,
                                os.environ.get('SOUSHUBA_USERNAME', "zhuqushi"),
                                os.environ.get('SOUSHUBA_PASSWORD', "lsy19126"))
        client.login()
        # client.space()
        credit = client.credit()
        logger.info(f'{client.username} 有 {credit} 银币!')
    except Exception as e:
        logger.error(e)
        sys.exit(1)

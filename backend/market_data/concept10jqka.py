# -*- coding: utf-8 -*-
import asyncio
import requests
import pandas as pd
import time
import json
import traceback
from playwright.async_api import async_playwright


def parse_market_cap(text):
    """解析流通市值，转换为亿元"""
    if not text or text == "--" or text == "-":
        return None
    try:
        original_text = text
        # 判断单位
        is_wan = "万" in original_text

        # 移除单位
        text = text.replace("亿", "").replace("万", "").strip()
        value = float(text)

        # 如果是万元，转换为亿
        if is_wan:
            value = value / 10000

        return value
    except Exception:
        return None


def parse_pe_ratio(text):
    """解析市盈率"""
    if not text or text == "--" or text == "-":
        return None
    try:
        return float(text)
    except Exception:
        return None


async def crawl(p_url):
    """
    爬取板块名称以及代码
    """
    # 获取排除的概念列表
    headers2 = {
        "X-Bmob-Application-Id": "ca8cc0da5351b1bef80ec5371ee3532e",
        "X-Bmob-REST-API-Key": "b70d44aedda27b342257ba6ac9edc39d",
        "Content-Type": "application/json",
        "Connection": "close",
    }

    try:
        excludecpt = (
            json.loads(
                requests.get(
                    "https://api2.bmob.cn/1/classes/text/mI76888D", headers=headers2
                ).text
            )["text"]
            .replace("，", ",")
            .split(",")
        )
    except Exception as e:
        print(f"获取排除列表失败: {e}")
        excludecpt = []

    async with async_playwright() as p:
        # 使用 chromium headless shell（最轻量）
        browser = await p.chromium.launch(headless=True, channel="chromium-headless-shell")
        page = await browser.new_page()

        # 获取主页面
        try:
            await page.goto(p_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"获取主页面失败: {e}")
            await browser.close()
            return

        # 提取板块名称和代码
        try:
            gnbk_elements = await page.query_selector_all("a")
            thsgnbk = []
            bkcode = []

            for elem in gnbk_elements:
                href = await elem.get_attribute("href")
                if href and "/detail/code/" in href:
                    text = await elem.text_content()
                    if text:
                        thsgnbk.append(text.strip())
                        bkcode.append(href.split("/")[-2])

            if len(thsgnbk) != len(bkcode):
                print(
                    f"警告: 板块名称数量({len(thsgnbk)})与代码数量({len(bkcode)})不匹配"
                )

            data = {"Name": thsgnbk}
            gnbk = pd.DataFrame(data, index=bkcode)

            bk_id = []
            bk_name = []
            print(f"找到 {len(gnbk)} 个板块")
            print(gnbk.index)
            start = time.time()

            for index, row in gnbk.iterrows():
                if index in excludecpt:
                    print(f"跳过排除的板块: {row['Name']}")
                    continue

                s_id = []
                s_name = []
                bk_code = index
                name = row["Name"]
                url = p_url + "/detail/code/" + bk_code + "/"
                print(f"\n处理板块: {name} ({bk_code})")

                # 获取板块详情页
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    print(f"获取板块详情页失败 {name}: {e}")
                    continue

                # 得出板块成分股有多少页
                try:
                    page_locator = page.locator("span#m-page")
                    page_text = await page_locator.text_content()
                    if page_text:
                        page = int(page_text.strip().split("/")[-1])
                        print(f"该板块共有 {page} 页")
                    else:
                        page = 1
                except Exception:
                    page = 1

                # 遍历所有页面
                count = 1
                while count <= page:
                    curl = (
                        p_url
                        + "/detail/field/199112/order/desc/page/"
                        + str(count)
                        + "/ajax/1/code/"
                        + bk_code
                    )
                    print(f"获取第 {count}/{page} 页: {curl}")

                    try:
                        await page.goto(curl, wait_until="networkidle", timeout=30000)
                        await page.wait_for_timeout(1000)

                        # 检查是否被限制
                        page_content = await page.content()
                        if "forbidden." in page_content.lower():
                            print("检测到访问限制，等待60秒...")
                            await asyncio.sleep(60)
                            continue

                        # 成分股代码 - 从表格中提取
                        stock_rows = await page.query_selector_all("table tbody tr")
                        stock_code = []

                        for row in stock_rows:
                            # 第2列是代码
                            code_elem = await row.query_selector("td:nth-child(2) a")
                            if code_elem:
                                text = await code_elem.text_content()
                                if text:
                                    stock_code.append(text.strip())

                        stock_name = []  # 暂时不用，保持兼容性

                        if len(stock_code) > 0:
                            print(f"找到 {len(stock_code)} 只成分股")
                            s_id += stock_code
                            s_name += stock_name
                            bk_id.extend([bk_code] * len(stock_code))
                            bk_name.extend([name] * len(stock_name))
                        else:
                            print("该页没有找到成分股")

                        count += 1
                        await asyncio.sleep(2)

                    except Exception as e:
                        print(f"获取第 {count} 页失败: {e}")
                        count += 1
                        await asyncio.sleep(2)
                        continue

                print(f"板块 {name} 完成，共 {len(s_id)} 只成分股")

            end = time.time()
            await browser.close()
            print(
                f"\n{p_url} 爬取结束！！\n开始时间：{time.ctime(start)}\n结束时间：{time.ctime(end)}\n耗时：{end - start:.2f}秒"
            )

        except Exception as e:
            print(f"爬取过程出错: {e}")
            await browser.close()


async def collect_concept_data(p_url: str) -> tuple[list[dict], list[dict]]:
    """
    采集概念板块和成分股数据，返回结构化数据
    返回: (concepts_list, stocks_list)
    """
    concepts_list = []
    stocks_list = []

    async with async_playwright() as p:
        # 使用 chromium headless shell（最轻量）
        browser = await p.chromium.launch(headless=True, channel="chromium-headless-shell")
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(p_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"获取主页面失败: {e}")
            await browser.close()
            return concepts_list, stocks_list

        try:
            gnbk_elements = await page.query_selector_all("a")
            thsgnbk = []
            bkcode = []

            for elem in gnbk_elements:
                href = await elem.get_attribute("href")
                if href and "/detail/code/" in href:
                    text = await elem.text_content()
                    if text:
                        thsgnbk.append(text.strip())
                        bkcode.append(href.split("/")[-2])

            data = {"Name": thsgnbk}
            gnbk = pd.DataFrame(data, index=bkcode)

            print(f"找到 {len(gnbk)} 个板块")

            for index, row in gnbk.iterrows():
                bk_code = index
                name = row["Name"]
                stocks_data = []  # 存储股票数据，包括代码、流通市值、市盈率

                url = p_url + "/detail/code/" + bk_code + "/"
                print(f"处理板块: {name} ({bk_code})")

                try:
                    # 访问详情页
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    print("  等待页面加载...")
                    await page.wait_for_timeout(5000)

                    # 等待表格加载
                    await page.wait_for_selector(
                        "table.m-table tbody tr", timeout=10000
                    )
                    print("  表格已加载")

                except Exception as e:
                    print(f"  加载失败: {e}，跳过此板块")
                    continue

                # 直接从当前页面提取成分股
                count = 1
                max_pages = 999  # 采集所有页

                while count <= max_pages:
                    try:
                        # 提取当前页的表格数据
                        stock_rows = await page.query_selector_all(
                            "table.m-table tbody tr"
                        )
                        page_data = []

                        for row in stock_rows:
                            cols = await row.query_selector_all("td")
                            if len(cols) >= 13:  # 确保有足够的列
                                # 提取股票代码 (列1)
                                code_elem = await cols[1].query_selector("a")
                                if code_elem:
                                    code_text = await code_elem.text_content()
                                    stock_code = (
                                        code_text.strip() if code_text else None
                                    )

                                    if stock_code:
                                        # 提取流通市值 (列12)
                                        market_cap_text = await cols[12].text_content()
                                        market_cap = parse_market_cap(
                                            market_cap_text.strip()
                                        )

                                        # 提取市盈率 (列13)
                                        pe_text = await cols[13].text_content()
                                        pe_ratio = parse_pe_ratio(pe_text.strip())

                                        page_data.append(
                                            {
                                                "code": stock_code,
                                                "market_cap": market_cap,
                                                "pe_ratio": pe_ratio,
                                            }
                                        )

                        if page_data:
                            print(f"  第 {count} 页: 找到 {len(page_data)} 只股票")
                            stocks_data.extend(page_data)
                        else:
                            print(f"  第 {count} 页: 无数据")
                            break

                        # 如果是第一页，尝试获取总页数
                        if count == 1:
                            try:
                                page_elem = await page.query_selector(
                                    "span#m-page, div.m-pager .page_info"
                                )
                                if page_elem:
                                    page_text = await page_elem.text_content()
                                    import re

                                    match = re.search(r"(\d+)/(\d+)", page_text)
                                    if match:
                                        total_pages = int(match.group(2))
                                        max_pages = total_pages
                                        print(f"  共 {total_pages} 页")
                            except Exception:
                                pass

                        # 如果还有下一页，点击下一页
                        if count < max_pages:
                            try:
                                # 查找"下一页"链接
                                next_link = None
                                page_links = await page.query_selector_all(
                                    "div.m-pager a.changePage"
                                )
                                for link in page_links:
                                    link_text = await link.text_content()
                                    if "下一页" in link_text:
                                        next_link = link
                                        break

                                if next_link:
                                    print("  点击下一页...")
                                    await next_link.click()
                                    await page.wait_for_timeout(3000)  # 等待页面加载

                                    # 等待新表格加载
                                    await page.wait_for_selector(
                                        "table.m-table tbody tr", timeout=5000
                                    )
                                    count += 1
                                else:
                                    print("  没有下一页，结束")
                                    break
                            except Exception as e:
                                print(f"  翻页失败: {e}，结束")
                                break
                        else:
                            break

                    except Exception as e:
                        print(f"  第 {count} 页处理失败: {e}")
                        break

                # 保存所有板块
                if len(stocks_data) > 0:
                    concepts_list.append(
                        {"code": bk_code, "name": name, "stock_count": len(stocks_data)}
                    )

                    for stock in stocks_data:
                        stocks_list.append(
                            {
                                "concept_code": bk_code,
                                "stock_code": stock["code"],
                                "circulating_market_cap": stock["market_cap"],
                                "pe_ratio": stock["pe_ratio"],
                            }
                        )

                    print(f"板块 {name} 完成，共 {len(stocks_data)} 只成分股")
                else:
                    print(f"板块 {name} 无成分股，跳过")

            await browser.close()
            print(f"采集完成: {len(concepts_list)} 个板块, {len(stocks_list)} 只成分股")

        except Exception as e:
            print(f"爬取过程出错: {e}")
            print("错误详情:")
            traceback.print_exc()
            print(f"已采集: {len(concepts_list)} 个板块, {len(stocks_list)} 只成分股")
            await browser.close()
            # Return collected data even if an error occurred
            return concepts_list, stocks_list

    return concepts_list, stocks_list


if __name__ == "__main__":
    asyncio.run(crawl("http://q.10jqka.com.cn/thshy"))
    asyncio.run(crawl("http://q.10jqka.com.cn/gn"))
    asyncio.run(crawl("http://q.10jqka.com.cn/dy"))
    exit()

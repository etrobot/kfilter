# -*- coding: utf-8 -*-
import asyncio
import requests
import pandas as pd
import time
import json
import traceback
import random
from playwright.async_api import async_playwright


# 请求频率控制
_last_request_time = 0
_request_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None
MIN_REQUEST_INTERVAL = 3.0  # 最小请求间隔（秒）
MAX_REQUEST_INTERVAL = 8.0  # 最大请求间隔（秒）
PAGE_REQUEST_DELAY = 5.0  # 页面请求间隔（秒）
MAX_CONCURRENT_REQUESTS = 3  # 最大并发请求数
_request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS) if hasattr(asyncio, 'Semaphore') else None
_forbidden_count = 0  # 403/429错误计数器
_RATE_LIMIT_THRESHOLD = 3  # 触发更严格限制的阈值
_FORBIDDEN_RESET_THRESHOLD = 10  # 成功请求数达到此值时重置forbidden_count
_success_count = 0  # 连续成功请求计数器


def safe_request(url, headers=None, timeout=30, max_retries=5, base_delay=3):
    """
    带有重试和延迟机制的HTTP请求函数

    Args:
        url: 请求URL
        headers: 请求头
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒），实际延迟会在此基础上随机波动

    Returns:
        Response对象，如果失败返回None
    """
    global _last_request_time, _forbidden_count

    for attempt in range(max_retries):
        try:
            # 频率控制：确保请求间隔
            current_time = time.time()
            time_since_last = current_time - _last_request_time
            if time_since_last < MIN_REQUEST_INTERVAL:
                sleep_time = MIN_REQUEST_INTERVAL - time_since_last + random.uniform(0, 2)
                print(f"频率控制：等待 {sleep_time:.1f} 秒")
                time.sleep(sleep_time)

            # 发送请求
            response = requests.get(url, headers=headers, timeout=timeout)
            _last_request_time = time.time()

            # 检查是否被限流
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** attempt)))
                retry_after = max(retry_after, 30)  # 最小等待30秒
                print(f"请求过于频繁(429)，等待 {retry_after} 秒后重试 (尝试 {attempt + 1}/{max_retries})...")
                time.sleep(retry_after)
                _forbidden_count += 1
                continue

            # 检查是否被封禁
            if response.status_code == 403:
                delay = base_delay * (2 ** attempt) + random.uniform(5, 10)
                delay = max(delay, 60)  # 最小等待60秒
                print(f"请求被拒绝(403)，可能触发反爬，等待 {delay:.1f} 秒后重试 (尝试 {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                _forbidden_count += 1
                continue

            # 检查响应
            response.raise_for_status()
            reset_forbidden_count_on_success()
            return response

        except requests.exceptions.Timeout:
            delay = base_delay * (2 ** attempt) + random.uniform(5, 15)
            print(f"请求超时，等待 {delay:.1f} 秒后重试 (尝试 {attempt + 1}/{max_retries})...")
            time.sleep(delay)

        except requests.exceptions.ConnectionError:
            delay = base_delay * (2 ** attempt) + random.uniform(10, 20)
            print(f"连接错误，等待 {delay:.1f} 秒后重试 (尝试 {attempt + 1}/{max_retries})...")
            time.sleep(delay)

        except requests.exceptions.RequestException as e:
            delay = base_delay * (2 ** attempt) + random.uniform(5, 10)
            print(f"请求异常: {e}，等待 {delay:.1f} 秒后重试 (尝试 {attempt + 1}/{max_retries})...")
            time.sleep(delay)

    print(f"请求失败，已达到最大重试次数 ({max_retries}): {url}")
    return None


def get_rate_limit_delay():
    """
    根据当前错误计数获取适当的延迟时间
    """
    global _forbidden_count
    if _forbidden_count >= _RATE_LIMIT_THRESHOLD:
        # 如果多次触发限制，使用更长的延迟
        base_delay = 10.0 + (_forbidden_count - _RATE_LIMIT_THRESHOLD) * 5.0
        # 使用指数退避，最小30秒，最大300秒（5分钟）
        delay = min(max(base_delay, 30.0), 300.0)
        print(f"⚠️ 频繁限制警告: 已触发 {_forbidden_count} 次限制，延迟 {delay:.1f} 秒")
        return delay
    return PAGE_REQUEST_DELAY


def reset_forbidden_count_on_success():
    """
    成功请求后，逐步重置forbidden计数器
    """
    global _forbidden_count, _success_count
    _success_count += 1
    
    if _success_count >= _FORBIDDEN_RESET_THRESHOLD and _forbidden_count > 0:
        _forbidden_count = max(0, _forbidden_count - 1)
        _success_count = 0
        print(f"✓ 连续成功 {_FORBIDDEN_RESET_THRESHOLD} 次，降低限制等级 (当前: {_forbidden_count})")


def report_rate_limit_status():
    """
    报告当前的速率限制状态
    """
    global _forbidden_count, _success_count
    if _forbidden_count > 0:
        print(f"📊 速率限制状态: 限制次数={_forbidden_count}, 成功次数={_success_count}/{_FORBIDDEN_RESET_THRESHOLD}")
    return {"forbidden_count": _forbidden_count, "success_count": _success_count}


async def safe_page_navigation(page, url, timeout=30000, max_retries=3):
    """
    安全的页面导航函数，带有重试和延迟机制

    Args:
        page: Playwright页面对象
        url: 目标URL
        timeout: 超时时间（毫秒）
        max_retries: 最大重试次数

    Returns:
        是否成功
    """
    global _forbidden_count
    
    for attempt in range(max_retries):
        try:
            # 添加适应性页面导航延迟
            rate_limit_delay = get_rate_limit_delay()
            await asyncio.sleep(rate_limit_delay + random.uniform(1, 3))

            await page.goto(url, wait_until="networkidle", timeout=timeout)

            # 检查是否被封禁
            page_content = await page.content()
            if "forbidden." in page_content.lower():
                delay = 60 * (2 ** attempt)
                print(f"检测到访问限制（第 {_forbidden_count + 1} 次），等待 {delay} 秒...")
                await asyncio.sleep(delay)
                _forbidden_count += 1
                continue

            reset_forbidden_count_on_success()
            return True

        except Exception as e:
            delay = 5 * (2 ** attempt) + random.uniform(3, 8)
            print(f"页面导航失败 (尝试 {attempt + 1}/{max_retries}): {e}，等待 {delay:.1f} 秒...")
            await asyncio.sleep(delay)

    print(f"页面导航失败，已达到最大重试次数 ({max_retries}): {url}")
    return False


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
        response = safe_request(
            "https://api2.bmob.cn/1/classes/text/mI76888D", 
            headers=headers2,
            max_retries=3,
            base_delay=2
        )
        if response:
            excludecpt = (
                json.loads(response.text)["text"]
                .replace("，", ",")
                .split(",")
            )
        else:
            print("获取排除列表失败: 请求返回None")
            excludecpt = []
    except Exception as e:
        print(f"获取排除列表失败: {e}")
        excludecpt = []

    async with async_playwright() as p:
        # 使用 chromium headless shell（最轻量）+ 反反爬策略
        browser = await p.chromium.launch(
            headless=True, 
            channel="chromium-headless-shell",
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        
        # 创建上下文，设置真实的浏览器特征
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        
        page = await context.new_page()
        
        # 隐藏 webdriver 特征
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # 获取主页面
        if not await safe_page_navigation(page, p_url, timeout=30000):
            print(f"获取主页面失败，关闭浏览器")
            await browser.close()
            return
        await page.wait_for_timeout(3000)  # 增加等待时间确保JS加载

        # 提取板块名称和代码
        try:
            # 提取隐藏字段 gnSection 中的板块代码
            gn_section_input = await page.query_selector("input#gnSection")
            if not gn_section_input:
                print("未找到 gnSection 隐藏字段")
                await browser.close()
                return
            
            gn_section_value = await gn_section_input.get_attribute("value")
            if not gn_section_value:
                print("gnSection 字段值为空")
                await browser.close()
                return
            
            # 解析 JSON 数据
            gn_data = json.loads(gn_section_value)
            
            # 提取板块名称和代码
            thsgnbk = []
            bkcode = []  # platecode - 保存到数据库
            cid_list = []  # cid - 用于构建URL
            
            for key, value in gn_data.items():
                if isinstance(value, dict) and "platecode" in value and "platename" in value and "cid" in value:
                    platecode = value["platecode"]
                    platename = value["platename"]
                    cid = value["cid"]
                    thsgnbk.append(platename)
                    bkcode.append(platecode)
                    cid_list.append(cid)

            if len(thsgnbk) != len(bkcode):
                print(
                    f"警告: 板块名称数量({len(thsgnbk)})与代码数量({len(bkcode)})不匹配"
                )

            data = {"Name": thsgnbk, "CID": cid_list}
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
                bk_code = index  # platecode - 保存到数据库
                cid = row["CID"]  # cid - 用于构建URL
                name = row["Name"]
                url = p_url + "/detail/code/" + cid + "/"
                print(f"\n处理板块: {name} (platecode={bk_code}, cid={cid})")
                report_rate_limit_status()

                # 获取板块详情页
                if not await safe_page_navigation(page, url, timeout=30000):
                    print(f"获取板块详情页失败 {name}")
                    continue
                await page.wait_for_timeout(2000)

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
                    try:
                        curl = (
                            p_url
                            + "/detail/field/199112/order/desc/page/"
                            + str(count)
                            + "/ajax/1/code/"
                            + bk_code
                        )
                        print(f"获取第 {count}/{page} 页: {curl}")

                        if not await safe_page_navigation(page, curl, timeout=30000):
                            continue
                        await page.wait_for_timeout(1000)

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


async def collect_concept_data(
    p_url: str,
    on_concept_collected=None,
) -> tuple[list[dict], list[dict]]:
    """
    采集概念板块和成分股数据，返回结构化数据
    返回: (concepts_list, stocks_list)
    """
    concepts_list = []
    stocks_list = []

    async with async_playwright() as p:
        # 使用 chromium headless shell（最轻量）+ 反反爬策略
        browser = await p.chromium.launch(
            headless=True, 
            channel="chromium-headless-shell",
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        
        # 创建上下文，设置真实的浏览器特征
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        
        page = await context.new_page()
        
        # 隐藏 webdriver 特征
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        if not await safe_page_navigation(page, p_url, timeout=30000):
            print(f"获取主页面失败")
            await browser.close()
            return concepts_list, stocks_list
        await page.wait_for_timeout(3000)  # 增加等待时间确保JS加载

        try:
            # 提取隐藏字段 gnSection 中的板块代码
            gn_section_input = await page.query_selector("input#gnSection")
            if not gn_section_input:
                print("未找到 gnSection 隐藏字段")
                await browser.close()
                return concepts_list, stocks_list
            
            gn_section_value = await gn_section_input.get_attribute("value")
            if not gn_section_value:
                print("gnSection 字段值为空")
                await browser.close()
                return concepts_list, stocks_list
            
            # 解析 JSON 数据
            gn_data = json.loads(gn_section_value)
            
            # 提取板块名称和代码
            thsgnbk = []
            bkcode = []  # platecode - 保存到数据库
            cid_list = []  # cid - 用于构建URL
            
            for key, value in gn_data.items():
                if isinstance(value, dict) and "platecode" in value and "platename" in value and "cid" in value:
                    platecode = value["platecode"]
                    platename = value["platename"]
                    cid = value["cid"]
                    thsgnbk.append(platename)
                    bkcode.append(platecode)
                    cid_list.append(cid)
            
            data = {"Name": thsgnbk, "CID": cid_list}
            gnbk = pd.DataFrame(data, index=bkcode)

            total_concepts_count = len(gnbk)
            print(f"找到 {total_concepts_count} 个板块")

            processed_concepts = 0

            for index, row in gnbk.iterrows():
                bk_code = index  # platecode - 保存到数据库
                cid = row["CID"]  # cid - 用于构建URL
                name = row["Name"]
                stocks_data = []  # 存储股票数据，包括代码、流通市值、市盈率

                url = p_url + "/detail/code/" + cid + "/"
                print(f"处理板块: {name} (platecode={bk_code}, cid={cid})")
                report_rate_limit_status()

                # 访问详情页
                if not await safe_page_navigation(page, url, timeout=30000):
                    print(f"  页面导航失败，跳过此板块")
                    continue
                print("  等待页面加载...")
                await page.wait_for_timeout(5000)

                try:
                    # 等待表格加载
                    await page.wait_for_selector(
                        "table.m-table tbody tr", timeout=10000
                    )
                    print("  表格已加载")

                except Exception as e:
                    print(f"  表格加载失败: {e}，跳过此板块")
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
                    # 计算板块总市值（亿元）
                    total_market_cap = sum(
                        stock["market_cap"] for stock in stocks_data 
                        if stock["market_cap"] is not None
                    )
                    
                    concept_entry = {
                        "code": bk_code,
                        "name": name,
                        "stock_count": len(stocks_data),
                        "total_market_cap": total_market_cap,
                    }
                    concept_stock_entries = [
                        {
                            "concept_code": bk_code,
                            "stock_code": stock["code"],
                            "circulating_market_cap": stock["market_cap"],
                            "pe_ratio": stock["pe_ratio"],
                        }
                        for stock in stocks_data
                    ]

                    concepts_list.append(concept_entry)
                    stocks_list.extend(concept_stock_entries)

                    processed_concepts += 1

                    if on_concept_collected:
                        try:
                            on_concept_collected(
                                concept_entry,
                                concept_stock_entries,
                                processed_concepts,
                                total_concepts_count,
                            )
                        except Exception as callback_error:
                            print(
                                f"实时保存板块 {name} 失败: {callback_error}"
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

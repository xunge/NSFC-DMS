"""项目信息爬虫"""
import re
import time
import logging
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)


def extract_project_info(url):
    """从URL提取项目信息 - 使用Edge浏览器和特定的元素定位"""
    try:
        logger.info(f"开始抓取: {url}")

        # 从URL中提取NSFC ID
        nsfc_id_match = re.search(r'id=([a-f0-9]{32})', url)
        nsfc_id = nsfc_id_match.group(1) if nsfc_id_match else None
        if nsfc_id:
            logger.info(f"提取到NSFC ID: {nsfc_id}")
        else:
            logger.warning(f"无法从URL提取NSFC ID: {url}")
        
        # 配置Edge选项 - 严格参考用户提供的代码
        edge_options = Options()
        edge_options.add_argument("--headless=new")   # 调试可注释
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--no-sandbox")
        
        # 使用用户指定的驱动路径
        service = Service("../drivers/msedgedriver")
        driver = webdriver.Edge(service=service, options=edge_options)
        
        try:
            # 访问页面
            driver.get(url)
            
            # 等待"info"区域真正渲染完成
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.ID, "info")))
            
            # 给Vue一点渲染时间
            time.sleep(2)
            
            # 查找所有信息行 - 使用用户提供的成功代码
            rows = driver.find_elements(
                By.XPATH,
                "//div[@id='info']//div[contains(@class,'el-row')]"
            )
            
            info = {}
            for row in rows:
                try:
                    # 使用用户提供的成功代码中的选择器
                    label = row.find_element(By.XPATH, "./div[1]").text.strip()
                    value = row.find_element(By.XPATH, "./div[2]").text.strip()
                    
                    # 清理字段名（移除冒号和空格）
                    label = label.rstrip('：: ').strip()
                    
                    # 跳过空字段
                    if label and value:
                        info[label] = value
                except:
                    continue
            
            logger.info(f"从表格中提取到 {len(info)} 个字段: {list(info.keys())}")
            
            # 提取摘要信息
            abstract = ""
            conclusion_abstract = ""
            
            # 尝试查找摘要区域
            try:
                # 查找项目摘要
                abstract_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '项目摘要')]")
                if abstract_elements:
                    for elem in abstract_elements:
                        text = elem.text
                        if '项目摘要' in text:
                            try:
                                parent = elem.find_element(By.XPATH, "./following-sibling::*[1]")
                                abstract = parent.text.strip()
                            except:
                                # 备用方法：从页面文本中提取
                                page_text = driver.find_element(By.TAG_NAME, 'body').text
                                match = re.search(r'项目摘要[:：]?\s*(.+?)(?=结题摘要|项目负责人|依托单位|研究期限|资助经费|$)', page_text, re.DOTALL)
                                if match:
                                    abstract = match.group(1).strip()
                            break
            except:
                pass
            
            # 尝试查找结题摘要
            try:
                conclusion_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '结题摘要')]")
                if conclusion_elements:
                    for elem in conclusion_elements:
                        text = elem.text
                        if '结题摘要' in text:
                            try:
                                parent = elem.find_element(By.XPATH, "./following-sibling::*[1]")
                                conclusion_abstract = parent.text.strip()
                            except:
                                page_text = driver.find_element(By.TAG_NAME, 'body').text
                                match = re.search(r'结题摘要[:：]?\s*(.+?)(?=项目负责人|依托单位|研究期限|资助经费|$)', page_text, re.DOTALL)
                                if match:
                                    conclusion_abstract = match.group(1).strip()
                            break
            except:
                pass
            
            # 如果没有从表格中提取到数据，使用备用方法
            if not info:
                logger.warning("表格提取失败，使用备用文本提取方法")
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                all_text = soup.get_text()
                
                # 使用正则表达式提取关键信息
                patterns = {
                    'approval_number': r'(项目批准号|批准号)[:：]?\s*([A-Z0-9]{8,})',
                    'application_code': r'(申请代码)[:：]?\s*([A-Z0-9]{2,})',
                    'title': r'(项目名称)[:：]?\s*(.+?)(?=\s*(?:项目批准号|申请代码|项目负责人|依托单位|研究期限|资助经费|$))',
                    'leader': r'(项目负责人|负责人)[:：]?\s*(.+?)(?=\s*(?:依托单位|申请代码|$))',
                    'unit': r'(依托单位|单位)[:：]?\s*(.+?)(?=\s*(?:研究期限|资助经费|$))',
                    'start_date': r'(研究期限|执行期限)[:：]?\s*(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})',
                    'end_date': r'(研究期限|执行期限)[:：]?\s*(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})',
                    'funding': r'(资助经费|经费)[:：]?\s*([\d.]+)\s*万元'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, all_text)
                    if match:
                        if key == 'start_date':
                            info['start_date'] = match.group(2).strip()
                            info['end_date'] = match.group(3).strip()
                        elif key == 'funding':
                            info['funding'] = float(match.group(2).strip())
                        elif key == 'title':
                            info['title'] = match.group(2).strip()
                        elif key == 'approval_number':
                            info['approval_number'] = match.group(2).strip()
                        elif key == 'application_code':
                            info['application_code'] = match.group(2).strip()
                        elif key == 'leader':
                            info['leader'] = match.group(2).strip()
                        elif key == 'unit':
                            info['unit'] = match.group(2).strip()
                
                # 提取摘要
                if not abstract:
                    match = re.search(r'项目摘要[:：]?\s*(.+?)(?=结题摘要|项目负责人|依托单位|研究期限|资助经费|$)', all_text, re.DOTALL)
                    if match:
                        abstract = match.group(1).strip()
                
                if not conclusion_abstract:
                    match = re.search(r'结题摘要[:：]?\s*(.+?)(?=项目负责人|依托单位|研究期限|资助经费|$)', all_text, re.DOTALL)
                    if match:
                        conclusion_abstract = match.group(1).strip()
            
            # 构建结果 - 根据实际提取的字段名进行映射
            result = {
                'nsfc_id': nsfc_id,
                'title': info.get('项目名称', ''),
                'approval_number': info.get('项目批准号', ''),
                'application_code': info.get('申请代码', ''),
                'leader': info.get('项目负责人', ''),
                'unit': info.get('依托单位', ''),
                'start_date': info.get('研究期限', '').split(' 至 ')[0] if ' 至 ' in info.get('研究期限', '') else '',
                'end_date': info.get('研究期限', '').split(' 至 ')[1] if ' 至 ' in info.get('研究期限', '') else '',
                'funding': info.get('资助经费', '').replace('（万元）', '').replace('万元', '') if info.get('资助经费') else '',
                'abstract': abstract,
                'conclusion_abstract': conclusion_abstract,
                'url': url
            }
            
            # 验证结果
            extracted_fields = [k for k, v in result.items() if v and k != 'url']
            logger.info(f"数据提取完成，共提取 {len(extracted_fields)} 个字段: {extracted_fields}")
            
            if len(extracted_fields) < 3:
                logger.warning(f"提取到的数据较少: {result}")
                # 保存调试信息
                try:
                    debug_html = f"debug_failed_{int(time.time())}.html"
                    with open(debug_html, 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    logger.info(f"已保存调试文件: {debug_html}")
                except:
                    pass
            
            return result
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"抓取失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

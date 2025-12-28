from flask import Flask, request, jsonify, send_file, Response, stream_with_context
from flask_cors import CORS
import sqlite3
import os
import json
import time
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
import fitz  # PyPDF2
import logging
from io import BytesIO
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import threading

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


class NsfcReportDownloader:
    """国自然结题报告下载器"""

    def __init__(self):
        self.base_url = "https://kd.nsfc.cn"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # 配置重试策略
        retry_strategy = Retry(
            total=10,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def init_session(self):
        """访问首页以获取初始Cookie"""
        try:
            logger.info(f"[INIT] 访问首页获取Cookie: {self.base_url}")
            resp = self.session.get(self.base_url, timeout=10)
            logger.info(f"[INIT] 首页访问状态: {resp.status_code}")
            logger.info(f"[INIT] Cookie: {self.session.cookies.get_dict()}")
        except Exception as e:
            logger.warning(f"[INIT] 首页访问失败: {e}")
            pass

    def get_project_info(self, project_id):
        """获取项目名称"""
        url = f"{self.base_url}/api/baseQuery/conclusionProjectInfo/{project_id}"
        try:
            logger.info(f"[INFO] 获取项目信息: {url}")
            resp = self.session.post(url, timeout=15)
            logger.info(f"[INFO] 项目信息响应状态: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                project_name = data.get('projectName', f'nsfc_{project_id}')
                logger.info(f"[INFO] 获取到项目名称: {project_name}")
                return project_name
        except Exception as e:
            logger.warning(f"[INFO] 获取项目信息预警: {e}")
        return f"nsfc_{project_id}"

    def get_image_url_from_api(self, nsfc_id, index):
        """从API获取图片下载地址"""
        api_url = f"{self.base_url}/api/baseQuery/completeProjectReport"
        data = {"id": nsfc_id, "index": index}

        try:
            logger.info(f"[API] 请求第 {index} 页: {api_url}, data={data}")
            resp = self.session.post(api_url, data=data, timeout=15)
            logger.info(f"[API] 第 {index} 页响应状态: {resp.status_code}")
            if resp.status_code == 200:
                json_data = resp.json()
                logger.info(f"[API] 第 {index} 页响应数据: {json_data}")
                if json_data.get('code') == 200 and json_data.get('data'):
                    img_url = self.base_url + json_data['data']['url']
                    logger.info(f"[API] 第 {index} 页获取到图片URL: {img_url}")
                    return img_url
                else:
                    logger.info(f"[API] 第 {index} 页无数据或code不为200")
                    return None
            else:
                logger.warning(f"[API] 第 {index} 页状态码异常: {resp.status_code}")
                return "RETRY"
        except Exception as e:
            logger.warning(f"[API] 第 {index} 页请求异常: {e}")
            return "RETRY"

    def download_image_content(self, img_url):
        """下载图片二进制内容"""
        try:
            logger.info(f"[IMG] 开始下载图片: {img_url}")
            resp = self.session.get(img_url, timeout=20)
            logger.info(f"[IMG] 图片响应状态: {resp.status_code}")
            if resp.status_code == 404:
                logger.info(f"[IMG] 图片返回404: {img_url}")
                return "404"
            if resp.status_code != 200:
                logger.warning(f"[IMG] 图片响应异常: {resp.status_code}")
                return None
            content_length = len(resp.content) if resp.content else 0
            logger.info(f"[IMG] 图片下载成功，大小: {content_length} bytes")
            return resp.content
        except Exception as e:
            logger.warning(f"[IMG] 图片下载异常: {e}")
            return None

    def download_report(self, nsfc_id, project_name, progress_callback=None):
        """
        下载结题报告并保存为PDF

        Args:
            nsfc_id: URL中的项目ID（如a04e2d4d939754a6f416195ef228422b）
            project_name: 项目名称
            progress_callback: 进度回调函数，接收当前进度和状态信息

        Returns:
            dict: {'success': bool, 'file_path': str, 'filename': str, 'message': str}
        """
        try:
            # 初始化会话
            if progress_callback:
                progress_callback(5, "初始化会话...")
            self.init_session()

            # 净化文件名
            safe_name = re.sub(r'[\\/*?:"<>|]', "", project_name).strip()
            if not safe_name:
                safe_name = f"nsfc_{nsfc_id}"

            images = []
            index = 1
            consecutive_failures = 0

            if progress_callback:
                progress_callback(10, f"开始下载项目: {safe_name}")

            while True:
                logger.info(f"========== 开始处理第 {index} 页 ==========")

                # 步骤1: 获取图片链接
                img_url = None
                retry_count = 0

                # API 获取 URL 的重试循环
                while retry_count < 3:
                    logger.info(f"[循环] 第 {index} 页，API重试次数: {retry_count}")
                    img_url = self.get_image_url_from_api(nsfc_id, index)
                    if img_url == "RETRY":
                        retry_count += 1
                        wait_time = 2 * retry_count
                        logger.info(f"[循环] API重试等待 {wait_time}秒...")
                        time.sleep(wait_time)
                        continue
                    break

                if not img_url:
                    logger.info(f"[循环] 第 {index} 页 API 返回空，判断为下载结束")
                    if progress_callback:
                        progress_callback(95, f"第 {index} 页 API 返回空，判断为下载结束")
                    break

                # 步骤2: 下载图片内容
                if progress_callback:
                    progress_callback(10 + (index * 80 // 100), f"正在处理第 {index} 页...")

                content = None
                dl_retry = 0

                # 图片下载的重试循环
                while dl_retry < 5:
                    logger.info(f"[循环] 第 {index} 页，图片下载重试次数: {dl_retry}")
                    content = self.download_image_content(img_url)

                    if content == "404":
                        logger.info(f"[循环] 第 {index} 页图片返回404，结束下载")
                        if progress_callback:
                            progress_callback(95, f"第 {index} 页图片返回 404，下载结束")
                        img_url = None
                        break

                    if content:
                        logger.info(f"[循环] 第 {index} 页图片下载成功")
                        break

                    dl_retry += 1
                    sleep_time = 2 + dl_retry
                    logger.info(f"[循环] 第 {index} 页下载失败，等待 {sleep_time}秒后重试")
                    if progress_callback:
                        progress_callback(10 + (index * 80 // 100),
                                         f"第 {index} 页下载失败，第 {dl_retry} 次重试 (等待{sleep_time}s)...")
                    time.sleep(sleep_time)

                if img_url is None:
                    logger.info(f"[循环] img_url为None，跳出循环")
                    break

                if not content:
                    logger.warning(f"第 {index} 页尝试多次后仍无法下载，已跳过")
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        if progress_callback:
                            progress_callback(100, "连续3页下载失败，可能IP被封或网络中断")
                        break
                    index += 1
                    continue

                consecutive_failures = 0

                # 步骤3: 处理图片
                try:
                    img = Image.open(BytesIO(content))
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    images.append(img)
                    logger.info(f"[图片] 第 {index} 页图片处理成功，当前已收集 {len(images)} 张图片")
                except Exception as e:
                    logger.error(f"图片损坏: {e}")

                index += 1
                sleep_time = random.uniform(1.5, 3.5)
                logger.info(f"[循环] 随机延时 {sleep_time:.2f}秒")
                time.sleep(sleep_time)

            logger.info(f"[循环] 主循环结束，共收集 {len(images)} 张图片")
            # 步骤4: 合成PDF
            if images:
                logger.info(f"[PDF] 开始合成PDF，共 {len(images)} 页")
                if progress_callback:
                    progress_callback(98, "正在合成PDF...")

                # 生成文件名
                timestamp = int(time.time())
                filename = f"{safe_name}_{timestamp}.pdf"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                logger.info(f"[PDF] 保存路径: {file_path}")

                images[0].save(
                    file_path, "PDF", resolution=100.0, save_all=True, append_images=images[1:]
                )
                logger.info(f"[PDF] PDF合成完成")

                if progress_callback:
                    progress_callback(100, f"成功！共 {len(images)} 页")

                return {
                    'success': True,
                    'file_path': file_path,
                    'filename': filename,
                    'page_count': len(images),
                    'message': f"成功下载 {len(images)} 页"
                }
            else:
                logger.warning(f"[PDF] 没有图片，无法生成PDF")
                if progress_callback:
                    progress_callback(100, "未能下载任何有效图片")
                return {
                    'success': False,
                    'message': "未能下载任何有效图片"
                }

        except Exception as e:
            logger.error(f"下载结题报告失败: {str(e)}")
            if progress_callback:
                progress_callback(100, f"下载失败: {str(e)}")
            return {
                'success': False,
                'message': f"下载失败: {str(e)}"
            }

# 配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 1000 * 1024 * 1024  # 1000MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 数据库初始化
def init_db():
    """初始化数据库"""
    conn = sqlite3.connect('nsfc.db')
    cursor = conn.cursor()
    
    # 项目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            nsfc_id TEXT,
            title TEXT NOT NULL,
            approval_number TEXT,
            application_code TEXT,
            leader TEXT,
            unit TEXT,
            start_date TEXT,
            end_date TEXT,
            funding REAL,
            abstract TEXT,
            conclusion_abstract TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 检查并添加缺失的列
    cursor.execute("PRAGMA table_info(projects)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'nsfc_id' not in columns:
        cursor.execute('ALTER TABLE projects ADD COLUMN nsfc_id TEXT')
        logger.info("已添加 nsfc_id 列到 projects 表")
    
    # PDF 文件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')
    
    # 搜索历史表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            search_type TEXT,
            results_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成")

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect('nsfc.db')
    conn.row_factory = sqlite3.Row
    return conn

def allowed_file(filename):
    """检查文件类型"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_project_info(url):
    """从URL提取项目信息 - 使用Edge浏览器和特定的元素定位"""
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.edge.service import Service
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time
    import re

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

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/projects/fetch', methods=['POST'])
def fetch_project():
    """获取项目信息"""
    data = request.get_json()
    url = data.get('url')
    auto_download = data.get('auto_download', False)  # 是否自动下载结题报告
    if not url:
        return jsonify({'error': 'URL不能为空'}), 400
    
    # 验证URL格式
    if 'kd.nsfc.cn' not in url:
        return jsonify({'error': '请提供kd.nsfc.cn的有效URL'}), 400
    
    try:
        project_info = extract_project_info(url)
        
        if not project_info:
            return jsonify({'error': '无法获取项目信息，请检查URL是否正确'}), 400
        
        # 保存到数据库
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查是否已存在（使用 nsfc_id 或 url）
        existing_project = None
        if project_info.get('nsfc_id'):
            cursor.execute('SELECT id FROM projects WHERE nsfc_id = ?', (project_info['nsfc_id'],))
            existing_project = cursor.fetchone()

        if not existing_project:
            cursor.execute('SELECT id FROM projects WHERE url = ?', (url,))
            existing_project = cursor.fetchone()

        if existing_project:
            # 更新现有记录
            project_id = existing_project['id']
            cursor.execute('''
                UPDATE projects
                SET nsfc_id=?, title=?, approval_number=?, application_code=?, leader=?, unit=?,
                    start_date=?, end_date=?, funding=?, abstract=?, conclusion_abstract=?, url=?
                WHERE id=?
            ''', (
                project_info.get('nsfc_id'), project_info['title'], project_info['approval_number'],
                project_info['application_code'], project_info['leader'], project_info['unit'],
                project_info['start_date'], project_info['end_date'], project_info['funding'],
                project_info['abstract'], project_info['conclusion_abstract'], url, project_id
            ))
        else:
            # 插入新记录
            project_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO projects (id, nsfc_id, title, approval_number, application_code, leader, unit,
                                    start_date, end_date, funding, abstract, conclusion_abstract, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id, project_info.get('nsfc_id'), project_info['title'], project_info['approval_number'],
                project_info['application_code'], project_info['leader'], project_info['unit'],
                project_info['start_date'], project_info['end_date'], project_info['funding'],
                project_info['abstract'], project_info['conclusion_abstract'], url
            ))
        
        conn.commit()
        conn.close()
        
        # 记录搜索历史
        record_search_history('url', url, 1)
        
        result = {
            'success': True,
            'data': project_info,
            'project_id': project_id
        }
        
        # 如果启用自动下载，返回一个标记，让前端调用单独的下载接口
        if auto_download:
            result['need_download_report'] = True

        return result

    except Exception as e:
        logger.error(f"处理项目失败: {str(e)}")
        return jsonify({'error': f'处理失败: {str(e)}'}), 500


@app.route('/api/projects/<project_id>/download-report', methods=['GET', 'POST'])
def download_project_report(project_id):
    """单独下载结题报告 - 使用 SSE 实时推送进度"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 检查项目是否存在，获取nsfc_id和项目名称
    cursor.execute('SELECT id, nsfc_id, title FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()

    if not project:
        conn.close()
        return jsonify({'error': '项目不存在'}), 404

    nsfc_id = project['nsfc_id']
    project_name = project['title']
    
    # 如果没有nsfc_id，尝试从URL中提取
    if not nsfc_id:
        cursor.execute('SELECT url FROM projects WHERE id = ?', (project_id,))
        url_result = cursor.fetchone()
        if url_result and url_result['url']:
            nsfc_id_match = re.search(r'id=([a-f0-9]{32})', url_result['url'])
            if nsfc_id_match:
                nsfc_id = nsfc_id_match.group(1)
    
    conn.close()

    def generate():
        """生成 SSE 事件流"""
        try:
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'message': '开始下载结题报告...'})}\n\n"
            logger.info(f"开始下载结题报告: {project_id}, nsfc_id: {nsfc_id}, 项目名称: {project_name}")

            # 定义进度回调函数
            def progress_callback(progress, message):
                # 发送进度事件
                event_data = json.dumps({
                    'type': 'progress',
                    'progress': progress,
                    'message': message
                })
                yield f"data: {event_data}\n\n"
                logger.info(f"[下载进度] {progress}% - {message}")

            # 执行下载 - 使用nsfc_id而不是project_id
            downloader = NsfcReportDownloader()
            result = downloader.download_report(nsfc_id, project_name, progress_callback)

            if result['success']:
                # 保存到数据库
                conn = get_db_connection()
                cursor = conn.cursor()

                report_id = str(uuid.uuid4())
                file_size = os.path.getsize(result['file_path'])

                cursor.execute('''
                    INSERT INTO reports (id, project_id, filename, file_path, file_size)
                    VALUES (?, ?, ?, ?, ?)
                ''', (report_id, project_id, result['filename'], result['file_path'], file_size))

                conn.commit()
                conn.close()

                logger.info(f"结题报告下载完成: {result['filename']}, 共 {result.get('page_count', 0)} 页")

                # 发送完成事件
                complete_data = {
                    'type': 'complete',
                    'success': True,
                    'report_id': report_id,
                    'filename': result['filename'],
                    'page_count': result.get('page_count', 0),
                    'message': result['message']
                }
                yield f"data: {json.dumps(complete_data)}\n\n"
            else:
                logger.warning(f"结题报告下载失败: {result['message']}")
                error_data = {
                    'type': 'error',
                    'message': result['message']
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        except Exception as e:
            logger.error(f"下载结题报告失败: {str(e)}")
            error_data = {
                'type': 'error',
                'message': f'下载失败: {str(e)}'
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    # 返回 SSE 响应
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )


@app.route('/api/projects/<project_id>/download-report-simple', methods=['POST'])
def download_project_report_simple(project_id):
    """简化版下载 - 不使用 SSE，只返回最终结果"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 检查项目是否存在，获取nsfc_id和项目名称
    cursor.execute('SELECT id, nsfc_id, title FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()

    if not project:
        conn.close()
        return jsonify({'error': '项目不存在'}), 404

    nsfc_id = project['nsfc_id']
    project_name = project['title']
    
    # 如果没有nsfc_id，尝试从URL中提取
    if not nsfc_id:
        cursor.execute('SELECT url FROM projects WHERE id = ?', (project_id,))
        url_result = cursor.fetchone()
        if url_result and url_result['url']:
            nsfc_id_match = re.search(r'id=([a-f0-9]{32})', url_result['url'])
            if nsfc_id_match:
                nsfc_id = nsfc_id_match.group(1)
    
    conn.close()

    # 定义进度回调函数，实时记录日志
    def progress_callback(progress, message):
        logger.info(f"[下载进度] {progress}% - {message}")

    try:
        logger.info(f"开始下载结题报告: {project_id}, nsfc_id: {nsfc_id}, 项目名称: {project_name}")
        downloader = NsfcReportDownloader()
        result = downloader.download_report(nsfc_id, project_name, progress_callback)

        if result['success']:
            # 保存到数据库
            conn = get_db_connection()
            cursor = conn.cursor()

            report_id = str(uuid.uuid4())
            file_size = os.path.getsize(result['file_path'])

            cursor.execute('''
                INSERT INTO reports (id, project_id, filename, file_path, file_size)
                VALUES (?, ?, ?, ?, ?)
            ''', (report_id, project_id, result['filename'], result['file_path'], file_size))

            conn.commit()
            conn.close()

            logger.info(f"结题报告下载完成: {result['filename']}, 共 {result.get('page_count', 0)} 页")

            return jsonify({
                'success': True,
                'report_id': report_id,
                'filename': result['filename'],
                'page_count': result.get('page_count', 0),
                'message': result['message']
            })
        else:
            logger.warning(f"结题报告下载失败: {result['message']}")
            return jsonify({'error': result['message']}), 500

    except Exception as e:
        logger.error(f"下载结题报告失败: {str(e)}")
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """查询项目列表"""
    unit = request.args.get('unit', '')
    code = request.args.get('code', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 构建查询
    query = 'SELECT * FROM projects WHERE 1=1'
    params = []
    
    if unit:
        query += ' AND unit LIKE ?'
        params.append(f'%{unit}%')
    
    if code:
        query += ' AND application_code LIKE ?'
        params.append(f'%{code}%')
    
    # 获取总数
    count_query = query.replace('SELECT *', 'SELECT COUNT(*) as count')
    cursor.execute(count_query, params)
    total = cursor.fetchone()['count']
    
    # 分页查询
    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    
    cursor.execute(query, params)
    projects = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # 记录搜索历史
    if unit or code:
        record_search_history('unit' if unit else 'code', unit or code, total)
    
    return jsonify({
        'success': True,
        'data': projects,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        }
    })

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project_detail(project_id):
    """获取项目详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()
    
    if not project:
        conn.close()
        return jsonify({'error': '项目不存在'}), 404
    
    # 获取关联的PDF文件
    cursor.execute('SELECT * FROM reports WHERE project_id = ? ORDER BY upload_date DESC', (project_id,))
    reports = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    result = dict(project)
    result['reports'] = reports
    
    return jsonify({'success': True, 'data': result})

@app.route('/api/projects', methods=['POST'])
def create_project():
    """手动创建项目"""
    data = request.get_json()
    
    required_fields = ['title', 'approval_number', 'unit']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field}不能为空'}), 400
    
    project_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO projects (id, title, approval_number, application_code, leader, unit, 
                            start_date, end_date, funding, abstract, conclusion_abstract, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_id,
        data.get('title'),
        data.get('approval_number'),
        data.get('application_code'),
        data.get('leader'),
        data.get('unit'),
        data.get('start_date'),
        data.get('end_date'),
        data.get('funding'),
        data.get('abstract'),
        data.get('conclusion_abstract'),
        data.get('url')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'project_id': project_id})

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目信息"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查项目是否存在
    cursor.execute('SELECT id FROM projects WHERE id = ?', (project_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': '项目不存在'}), 404
    
    # 更新项目
    cursor.execute('''
        UPDATE projects 
        SET title=?, approval_number=?, application_code=?, leader=?, unit=?, 
            start_date=?, end_date=?, funding=?, abstract=?, conclusion_abstract=?, url=?
        WHERE id=?
    ''', (
        data.get('title'),
        data.get('approval_number'),
        data.get('application_code'),
        data.get('leader'),
        data.get('unit'),
        data.get('start_date'),
        data.get('end_date'),
        data.get('funding'),
        data.get('abstract'),
        data.get('conclusion_abstract'),
        data.get('url'),
        project_id
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查项目是否存在
    cursor.execute('SELECT id FROM projects WHERE id = ?', (project_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': '项目不存在'}), 404
    
    # 删除关联的PDF文件记录
    cursor.execute('SELECT file_path FROM reports WHERE project_id = ?', (project_id,))
    reports = cursor.fetchall()
    
    for report in reports:
        file_path = report['file_path']
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"删除文件失败: {str(e)}")
    
    cursor.execute('DELETE FROM reports WHERE project_id = ?', (project_id,))
    cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/reports/upload', methods=['POST'])
def upload_report():
    """上传结题报告PDF"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    project_id = request.form.get('project_id')
    
    if not project_id:
        return jsonify({'error': '项目ID不能为空'}), 400
    
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': '只支持PDF格式文件'}), 400
    
    # 检查项目是否存在并获取项目信息
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, application_code, title FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()
    if not project:
        conn.close()
        return jsonify({'error': '项目不存在'}), 404
    
    # 获取项目信息用于文件命名
    application_code = project['application_code'] or '未知代码'
    title = project['title'] or '未知项目'
    
    conn.close()
    
    try:
        # 生成新的文件名：申请代码_项目名称_项目批准号.pdf
        # 获取项目批准号
        conn_temp = get_db_connection()
        cursor_temp = conn_temp.cursor()
        cursor_temp.execute('SELECT approval_number FROM projects WHERE id = ?', (project_id,))
        project_info = cursor_temp.fetchone()
        approval_number = project_info['approval_number'] if project_info else '未知批准号'
        conn_temp.close()
        
        # 清理文件名中的非法字符
        safe_code = re.sub(r'[\\/*?:"<>|]', '_', application_code)
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
        safe_approval_number = re.sub(r'[\\/*?:"<>|]', '_', approval_number)
        
        # 限制文件名长度，避免过长
        if len(safe_title) > 50:
            safe_title = safe_title[:50]
        
        new_filename = f"{safe_code}_{safe_title}_{safe_approval_number}.pdf"
        
        # 保存文件
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        
        # 如果文件已存在，添加时间戳避免冲突
        if os.path.exists(file_path):
            timestamp = int(time.time())
            new_filename = f"{safe_code}_{safe_title}_{timestamp}.pdf"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        
        file.save(file_path)
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        
        # 保存到数据库
        report_id = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reports (id, project_id, filename, file_path, file_size)
            VALUES (?, ?, ?, ?, ?)
        ''', (report_id, project_id, new_filename, file_path, file_size))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'report_id': report_id,
            'filename': new_filename,
            'file_size': file_size
        })
        
    except Exception as e:
        logger.error(f"上传失败: {str(e)}")
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/api/reports/<report_id>/view', methods=['GET'])
def view_report(report_id):
    """查看PDF内容"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_path FROM reports WHERE id = ?', (report_id,))
    report = cursor.fetchone()
    
    if not report:
        conn.close()
        return jsonify({'error': '文件不存在'}), 404
    
    file_path = report['file_path']
    
    if not os.path.exists(file_path):
        conn.close()
        return jsonify({'error': '文件不存在'}), 404
    
    conn.close()
    
    try:
        # 读取PDF内容
        doc = fitz.open(file_path)
        text = ""
        page_count = doc.page_count
        
        # 读取所有页面的内容
        for page_num in range(page_count):
            page = doc.load_page(page_num)
            text += page.get_text()
            
            # 在页面之间添加分隔符
            if page_num < page_count - 1:
                text += "\n\n--- 页面分隔 ---\n\n"
        
        doc.close()
        
        # 如果内容为空，提供提示信息
        if not text.strip():
            text = "该PDF文件可能只包含图片或格式化内容，无法提取文本。\n\n您可以下载后查看完整内容。"
        
        return jsonify({
            'success': True,
            'content': text,
            'page_count': page_count
        })
        
    except Exception as e:
        logger.error(f"读取PDF失败: {str(e)}")
        return jsonify({'error': f'读取PDF失败: {str(e)}'}), 500

@app.route('/api/reports/<report_id>/download', methods=['GET'])
def download_report(report_id):
    """下载PDF文件"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_path, filename FROM reports WHERE id = ?', (report_id,))
    report = cursor.fetchone()
    
    if not report:
        conn.close()
        return jsonify({'error': '文件不存在'}), 404
    
    file_path = report['file_path']
    filename = report['filename']
    
    if not os.path.exists(file_path):
        conn.close()
        return jsonify({'error': '文件不存在'}), 404
    
    conn.close()
    
    try:
        # 使用 send_file 直接返回文件，支持预览和下载
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=False,  # 设置为 False 以支持预览
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@app.route('/api/pdf/preview/<report_id>', methods=['GET'])
def preview_pdf(report_id):
    """PDF预览接口"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_path FROM reports WHERE id = ?', (report_id,))
    report = cursor.fetchone()
    
    if not report:
        conn.close()
        return jsonify({'error': '文件不存在'}), 404
    
    file_path = report['file_path']
    
    if not os.path.exists(file_path):
        conn.close()
        return jsonify({'error': '文件不存在'}), 404
    
    conn.close()
    
    try:
        # 使用 send_file 返回 PDF，浏览器会自动预览
        return send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=False,  # 关键：不触发下载，直接预览
            download_name=f'preview_{report_id}.pdf'
        )
    except Exception as e:
        logger.error(f"预览失败: {str(e)}")
        return jsonify({'error': f'预览失败: {str(e)}'}), 500

@app.route('/api/reports/<report_id>', methods=['DELETE'])
def delete_report(report_id):
    """删除PDF文件"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_path FROM reports WHERE id = ?', (report_id,))
    report = cursor.fetchone()
    
    if not report:
        conn.close()
        return jsonify({'error': '文件不存在'}), 404
    
    file_path = report['file_path']
    
    # 删除文件
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.error(f"删除文件失败: {str(e)}")
    
    # 删除数据库记录
    cursor.execute('DELETE FROM reports WHERE id = ?', (report_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/search/history', methods=['GET'])
def get_search_history():
    """获取搜索历史"""
    limit = int(request.args.get('limit', 10))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM search_history 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'success': True, 'data': history})

@app.route('/api/search/history', methods=['DELETE'])
def clear_search_history():
    """清空搜索历史"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM search_history')
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/export/projects', methods=['GET'])
def export_projects():
    """导出项目列表"""
    unit = request.args.get('unit', '')
    code = request.args.get('code', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM projects WHERE 1=1'
    params = []
    
    if unit:
        query += ' AND unit LIKE ?'
        params.append(f'%{unit}%')
    
    if code:
        query += ' AND application_code LIKE ?'
        params.append(f'%{code}%')
    
    query += ' ORDER BY created_at DESC'
    
    cursor.execute(query, params)
    projects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # 生成CSV内容
    import csv
    import io
    
    # 使用StringIO，然后编码为bytes
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(['项目名称', '批准号', '申请代码', '负责人', '依托单位', '开始日期', '结束日期', '资助经费', '项目摘要', '结题摘要', 'URL'])
    
    # 写入数据
    for project in projects:
        writer.writerow([
            project.get('title', ''),
            project.get('approval_number', ''),
            project.get('application_code', ''),
            project.get('leader', ''),
            project.get('unit', ''),
            project.get('start_date', ''),
            project.get('end_date', ''),
            project.get('funding', ''),
            project.get('abstract', ''),
            project.get('conclusion_abstract', ''),
            project.get('url', '')
        ])
    
    # 获取CSV内容并编码为UTF-8 with BOM
    csv_content = output.getvalue().encode('utf-8-sig')
    
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=projects_{int(time.time())}.csv',
            'Content-Type': 'text/csv; charset=utf-8-sig'
        }
    )

def record_search_history(search_type, keyword, results_count):
    """记录搜索历史"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO search_history (keyword, search_type, results_count)
            VALUES (?, ?, ?)
        ''', (keyword, search_type, results_count))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"记录搜索历史失败: {str(e)}")

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动应用
    logger.info("启动Flask应用...")
    app.run(debug=True, host='0.0.0.0', port=5002)

"""国自然结题报告下载器"""
import requests
import time
import random
import re
import logging
from io import BytesIO
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


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
                import os
                # 获取当前文件的目录，然后构建 uploads 路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                file_path = os.path.join(current_dir, '..', 'uploads', filename)
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

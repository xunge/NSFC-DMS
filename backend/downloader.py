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

    def get_image_url_from_api(self, nsfc_id, index, check_only=False):
        """
        从API获取图片下载地址
        
        Args:
            nsfc_id: 项目ID
            index: 页码
            check_only: 如果为True，只检查页面是否存在，不记录详细日志
        
        Returns:
            str: 图片URL，如果页面不存在返回None，如果请求失败返回"RETRY"
        """
        api_url = f"{self.base_url}/api/baseQuery/completeProjectReport"
        data = {"id": nsfc_id, "index": index}

        try:
            if not check_only:
                logger.info(f"[API] 请求第 {index} 页: {api_url}, data={data}")
            resp = self.session.post(api_url, data=data, timeout=15)
            if not check_only:
                logger.info(f"[API] 第 {index} 页响应状态: {resp.status_code}")
            if resp.status_code == 200:
                json_data = resp.json()
                if not check_only:
                    logger.info(f"[API] 第 {index} 页响应数据: {json_data}")
                
                # 严格检查：code必须为200，data必须存在，且data中必须有url字段且不为空
                if json_data.get('code') == 200:
                    data_obj = json_data.get('data')
                    if data_obj and isinstance(data_obj, dict):
                        url = data_obj.get('url')
                        # url必须存在且不为空字符串
                        if url and url.strip():
                            img_url = self.base_url + url
                            
                            # 在扫描模式下，额外验证图片URL是否真的可访问（避免API返回无效URL）
                            if check_only:
                                # 尝试HEAD请求验证图片是否存在（不下载完整内容）
                                try:
                                    head_resp = self.session.head(img_url, timeout=5, allow_redirects=True)
                                    if head_resp.status_code == 404:
                                        logger.debug(f"[扫描] 第 {index} 页：图片URL返回404，页面不存在")
                                        return None
                                    elif head_resp.status_code != 200:
                                        # 非200非404，可能是其他错误，记录但继续
                                        logger.debug(f"[扫描] 第 {index} 页：图片URL状态码 {head_resp.status_code}，可能存在问题")
                                except Exception as e:
                                    # HEAD请求失败，可能是网络问题，记录但继续
                                    logger.debug(f"[扫描] 第 {index} 页：验证图片URL时出错: {e}")
                            
                            if not check_only:
                                logger.info(f"[API] 第 {index} 页获取到图片URL: {img_url}")
                            return img_url
                        else:
                            # url为空或不存在，说明页面不存在
                            if check_only:
                                logger.debug(f"[扫描] 第 {index} 页：data.url为空，页面不存在")
                            else:
                                logger.info(f"[API] 第 {index} 页：data.url为空，页面不存在")
                            return None
                    else:
                        # data不存在或不是字典，说明页面不存在
                        if check_only:
                            logger.debug(f"[扫描] 第 {index} 页：data不存在或格式错误")
                        else:
                            logger.info(f"[API] 第 {index} 页：data不存在或格式错误")
                        return None
                else:
                    # code不为200，说明页面不存在或请求失败
                    if check_only:
                        logger.debug(f"[扫描] 第 {index} 页：code={json_data.get('code')}，页面不存在")
                    else:
                        logger.info(f"[API] 第 {index} 页：code={json_data.get('code')}，页面不存在")
                    return None
            else:
                if not check_only:
                    logger.warning(f"[API] 第 {index} 页状态码异常: {resp.status_code}")
                return "RETRY"
        except Exception as e:
            if not check_only:
                logger.warning(f"[API] 第 {index} 页请求异常: {e}")
            return "RETRY"
    
    def scan_total_pages(self, nsfc_id, progress_callback=None):
        """
        使用二分查找法快速定位总页数（只获取URL，不下载图片）
        
        Args:
            nsfc_id: 项目ID
            progress_callback: 进度回调函数
        
        Returns:
            int: 总页数，如果无法确定返回None
        """
        try:
            if progress_callback:
                progress_callback(15, "正在扫描总页数...", 0, 0, None)
            
            logger.info(f"[扫描] 开始使用二分查找法扫描总页数")
            
            # 第一步：确定上界，先测试一些较大的页码
            test_pages = [50, 100, 200, 500, 1000]
            upper_bound = None
            
            for test_page in test_pages:
                if progress_callback:
                    progress_callback(15, f"测试第 {test_page} 页是否存在...", 0, 0, None)
                
                result = self.get_image_url_from_api(nsfc_id, test_page, check_only=True)
                if result and result != "RETRY":
                    # 页面存在，继续测试更大的页码
                    upper_bound = test_page
                    logger.info(f"[扫描] 第 {test_page} 页存在，继续扩大范围")
                    time.sleep(0.5)  # 短暂延时，避免请求过快
                elif result is None:
                    # 页面不存在，找到上界
                    upper_bound = test_page - 1
                    logger.info(f"[扫描] 第 {test_page} 页不存在，上界为 {upper_bound}")
                    break
                else:
                    # RETRY，可能是网络问题，重试一次
                    time.sleep(1)
                    result = self.get_image_url_from_api(nsfc_id, test_page, check_only=True)
                    if result and result != "RETRY":
                        upper_bound = test_page
                    elif result is None:
                        upper_bound = test_page - 1
                        break
            
            # 如果所有测试页码都存在，继续扩大范围查找上界
            # 但需要设置一个合理的上限，避免无限扩大
            if upper_bound is None or upper_bound == test_pages[-1]:
                # 从最后一个测试页码开始，继续扩大范围
                current_test = test_pages[-1]
                max_attempts = 10  # 最多尝试10次扩大范围
                attempt = 0
                max_reasonable_pages = 10000  # 设置一个合理的最大页数上限
                
                while attempt < max_attempts and current_test < max_reasonable_pages:
                    current_test = current_test * 2  # 每次翻倍
                    if progress_callback:
                        progress_callback(15, f"测试第 {current_test} 页是否存在...", 0, 0, None)
                    
                    result = self.get_image_url_from_api(nsfc_id, current_test, check_only=True)
                    if result and result != "RETRY":
                        upper_bound = current_test
                        logger.info(f"[扫描] 第 {current_test} 页存在，继续扩大范围")
                        time.sleep(0.5)
                    elif result is None:
                        # 页面不存在，找到上界
                        upper_bound = current_test - 1
                        logger.info(f"[扫描] 第 {current_test} 页不存在，上界为 {upper_bound}")
                        break
                    else:
                        # RETRY，重试一次
                        time.sleep(1)
                        result = self.get_image_url_from_api(nsfc_id, current_test, check_only=True)
                        if result and result != "RETRY":
                            upper_bound = current_test
                        elif result is None:
                            upper_bound = current_test - 1
                            logger.info(f"[扫描] 第 {current_test} 页不存在（重试后），上界为 {upper_bound}")
                            break
                    
                    attempt += 1
                
                # 如果达到最大尝试次数或超过合理上限，使用当前上界
                if upper_bound is None or (current_test >= max_reasonable_pages and upper_bound == test_pages[-1]):
                    # 如果已经测试了很多页都还存在，可能是判断逻辑有问题
                    # 使用一个保守的上界，或者返回None让系统使用动态方式
                    logger.warning(f"[扫描] 达到最大测试范围 {current_test}，可能判断逻辑有问题，使用保守上界")
                    # 使用最后一次测试的页码作为上界，但限制在合理范围内
                    upper_bound = min(current_test, max_reasonable_pages)
                    logger.info(f"[扫描] 使用保守上界: {upper_bound}")
            
            # 第二步：使用二分查找在1到upper_bound之间定位最后一页
            left, right = 1, upper_bound
            last_valid_page = 0
            
            if progress_callback:
                progress_callback(20, f"使用二分查找定位最后一页（范围：1-{upper_bound}）...", 0, 0, None)
            
            logger.info(f"[扫描] 开始二分查找，范围：1-{upper_bound}")
            
            while left <= right:
                mid = (left + right) // 2
                
                if progress_callback:
                    progress_callback(20, f"二分查找：测试第 {mid} 页（范围：{left}-{right}）...", 0, 0, None)
                
                result = self.get_image_url_from_api(nsfc_id, mid, check_only=True)
                
                if result and result != "RETRY":
                    # 页面存在，继续向右查找
                    last_valid_page = mid
                    left = mid + 1
                    logger.info(f"[扫描] 第 {mid} 页存在，继续向右查找")
                elif result is None:
                    # 页面不存在，向左查找
                    right = mid - 1
                    logger.info(f"[扫描] 第 {mid} 页不存在，向左查找")
                else:
                    # RETRY，可能是网络问题，重试一次
                    time.sleep(1)
                    result = self.get_image_url_from_api(nsfc_id, mid, check_only=True)
                    if result and result != "RETRY":
                        last_valid_page = mid
                        left = mid + 1
                    elif result is None:
                        right = mid - 1
                
                time.sleep(0.3)  # 短暂延时，避免请求过快
            
            if last_valid_page > 0:
                logger.info(f"[扫描] 二分查找完成，总页数：{last_valid_page}")
                if progress_callback:
                    progress_callback(25, f"扫描完成，共 {last_valid_page} 页", 0, 0, last_valid_page)
                return last_valid_page
            else:
                logger.warning(f"[扫描] 无法确定总页数")
                if progress_callback:
                    progress_callback(25, "无法确定总页数，将动态显示进度", 0, 0, None)
                return None
                
        except Exception as e:
            logger.error(f"[扫描] 扫描总页数失败: {str(e)}")
            if progress_callback:
                progress_callback(25, f"扫描总页数失败: {str(e)}", 0, 0, None)
            return None

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
            progress_callback: 进度回调函数，接收当前进度、消息、当前页码、已收集页数、总页数

        Returns:
            dict: {'success': bool, 'file_path': str, 'filename': str, 'message': str, 'page_count': int}
        """
        try:
            # 初始化会话
            if progress_callback:
                progress_callback(5, "初始化会话...", 0, 0, None)
            self.init_session()

            # 净化文件名
            safe_name = re.sub(r'[\\/*?:"<>|]', "", project_name).strip()
            if not safe_name:
                safe_name = f"nsfc_{nsfc_id}"

            # 使用二分查找法扫描总页数
            total_pages = self.scan_total_pages(nsfc_id, progress_callback)

            images = []
            index = 1
            consecutive_failures = 0

            if progress_callback:
                progress_callback(30, f"开始下载项目: {safe_name}", 0, 0, total_pages)

            while True:
                logger.info(f"========== 开始处理第 {index} 页 ==========")
                
                # 通知开始处理当前页
                if progress_callback:
                    # 如果有总页数，计算准确进度；否则使用估算进度
                    if total_pages:
                        progress = 30 + int((len(images) / total_pages) * 65)
                    else:
                        progress = 30 + min(int((index * 65 / 100)), 65)
                    progress_callback(progress, f"开始处理第 {index} 页...", index, len(images), total_pages)

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
                        progress = 95 if total_pages else 95
                        progress_callback(progress, f"第 {index} 页 API 返回空，判断为下载结束", index, len(images), total_pages)
                    break

                # 步骤2: 下载图片内容
                if progress_callback:
                    # 如果有总页数，计算准确进度；否则使用估算进度
                    if total_pages:
                        progress = 30 + int((len(images) / total_pages) * 65)
                    else:
                        progress = 30 + min(int((index * 65 / 100)), 65)
                    progress_callback(progress, f"正在下载第 {index} 页...", index, len(images), total_pages)

                content = None
                dl_retry = 0

                # 图片下载的重试循环
                while dl_retry < 5:
                    logger.info(f"[循环] 第 {index} 页，图片下载重试次数: {dl_retry}")
                    content = self.download_image_content(img_url)

                    if content == "404":
                        logger.info(f"[循环] 第 {index} 页图片返回404，结束下载")
                        if progress_callback:
                            progress = 95 if total_pages else 95
                            progress_callback(progress, f"第 {index} 页图片返回 404，下载结束", index, len(images), total_pages)
                        img_url = None
                        break

                    if content:
                        logger.info(f"[循环] 第 {index} 页图片下载成功")
                        break

                    dl_retry += 1
                    sleep_time = 2 + dl_retry
                    logger.info(f"[循环] 第 {index} 页下载失败，等待 {sleep_time}秒后重试")
                    if progress_callback:
                        # 如果有总页数，计算准确进度；否则使用估算进度
                        if total_pages:
                            progress = 30 + int((len(images) / total_pages) * 65)
                        else:
                            progress = 30 + min(int((index * 65 / 100)), 65)
                        progress_callback(progress,
                                         f"第 {index} 页下载失败，第 {dl_retry} 次重试 (等待{sleep_time}s)...", index, len(images), total_pages)
                    time.sleep(sleep_time)

                if img_url is None:
                    logger.info(f"[循环] img_url为None，跳出循环")
                    break

                if not content:
                    logger.warning(f"第 {index} 页尝试多次后仍无法下载，已跳过")
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        if progress_callback:
                            progress_callback(100, "连续3页下载失败，可能IP被封或网络中断", index, len(images), total_pages)
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
                    # 通知图片处理成功
                    if progress_callback:
                        # 如果有总页数，计算准确进度；否则使用估算进度
                        if total_pages:
                            progress = 30 + int((len(images) / total_pages) * 65)
                        else:
                            progress = 30 + min(int((index * 65 / 100)), 65)
                        progress_callback(progress, f"第 {index} 页处理成功，已收集 {len(images)} 张图片", index, len(images), total_pages)
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
                    progress_callback(98, f"正在合成PDF，共 {len(images)} 页...", len(images), len(images), total_pages or len(images))

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
                    progress_callback(100, f"成功！共 {len(images)} 页", len(images), len(images), total_pages or len(images))

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
                    progress_callback(100, "未能下载任何有效图片", 0, 0, total_pages)
                return {
                    'success': False,
                    'message': "未能下载任何有效图片"
                }

        except Exception as e:
            logger.error(f"下载结题报告失败: {str(e)}")
            if progress_callback:
                progress_callback(100, f"下载失败: {str(e)}", 0, 0, None)
            return {
                'success': False,
                'message': f"下载失败: {str(e)}"
            }

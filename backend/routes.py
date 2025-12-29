"""Flask路由和API端点"""
from flask import Flask, request, jsonify, send_file, Response, stream_with_context, current_app
from flask_cors import CORS
import os
import re
import time
import uuid
import logging
import json
import queue
import threading
from datetime import datetime
from werkzeug.utils import secure_filename
try:
    import fitz  # PyPDF2
except ImportError:
    fitz = None
from io import BytesIO
from PIL import Image

from models import (
    init_db, get_db_connection, create_project, update_project, 
    find_existing_project, get_projects_list, get_project_detail,
    delete_project_and_reports, create_report_record, get_report_info,
    delete_report, record_search_history, get_search_history,
    clear_search_history, export_projects_to_csv
)
from downloader import NsfcReportDownloader
from scraper import extract_project_info

logger = logging.getLogger(__name__)

# 配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 1000 * 1024 * 1024  # 1000MB


def allowed_file(filename):
    """检查文件类型"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def register_routes(app: Flask):
    """注册所有路由"""
    CORS(app)
    
    # 配置上传文件夹
    # 获取应用根目录的绝对路径
    app_root = os.path.dirname(os.path.abspath(__file__))
    upload_path = os.path.join(app_root, '..', UPLOAD_FOLDER)
    app.config['UPLOAD_FOLDER'] = upload_path
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    os.makedirs(upload_path, exist_ok=True)

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """健康检查"""
        return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

    @app.route('/api/projects/fetch', methods=['POST'])
    def fetch_project():
        """获取项目信息"""
        data = request.get_json()
        url = data.get('url')
        auto_download = data.get('auto_download', False)
        
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
            existing_project = find_existing_project(url, project_info.get('nsfc_id'))
            
            if existing_project:
                # 更新现有记录
                project_id = existing_project['id']
                update_project(project_id, project_info)
            else:
                # 插入新记录
                project_id = create_project(project_info)
            
            # 记录搜索历史
            record_search_history('url', url, 1)
            
            result = {
                'success': True,
                'data': project_info,
                'project_id': project_id
            }
            
            # 如果启用自动下载，返回标记让前端调用单独的下载接口
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

                # 使用队列来收集进度消息
                progress_queue = queue.Queue()

                # 定义进度回调函数
                def progress_callback(progress, message, current_page=0, collected_pages=0):
                    # 将进度事件放入队列
                    event_data = {
                        'type': 'progress',
                        'progress': progress,
                        'message': message,
                        'current_page': current_page,
                        'collected_pages': collected_pages
                    }
                    progress_queue.put(event_data)
                    logger.info(f"[下载进度] {progress}% - {message} (第{current_page}页，已收集{collected_pages}页)")

                # 在单独的线程中执行下载
                download_result = {'result': None, 'exception': None}
                
                def download_thread():
                    try:
                        downloader = NsfcReportDownloader()
                        result = downloader.download_report(nsfc_id, project_name, progress_callback)
                        download_result['result'] = result
                    except Exception as e:
                        download_result['exception'] = e

                thread = threading.Thread(target=download_thread)
                thread.start()

                # 持续发送进度消息，直到下载完成
                while thread.is_alive():
                    try:
                        # 从队列中获取进度消息（超时0.1秒）
                        event_data = progress_queue.get(timeout=0.1)
                        yield f"data: {json.dumps(event_data)}\n\n"
                    except queue.Empty:
                        # 队列为空，继续等待
                        continue

                # 等待下载线程完成
                thread.join()
                
                # 发送队列中剩余的所有消息
                while not progress_queue.empty():
                    try:
                        event_data = progress_queue.get_nowait()
                        yield f"data: {json.dumps(event_data)}\n\n"
                    except queue.Empty:
                        break
                
                result = download_result['result']
                
                if download_result['exception']:
                    raise download_result['exception']

                if result['success']:
                    # 保存到数据库
                    report_id = create_report_record(
                        project_id, 
                        result['filename'], 
                        result['file_path'], 
                        os.path.getsize(result['file_path'])
                    )

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
        def progress_callback(progress, message, current_page=0, collected_pages=0):
            logger.info(f"[下载进度] {progress}% - {message} (第{current_page}页，已收集{collected_pages}页)")

        try:
            logger.info(f"开始下载结题报告: {project_id}, nsfc_id: {nsfc_id}, 项目名称: {project_name}")
            downloader = NsfcReportDownloader()
            result = downloader.download_report(nsfc_id, project_name, progress_callback)

            if result['success']:
                # 保存到数据库
                report_id = create_report_record(
                    project_id, 
                    result['filename'], 
                    result['file_path'], 
                    os.path.getsize(result['file_path'])
                )

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
        
        projects, total = get_projects_list(unit, code, page, per_page)
        
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
    def get_project_detail_route(project_id):
        """获取项目详情"""
        project = get_project_detail(project_id)
        
        if not project:
            return jsonify({'error': '项目不存在'}), 404
        
        return jsonify({'success': True, 'data': project})

    @app.route('/api/projects', methods=['POST'])
    def create_project_route():
        """手动创建项目"""
        data = request.get_json()
        
        required_fields = ['title', 'approval_number', 'unit']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field}不能为空'}), 400
        
        project_info = {
            'nsfc_id': data.get('nsfc_id'),
            'title': data.get('title'),
            'approval_number': data.get('approval_number'),
            'application_code': data.get('application_code'),
            'leader': data.get('leader'),
            'unit': data.get('unit'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'funding': data.get('funding'),
            'abstract': data.get('abstract'),
            'conclusion_abstract': data.get('conclusion_abstract'),
            'url': data.get('url')
        }
        
        project_id = create_project(project_info)
        
        return jsonify({'success': True, 'project_id': project_id})

    @app.route('/api/projects/<project_id>', methods=['PUT'])
    def update_project_route(project_id):
        """更新项目信息"""
        data = request.get_json()
        
        # 检查项目是否存在
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM projects WHERE id = ?', (project_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': '项目不存在'}), 404
        conn.close()
        
        project_info = {
            'nsfc_id': data.get('nsfc_id'),
            'title': data.get('title'),
            'approval_number': data.get('approval_number'),
            'application_code': data.get('application_code'),
            'leader': data.get('leader'),
            'unit': data.get('unit'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'funding': data.get('funding'),
            'abstract': data.get('abstract'),
            'conclusion_abstract': data.get('conclusion_abstract'),
            'url': data.get('url')
        }
        
        update_project(project_id, project_info)
        
        return jsonify({'success': True})

    @app.route('/api/projects/<project_id>', methods=['DELETE'])
    def delete_project_route(project_id):
        """删除项目"""
        # 检查项目是否存在
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM projects WHERE id = ?', (project_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': '项目不存在'}), 404
        conn.close()
        
        delete_project_and_reports(project_id)
        
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
            report_id = create_report_record(project_id, new_filename, file_path, file_size)
            
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
        if fitz is None:
            return jsonify({'error': 'PDF处理功能未安装，请安装 PyMuPDF'}), 503
        
        report = get_report_info(report_id)
        
        if not report:
            return jsonify({'error': '文件不存在'}), 404
        
        file_path = report['file_path']
        
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
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
    def download_report_file(report_id):
        """下载PDF文件"""
        report = get_report_info(report_id)
        
        if not report:
            return jsonify({'error': '文件不存在'}), 404
        
        file_path = report['file_path']
        filename = report['filename']
        
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
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
        report = get_report_info(report_id)
        
        if not report:
            return jsonify({'error': '文件不存在'}), 404
        
        file_path = report['file_path']
        
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
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
    def delete_report_route(report_id):
        """删除PDF文件"""
        report = get_report_info(report_id)
        
        if not report:
            return jsonify({'error': '文件不存在'}), 404
        
        delete_report(report_id)
        
        return jsonify({'success': True})

    @app.route('/api/search/history', methods=['GET'])
    def get_search_history_route():
        """获取搜索历史"""
        limit = int(request.args.get('limit', 10))
        history = get_search_history(limit)
        return jsonify({'success': True, 'data': history})

    @app.route('/api/search/history', methods=['DELETE'])
    def clear_search_history_route():
        """清空搜索历史"""
        clear_search_history()
        return jsonify({'success': True})

    @app.route('/api/export/projects', methods=['GET'])
    def export_projects_route():
        """导出项目列表"""
        unit = request.args.get('unit', '')
        code = request.args.get('code', '')
        
        csv_content = export_projects_to_csv(unit, code)
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=projects_{int(time.time())}.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig'
            }
        )

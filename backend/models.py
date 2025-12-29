"""数据库模型和操作"""
import sqlite3
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


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


def create_project(project_info):
    """创建项目"""
    project_id = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO projects (id, nsfc_id, title, approval_number, application_code, leader, unit,
                            start_date, end_date, funding, abstract, conclusion_abstract, url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_id,
        project_info.get('nsfc_id'),
        project_info['title'],
        project_info['approval_number'],
        project_info['application_code'],
        project_info['leader'],
        project_info['unit'],
        project_info['start_date'],
        project_info['end_date'],
        project_info['funding'],
        project_info['abstract'],
        project_info['conclusion_abstract'],
        project_info['url']
    ))
    
    conn.commit()
    conn.close()
    return project_id


def update_project(project_id, project_info):
    """更新项目"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE projects
        SET nsfc_id=?, title=?, approval_number=?, application_code=?, leader=?, unit=?,
            start_date=?, end_date=?, funding=?, abstract=?, conclusion_abstract=?, url=?
        WHERE id=?
    ''', (
        project_info.get('nsfc_id'),
        project_info['title'],
        project_info['approval_number'],
        project_info['application_code'],
        project_info['leader'],
        project_info['unit'],
        project_info['start_date'],
        project_info['end_date'],
        project_info['funding'],
        project_info['abstract'],
        project_info['conclusion_abstract'],
        project_info['url'],
        project_id
    ))
    
    conn.commit()
    conn.close()


def find_existing_project(url, nsfc_id=None):
    """查找已存在的项目"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    existing_project = None
    if nsfc_id:
        cursor.execute('SELECT id FROM projects WHERE nsfc_id = ?', (nsfc_id,))
        existing_project = cursor.fetchone()
    
    if not existing_project:
        cursor.execute('SELECT id FROM projects WHERE url = ?', (url,))
        existing_project = cursor.fetchone()
    
    conn.close()
    return existing_project


def get_projects_list(unit='', code='', page=1, per_page=20):
    """获取项目列表"""
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
    
    return projects, total


def get_project_detail(project_id):
    """获取项目详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()
    
    if project:
        # 获取关联的PDF文件
        cursor.execute('SELECT * FROM reports WHERE project_id = ? ORDER BY upload_date DESC', (project_id,))
        reports = [dict(row) for row in cursor.fetchall()]
        project = dict(project)
        project['reports'] = reports
    
    conn.close()
    return project


def delete_project_and_reports(project_id):
    """删除项目及其关联的报告文件"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取并删除关联的PDF文件
    cursor.execute('SELECT file_path FROM reports WHERE project_id = ?', (project_id,))
    reports = cursor.fetchall()
    
    import os
    for report in reports:
        file_path = report['file_path']
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"删除文件失败: {str(e)}")
    
    # 删除数据库记录
    cursor.execute('DELETE FROM reports WHERE project_id = ?', (project_id,))
    cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    
    conn.commit()
    conn.close()


def create_report_record(project_id, filename, file_path, file_size):
    """创建报告记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    report_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO reports (id, project_id, filename, file_path, file_size)
        VALUES (?, ?, ?, ?, ?)
    ''', (report_id, project_id, filename, file_path, file_size))
    
    conn.commit()
    conn.close()
    return report_id


def get_report_info(report_id):
    """获取报告信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM reports WHERE id = ?', (report_id,))
    report = cursor.fetchone()
    
    conn.close()
    return dict(report) if report else None


def delete_report(report_id):
    """删除报告记录和文件"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT file_path FROM reports WHERE id = ?', (report_id,))
    report = cursor.fetchone()
    
    if report:
        import os
        file_path = report['file_path']
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"删除文件失败: {str(e)}")
        
        cursor.execute('DELETE FROM reports WHERE id = ?', (report_id,))
        conn.commit()
    
    conn.close()


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


def get_search_history(limit=10):
    """获取搜索历史"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM search_history 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (limit,))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return history


def clear_search_history():
    """清空搜索历史"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM search_history')
    conn.commit()
    conn.close()


def export_projects_to_csv(unit='', code=''):
    """导出项目列表为CSV"""
    import csv
    import io
    
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
    
    return output.getvalue().encode('utf-8-sig')

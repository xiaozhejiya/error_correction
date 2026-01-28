"""
错题本生成系统 - Web应用
提供前端界面用于测试工作流
"""

import os
import json
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from src.workflow import ErrorCorrectionWorkflow

# 加载环境变量
load_dotenv()

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 全局工作流实例（用于保存状态）
current_workflow = None


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/upload-page')
def upload_page():
    """文件上传页面"""
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def simple_upload():
    """
    简单文件上传接口（不执行OCR工作流）
    用于文件上传演示页面
    """
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    try:
        # 保存文件
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 获取文件大小
        file_size = os.path.getsize(filepath)

        return jsonify({
            'message': '文件上传成功',
            'filename': filename,
            'size': file_size,
            'path': f'/uploads/{filename}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    处理文件上传和工作流执行

    Returns:
        JSON响应，包含处理结果
    """
    # 检查文件
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'不支持的文件格式。支持: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    try:
        global current_workflow

        # 保存文件
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # 创建新的工作流实例
        current_workflow = ErrorCorrectionWorkflow()

        # 执行步骤1-2（准备和OCR）
        result = current_workflow.run(filepath, auto_split=False)

        return jsonify({
            'success': True,
            'message': '文件处理成功',
            'result': {
                'image_count': len(result['image_paths']),
                'ocr_count': len(result['ocr_results']),
                'image_paths': result['image_paths'],
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/split', methods=['POST'])
def split_questions():
    """
    调用Agent分割题目

    Expects:
        JSON body (可选，用于指定特定的OCR结果)

    Returns:
        JSON响应，包含分割后的题目
    """
    try:
        global current_workflow

        # 检查是否已上传文件
        if current_workflow is None:
            return jsonify({
                'success': False,
                'error': '请先上传文件'
            }), 400

        # 检查是否有OCR结果
        if not current_workflow.ocr_results:
            return jsonify({
                'success': False,
                'error': '请先完成OCR解析'
            }), 400

        # 调用Agent分割
        questions = current_workflow.split_questions_with_agent()

        return jsonify({
            'success': True,
            'message': f'成功分割 {len(questions)} 道题目',
            'questions': questions
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/export', methods=['POST'])
def export_wrongbook():
    """
    导出错题本

    Expects:
        JSON body with selected_ids: List[str]

    Returns:
        JSON响应，包含导出文件路径
    """
    try:
        global current_workflow

        data = request.get_json()
        selected_ids = data.get('selected_ids', [])

        if not selected_ids:
            return jsonify({
                'success': False,
                'error': '未选择任何题目'
            }), 400

        # 检查是否已分割题目
        if current_workflow is None or not current_workflow.questions:
            return jsonify({
                'success': False,
                'error': '请先分割题目'
            }), 400

        # 导出
        output_path = current_workflow.export_selected(selected_ids)

        return jsonify({
            'success': True,
            'message': '错题本导出成功',
            'output_path': output_path
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/questions', methods=['GET'])
def get_questions():
    """
    获取已分割的题目列表

    Returns:
        JSON响应，包含题目列表
    """
    try:
        results_dir = os.getenv("RESULTS_DIR", "results")
        questions_file = os.path.join(results_dir, "questions.json")

        if not os.path.exists(questions_file):
            return jsonify({
                'success': True,
                'questions': [],
                'message': '暂无题目数据'
            })

        with open(questions_file, 'r', encoding='utf-8') as f:
            questions = json.load(f)

        return jsonify({
            'success': True,
            'questions': questions
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/preview')
def preview():
    """显示预览页面"""
    results_dir = os.getenv("RESULTS_DIR", "results")
    preview_file = os.path.join(results_dir, "preview.html")

    if os.path.exists(preview_file):
        with open(preview_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    else:
        return "预览文件不存在，请先分割题目", 404


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """访问上传的文件"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/download/<path:filename>')
def download_file(filename):
    """下载结果文件"""
    results_dir = os.getenv("RESULTS_DIR", "results")
    return send_from_directory(results_dir, filename, as_attachment=True)


@app.route('/api/status', methods=['GET'])
def get_status():
    """
    获取系统状态

    Returns:
        JSON响应，包含系统配置和状态
    """
    try:
        # 检查配置
        status = {
            'paddleocr_configured': bool(os.getenv('PADDLEOCR_API_URL')),
            'deepseek_configured': bool(os.getenv('DEEPSEEK_API_KEY')),
            'langsmith_enabled': os.getenv('LANGSMITH_TRACING', 'false').lower() == 'true',
            'output_dirs': {
                'pages': os.getenv('PAGES_DIR', 'output/pages'),
                'struct': os.getenv('STRUCT_DIR', 'output/struct'),
                'results': os.getenv('RESULTS_DIR', 'results'),
            }
        }

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("错题本生成系统 - Web应用")
    print("=" * 60)
    print("访问地址: http://localhost:5001")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5001, debug=True)

from flask import Flask, request, render_template_string, send_from_directory, redirect, url_for
from flask_cors import CORS
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)
# السماح للطلبات الخارجية بالوصول إلى هذا السيرفر
CORS(app) 

UPLOAD_FOLDER = '.'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DB_NAME = 'server_logs.db'

# إنشاء قاعدة البيانات وجدول السجلات تلقائياً إذا لم تكن موجودة
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT,
                status TEXT,
                message TEXT,
                filename TEXT
            )
        ''')
        conn.commit()

init_db()

# دالة لتسجيل الأحداث في قاعدة البيانات
def log_to_db(time, status, message, filename):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('INSERT INTO logs (time, status, message, filename) VALUES (?, ?, ?, ?)', 
                     (time, status, message, filename))
        conn.commit()

# واجهة لوحة التحكم المطورة باستخدام Tailwind CSS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <!-- تحديث الصفحة تلقائياً كل 5 ثواني لرؤية التغييرات الحية -->
    <meta http-equiv="refresh" content="5">
    <title>لوحة التحكم المتقدمة لاستقبال الملفات</title>
    <!-- استدعاء تصميم Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans p-6">
    <div class="max-w-5xl mx-auto bg-white shadow-xl rounded-2xl p-6">
        
        <!-- رأس اللوحة -->
        <div class="flex justify-between items-center border-b pb-4 mb-6">
            <div class="flex items-center gap-3">
                <h2 class="text-2xl font-bold text-gray-800">🚀 لوحة مراقبة السيرفر المتقدمة</h2>
                <span class="bg-red-100 text-red-600 text-sm font-semibold px-3 py-1 rounded-full animate-pulse">🔴 تحديث حي (Live)</span>
            </div>
            
            <!-- زر مسح وتنظيف الملفات والسجلات -->
            <a href="/clear" onclick="return confirm('هل أنت متأكد من رغبتك في حذف جميع السجلات والملفات المخزنة؟');" 
               class="bg-rose-600 hover:bg-rose-700 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow transition flex items-center gap-2">
                🗑️ تنظيف الكل (Clear)
            </a>
        </div>
        
        <!-- جدول السجلات -->
        <div class="overflow-x-auto">
            <table class="w-full text-right border-collapse">
                <thead>
                    <tr class="bg-gray-50 text-gray-700 border-b">
                        <th class="p-3">الوقت</th>
                        <th class="p-3">الحالة</th>
                        <th class="p-3">التفاصيل / السبب</th>
                        <th class="p-3 text-center">الإجراء</th>
                    </tr>
                </thead>
                <tbody>
                    {% if logs %}
                        {% for log in logs %}
                        <tr class="border-b hover:bg-gray-50 transition">
                            <td class="p-3 text-sm text-gray-600 font-mono" dir="ltr" style="text-align: right;">{{ log[1] }}</td>
                            <td class="p-3">
                                {% if log[2] == 'success' %}
                                    <span class="bg-green-100 text-green-700 px-3 py-1 rounded-md text-xs font-bold">✅ نجاح</span>
                                {% else %}
                                    <span class="bg-red-100 text-red-700 px-3 py-1 rounded-md text-xs font-bold">❌ فشل</span>
                                {% endif %}
                            </td>
                            <td class="p-3 text-sm text-gray-800">{{ log[3] }}</td>
                            <td class="p-3 text-center">
                                {% if log[4] %}
                                    <a href="/download/{{ log[4] }}" class="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow transition inline-block">📥 تحميل</a>
                                {% else %}
                                    <span class="text-gray-400">-</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="4" class="text-center py-10 text-gray-400 text-lg">⏳ لا توجد سجلات حتى الآن، السيرفر في انتظار البيانات...</td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# 1. مسار لوحة التحكم الرئيسية
@app.route('/', methods=['GET'])
def dashboard():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # جلب السجلات مرتبة من الأحدث للأقدم
        cursor.execute('SELECT id, time, status, message, filename FROM logs ORDER BY id DESC')
        logs = cursor.fetchall()
    return render_template_string(HTML_TEMPLATE, logs=logs)

# 2. مسار تنظيف الحذف (Clear Route)
@app.route('/clear', methods=['GET'])
def clear_data():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            # جلب أسماء الملفات المحفوظة لحذفها من المجلد أيضاً
            cursor.execute('SELECT filename FROM logs WHERE filename IS NOT NULL')
            files = cursor.fetchall()
            
            for file_row in files:
                filename = file_row[0]
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                # حذف الملف الفعلي إذا كان موجوداً
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"تعذر حذف الملف {filename}: {e}")
            
            # تفريغ جدول السجلات بالكامل
            cursor.execute('DELETE FROM logs')
            conn.commit()
            
        print("🧹 تم تنظيف جميع السجلات والملفات بنجاح.")
    except Exception as e:
        print(f"حدث خطأ أثناء عملية التطهير: {e}")
        
    return redirect(url_for('dashboard'))

# 3. مسار استقبال الملفات (API Endpoint) مع الحفظ في قاعدة البيانات
@app.route('/upload', methods=['POST'])
def upload_file():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if 'file' not in request.files:
        log_to_db(current_time, 'error', 'الطلب وصل ولكن لا يحتوي على مفتاح "file"', None)
        return "لم يتم العثور على ملف", 400
        
    file = request.files['file']
    
    if file.filename == '':
        log_to_db(current_time, 'error', 'تم إرسال الطلب ولكن اسم الملف كان فارغاً', None)
        return "اسم الملف فارغ", 400
        
    try:
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(save_path)
        
        print(f"تم استلام وحفظ الملف: {file.filename}")
        log_to_db(current_time, 'success', f'تم حفظ الملف بنجاح: {file.filename}', file.filename)
        return "تم استلام الملف بنجاح!", 200
        
    except Exception as e:
        log_to_db(current_time, 'error', f'فشل أثناء محاولة حفظ الملف: {str(e)}', None)
        return "حدث خطأ داخلي", 500

# 4. مسار تحميل الملفات المخزنة (تم التصحيح هنا)
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        return f"الملف غير موجود أو حدث خطأ: {str(e)}", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
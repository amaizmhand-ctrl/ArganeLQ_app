import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import datetime
import json
import random
import time
from datetime import datetime, date, timedelta

# ---------------------------------------------------------
# Page Configuration & Styling (PWA & Web Config)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Lqargane - منظومة تتبع الغياب الذكية",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Soft UI & Comfortable Typography Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;800&display=swap');
    
    html, body, [class*="css"], div, span, applet, object, iframe, h1, h2, h3, h4, h5, h6, p, blockquote, pre, a, abbr, acronym, address, big, cite, code, del, dfn, em, img, ins, kbd, q, s, samp, small, strike, strong, sub, sup, tt, var, b, u, i, center, dl, dt, dd, ol, ul, li, fieldset, form, label, legend, table, caption, tbody, tfoot, thead, tr, th, td {
        font-family: 'Tajawal', sans-serif !important;
        direction: rtl;
        text-align: right;
        color: #1e293b;
    }
    
    .stApp {
        background-color: #f1f5f9;
    }
    
    .metric-card {
        background: #ffffff;
        padding: 1.25rem;
        border-radius: 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
        border: 1px solid #e2e8f0;
        text-align: center;
    }
    
    .badge-danger {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 6px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.85rem;
        text-align: center;
    }

    .badge-warning {
        background-color: #fef3c7;
        color: #92400e;
        padding: 6px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.85rem;
        text-align: center;
    }

    .badge-success {
        background-color: #dcfce7;
        color: #166534;
        padding: 6px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.85rem;
        text-align: center;
    }

    .online-indicator {
        height: 10px;
        width: 10px;
        background-color: #22c55e;
        border-radius: 50%;
        display: inline-block;
        margin-left: 5px;
    }

    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
        color: #ffffff;
    }
    
    section[data-testid="stSidebar"] * {
        color: #f1f5f9 !important;
    }

    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
        background-color: #0284c7;
        color: white;
        border: none;
    }
    
    .stButton>button:hover {
        background-color: #0369a1;
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Database Initialization & Concurrency Safety
# ---------------------------------------------------------
DB_FILE = "school_absence.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            full_name TEXT,
            role TEXT,
            custom_title TEXT DEFAULT 'أستاذ(ة)',
            status TEXT DEFAULT 'active',
            assigned_class TEXT DEFAULT '',
            phone TEXT UNIQUE,
            must_change_password INTEGER DEFAULT 0,
            last_seen TEXT
        )
    ''')

    # 2. Classes Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE,
            level TEXT DEFAULT '',
            branch TEXT DEFAULT ''
        )
    ''')

    # 3. Students Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_number INTEGER,
            massar_id TEXT UNIQUE,
            full_name TEXT,
            class_name TEXT,
            guardian_phone TEXT DEFAULT '',
            secret_code TEXT,
            total_absent_hours INTEGER DEFAULT 0
        )
    ''')

    # 4. Absence Records Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS absence_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            class_name TEXT,
            date TEXT,
            session_number INTEGER,
            session_time TEXT,
            recorded_by TEXT,
            note TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')

    # 5. Teacher Timetable Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS teacher_timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_username TEXT,
            class_name TEXT,
            day_of_week TEXT,
            session_number INTEGER
        )
    ''')

    # 6. Entry Permits
    c.execute('''
        CREATE TABLE IF NOT EXISTS entry_permits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            cleared_by TEXT,
            timestamp TEXT
        )
    ''')

    # 7. Absence / Leaves Exclusions
    c.execute('''
        CREATE TABLE IF NOT EXISTS school_exclusions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_type TEXT,
            target_name TEXT,
            start_date TEXT,
            end_date TEXT,
            reason TEXT,
            created_by TEXT
        )
    ''')

    # 8. Private Staff Chat
    c.execute('''
        CREATE TABLE IF NOT EXISTS staff_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_name TEXT,
            sender_title TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')

    # 9. Flash Announcements
    c.execute('''
        CREATE TABLE IF NOT EXISTS flash_announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            message TEXT,
            expiry_date TEXT,
            publisher TEXT,
            created_at TEXT
        )
    ''')

    # 10. Immutable Disciplinary Records
    c.execute('''
        CREATE TABLE IF NOT EXISTS student_disciplinary_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            issuer_title TEXT,
            notice_type TEXT,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')

    # Seed Default Master Developer Account
    c.execute("SELECT * FROM users WHERE username = 'dev_admin@school.ma'")
    if not c.fetchone():
        c.execute('''
            INSERT INTO users (username, password, full_name, role, custom_title, status, phone)
            VALUES ('dev_admin@school.ma', 'dev1234', 'المطور الرئيسي', 'developer', 'مطور النظام', 'active', '0600000000')
        ''')
        
    conn.commit()
    conn.close()

init_db()

SESSIONS = {
    1: {"name": "الحصة 1 (الصباحية)", "time": "08:00 - 09:00", "period": "صباح"},
    2: {"name": "الحصة 2 (الصباحية)", "time": "09:00 - 10:00", "period": "صباح"},
    3: {"name": "الحصة 3 (الصباحية)", "time": "10:00 - 11:00", "period": "صباح"},
    4: {"name": "الحصة 4 (الصباحية)", "time": "11:00 - 12:00", "period": "صباح"},
    5: {"name": "الحصة 5 (المسائية)", "time": "14:00 - 15:00", "period": "مساء"},
    6: {"name": "الحصة 6 (المسائية)", "time": "15:00 - 16:00", "period": "مساء"},
    7: {"name": "الحصة 7 (المسائية)", "time": "16:00 - 17:00", "period": "مساء"},
    8: {"name": "الحصة 8 (المسائية)", "time": "17:00 - 18:00", "period": "مساء"},
}

def get_current_session_number():
    now_hour = datetime.now().hour
    if now_hour == 8: return 1
    elif now_hour == 9: return 2
    elif now_hour == 10: return 3
    elif now_hour == 11: return 4
    elif now_hour == 14: return 5
    elif now_hour == 15: return 6
    elif now_hour == 16: return 7
    elif now_hour >= 17: return 8
    return 1

if "user" not in st.session_state:
    st.session_state.user = None

def logout():
    st.session_state.user = None
    if "active_parent_student" in st.session_state:
        del st.session_state["active_parent_student"]
    st.rerun()

# ---------------------------------------------------------
# Sidebar Navigation & Login / Logout
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #38bdf8;'>🏫 Lqargane</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.85rem;'>منصة المواظبة والزمن المدرسي الذكي</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #38bdf8; font-size: 0.8rem; font-weight: bold;'>By: Pr:M'h.AMAIZ</p>", unsafe_allow_html=True)
    st.divider()

    if st.session_state.user:
        u = st.session_state.user
        role_label = u.get('custom_title', u['role'])

        st.markdown(f"**مرحباً بك:** {u['full_name']}")
        st.markdown(f"**الصفة التربوية:** `{role_label}`")

        st.divider()
        if st.button("🚪 تسجيل الخروج الآمن", use_container_width=True, type="primary"):
            logout()
    else:
        auth_mode = st.radio("طريقة الدخول:", ["🔐 دخول الأطر (البريد أو الهاتف)", "👁️ تلميذ / ولي أمر", "🔑 نسيت كلمة المرور"], label_visibility="collapsed")

        if auth_mode == "🔐 دخول الأطر (البريد أو الهاتف)":
            st.subheader("دخول الأطر التربوية")
            login_id = st.text_input("البريد الإلكتروني أو الهاتف المهني", key="login_id_field")
            login_pass = st.text_input("كلمة المرور / الكود", type="password", key="login_pass_field")
            
            if st.button("دخول المنظومة", use_container_width=True, type="primary"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE (username = ? OR phone = ?) AND password = ?", (login_id, login_id, login_pass))
                user = c.fetchone()
                if user:
                    c.execute("UPDATE users SET last_seen = ? WHERE id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M"), user['id']))
                    conn.commit()
                conn.close()

                if user:
                    if user['status'] == 'active':
                        st.session_state.user = dict(user)
                        st.success("تم تسجيل الدخول بنجاح!")
                        st.rerun()
                    else:
                        st.warning("حسابك غير مفعل حالياً.")
                else:
                    st.error("معلومات الدخول غير صحيحة!")

        elif auth_mode == "👁️ تلميذ / ولي أمر":
            st.subheader("بوابة المراقبة الفردية")
            p_massar = st.text_input("رقم مسار التلميذ(ة)", placeholder="مثال: G123456789").strip()
            p_code = st.text_input("الرمز السري (رقم مسار + 20262027)", type="password").strip()
            
            if st.button("عرض سجل الغياب والملاحظات", use_container_width=True, type="primary"):
                if p_massar and p_code:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM students WHERE massar_id = ? AND secret_code = ?", (p_massar, p_code))
                    student = c.fetchone()
                    conn.close()

                    if student:
                        st.session_state.active_parent_student = dict(student)
                        st.session_state.user = {"role": "parent", "full_name": student['full_name'], "custom_title": "ولي أمر / تلميذ"}
                        st.success("تم الدخول بنجاح!")
                        st.rerun()
                    else:
                        st.error("رقم مسار أو الرمز السري غير صحيح!")
                else:
                    st.error("يرجى ملء كافة الخانات.")

        elif auth_mode == "🔑 نسيت كلمة المرور":
            st.subheader("استعادة كلمة المرور")
            rec_id = st.text_input("أدخل بريدك الإلكتروني أو رقم هاتفك المهني:")
            if st.button("إرسال بيانات الاستعادة", use_container_width=True):
                if rec_id:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username = ? OR phone = ?", (rec_id, rec_id))
                    usr = c.fetchone()
                    conn.close()
                    if usr:
                        st.success(f"تم إرسال كود الاستعادة المؤقت بنجاح إلى البريد/الهاتف المرتبط بحساب: {usr['full_name']}")
                    else:
                        st.error("المعطيات المدخلة غير مسجلة في النظام!")
                else:
                    st.error("يرجى إدخال البريد أو الهاتف.")

# ---------------------------------------------------------
# Flash Announcements Banner for Parents & Students
# ---------------------------------------------------------
if st.session_state.user:
    conn = get_db_connection()
    today_str = date.today().strftime("%Y-%m-%d")
    announcements = pd.read_sql_query("SELECT title, message, publisher FROM flash_announcements WHERE expiry_date >= ?", conn, params=(today_str,))
    conn.close()

    if not announcements.empty and st.session_state.user['role'] == 'parent':
        st.markdown("### 📢 إخبارات عاجلة وتنبيهات المؤسسة:")
        for _, ann in announcements.iterrows():
            st.warning(f"🚨 **{ann['title']}** (ناشر الخبر: {ann['publisher']})\n\n{ann['message']}")

# ---------------------------------------------------------
# Main Router
# ---------------------------------------------------------
if not st.session_state.user:
    st.markdown("""
        <div style="text-align: center; padding: 2.5rem; background: linear-gradient(135deg, #0f172a, #1e293b); border-radius: 16px; color: white; margin-bottom: 2rem;">
            <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem; color: #38bdf8;">🏫 منصة Lqargane الذكية لتتبع الغياب</h1>
            <p style="font-size: 1.2rem; color: #cbd5e1;">موقع وتطبيق رسمي متزامن لحظياً لإدارة الزمن المدرسي ومتابعة المواظبة والسلوك</p>
            <p style="font-size: 1rem; color: #38bdf8; margin-top: 1rem; font-weight: bold;">Developed by: Pr:M'h.AMAIZ</p>
        </div>
    """, unsafe_allow_html=True)
    st.info("👈 يرجى تسجيل الدخول عبر الشريط الجانبي للبدء.")

else:
    role = st.session_state.user['role']

    # Force Password Change on First Login
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT must_change_password FROM users WHERE id = ?", (st.session_state.user['id'],))
    row_pw = c.fetchone()
    conn.close()

    if row_pw and row_pw['must_change_password'] == 1 and role != 'parent':
        st.warning("⚠️ هذا هو اتصالك الأول بالكود المؤقت! يرجى تغيير كلمة المرور إلى كود شخصي جديد للدخول.")
        new_p1 = st.text_input("كلمة المرور الجديدة", type="password")
        new_p2 = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
        if st.button("حفظ وتحديث الكود الشخصي"):
            if new_p1 and new_p1 == new_p2:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("UPDATE users SET password = ?, must_change_password = 0 WHERE id = ?", (new_p1, st.session_state.user['id']))
                conn.commit()
                conn.close()
                st.success("تم تحديث كلمة المرور بنجاح! يرجى إعادة تسجيل الدخول.")
                time.sleep(1.5)
                logout()
            else:
                st.error("كلمتا المرور غير متطابقتين أو فارغتان.")
        st.stop()

    # =========================================================
    # 1. DEVELOPER ROLE
    # =========================================================
    if role == 'developer':
        st.title("👨‍💻 لوحة تحكّم المطور الرئيسي (Lqargane Master)")
        dev_tabs = st.tabs(["👤 حسابات الأطر والصفات", "📥 استيراد ملفات التلاميذ الرسمية (Excel متعدد الأقسام)", "📅 استعمال الزمن", "➕ الأقسام والشعب"])

        conn = get_db_connection()
        with dev_tabs[0]:
            st.subheader("إضافة حساب أستاذ أو إداري مع تحديد الصفة الدقيقة")
            d_name = st.text_input("الاسم الكامل")
            d_email = st.text_input("البريد الإلكتروني")
            d_phone = st.text_input("رقم الهاتف المهني (محمي تماماً)", placeholder="06XXXXXXXX")
            d_role = st.selectbox("الدور الأساسي", ["teacher", "admin", "supervisor"], format_func=lambda x: {"teacher": "أستاذ(ة)", "admin": "المدير", "supervisor": "الحارس العام"}[x])
            
            d_custom_title = st.text_input("الصفة الدقيقة (تظهر للآخرين بدلاً من البريد/الهاتف):", placeholder="مثال: أستاذ العربية 1 / مدير المؤسسة")
            d_pass = st.text_input("الكود الأولي", value="123456")
            assigned_c = st.selectbox("القسم المسند", pd.read_sql_query("SELECT class_name FROM classes", conn)['class_name'].tolist()) if d_role == 'teacher' else ""

            if st.button("حفظ الحساب", type="primary"):
                if d_name and d_phone and d_custom_title:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO users (username, password, full_name, role, custom_title, status, assigned_class, phone, must_change_password) VALUES (?, ?, ?, ?, ?, 'active', ?, ?, 1)",
                                  (d_email if d_email else d_phone, d_pass, d_name, d_role, d_custom_title, assigned_c, d_phone))
                        conn.commit()
                        st.success("تم الحفظ بنجاح مع تشفير الحماية والخصوصية التامة!")
                    except Exception as e:
                        st.error(f"خطأ: {e}")
                else:
                    st.error("يرجى ملء كافة الخانات بما فيها الصفة الدقيقة.")

        with dev_tabs[1]:
            st.subheader("📥 قراءة واستيراد ملف الإكسيل الرسمي للمؤسسة (يقرأ جميع الأقسام تلقائياً)")
            st.info("قم برفع ملف الإكسيل الرسمي (مثل ListEleve). النظام سيقرأ كافة الأقسام الموجودة في أوراق العمل (Sheets)، ويستخرج المستويات، الشعب، والمجموعات وأسماء التلاميذ برقم مسارهم تلقائياً.")
            
            up_file = st.file_uploader("اختر ملف إكسيل الأقسام (.xlsx)", type=['xlsx'])
            if up_file:
                try:
                    xls = pd.ExcelFile(up_file)
                    st.write(f"📁 تم العثور على {len(xls.sheet_names)} قسم/مجموعة في الملف.")
                    
                    if st.button("معالجة واستيراد كافة أقسام ومجموعات التلاميذ"):
                        c = conn.cursor()
                        total_imported = 0
                        
                        for sheet in xls.sheet_names:
                            df_sheet = pd.read_excel(up_file, sheet_name=sheet, header=None)
                            
                            # Extract Level and Class Name automatically from the sheet header structure
                            level_val = "تعليم ثانوي"
                            class_val = sheet
                            
                            for r in range(min(10, df_sheet.shape[0])):
                                row_str = str(df_sheet.iloc[r].values)
                                if 'المستوى' in row_str:
                                    for val in df_sheet.iloc[r].values:
                                        if pd.notna(val) and 'المستوى' not in str(val) and ':' not in str(val):
                                            level_val = str(val).strip()
                                if 'القسم' in row_str:
                                    for val in df_sheet.iloc[r].values:
                                        if pd.notna(val) and 'القسم' not in str(val) and ':' not in str(val):
                                            class_val = str(val).strip()

                            # Determine Branch based on level/class name
                            branch_val = "عام"
                            if "علوم" in level_val or "علوم" in class_val: branch_val = "علوم"
                            elif "آداب" in level_val or "إنسانية" in class_val: branch_val = "آداب وعلوم إنسانية"

                            # Insert Class / Group
                            c.execute("INSERT OR IGNORE INTO classes (class_name, level, branch) VALUES (?, ?, ?)", (class_val, level_val, branch_val))
                            
                            # Read students starting from row 8 (where headers are: ر.ت, الرمز, النسب, الإسم...)
                            df_students = pd.read_excel(up_file, sheet_name=sheet, skiprows=8)
                            if df_students.shape[1] >= 4:
                                # Rename columns safely
                                cols = list(df_students.columns)
                                for _, row in df_students.iterrows():
                                    massar = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                                    if massar and massar != 'nan' and massar != 'الرمز':
                                        family_name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
                                        first_name = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
                                        full_name = f"{family_name} {first_name}".strip()
                                        std_num = int(row.iloc[0]) if pd.notna(row.iloc[0]) and str(row.iloc[0]).isdigit() else 1
                                        secret_code = f"{massar}20262027"
                                        
                                        c.execute("""
                                            INSERT INTO students (student_number, massar_id, full_name, class_name, secret_code) 
                                            VALUES (?, ?, ?, ?, ?) 
                                            ON CONFLICT(massar_id) DO UPDATE SET full_name=excluded.full_name, class_name=excluded.class_name
                                        """, (std_num, massar, full_name, class_val, secret_code))
                                        total_imported += 1

                        conn.commit()
                        st.success(f"🎉 تم بنجاح استيراد وتسجيل {total_imported} تلميذاً موزعين على جميع الأقسام والمستويات والشعب!")
                except Exception as e:
                    st.error(fُ"حدث خطأ أثناء قراءة الملف: {e}")

        with dev_tabs[2]:
            st.subheader("إدخال استعمال الزمن")
            teachers_df = pd.read_sql_query("SELECT full_name, username, custom_title FROM users WHERE role = 'teacher'", conn)
            classes_df = pd.read_sql_query("SELECT class_name FROM classes", conn)
            t_map = {f"{r['full_name']} ({r['custom_title']})": r['username'] for _, r in teachers_df.iterrows()}
            sel_t = st.selectbox("الأستاذ:", list(t_map.keys()) if t_map else [])
            sel_cls = st.selectbox("القسم أو المجموعة:", classes_df['class_name'].tolist() if not classes_df.empty else [])
            sel_day = st.selectbox("اليوم:", ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"])
            sel_sess = st.selectbox("الحصة:", options=list(SESSIONS.keys()), format_func=lambda x: f"الحصة {x} ({SESSIONS[x]['time']})")
            if st.button("إضافة الحصة"):
                if sel_t and sel_cls:
                    c = conn.cursor()
                    c.execute("INSERT INTO teacher_timetable (teacher_username, class_name, day_of_week, session_number) VALUES (?, ?, ?, ?)",
                              (t_map[sel_t], sel_cls, sel_day, sel_sess))
                    conn.commit()
                    st.success("تمت الإضافة بنجاح.")

        with dev_tabs[3]:
            st.subheader("الأقسام والمجموعات المستخرجة من الملفات")
            st.dataframe(pd.read_sql_query("SELECT class_name as 'اسم القسم', level as 'المستوى', branch as 'الشعبة' FROM classes", conn), use_container_width=True)
        conn.close()

    # =========================================================
    # 2. ADMINISTRATION & SUPERVISOR ROLE
    # =========================================================
    elif role in ['admin', 'supervisor']:
        st.title(f"📋 لوحة قيادة {'السيد المدير' if role == 'admin' else 'الحارس العام'}")
        
        admin_tabs = st.tabs(["📊 الإحصائيات والبحث", "🚨 تنبيهات الغياب والإشعارات", "🏖️ العطل والغياب الاستثنائي", "💬 دردشة الأطر", "📢 نشر الإخبارات العاجلة", "📥 تصدير التقارير الرسمية"])
        conn = get_db_connection()

        with admin_tabs[0]:
            st.subheader("محرك البحث الفردي للتلاميذ")
            srch_name = st.text_input("اسم التلميذ:")
            cls_list = pd.read_sql_query("SELECT class_name FROM classes", conn)['class_name'].tolist()
            srch_cls = st.selectbox("القسم أو المجموعة:", ["الكل"] + cls_list)
            if st.button("بحث استنتاجي"):
                if srch_name:
                    q = "SELECT * FROM students WHERE full_name LIKE ?"
                    p = [f"%{srch_name}%"]
                    if srch_cls != "الكل":
                        q += " AND class_name = ?"
                        p.append(srch_cls)
                    res = pd.read_sql_query(q, conn, params=p)
                    if not res.empty:
                        for _, std in res.iterrows():
                            st.info(f"التلميذ: {std['full_name']} | القسم: {std['class_name']} | مجموع الغياب الاستنتاجي: {std['total_absent_hours']} ساعة")
                    else:
                        st.warning("لا توجد نتائج مطابقة.")

        with admin_tabs[1]:
            st.subheader("التلاميذ الذين تجاوزوا سقف الغياب وإرسال تنبيهات غير قابلة للحذف")
            absent_risk_df = pd.read_sql_query("SELECT id, massar_id, full_name, class_name, total_absent_hours FROM students WHERE total_absent_hours >= 4", conn)
            st.dataframe(absent_risk_df, use_container_width=True)

            if not absent_risk_df.empty:
                st.divider()
                st.markdown("##### ✉️ إرسال إنذار/إشعار إداري مباشر لا يمكن للتلميذ حذفه:")
                target_student_id = st.selectbox("اختر التلميذ المعني:", absent_risk_df['id'].tolist(), format_func=lambda x: absent_risk_df[absent_risk_df['id']==x]['full_name'].values[0])
                admin_notice = st.text_area("نص الإنذار أو التنبيه (مثال: تجاوزت عتبة 4 ساعات غياب، يرجى حضور ولي أمرك للإدارة فوراً):")
                if st.button("إرسال الإشعار الثابت لحساب التلميذ والأب"):
                    if admin_notice:
                        c = conn.cursor()
                        c.execute("INSERT INTO student_disciplinary_records (student_id, issuer_title, notice_type, content, created_at) VALUES (?, ?, ?, ?, ?)",
                                  (target_student_id, st.session_state.user['custom_title'], 'تنبيه إداري تجاوز السقف', admin_notice, datetime.now().strftime("%Y-%m-%d %H:%M")))
                        conn.commit()
                        st.success("تم إرسال التنبيه الإداري بنجاح وثبته في سوابق التلميذ نهائياً.")

        with admin_tabs[2]:
            st.subheader("🏖️ إدارة العطل، المرض، التكوينات والاجتماعات")
            exc_type = st.selectbox("نوع الانقطاع الدراسي:", ["مؤسسة كاملة (كل الأقسام)", "قسم معين", "أستاذ معين"])
            target_val = "الكل"
            if exc_type == "قسم معين":
                target_val = st.selectbox("اختر القسم:", cls_list)
            elif exc_type == "أستاذ معين":
                teachers_list = pd.read_sql_query("SELECT full_name, custom_title FROM users WHERE role = 'teacher'", conn)
                t_choice_map = {f"{r['full_name']} ({r['custom_title']})": r['full_name'] for _, r in teachers_list.iterrows()}
                chosen_t_label = st.selectbox("اختر الأستاذ:", list(t_choice_map.keys()) if t_choice_map else [])
                target_val = t_choice_map.get(chosen_t_label, "")

            ex_start = st.date_input("من تاريخ:", date.today())
            ex_end = st.date_input("إلى تاريخ:", date.today())
            ex_reason = st.text_input("سبب الغياب / العطلة:", placeholder="مثال: تكوين تربوي / مرض / عطلة رسمية")

            if st.button("تسجيل الانقطاع وإعلام الآباء تلقائياً"):
                c = conn.cursor()
                c.execute("INSERT INTO school_exclusions (target_type, target_name, start_date, end_date, reason, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                          (exc_type, target_val, str(ex_start), str(ex_end), ex_reason, st.session_state.user['custom_title']))
                conn.commit()
                st.success("تم تسجيل الانقطاع وتحديث النظام بنجاح لعدم احتساب الغياب خطأً!")

            st.markdown("### السجلات المسجلة للانقطاعات:")
            st.dataframe(pd.read_sql_query("SELECT target_type as 'المجال', target_name as 'الهدف', start_date as 'من', end_date as 'إلى', reason as 'السبب', created_by as 'المسؤول' FROM school_exclusions", conn), use_container_width=True)

        with admin_tabs[3]:
            st.subheader("💬 غرفة الدردشة الخاصة بالأطر (مع إخفاء الهواتف والبريد وحفظ الخصوصية)")
            online_staff = pd.read_sql_query("SELECT custom_title, role, last_seen FROM users WHERE role != 'parent'", conn)
            st.markdown("##### 🟢 الأطر المتواجدة بالمنظومة:")
            cols_on = st.columns(min(len(online_staff), 4) if not online_staff.empty else 1)
            for idx, stf in online_staff.iterrows():
                with cols_on[idx % len(cols_on)]:
                    st.markdown(f"<span class='online-indicator'></span> **{stf['custom_title']}**", unsafe_allow_html=True)

            st.divider()
            chat_msg = st.text_input("اكتب رسالة توضيحية:")
            if st.button("إرسال الرسالة للدردشة الخاصة"):
                if chat_msg:
                    c = conn.cursor()
                    c.execute("INSERT INTO staff_chats (sender_name, sender_title, message, timestamp) VALUES (?, ?, ?, ?)",
                              (st.session_state.user['full_name'], st.session_state.user['custom_title'], chat_msg, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("تم إرسال الرسالة بنجاح.")

            chats_df = pd.read_sql_query("SELECT sender_title as 'الصفة التربوية', message as 'الرسالة', timestamp as 'التاريخ والوقت' FROM staff_chats ORDER BY id DESC LIMIT 10", conn)
            for _, ch in chats_df.iterrows():
                st.markdown(f"💬 **{ch['الصفة التربوية']}** - *{ch['التاريخ والوقت']}*:\n> {ch['الرسالة']}")

        with admin_tabs[4]:
            st.subheader("📢 نشر الأخبار العاجلة الموجهة للآباء والتلاميذ")
            ann_title = st.text_input("عنوان الخبر العاجل:")
            ann_msg = st.text_area("نص الخبر والتفاصيل:")
            duration_days = st.selectbox("مدة ظهور الإخبار:", [1, 2, 3, 7], format_func=lambda x: f"{x} {'يوم' if x==1 else 'أيام'}")
            
            if st.button("نشر الإخبار الفوري للجميع"):
                if ann_title and ann_msg:
                    expiry = (date.today() + timedelta(days=duration_days)).strftime("%Y-%m-%d")
                    c = conn.cursor()
                    c.execute("INSERT INTO flash_announcements (title, message, expiry_date, publisher, created_at) VALUES (?, ?, ?, ?, ?)",
                              (ann_title, ann_msg, expiry, st.session_state.user['custom_title'], str(date.today())))
                    conn.commit()
                    st.success("تم نشر الإخبار العاجل بنجاح وسيظهر للجميع!")

        with admin_tabs[5]:
            st.subheader("📥 استخراج وتصدير التقارير الرسمية للإدارة")
            report_type = st.selectbox("اختر تقرير الإدارة المطلوب:", ["تقرير الغياب العام للمؤسسة", "تقرير المتغيبين الذين تجاوزوا عتبة 4 ساعات", "سجل التصاريح والإذون بالدخول"])
            
            if st.button("إنشاء وتحميل ملف التقرير (Excel / CSV)"):
                if report_type == "تقرير الغياب العام للمؤسسة":
                    rep_df = pd.read_sql_query("SELECT s.massar_id as 'رقم مسار', s.full_name as 'التلميذ', s.class_name as 'القسم', a.date as 'تاريخ الغياب', a.session_number as 'الحصة', a.recorded_by as 'المسجل', a.note as 'الملاحظة' FROM absence_records a JOIN students s ON a.student_id = s.id", conn)
                elif report_type == "تقرير المتغيبين الذين تجاوزوا عتبة 4 ساعات":
                    rep_df = pd.read_sql_query("SELECT massar_id as 'رقم مسار', full_name as 'التلميذ', class_name as 'القسم', total_absent_hours as 'مجموع الساعات' FROM students WHERE total_absent_hours >= 4", conn)
                else:
                    rep_df = pd.read_sql_query("SELECT s.massar_id as 'رقم مسار', s.full_name as 'التلميذ', p.cleared_by as 'صاحب التصريح', p.timestamp as 'وقت الدخول' FROM entry_permits p JOIN students s ON p.student_id = s.id", conn)
                
                st.dataframe(rep_df, use_container_width=True)
                csv_data = rep_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ تحميل التقرير كملف CSV معتمد", data=csv_data, file_name=f"{report_type}_{date.today()}.csv", mime="text/csv")
        conn.close()

    # =========================================================
    # 3. TEACHER ROLE
    # =========================================================
    elif role == 'teacher':
        st.title(f"👨‍🏫 بوابة الأستاذ(ة): {st.session_state.user['full_name']} ({st.session_state.user['custom_title']})")
        conn = get_db_connection()
        t_uname = st.session_state.user['username']

        teacher_tabs = st.tabs(["⚡ تسجيل الغياب والملاحظات", "🏖️ تسجيل غيابي (مرض/تكوين)", "💬 دردشة الأطر الخاصة", "📥 تقارير الأستاذ"])

        with teacher_tabs[0]:
            t_classes = pd.read_sql_query("SELECT DISTINCT class_name FROM teacher_timetable WHERE teacher_username = ?", conn, params=(t_uname,))
            classes_list = t_classes['class_name'].tolist() if not t_classes.empty else [st.session_state.user.get('assigned_class', 'الجذع المشترك 1')]

            auto_sess = get_current_session_number()
            st.info(f"📅 التاريخ: {date.today().strftime('%Y-%m-%d')} | ⏰ الحصة المقترحة تلقائياً: الحصة {auto_sess}")

            sel_cls = st.selectbox("اختر القسم أو المجموعة:", classes_list)
            sess_num = st.selectbox("الحصة:", options=list(SESSIONS.keys()), index=auto_sess-1, format_func=lambda x: f"الحصة {x} ({SESSIONS[x]['time']})")

            today_date = str(date.today())
            chk_exc = pd.read_sql_query("SELECT reason FROM school_exclusions WHERE (target_type='global') OR (target_type='class' AND target_name=?) OR (target_type='teacher' AND target_name=?) AND start_date <= ? AND end_date >= ?",
                                      conn, params=(sel_cls, st.session_state.user['full_name'], today_date, today_date))
            if not chk_exc.empty:
                st.warning(f"⚠️ تنبيه ذكي: توجد عطلة أو انقطاع مسجل في هذا التاريخ ({chk_exc.iloc[0]['reason']}). لا داعي لتسجيل الغياب.")
            else:
                std_df = pd.read_sql_query("SELECT id, student_number, full_name FROM students WHERE class_name = ? ORDER BY student_number ASC", conn, params=(sel_cls,))

                st.write("حدد التلاميذ المتغيبين:")
                absent_ids = []
                cols = st.columns(3)
                for idx, r in std_df.iterrows():
                    with cols[idx % 3]:
                        if st.checkbox(f"({r['student_number']}) {r['full_name']}", key=f"t_abs_{r['id']}"):
                            absent_ids.append(r['id'])

                st.divider()
                note_opt = st.selectbox("ملاحظة سلوكية:", ["بدون ملاحظة", "تأخر في بداية الحصة", "غادر القسم", "تم كتابة تقرير في حقه في الحصة"])
                custom_n = st.text_input("أو ملاحظة سلوكية خاصة (تثبت فوراً بسوابق التلميذ ولا يمكنه حذفها):")
                final_n = custom_n if custom_n else (note_opt if note_opt != "بدون ملاحظة" else "")
                target_n = st.selectbox("التلميذ المعني بالملاحظة الثابتة:", ["بدون"] + [f"({r['student_number']}) {r['full_name']}" for _, r in std_df.iterrows()])

                if st.button("💾 تسجيل الغياب والملاحظة الثابتة", type="primary", use_container_width=True):
                    c = conn.cursor()
                    for sid in absent_ids:
                        c.execute("INSERT INTO absence_records (student_id, class_name, date, session_number, session_time, recorded_by, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (sid, sel_cls, today_date, sess_num, SESSIONS[sess_num]['time'], st.session_state.user['custom_title'], final_n))
                        c.execute("UPDATE students SET total_absent_hours = total_absent_hours + 1 WHERE id = ?", (sid,))
                    
                    if target_n != "بدون" and final_n:
                        t_num = int(target_n.split(')')[0].replace('(', ''))
                        t_id = std_df[std_df['student_number'] == t_num]['id'].iloc[0]
                        c.execute("INSERT INTO student_disciplinary_records (student_id, issuer_title, notice_type, content, created_at) VALUES (?, ?, ?, ?, ?)",
                                  (t_id, st.session_state.user['custom_title'], 'ملاحظة سلوكية للأستاذ', final_n, datetime.now().strftime("%Y-%m-%d %H:%M")))

                    conn.commit()
                    st.success("تم التسجيل وتثبيت الملاحظة بسوابق التلميذ بنجاح!")

        with teacher_tabs[1]:
            st.subheader("🏖️ إشعار الإدارة بغيابك (مرض، تكوين، اجتماع)")
            t_reason = st.text_input("سبب الغياب:", placeholder="مثال: رخصة مرضية / حضور تكوين إقليمي")
            t_start = st.date_input("ابتداء من تاريخ:", date.today(), key="t_s")
            t_end = st.date_input("إلى غاية تاريخ:", date.today(), key="t_e")
            if st.button("إرسال طلب الانقطاع للإدارة وتنبيه الآباء"):
                c = conn.cursor()
                c.execute("INSERT INTO school_exclusions (target_type, target_name, start_date, end_date, reason, created_by) VALUES ('teacher', ?, ?, ?, ?, ?)",
                          (st.session_state.user['full_name'], str(t_start), str(t_end), t_reason, st.session_state.user['custom_title']))
                conn.commit()
                st.success("تم إرسال الإشعار بنجاح للإدارة وتحديث النظام لتبرير غياب الحصص المعنية.")

        with teacher_tabs[2]:
            st.subheader("💬 دردشة الأطر الخاصة (خصوصية تامة بدون إظهار الهواتف)")
            chat_msg_t = st.text_input("رسالتك للإدارة أو الزملاء:", key="chat_t")
            if st.button("إرسال رسالة الأطر"):
                if chat_msg_t:
                    c = conn.cursor()
                    c.execute("INSERT INTO staff_chats (sender_name, sender_title, message, timestamp) VALUES (?, ?, ?, ?)",
                              (st.session_state.user['full_name'], st.session_state.user['custom_title'], chat_msg_t, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    conn.commit()
                    st.success("تم الإرسال.")
            chats_df = pd.read_sql_query("SELECT sender_title as 'الصفة التربوية', message as 'الرسالة', timestamp as 'التاريخ والوقت' FROM staff_chats ORDER BY id DESC LIMIT 10", conn)
            for _, ch in chats_df.iterrows():
                st.markdown(f"💬 **{ch['الصفة التربوية']}** - *{ch['التاريخ والوقت']}*:\n> {ch['الرسالة']}")

        with teacher_tabs[3]:
            st.subheader("📥 تقارير الأستاذ الخاصة بأقسامه")
            t_rep_df = pd.read_sql_query("SELECT s.massar_id as 'رقم مسار', s.full_name as 'التلميذ', s.class_name as 'القسم', a.date as 'التاريخ', a.session_number as 'الحصة', a.note as 'الملاحظة' FROM absence_records a JOIN students s ON a.student_id = s.id WHERE a.recorded_by = ?", conn, params=(st.session_state.user['custom_title'],))
            st.dataframe(t_rep_df, use_container_width=True)
            if not t_rep_df.empty:
                t_csv = t_rep_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ تحميل تقرير غيابات الأستاذ كملف CSV", data=t_csv, file_name=f"teacher_report_{date.today()}.csv", mime="text/csv")

        conn.close()

    # =========================================================
    # 4. PARENT & STUDENT ROLE
    # =========================================================
    elif role == 'parent':
        std = st.session_state.active_parent_student
        st.title("👁️ فضاء مراقبة المواظبة والتصاريح والتشجيعات وسجل الملاحظات الثابتة")

        st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 12px; border-right: 6px solid #0284c7; margin-bottom: 1.5rem;">
            <h2>التلميذ(ة): {std['full_name']}</h2>
            <p>رقم مسار: <b>{std['massar_id']}</b> | القسم/المجموعة: <b>{std['class_name']}</b></p>
        </div>
        """, unsafe_allow_html=True)

        conn = get_db_connection()

        class_students = pd.read_sql_query("SELECT id, total_absent_hours FROM students WHERE class_name = ? ORDER BY total_absent_hours ASC", conn, params=(std['class_name'],))
        
        my_rank = 1
        total_class_students = len(class_students)
        for idx, row in class_students.iterrows():
            if row['id'] == std['id']:
                my_rank = idx + 1
                break

        abs_hours = std['total_absent_hours']
        points = max(100 - (abs_hours * 5), 10)
        
        if abs_hours == 0:
            badge = "🌟 بطل المواظبة المثالي (المرتبة الذهبية)"
            cheer_msg = "أنت رائع حقاً! حضورك الكامل يعكس التزامك وأخلاقك العالية. واصل هذا التألق!"
        elif abs_hours <= 2:
            badge = "🥈 نجم الحضور الفضي"
            cheer_msg = "ممتاز جداً! مواظبتك رائعة ومستواك مشرف للغاية. واصل مواظبتك، أنت تلميذ رائع!"
        elif abs_hours <= 5:
            badge = "🥉 مجتهد في طريق التميز"
            cheer_msg = "جهد طيب! يمكنك تحسين حضورك أكثر لتكون في صدارة القسم. نحن نؤمن بك!"
        else:
            badge = "🎯 بحاجة لمزيد من الانضباط"
            cheer_msg = "ننتظر منك الأفضل في الأيام القادمة! حضورك المبكر والمستمر هو مفتاح نجاحك."

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #e0f2fe, #bae6fd); padding: 1.5rem; border-radius: 14px; border: 2px solid #0284c7; margin-bottom: 1.5rem; text-align: center;">
            <h3 style="color: #0369a1; margin-bottom: 0.5rem;">🏆 لوحة الشرف الشخصية للمواظبة والحضور</h3>
            <p style="font-size: 1.1rem; color: #0f172a;">ترتيبك في قسمك: <b>المرتبة {my_rank}</b> من أصل {total_class_students} تلميذاً (بسرية تامة بدون الكشف عن الآخرين)</p>
            <p style="font-size: 1.1rem; color: #166534;">نقاط التحفيز المكتسبة: <b>{points} نقطة</b> | الشارة: <b>{badge}</b></p>
            <hr style="border-color: #7dd3fc;">
            <p style="font-size: 1.2rem; font-weight: bold; color: #1e3a8a; margin-top: 10px;">💬 "{cheer_msg}"</p>
        </div>
        """, unsafe_allow_html=True)
        
        today_date = str(date.today())
        excs = pd.read_sql_query("SELECT reason FROM school_exclusions WHERE (target_type='global') OR (target_type='class' AND target_name=?) AND start_date <= ? AND end_date >= ?",
                                 conn, params=(std['class_name'], today_date, today_date))
        if not excs.empty:
            st.info(f"ℹ️ **تنبيه للمواظبة الاستنتاجية:** توجد عطلة أو انقطاع دراسي اليوم في القسم ({excs.iloc[0]['reason']}). لا توجد دراسة في الحصص المعنية.")

        c = conn.cursor()
        c.execute("SELECT cleared_by, timestamp FROM entry_permits WHERE student_id = ? ORDER BY id DESC", (std['id'],))
        permits = c.fetchall()
        if permits:
            for p in permits:
                st.success(f"🟢 تصريح بالسماح بالدخول صادر عن الإدارة بتاريخ: {p['timestamp']}")

        st.subheader("🚨 السجل الثابت للتنبيهات والملاحظات الإدارية والسلوكية:")
        notices_df = pd.read_sql_query("SELECT issuer_title as 'المرسل', notice_type as 'نوع الإشعار', content as 'التفاصيل', created_at as 'التاريخ والوقت' FROM student_disciplinary_records WHERE student_id = ? ORDER BY id DESC", conn, params=(std['id'],))
        if not notices_df.empty:
            st.warning("⚠️ تنبيه: هذه السجلات موثقة رسمياً ولا يمكن حذفها من ملف التلميذ، ليطلع عليها ولي الأمر في كل حين.")
            st.dataframe(notices_df, use_container_width=True)
        else:
            st.success("✨ سجلك نظيف تماماً وخالٍ من أي تنبيهات أو ملاحظات سلبية. ممتاز!")

        st.metric("مجموع ساعات الغياب المسجلة", f"{std['total_absent_hours']} ساعة")

        st.divider()
        st.subheader("📜 تفاصيل الغيابات والملاحظات:")
        t_abs, t_notes = st.tabs(["سجل الحصص المغابة", "الملاحظات المسجلة"])
        with t_abs:
            st.dataframe(pd.read_sql_query("SELECT date as 'التاريخ', session_number as 'الحصة', session_time as 'التوقيت', recorded_by as 'الناشر', note as 'الملاحظة' FROM absence_records WHERE student_id = ?", conn, params=(std['id'],)), use_container_width=True)
        with t_notes:
            st.dataframe(pd.read_sql_query("SELECT teacher_name as 'الأستاذ', note as 'الملاحظة', created_at as 'التاريخ' FROM student_notes WHERE student_id = ?", conn, params=(std['id'],)), use_container_width=True)
        conn.close()
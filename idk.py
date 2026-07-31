from datetime import date
import bcrypt
import mysql.connector
from mysql.connector import pooling
import pandas as pd
import streamlit as st

# ---------------- APP CONFIG ----------------
st.set_page_config(
    page_title="School Portal",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None


# ---------------- DATABASE POOLING ----------------
@st.cache_resource
def get_db_pool():
    """Create and cache the database connection pool using st.secrets."""
    try:
        db_config = st.secrets["mysql"]
        pool = pooling.MySQLConnectionPool(
            pool_name="school_pool",
            pool_size=5,
            pool_reset_session=True,
            host=db_config["host"],
            port=int(db_config["port"]),
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"],
            connection_timeout=5,
        )
        return pool
    except Exception as err:
        st.error(
            f"Error initializing database pool. Check `.streamlit/secrets.toml`: {err}"
        )
        return None


def get_db_connection():
    """Retrieve a connection from the connection pool."""
    pool = get_db_pool()
    if pool:
        try:
            return pool.get_connection()
        except mysql.connector.Error as err:
            st.error(f"Could not fetch database connection: {err}")
    return None


# ---------------- HELPER FUNCTIONS & AUTH ----------------
def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"), hashed_password.encode("utf-8")
    )


@st.cache_resource
def setup_database_schema():
    """Initialize database tables and set up default hashed admin password."""
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                roll_number VARCHAR(100) UNIQUE NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id INT AUTO_INCREMENT PRIMARY KEY,
                subject_name VARCHAR(255) UNIQUE NOT NULL
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                assessment_id INT AUTO_INCREMENT PRIMARY KEY,
                subject_id INT,
                title VARCHAR(255) NOT NULL,
                type VARCHAR(50),
                due_date DATE,
                total_marks INT,
                FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_marks (
                mark_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                assessment_id INT,
                marks_obtained INT,
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT,
                subject_id INT,
                date DATE,
                status VARCHAR(20),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
            );
        """)

        # Ensure default 'admin' user exists with a hashed password ('root')
        cursor.execute(
            "SELECT password FROM admin WHERE username = 'admin'"
        )
        row = cursor.fetchone()
        hashed_root = hash_password("root")

        if not row:
            cursor.execute(
                "INSERT INTO admin (username, password) VALUES ('admin', %s)",
                (hashed_root,),
            )
        conn.commit()
    except mysql.connector.Error as err:
        st.error(f"Error setting up database tables: {err}")
    finally:
        cursor.close()
        conn.close()


def verify_admin(username, password):
    """Authenticate admin credentials using bcrypt verification."""
    conn = get_db_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    cursor.execute(
        "SELECT password FROM admin WHERE username = %s", (username,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and verify_password(password, user[0]):
        return True
    return False


setup_database_schema()

# ---------------- LOGIN SCREEN ----------------
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            "<h1 style='text-align: center;'>🏫 School Portal</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: gray;'>Welcome back! Please"
            " sign in to access your dashboard.</p>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            login_type = st.radio(
                "Select Access Level",
                ["Teacher", "Head Teacher (Admin)"],
                horizontal=True,
            )

            if login_type == "Teacher":
                st.write("---")
                if st.button("Log In as Teacher", use_container_width=True):
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = "teacher"
                    st.rerun()

            elif login_type == "Head Teacher (Admin)":
                st.write("---")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.button(
                    "Log In as Admin", type="primary", use_container_width=True
                ):
                    if verify_admin(username, password):
                        st.session_state["logged_in"] = True
                        st.session_state["role"] = "admin"
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password!")

# ---------------- MAIN DASHBOARD ----------------
else:
    # Sidebar Navigation
    with st.sidebar:
        st.markdown(
            f"### 👤 **{st.session_state['role'].upper()} MODE**",
            help="Current Logged In Role",
        )
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["role"] = None
            st.rerun()

        st.divider()

        menu = [
            "📌 Dashboard",
            "🔍 Search Student",
            "📊 View Reports",
            "📅 Mark Attendance",
            "💯 Record Marks",
            "📝 Create Test/Assignment",
            "🗑️ Delete Test/Assignment",
            "➕ Add Student (Admin)",
            "❌ Delete Student (Admin)",
            "📘 Add Subject (Admin)",
            "🗑️ Delete Subject (Admin)",
        ]
        choice = st.selectbox("Navigation", menu)

    # PAGE: DASHBOARD
    if choice == "📌 Dashboard":
        st.title("📌 Dashboard & Overview")

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM students")
            total_students = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM subjects")
            total_subjects = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM assessments")
            total_assessments = cursor.fetchone()[0]

            m1, m2, m3 = st.columns(3)
            m1.metric(label="Total Students", value=total_students)
            m2.metric(label="Active Subjects", value=total_subjects)
            m3.metric(label="Total Assessments", value=total_assessments)

            st.divider()
            st.subheader("🔔 Upcoming Assessments")

            today = date.today().strftime("%Y-%m-%d")
            query = """
                SELECT a.title, a.type, a.due_date, s.subject_name 
                FROM assessments a
                JOIN subjects s ON a.subject_id = s.subject_id
                WHERE a.due_date >= %s
                ORDER BY a.due_date ASC
            """
            cursor.execute(query, (today,))
            reminders = cursor.fetchall()

            if reminders:
                df = pd.DataFrame(
                    reminders, columns=["Title", "Type", "Due Date", "Subject"]
                )
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("🎉 No upcoming tests or assignments!")

            cursor.close()
            conn.close()

    # PAGE: SEARCH STUDENT
    elif choice == "🔍 Search Student":
        st.title("🔍 Search Student Records")
        search_query = st.text_input(
            "Enter Student Name or Roll Number",
            placeholder="Type here to search...",
        ).strip()

        if search_query:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                query = """
                    SELECT student_id, name, roll_number 
                    FROM students 
                    WHERE LOWER(TRIM(CAST(roll_number AS CHAR))) = LOWER(%s)
                       OR LOWER(name) LIKE LOWER(%s)
                """
                cursor.execute(query, (search_query, f"%{search_query}%"))
                students = cursor.fetchall()

                if not students:
                    st.warning("No student found matching query.")
                else:
                    for s_id, name, roll in students:
                        with st.container(border=True):
                            c1, c2 = st.columns(2)
                            c1.subheader(f"👤 {name}")
                            c2.markdown(f"**Roll Number:** `{roll}`")

                            st.divider()

                            # Attendance Stats
                            cursor.execute(
                                "SELECT status FROM attendance WHERE student_id"
                                " = %s",
                                (s_id,),
                            )
                            att = cursor.fetchall()
                            if att:
                                presents = sum(
                                    1
                                    for status in att
                                    if status[0] == "Present"
                                )
                                pct = (presents / len(att)) * 100
                                c1.metric(
                                    "Attendance Rate",
                                    f"{pct:.1f}%",
                                    f"{presents}/{len(att)} days",
                                )
                            else:
                                c1.info("No attendance records.")

                            # Marks Table
                            marks_q = """
                                SELECT a.title, s.subject_name, m.marks_obtained, a.total_marks
                                FROM student_marks m
                                JOIN assessments a ON m.assessment_id = a.assessment_id
                                JOIN subjects s ON a.subject_id = s.subject_id
                                WHERE m.student_id = %s
                            """
                            cursor.execute(marks_q, (s_id,))
                            marks = cursor.fetchall()
                            if marks:
                                df_marks = pd.DataFrame(
                                    marks,
                                    columns=[
                                        "Assessment",
                                        "Subject",
                                        "Marks Scored",
                                        "Total Marks",
                                    ],
                                )
                                c2.dataframe(
                                    df_marks,
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            else:
                                c2.info("No assessment marks recorded.")
                cursor.close()
                conn.close()

    # PAGE: MARK ATTENDANCE
    elif choice == "📅 Mark Attendance":
        st.title("📅 Mark Attendance")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT subject_id, subject_name FROM subjects")
            subjects = cursor.fetchall()

            cursor.execute(
                "SELECT student_id, name, roll_number FROM students"
            )
            students = cursor.fetchall()

            if not subjects or not students:
                st.warning(
                    "Please ensure subjects and students exist in the system."
                )
            else:
                col1, col2 = st.columns(2)
                subj_dict = {f"{s[1]} (ID: {s[0]})": s[0] for s in subjects}
                selected_subj_str = col1.selectbox(
                    "Select Subject", list(subj_dict.keys())
                )
                att_date = col2.date_input("Attendance Date", date.today())

                st.divider()

                # Build Editable DataFrame
                df_roster = pd.DataFrame(
                    students, columns=["Student ID", "Name", "Roll Number"]
                )
                df_roster["Status"] = "Present"

                edited_df = st.data_editor(
                    df_roster[["Student ID", "Name", "Roll Number", "Status"]],
                    column_config={
                        "Student ID": st.column_config.NumberColumn(
                            disabled=True
                        ),
                        "Name": st.column_config.TextColumn(disabled=True),
                        "Roll Number": st.column_config.TextColumn(
                            disabled=True
                        ),
                        "Status": st.column_config.SelectboxColumn(
                            "Status",
                            options=["Present", "Absent"],
                            required=True,
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

                if st.button(
                    "Save Attendance", type="primary", use_container_width=True
                ):
                    sub_id = subj_dict[selected_subj_str]
                    formatted_date = att_date.strftime("%Y-%m-%d")

                    for _, row in edited_df.iterrows():
                        cursor.execute(
                            """
                            INSERT INTO attendance (student_id, subject_id, date, status)
                            VALUES (%s, %s, %s, %s)
                        """,
                            (
                                int(row["Student ID"]),
                                sub_id,
                                formatted_date,
                                row["Status"],
                            ),
                        )
                    conn.commit()
                    st.success("✅ Attendance saved successfully!")

            cursor.close()
            conn.close()

    # PAGE: VIEW REPORTS
    elif choice == "📊 View Reports":
        st.title("📊 Class Performance & Reports")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT student_id, name, roll_number FROM students"
            )
            students = cursor.fetchall()

            if not students:
                st.info("No students registered.")
            else:
                for s_id, name, roll in students:
                    with st.expander(f"👤 {name} (Roll No: {roll})"):
                        cursor.execute(
                            "SELECT status FROM attendance WHERE student_id ="
                            " %s",
                            (s_id,),
                        )
                        att = cursor.fetchall()
                        if att:
                            presents = sum(
                                1 for status in att if status[0] == "Present"
                            )
                            rate = presents / len(att)
                            st.progress(
                                rate,
                                text=f"Attendance Rate: {rate * 100:.1f}%",
                            )

                        marks_q = """
                            SELECT a.title, m.marks_obtained, a.total_marks
                            FROM student_marks m
                            JOIN assessments a ON m.assessment_id = a.assessment_id
                            WHERE m.student_id = %s
                        """
                        cursor.execute(marks_q, (s_id,))
                        marks = cursor.fetchall()
                        if marks:
                            df_m = pd.DataFrame(
                                marks,
                                columns=["Assessment", "Scored", "Total Marks"],
                            )
                            st.dataframe(
                                df_m, use_container_width=True, hide_index=True
                            )
                        else:
                            st.caption("No marks recorded.")
            cursor.close()
            conn.close()

    # PAGE: RECORD MARKS
    elif choice == "💯 Record Marks":
        st.title("💯 Record Assessment Marks")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.assessment_id, a.title, a.type, a.total_marks, s.subject_name
                FROM assessments a
                JOIN subjects s ON a.subject_id = s.subject_id
            """)
            assessments = cursor.fetchall()
            cursor.execute(
                "SELECT student_id, name, roll_number FROM students"
            )
            students = cursor.fetchall()

            if not assessments or not students:
                st.warning("Please create assessments and students first.")
            else:
                ass_dict = {
                    f"[{a[2].upper()}] {a[1]} ({a[4]}) - Max: {a[3]}": (
                        a[0],
                        a[3],
                    )
                    for a in assessments
                }
                selected_ass_str = st.selectbox(
                    "Select Assessment", list(ass_dict.keys())
                )
                selected_ass_id, total_marks = ass_dict[selected_ass_str]

                st.divider()

                # Build Interactive Data Editor for Batch Entry
                df_marks_entry = pd.DataFrame(
                    students, columns=["Student ID", "Name", "Roll Number"]
                )
                df_marks_entry["Marks Obtained"] = 0

                edited_marks_df = st.data_editor(
                    df_marks_entry[
                        ["Student ID", "Name", "Roll Number", "Marks Obtained"]
                    ],
                    column_config={
                        "Student ID": st.column_config.NumberColumn(
                            disabled=True
                        ),
                        "Name": st.column_config.TextColumn(disabled=True),
                        "Roll Number": st.column_config.TextColumn(
                            disabled=True
                        ),
                        "Marks Obtained": st.column_config.NumberColumn(
                            "Marks Obtained",
                            min_value=0,
                            max_value=total_marks,
                            step=1,
                            required=True,
                        ),
                    },
                    hide_index=True,
                    use_container_width=True,
                )

                if st.button(
                    "Save Marks", type="primary", use_container_width=True
                ):
                    for _, row in edited_marks_df.iterrows():
                        s_id = int(row["Student ID"])
                        obtained = int(row["Marks Obtained"])

                        cursor.execute(
                            "SELECT mark_id FROM student_marks WHERE student_id"
                            " = %s AND assessment_id = %s",
                            (s_id, selected_ass_id),
                        )
                        existing = cursor.fetchone()

                        if existing:
                            cursor.execute(
                                "UPDATE student_marks SET marks_obtained = %s"
                                " WHERE mark_id = %s",
                                (obtained, existing[0]),
                            )
                        else:
                            cursor.execute(
                                "INSERT INTO student_marks (student_id,"
                                " assessment_id, marks_obtained) VALUES (%s,"
                                " %s, %s)",
                                (s_id, selected_ass_id, obtained),
                            )
                    conn.commit()
                    st.success("✅ Marks recorded successfully!")
            cursor.close()
            conn.close()

    # PAGE: CREATE TEST
    elif choice == "📝 Create Test/Assignment":
        st.title("📝 Create Test or Assignment")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT subject_id, subject_name FROM subjects")
            subjects = cursor.fetchall()

            if not subjects:
                st.warning("Please add subjects first.")
            else:
                with st.form("create_assessment_form"):
                    subj_dict = {
                        f"{name} (ID: {sid})": sid for sid, name in subjects
                    }
                    selected_subj = st.selectbox(
                        "Select Subject", list(subj_dict.keys())
                    )
                    title = st.text_input(
                        "Title", placeholder="e.g. Midterm Exam"
                    ).strip()
                    type_ = st.selectbox("Type", ["Test", "Assignment"])
                    c1, c2 = st.columns(2)
                    due_date = c1.date_input("Due Date", min_value=date.today())
                    total_marks = c2.number_input(
                        "Total Marks", min_value=1, value=100
                    )

                    if st.form_submit_button("Create Assessment"):
                        if not title:
                            st.error("Please enter a title.")
                        else:
                            cursor.execute(
                                "INSERT INTO assessments (subject_id, title,"
                                " type, due_date, total_marks) VALUES (%s, %s,"
                                " %s, %s, %s)",
                                (
                                    subj_dict[selected_subj],
                                    title,
                                    type_,
                                    due_date.strftime("%Y-%m-%d"),
                                    total_marks,
                                ),
                            )
                            conn.commit()
                            st.success("✅ Assessment created!")
            cursor.close()
            conn.close()

    # PAGE: ADD STUDENT
    elif choice == "➕ Add Student (Admin)":
        st.title("➕ Add New Student")
        if st.session_state["role"] != "admin":
            st.error("🔒 Admin permission required.")
        else:
            with st.form("add_student_form"):
                name = st.text_input("Student Name").strip()
                roll = st.text_input("Roll Number").strip()
                if st.form_submit_button("Save Student"):
                    if not name or not roll:
                        st.error("Please fill in both Name and Roll Number.")
                    else:
                        conn = get_db_connection()
                        if conn:
                            cursor = conn.cursor()
                            try:
                                cursor.execute(
                                    "INSERT INTO students (name, roll_number)"
                                    " VALUES (%s, %s)",
                                    (name, roll),
                                )
                                conn.commit()
                                st.success(f"✅ Student '{name}' added!")
                            except mysql.connector.Error as err:
                                if err.errno == 1062:
                                    st.error(
                                        "A student with this Roll Number"
                                        " already exists."
                                    )
                                else:
                                    st.error(f"Error: {err}")
                            finally:
                                cursor.close()
                                conn.close()

    # PAGE: ADD SUBJECT
    elif choice == "📘 Add Subject (Admin)":
        st.title("📘 Add New Subject")
        if st.session_state["role"] != "admin":
            st.error("🔒 Admin permission required.")
        else:
            with st.form("add_subject_form"):
                subject_name = st.text_input("Subject Name").strip()
                if st.form_submit_button("Save Subject"):
                    if not subject_name:
                        st.error("Please enter a subject name.")
                    else:
                        conn = get_db_connection()
                        if conn:
                            cursor = conn.cursor()
                            try:
                                cursor.execute(
                                    "INSERT INTO subjects (subject_name)"
                                    " VALUES (%s)",
                                    (subject_name,),
                                )
                                conn.commit()
                                st.success(
                                    f"✅ Subject '{subject_name}' added!"
                                )
                            except mysql.connector.Error as err:
                                if err.errno == 1062:
                                    st.error(
                                        "This subject name already exists."
                                    )
                                else:
                                    st.error(f"Error: {err}")
                            finally:
                                cursor.close()
                                conn.close()

    # PAGE: DELETE STUDENT
    elif choice == "❌ Delete Student (Admin)":
        st.title("🗑️ Delete Student")
        if st.session_state["role"] != "admin":
            st.error("🔒 Admin permission required.")
        else:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT student_id, name, roll_number FROM students"
                )
                students = cursor.fetchall()
                if students:
                    stud_dict = {
                        f"{name} (Roll: {roll})": sid
                        for sid, name, roll in students
                    }
                    selected_stud = st.selectbox(
                        "Select Student", list(stud_dict.keys())
                    )
                    confirm = st.checkbox("Confirm Permanent Deletion")
                    if st.button("Delete Student", type="primary"):
                        if confirm:
                            sid_to_delete = stud_dict[selected_stud]
                            cursor.execute(
                                "DELETE FROM students WHERE student_id = %s",
                                (sid_to_delete,),
                            )
                            conn.commit()
                            st.success("Deleted successfully!")
                            st.rerun()
                        else:
                            st.warning(
                                "Please check the confirmation box first."
                            )
                else:
                    st.info("No students found.")
                cursor.close()
                conn.close()

    # PAGE: DELETE SUBJECT
    elif choice == "🗑️ Delete Subject (Admin)":
        st.title("🗑️ Delete Subject")
        if st.session_state["role"] != "admin":
            st.error("🔒 Admin permission required.")
        else:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT subject_id, subject_name FROM subjects")
                subjects = cursor.fetchall()
                if subjects:
                    subj_dict = {
                        f"{name} (ID: {sid})": sid for sid, name in subjects
                    }
                    selected_subj = st.selectbox(
                        "Select Subject", list(subj_dict.keys())
                    )
                    confirm = st.checkbox("Confirm Deletion")
                    if st.button("Delete Subject", type="primary"):
                        if confirm:
                            sub_id_to_delete = subj_dict[selected_subj]
                            cursor.execute(
                                "DELETE FROM subjects WHERE subject_id = %s",
                                (sub_id_to_delete,),
                            )
                            conn.commit()
                            st.success("Deleted successfully!")
                            st.rerun()
                        else:
                            st.warning(
                                "Please check the confirmation box first."
                            )
                else:
                    st.info("No subjects found.")
                cursor.close()
                conn.close()

    # PAGE: DELETE TEST
    elif choice == "🗑️ Delete Test/Assignment":
        st.title("🗑️ Delete Assessment")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.assessment_id, a.title, a.type, s.subject_name 
                FROM assessments a 
                JOIN subjects s ON a.subject_id = s.subject_id
            """)
            assessments = cursor.fetchall()
            if assessments:
                ass_dict = {
                    f"[{a[2].upper()}] {a[1]} - {a[3]}": a[0]
                    for a in assessments
                }
                selected_ass = st.selectbox(
                    "Select Assessment", list(ass_dict.keys())
                )
                if st.button("Delete Assessment", type="primary"):
                    cursor.execute(
                        "DELETE FROM assessments WHERE assessment_id = %s",
                        (ass_dict[selected_ass],),
                    )
                    conn.commit()
                    st.success("Deleted successfully!")
                    st.rerun()
            else:
                st.info("No assessments found.")
            cursor.close()
            conn.close()

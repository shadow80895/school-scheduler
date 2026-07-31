from datetime import date
import hashlib
import mysql.connector
import streamlit as st

st.set_page_config(
    page_title="School Management System", page_icon="🎓", layout="wide"
)


# --- HELPERS ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# --- DATABASE CONNECTION ---
def get_db_connection():
    try:
        cfg = st.secrets["mysql"]
        return mysql.connector.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            connection_timeout=5,
        )
    except Exception as err:
        st.error(f"Error connecting to cloud database: {err}")
        return None


# --- INITIAL SETUP ---
def setup_database():
    conn = get_db_connection()
    if not conn:
        return

    tables = [
        """
        CREATE TABLE IF NOT EXISTS admin (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS students (
            student_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            roll_number VARCHAR(100) UNIQUE NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id INT AUTO_INCREMENT PRIMARY KEY,
            subject_name VARCHAR(255) NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS assessments (
            assessment_id INT AUTO_INCREMENT PRIMARY KEY,
            subject_id INT,
            title VARCHAR(255) NOT NULL,
            type VARCHAR(50),
            due_date DATE,
            total_marks INT,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS student_marks (
            mark_id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            assessment_id INT,
            marks_obtained INT,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id) ON DELETE CASCADE,
            UNIQUE KEY unique_student_assessment (student_id, assessment_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            subject_id INT,
            date DATE,
            status VARCHAR(20),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
            UNIQUE KEY unique_daily_attendance (student_id, subject_id, date)
        );
        """,
    ]

    try:
        with conn.cursor() as cursor:
            for query in tables:
                cursor.execute(query)

            # Insert default admin with hashed password if not present
            default_pass_hash = hash_password("root")
            cursor.execute(
                """
                INSERT INTO admin (username, password) 
                VALUES ('admin', %s) 
                ON DUPLICATE KEY UPDATE username=username
            """,
                (default_pass_hash,),
            )
        conn.commit()
    except mysql.connector.Error as err:
        st.error(f"Error setting up database: {err}")
    finally:
        conn.close()


# Run DB initialization once per app start
if "db_initialized" not in st.session_state:
    setup_database()
    st.session_state["db_initialized"] = True

# --- AUTHENTICATION & SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None


def verify_admin(username, password):
    conn = get_db_connection()
    if not conn:
        return False
    hashed = hash_password(password)
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM admin WHERE username = %s AND password = %s",
            (username, hashed),
        )
        user = cursor.fetchone()
    conn.close()
    return user is not None


# --- APP ROUTING ---
st.title("🎓 School Management System")

if not st.session_state["logged_in"]:
    st.subheader("Select Login Type")
    login_type = st.radio("Choose Role:", ["Teacher", "Head Teacher (Admin)"])

    if login_type == "Teacher":
        if st.button("Log In as Teacher"):
            st.session_state["logged_in"] = True
            st.session_state["role"] = "teacher"
            st.rerun()

    elif login_type == "Head Teacher (Admin)":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Log In as Admin"):
            if verify_admin(username, password):
                st.session_state["logged_in"] = True
                st.session_state["role"] = "admin"
                st.success("Welcome Head Teacher!")
                st.rerun()
            else:
                st.error("Invalid Username or Password!")

else:
    st.sidebar.title(f"Logged in as: {st.session_state['role'].upper()}")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["role"] = None
        st.rerun()

    menu = [
        "Dashboard & Reminders",
        "Search Student by Roll",
        "View Reports",
        "Mark Attendance",
        "Record Assessment Marks",
        "Create Test / Assignment",
        "Delete / Undo Test or Assignment",
        "Add Student (Admin)",
        "Delete Student (Admin)",
        "Add Subject (Admin)",
        "Delete Subject (Admin)",
    ]
    choice = st.sidebar.selectbox("Navigation", menu)

    # 1. Dashboard
    if choice == "Dashboard & Reminders":
        st.header("🔔 Upcoming Assignments & Tests")
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
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
            conn.close()

            if reminders:
                for title, type_, due, subject in reminders:
                    st.info(
                        f"**[{type_.upper()}]** {title} ({subject}) — **Due:** {due}"
                    )
            else:
                st.success("No upcoming tests or assignments!")

    # 2. Search Student
    elif choice == "Search Student by Roll":
        st.header("🔍 Search Student")
        search_query = st.text_input("Enter Roll Number or Name")
        if st.button("Search") and search_query:
            conn = get_db_connection()
            if conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT student_id, name, roll_number 
                        FROM students 
                        WHERE roll_number = %s OR name LIKE %s
                    """
                    cursor.execute(query, (search_query, f"%{search_query}%"))
                    students = cursor.fetchall()

                    if not students:
                        st.warning("No student found matching query.")
                    else:
                        for s_id, name, roll in students:
                            st.subheader(f"📌 {name} (Roll No: {roll})")

                            cursor.execute(
                                "SELECT status FROM attendance WHERE student_id = %s",
                                (s_id,),
                            )
                            att = cursor.fetchall()
                            if att:
                                presents = sum(
                                    1 for status in att if status[0] == "Present"
                                )
                                pct = (presents / len(att)) * 100
                                st.write(
                                    f"**Attendance:** {presents}/{len(att)} days ({pct:.1f}%)"
                                )
                            else:
                                st.write("**Attendance:** No records found.")

                            marks_q = """
                                SELECT a.title, m.marks_obtained, a.total_marks
                                FROM student_marks m
                                JOIN assessments a ON m.assessment_id = a.assessment_id
                                WHERE m.student_id = %s
                            """
                            cursor.execute(marks_q, (s_id,))
                            marks = cursor.fetchall()
                            if marks:
                                st.write("**Marks:**")
                                for title, score, total in marks:
                                    st.write(f"- {title}: {score}/{total}")
                            else:
                                st.write("**Marks:** No marks recorded.")
                conn.close()

    # 4. Mark Attendance (Updated with UPSERT)
    elif choice == "Mark Attendance":
        st.header("📅 Mark Attendance")
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT subject_id, subject_name FROM subjects")
                subjects = cursor.fetchall()
                cursor.execute("SELECT student_id, name, roll_number FROM students")
                students = cursor.fetchall()
            conn.close()

            if not subjects:
                st.warning("Please add at least one subject first.")
            elif not students:
                st.warning("Please add students first.")
            else:
                subj_dict = {f"{s[1]} (ID: {s[0]})": s[0] for s in subjects}
                selected_subj_str = st.selectbox("Select Subject", list(subj_dict.keys()))
                selected_subj_id = subj_dict[selected_subj_str]
                att_date = st.date_input("Attendance Date", date.today())

                st.subheader("Student List")
                with st.form("attendance_form"):
                    attendance_status = {}
                    for s_id, name, roll in students:
                        status = st.radio(
                            f"{name} (Roll: {roll})",
                            ["Present", "Absent"],
                            key=f"att_{s_id}",
                            horizontal=True,
                        )
                        attendance_status[s_id] = status

                    submitted = st.form_submit_button("Save Attendance")

                if submitted:
                    conn = get_db_connection()
                    if conn:
                        try:
                            with conn.cursor() as cursor:
                                for s_id, status in attendance_status.items():
                                    cursor.execute(
                                        """
                                        INSERT INTO attendance (student_id, subject_id, date, status)
                                        VALUES (%s, %s, %s, %s)
                                        ON DUPLICATE KEY UPDATE status = VALUES(status)
                                        """,
                                        (
                                            s_id,
                                            selected_subj_id,
                                            att_date.strftime("%Y-%m-%d"),
                                            status,
                                        ),
                                    )
                            conn.commit()
                            st.success("Attendance saved successfully!")
                        except mysql.connector.Error as err:
                            st.error(f"Error saving attendance: {err}")
                        finally:
                            conn.close()

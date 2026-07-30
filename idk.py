from datetime import date
import mysql.connector
import streamlit as st
#password
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="mysql-327a1c97-school-scheduler.j.aivencloud.com",
            port=24033,
            user="avnadmin",
            password="AVNS_QcMH792wuF0McXRXNc1", 
            database="defaultdb",
        )
        return connection
    except mysql.connector.Error as err:
        st.error(f"Error connecting to cloud database: {err}")
        return None


def setup_default_admin():
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
        if cursor.fetchone():
            cursor.execute(
                "UPDATE admin SET password = 'root' WHERE username = 'admin'"
            )
        else:
            cursor.execute(
                "INSERT INTO admin (username, password) VALUES ('admin',"
                " 'root')"
            )
        conn.commit()
    except mysql.connector.Error as err:
        st.error(f"Error setting up admin: {err}")
    finally:
        cursor.close()
        conn.close()


setup_default_admin()

#login steup
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None


def verify_admin(username, password):
    conn = get_db_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM admin WHERE username = %s AND password = %s",
        (username, password),
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user is not None

st.set_page_config(
    page_title="School Management System", page_icon="🎓", layout="wide"
)
st.title("🎓 School Management System")

# login View
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

#maindisplay--
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

#reminders
    if choice == "Dashboard & Reminders":
        st.header("🔔 Upcoming Assignments & Tests")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
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
                for title, type_, due, subject in reminders:
                    st.info(
                        f"**[{type_.upper()}]** {title} ({subject}) — **Due:**"
                        f" {due}"
                    )
            else:
                st.success("No upcoming tests or assignments!")
            cursor.close()
            conn.close()

#rollno
    elif choice == "Search Student by Roll":
        st.header("🔍 Search Student")
        search_query = st.text_input("Enter Roll Number or Name")
        if st.button("Search"):
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                query = """
                    SELECT student_id, name, roll_number 
                    FROM students 
                    WHERE LOWER(TRIM(CAST(roll_number AS CHAR))) = LOWER(TRIM(%s))
                       OR LOWER(name) LIKE LOWER(%s)
                """
                cursor.execute(query, (search_query, f"%{search_query}%"))
                students = cursor.fetchall()

                if not students:
                    st.warning("No student found matching query.")
                else:
                    for s_id, name, roll in students:
                        st.subheader(f"📌 {name} (Roll No: {roll})")

                        # attendance
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
                            pct = (presents / len(att)) * 100
                            st.write(
                                f"**Attendance:** {presents}/{len(att)} days"
                                f" ({pct:.1f}%)"
                            )
                        else:
                            st.write("**Attendance:** No records found.")

                        # marksss
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
                cursor.close()
                conn.close()

    #  VIEW REPORTS
    elif choice == "View Reports":
        st.header("📊 Student Performance Reports")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT student_id, name, roll_number FROM students"
            )
            students = cursor.fetchall()
            for s_id, name, roll in students:
                with st.expander(f"Student: {name} | Roll No: {roll}"):
                    # attendance
                    cursor.execute(
                        "SELECT status FROM attendance WHERE student_id = %s",
                        (s_id,),
                    )
                    att = cursor.fetchall()
                    if att:
                        presents = sum(
                            1 for status in att if status[0] == "Present"
                        )
                        st.write(
                            f"**Attendance:** {presents}/{len(att)} days"
                            f" ({(presents/len(att))*100:.1f}%)"
                        )


                    marks_q = """
                        SELECT a.title, m.marks_obtained, a.total_marks
                        FROM student_marks m
                        JOIN assessments a ON m.assessment_id = a.assessment_id
                        WHERE m.student_id = %s
                    """
                    cursor.execute(marks_q, (s_id,))
                    marks = cursor.fetchall()
                    for title, score, total in marks:
                        st.write(f"- {title}: **{score}/{total}**")
            cursor.close()
            conn.close()

#assignments
    elif choice == "Create Test / Assignment":
        st.header("📝 Create Test or Assignment")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT subject_id, subject_name FROM subjects")
            subjects = cursor.fetchall()
            if not subjects:
                st.warning("Please add subjects first.")
            else:
                subj_dict = {
                    f"{name} (ID: {sid})": sid for sid, name in subjects
                }
                selected_subj = st.selectbox(
                    "Select Subject", list(subj_dict.keys())
                )
                title = st.text_input("Title (e.g. Unit Test 1)")
                type_ = st.selectbox("Type", ["Test", "Assignment"])
                due_date = st.date_input("Due Date")
                total_marks = st.number_input(
                    "Total Marks", min_value=1, value=100
                )

                if st.button("Create Assessment"):
                    cursor.execute(
                        "INSERT INTO assessments (subject_id, title, type,"
                        " due_date, total_marks) VALUES (%s, %s, %s, %s, %s)",
                        (
                            subj_dict[selected_subj],
                            title,
                            type_,
                            due_date.strftime("%Y-%m-%d"),
                            total_marks,
                        ),
                    )
                    conn.commit()
                    st.success("Assessment created successfully!")
            cursor.close()
            conn.close()

#del assignments
    elif choice == "Delete / Undo Test or Assignment":
        st.header("🗑️ Delete / Undo Test or Assignment")
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            query = """
                SELECT a.assessment_id, a.title, a.type, s.subject_name 
                FROM assessments a 
                JOIN subjects s ON a.subject_id = s.subject_id
            """
            cursor.execute(query)
            assessments = cursor.fetchall()

            if not assessments:
                st.info("No assessments found in the system.")
            else:
                ass_dict = {
                    f"[{a_type.upper()}] {title} - {subj_name} (ID: {aid})": aid
                    for aid, title, a_type, subj_name in assessments
                }
                selected_ass = st.selectbox(
                    "Select Test/Assignment to Delete", list(ass_dict.keys())
                )

                if st.button("Delete Assessment", type="primary"):
                    aid_to_delete = ass_dict[selected_ass]
                    try:
                        
                        cursor.execute(
                            "DELETE FROM student_marks WHERE assessment_id ="
                            " %s",
                            (aid_to_delete,),
                        )
                   
                        cursor.execute(
                            "DELETE FROM assessments WHERE assessment_id = %s",
                            (aid_to_delete,),
                        )
                        conn.commit()
                        st.success(
                            "Assessment and its marks deleted successfully!"
                        )
                        st.rerun()
                    except mysql.connector.Error as err:
                        st.error(f"Error deleting assessment: {err}")
            cursor.close()
            conn.close()

#admin only
    elif choice == "Add Student (Admin)":
        st.header("➕ Add New Student")
        if st.session_state["role"] != "admin":
            st.error("🔒 Head Teacher / Admin access required!")
        else:
            name = st.text_input("Student Name")
            roll = st.text_input("Roll Number")
            if st.button("Save Student"):
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO students (name, roll_number) VALUES"
                            " (%s, %s)",
                            (name, roll),
                        )
                        conn.commit()
                        st.success(f"Student '{name}' added successfully!")
                    except mysql.connector.Error as err:
                        st.error(f"Error: {err}")
                    finally:
                        cursor.close()
                        conn.close()

#admin only 
    elif choice == "Delete Student (Admin)":
        st.header("🗑️ Delete Student")
        if st.session_state["role"] != "admin":
            st.error("🔒 Head Teacher / Admin access required!")
        else:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT student_id, name, roll_number FROM students"
                )
                students = cursor.fetchall()

                if not students:
                    st.info("No students found in the database.")
                else:
                    stud_dict = {
                        f"{name} (Roll: {roll})": sid
                        for sid, name, roll in students
                    }
                    selected_stud = st.selectbox(
                        "Select Student to Delete", list(stud_dict.keys())
                    )

                    confirm = st.checkbox(
                        "I confirm I want to permanently delete this student"
                    )
                    if st.button("Delete Student", type="primary"):
                        if confirm:
                            sid_to_delete = stud_dict[selected_stud]
                            try:
                                cursor.execute(
                                    "DELETE FROM attendance WHERE student_id ="
                                    " %s",
                                    (sid_to_delete,),
                                )
                                cursor.execute(
                                    "DELETE FROM student_marks WHERE student_id"
                                    " = %s",
                                    (sid_to_delete,),
                                )
                                cursor.execute(
                                    "DELETE FROM students WHERE student_id ="
                                    " %s",
                                    (sid_to_delete,),
                                )
                                conn.commit()
                                st.success(
                                    "Student records deleted successfully!"
                                )
                                st.rerun()
                            except mysql.connector.Error as err:
                                st.error(f"Error deleting student: {err}")
                        else:
                            st.warning(
                                "Please check the confirmation box first."
                            )
                cursor.close()
                conn.close()

#add subjects
    elif choice == "Add Subject (Admin)":
        st.header("📘 Add New Subject")
        if st.session_state["role"] != "admin":
            st.error("🔒 Head Teacher / Admin access required!")
        else:
            subject_name = st.text_input("Subject Name")
            if st.button("Save Subject"):
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO subjects (subject_name) VALUES (%s)",
                            (subject_name,),
                        )
                        conn.commit()
                        st.success(
                            f"Subject '{subject_name}' added successfully!"
                        )
                    except mysql.connector.Error as err:
                        st.error(f"Error: {err}")
                    finally:
                        cursor.close()
                        conn.close()

#del subjects
    elif choice == "Delete Subject (Admin)":
        st.header("🗑️ Delete Subject")
        if st.session_state["role"] != "admin":
            st.error("🔒 Head Teacher / Admin access required!")
        else:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT subject_id, subject_name FROM subjects"
                )
                subjects = cursor.fetchall()

                if not subjects:
                    st.info("No subjects found in the database.")
                else:
                    subj_dict = {
                        f"{name} (ID: {sid})": sid for sid, name in subjects
                    }
                    selected_subj = st.selectbox(
                        "Select Subject to Delete", list(subj_dict.keys())
                    )

                    confirm = st.checkbox(
                        "I confirm I want to delete this subject and"
                        " associated data"
                    )
                    if st.button("Delete Subject", type="primary"):
                        if confirm:
                            sub_id_to_delete = subj_dict[selected_subj]
                            try:
                                
                                cursor.execute(
                                    "SELECT assessment_id FROM assessments"
                                    " WHERE subject_id = %s",
                                    (sub_id_to_delete,),
                                )
                                ass_ids = [row[0] for row in cursor.fetchall()]

                                
                                for aid in ass_ids:
                                    cursor.execute(
                                        "DELETE FROM student_marks WHERE"
                                        " assessment_id = %s",
                                        (aid,),
                                    )

                                
                                cursor.execute(
                                    "DELETE FROM assessments WHERE subject_id ="
                                    " %s",
                                    (sub_id_to_delete,),
                                )
                                cursor.execute(
                                    "DELETE FROM attendance WHERE subject_id ="
                                    " %s",
                                    (sub_id_to_delete,),
                                )
                                cursor.execute(
                                    "DELETE FROM subjects WHERE subject_id ="
                                    " %s",
                                    (sub_id_to_delete,),
                                )
                                conn.commit()
                                st.success("Subject deleted successfully!")
                                st.rerun()
                            except mysql.connector.Error as err:
                                st.error(f"Error deleting subject: {err}")
                        else:
                            st.warning(
                                "Please check the confirmation box first."
                            )
                cursor.close()
                conn.close()

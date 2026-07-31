# PAGE: DELETE TEST
    elif choice == "🗑️ Delete Test/Assignment":
        st.title("🗑️ Delete Assessment")
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT a.assessment_id, a.title, a.type, s.subject_name 
                    FROM assessments a
                    JOIN subjects s ON a.subject_id = s.subject_id
                """)
                assessments = cursor.fetchall()
                
                if assessments:
                    ass_dict = {
                        f"[{a[2].upper()}] {a[1]} ({a[3]})": a[0]
                        for a in assessments
                    }
                    selected_ass = st.selectbox(
                        "Select Assessment to Delete", list(ass_dict.keys())
                    )
                    confirm = st.checkbox("Confirm Assessment Deletion")
                    
                    if st.button("Delete Assessment", type="primary"):
                        if confirm:
                            ass_id_to_delete = ass_dict[selected_ass]
                            cursor.execute(
                                "DELETE FROM assessments WHERE assessment_id = %s",
                                (ass_id_to_delete,),
                            )
                            conn.commit()
                            st.success("✅ Assessment deleted successfully!")
                            st.rerun()
                        else:
                            st.warning("Please check the confirmation box first.")
                else:
                    st.info("No assessments found.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
            finally:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                conn.close()

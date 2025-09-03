import streamlit as st
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
import os
from dotenv import load_dotenv

def edit_delete_book():
    # --- Load AWS credentials ---
    load_dotenv()
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "ap-south-1")

    # --- Check user login ---
    if "user_id" not in st.session_state:
        st.error("Please login first.")
        return

    user_id = st.session_state["user_id"]

    # --- Connect to DynamoDB ---
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    table = dynamodb.Table("BooksTable")

    # --- Get all books for user ---
    response = table.query(KeyConditionExpression=Key('user_id').eq(user_id))
    items = response.get("Items", [])

    # --- Filter books ---
    books = [b for b in items if not b.get("archived", False)]
    archived_books = [b for b in items if b.get("archived", False)]

    # --- Helper functions ---
    def calculate_progress(pages_read, total_pages):
        return (pages_read / total_pages) * 100 if total_pages else 0

    def is_overdue(due_date_str, status):
        if status == "Completed":
            return False
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            return datetime.today().date() > due_date
        except:
            return False

    st.title("🛠️ Edit and Delete Books")

    # --- Mark overdue and sort ---
    for book in books:
        book["overdue"] = is_overdue(book.get("due_date", ""), book.get("status", ""))
    books = sorted(books, key=lambda b: b["overdue"], reverse=True)

    status_options = ["To Read", "Reading", "Completed"]

    # --- Display books ---
    if books:
        for book in books:
            title = f"{book['title']}"
            if book["overdue"]:
                title += "⏰❗OVERDUE"

            with st.expander(title):
                st.write(f"**✍️ Author:** {book.get('author', 'N/A')} | **Genre:** {book.get('genre', 'N/A')}")

                new_status = st.selectbox("📌 Status", status_options,
                                          index=status_options.index(book.get("status", "To Read")),
                                          key=f"status_{book['book_id']}")

                total_pages = int(st.number_input("Total Pages", min_value=1,
                                                  value=max(1, int(book.get("total_pages", 1))),
                                                  step=1, key=f"tp_{book['book_id']}"))

                pages_read = int(st.number_input("Pages Read", min_value=0, max_value=total_pages,
                                                 value=min(int(book.get("pages_read", 0)), total_pages),
                                                 step=1, key=f"pr_{book['book_id']}"))

                try:
                    due_date = datetime.strptime(book.get("due_date", ""), "%Y-%m-%d").date()
                except:
                    due_date = datetime.today().date()

                new_due_date = st.date_input("Due Date", value=due_date, key=f"due_{book['book_id']}")

                rating_value = book.get("rating")
                clean_rating = int(rating_value) if rating_value not in [None, ''] else 0

                new_rating = st.slider("⭐ Rating", min_value=0, max_value=5,
                                       value=clean_rating, key=f"rating_{book['book_id']}")

                progress = int(calculate_progress(pages_read, total_pages))
                st.progress(progress)
                st.caption(f"{progress}% completed")

                if new_status != "Completed" and new_due_date < datetime.today().date():
                    st.warning("This book is overdue!")

                if st.button("💾 Save Changes", key=f"save_{book['book_id']}"):
                    # --- Validation logic ---
                    if new_status == "Completed" and pages_read != total_pages:
                        st.warning("For 'Completed' status, Pages Read must equal Total Pages.")
                    elif new_status == "Reading" and not (0 < pages_read < total_pages):
                        st.warning("For 'Reading' status, Pages Read must be > 0 and < Total Pages.")
                    elif new_status == "To Read" and pages_read != 0:
                        st.warning("For 'To Read' status, Pages Read must be 0.")
                    else:
                        try:
                            table.update_item(
                                Key={'user_id': user_id, 'book_id': book['book_id']},
                                UpdateExpression="""
                                    SET #s = :s, pages_read = :pr, total_pages = :tp,
                                        due_date = :dd, rating = :rt
                                """,
                                ExpressionAttributeNames={'#s': 'status'},
                                ExpressionAttributeValues={
                                    ':s': new_status,
                                    ':pr': pages_read,
                                    ':tp': total_pages,
                                    ':dd': str(new_due_date),
                                    ':rt': new_rating
                                }
                            )
                            st.success("Book updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to update: {e}")

                if st.button("🗑️ Delete Book", key=f"del_{book['book_id']}"):
                    try:
                        table.delete_item(
                            Key={'user_id': user_id, 'book_id': book['book_id']}
                        )
                        st.success("Book deleted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {e}")

                if new_status == "Completed" and not book.get("archived", False):
                    if st.button("🗃️ Archive Book", key=f"archive_{book['book_id']}"):
                        try:
                            table.update_item(
                                Key={'user_id': user_id, 'book_id': book['book_id']},
                                UpdateExpression="SET archived = :a, archived_date = :d",
                                ExpressionAttributeValues={
                                    ':a': True,
                                    ':d': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }
                            )
                            st.success("Book archived successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error archiving book: {e}")
    else:
        st.info("📭 No active books found.")

    # --- Archived Books Section ---
    if archived_books:
        st.subheader("🗃️ Archived Books")
        show_archived = st.checkbox("View Archived Books", value=True)

        if show_archived:
            for book in archived_books:
                with st.expander(f"{book['title']} by {book['author']}"):
                    st.markdown(f"**Pages Read:** {book['pages_read']} / {book['total_pages']}")
                    st.markdown(f"**📌 Status:** {book['status']}")
                    st.markdown(f"**⏰ Due Date:** {book.get('due_date', 'N/A')}")

                    if st.button("Unarchive Book", key=f"unarchive_{book['book_id']}"):
                        try:
                            table.update_item(
                                Key={'user_id': user_id, 'book_id': book['book_id']},
                                UpdateExpression='REMOVE archived'
                            )
                            st.success("Book unarchived successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error unarchiving book: {e}")

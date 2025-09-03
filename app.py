import streamlit as st
from datetime import datetime
import database as db
import recommendations
import os
from dotenv import load_dotenv
import dashboard
import edit_delete


load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")


STATUS_OPTIONS = ["To Read", "Reading", "Completed"]
GENRE_OPTIONS = [
    'Adventure Fiction', 'Alternate History', 'Autobiography', 'Beat Literature',
    'Biography', 'Children\'s Literature', 'Comedy Fantasy', 'Coming of Age',
    'Crime Fiction', 'Cyberpunk', 'Dark Fantasy', 'Drama', 'Dystopian Fiction',
    'Fantasy', 'Gothic Fiction', 'Gothic Romance', 'Graphic Novel', 'Historical Fiction',
    'Historical Romance', 'History', 'Holocaust Memoir', 'Horror', 'Literary Fiction',
    'Magical Realism', 'Memoir', 'Paranormal Romance', 'Political Memoir',
    'Post-Apocalyptic Fiction', 'Psychological Thriller', 'Romance', 'Science Fiction',
    'Short Stories', 'Thriller', 'Urban Fantasy', 'Vampire Fiction', 'War Fiction',
    'War Journalism', 'War Memoir', 'Young Adult', 'Other'
]

# ------------------------Landing Page------------------------
def landing_page():
    st.markdown("""
        <style>
            .main-title {
                text-align: center;
                font-size: 48px;
                font-weight: bold;
                color: #2E8BC0;
                margin-top: 30px;
            }
            .sub-title {
                text-align: center;
                font-size: 28px;
                color: #333333;
            }
            .description {
                text-align: center;
                font-size: 18px;
                color: #555555;
                margin-bottom: 40px;
            }
        </style>
        <h1 class='main-title'>🤝 BookMate ✨</h1>
        <h3 class='sub-title'>🎉 Welcome to Your Personal Book Tracker !</h3>
        <p class='description'>Easily manage your reading list ✅, track progress 📈, and get book recommendations 🎯 — all in one place ☺️ !</p>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔐 Go to Login", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()
    with col2:
        if st.button("🆕 Register", use_container_width=True):
            st.session_state.page = "register"
            st.rerun()


# ------------------------Register Page------------------------
def register():
    st.title("Register")
    with st.form("register_form", clear_on_submit=True):
        name = st.text_input("👤 Enter Your Name")
        email = st.text_input("📧 Enter Your Email")
        password = st.text_input("🔑 Enter Password", type="password")
        submitted = st.form_submit_button("📋 Register")

        if submitted:
            if not (name and email and password):
                st.error("All fields are required.")
                return
            user = db.load_user(email)
            if user:
                st.error("User with this email already exists.")
            else:
                user_id = db.generate_next_user_id()
                db.save_user(user_id, name, email, password)
                st.session_state.update({
                    'user_id': user_id,
                    'email': email,
                    'user_email': email,
                    'logged_in': True,
                    'page': "main"
                })
                st.success(f"Registration successful!")
                st.rerun()


# ------------------------Login Page------------------------
def login_page():
    st.title("Login")
    with st.form("login_form"):
        email = st.text_input("📧 Email")
        password = st.text_input("🔑 Password", type="password")
        login_clicked = st.form_submit_button("🧑‍💻 Login")
        if login_clicked:
            user = db.load_user(email)
            if user and user.get('password') == password:
                st.session_state.update({
                    'user_id': user['user_id'],
                    'email': email,
                    'logged_in': True,
                    'page': "main"
                })
                st.session_state["user_email"] = email
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid email or password.")
    if st.button("📝 Go to Register"):
        st.session_state.page = "register"
        st.rerun()


# ------------------------Welcome Page------------------------
def welcome_page():
    st.markdown("""
        <style>
            .welcome-title {
                text-align: center;
                font-size: 40px;
                font-weight: bold;
                color: #2E8BC0;
                margin-top: 30px;
            }
            .tagline {
                text-align: center;
                font-size: 24px;
                color: #555;
                margin-bottom: 20px;
            }
            .description {
                text-align: center;
                font-size: 18px;
                color: #444;
                margin: 20px 0;
                padding: 0 50px;
            }
        </style>
        <h1 class='welcome-title'>Welcome to Book Buddy</h1>
        <h3 class='tagline'>“Your Gateway to an Enriched Reading Journey”</h3>
        <p class='description'>Explore your personal library, track your progress, and get recommendations tailored just for you. Let’s begin by adding your first book!</p>
    """, unsafe_allow_html=True)


# ------------------------Page Functions------------------------
def add_book():
    st.subheader("📚 Add New Book")

    with st.form("add_book_form", clear_on_submit=True):
        title = st.text_input("🏷️ Title").strip()
        author = st.text_input("✍️ Author").strip()

        col1, col2 = st.columns(2)
        with col1:
            total_pages = st.number_input("Total Pages", min_value=0, step=1)
        with col2:
            pages_read = st.number_input("📖 Pages Read", min_value=0, step=1)

        selected_genre = st.selectbox("🎭 Select Genre", GENRE_OPTIONS)
        if selected_genre == "Other":
            genre = st.text_input("Enter custom genre")
        else:
            genre = selected_genre
        status = st.selectbox("📌 Status", STATUS_OPTIONS)

        if status == "To Read":
            st.info("🚫 Rating is disabled for 'To Read' status.")
            rating = None
        else:
            rating = st.slider("⭐ Rating", 1, 5, 3)
        tags = st.text_input("Tags (comma separated)")


        submitted = st.form_submit_button("📚 Add Book")
        if submitted:
            if not title or not author:
                st.warning("Title and Author are required.")
                return
            if selected_genre == "Other" and not genre.strip():
                st.warning("Please enter a custom genre.")
                return

            user_id = st.session_state.user_id
            user_email = st.session_state.user_email
            existing_books = db.get_user_books(user_id).values()

            for book in existing_books:
                if book['title'].strip().lower() == title.strip().lower() and \
                        book['author'].strip().lower() == author.strip().lower():
                    st.error(f"This book ('{title}' by {author}) is already in your collection.")
                    return

            book_id = db.generate_next_book_id(user_id)
            book_data = {
                'user_id': user_id,
                'book_id': book_id,
                'title': title,
                'author': author,
                'genre': genre,
                'rating': rating if rating is not None else "",
                'status': status,
                'tags': [t.strip() for t in tags.split(',') if t.strip()],
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_pages': total_pages,
                'pages_read': pages_read,
                'email': user_email
            }

            db.save_book(book_data)
            st.success(f"Book '{title}' added")

            user_info = db.get_user(user_email)
            recommend = user_info.get('recommendation', [])

            if recommend:
                with st.expander("Recommended for You!", expanded=True):
                    for rec in recommend:
                        rec_title = rec.get("title", "Unknown")
                        rec_author = rec.get("author", "Unknown")
                        rec_genre = rec.get("genre", "Unknown")
                        st.markdown(f"- **{rec_title}** by *{rec_author}* ({rec_genre})")
            else:
                st.info("No recommendations found yet. Please add more books or wait a few seconds.")


def view_books():
    st.subheader("Your Book Collection")
    books = list(db.get_user_books(st.session_state.user_id).values())
    if not books:
        st.info("Your book collection is empty. Add a book to get started!")
        return

    num_columns = 3
    for i in range(0, len(books), num_columns):
        cols = st.columns(num_columns)
        row_books = books[i:i + num_columns]
        for j, book in enumerate(row_books):
            with cols[j]:
                with st.container():
                    st.markdown("### " + book.get('title', 'N/A'))
                    st.caption(f"by {book.get('author', 'N/A')}")
                    rating_str = str(book.get('rating', '0')).strip()
                    rating_val = int(rating_str) if rating_str.isdigit() else 0
                    st.write(f"**Rating:** {'⭐' * rating_val}")
                    st.write(f"**Status:** {book.get('status', 'N/A')}")

                    total_pages = int(book.get('total_pages', 0))
                    pages_read = int(book.get('pages_read', 0))

                    if total_pages > 0:
                        progress_value = pages_read / total_pages
                        st.progress(progress_value)
                        st.caption(f"{pages_read} / {total_pages} pages")
                    else:
                        st.write("Pages: N/A")

                    tags = book.get('tags', [])
                    if tags:
                        st.caption(" | ".join(tags))
                    st.markdown("---")


def search_books():
    st.subheader("🔍 Search Books by Tag")
    books = list(db.get_user_books(st.session_state.user_id).values())
    if not books:
        st.info("You have no books to search.")
        return
    tag = st.text_input("🏷️ Enter a tag to search for:").strip()
    if tag:
        found_books = [b for b in books if tag.lower() in [t.lower() for t in b.get('tags', [])]]
        if found_books:
            st.write(f"Found {len(found_books)} book(s) with the tag '{tag}':")
            for b in found_books:
                st.markdown(f"- **{b['title']}** by {b['author']}")
        else:
            st.warning(f"No books found with the tag '{tag}'.")

# --- NEW: Helper function to display query results ---
def display_query_results(books):
    if not books:
        st.info("No books found matching your criteria.")
        return

    st.success(f"Found {len(books)} book(s).")
    for book in books:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(book.get('title', 'N/A'))
                st.write(f"**Author:** {book.get('author', 'N/A')}")
                st.write(f"**Genre:** {book.get('genre', 'N/A')}")
            with col2:
                rating_str = str(book.get('rating', '')).strip()
                if rating_str and rating_str.isdigit():
                    rating_val = int(rating_str)
                    st.write(f"**Rating:** {'⭐' * rating_val}")
                else:
                    st.write("**Rating:** Not Rated")
                st.write(f"**Status:** {book.get('status', 'N/A')}")


# --- NEW: Page for querying books by different criteria ---
def query_page():
    user_id = st.session_state.user_id
    st.header("Query Your Library")
    st.info("Find books in your collection using different criteria. Note that these queries rely on database indexes for performance.")

    tab_status, tab_genre, tab_rating = st.tabs(["🗂️ By Status", "🎨 By Genre", "⭐ By Rating"])

    with tab_status:
        st.subheader("Find Books by Reading Status")
        selected_status = st.selectbox("Select a status", options=STATUS_OPTIONS, key="status_query")
        if st.button("🔍 Search by Status"):
            with st.spinner("Searching..."):
                results = db.query_books_by_status(selected_status,user_id)
                display_query_results(results)

    with tab_genre:
        st.subheader("Find Books by Genre")
        selected_genre = st.selectbox("Select a genre", options=GENRE_OPTIONS, key="genre_query")
        if st.button("Search by Genre"):
            with st.spinner("Searching..."):
                results = db.query_books_by_genre(selected_genre,user_id)
                display_query_results(results)

    with tab_rating:
        st.subheader("Find Books by Rating")
        comparison_map = {
            "Greater than or equal to": "gte",
            "Less than or equal to": "lte",
            "Equal to": "eq",
            "Greater than": "gt",
            "Less than": "lt"
        }
        comparison_label = st.selectbox("Select comparison type", options=list(comparison_map.keys()))
        rating_value = st.slider("Select rating", min_value=1, max_value=5, value=3)

        if st.button("Search by Rating"):
            with st.spinner("Searching..."):
                comparison_code = comparison_map[comparison_label]
                results = db.query_books_by_rating(rating_value, user_id,comparison=comparison_code)
                display_query_results(results)


# ------------------------Main Application------------------------
def main_app():
    st.sidebar.title(f"Welcome, {st.session_state.get('email', '').split('@')[0]}!")

    # --- UPDATED: Menu options ---
    menu_options = {
        "Dashboard": "📊",
        "View Books": "📚",
        "Add Book": "➕",
        "Edit and Delete Books": "✏️",
        "Search by Tag": "🏷️",
        "Query Library": "🗂️",
        "Recommendation": "💡",
        "Logout": "🚪"
    }

    def format_menu_option(option):
        return f"{menu_options[option]} {option}"

    if "menu_selection" not in st.session_state:
        st.session_state.menu_selection = "Dashboard"

    st.sidebar.radio(
        "Menu",
        options=list(menu_options.keys()),
        key="menu_selection",
        format_func=format_menu_option,
    )

    selection = st.session_state.menu_selection

    # --- UPDATED: Navigation logic ---
    if selection == "Dashboard":
        dashboard.dashboard_page()
    elif selection == "Recommendation":
        recommendations.show_recommendations_page()
    elif selection == "Add Book":
        add_book()
    elif selection == "Edit and Delete Books":
        edit_delete.edit_delete_book()
    elif selection == "View Books":
        view_books()
    elif selection == "Search by Tag":
        search_books()
    elif selection == "Query Library":
        query_page()
    elif selection == "Logout":
        for key in list(st.session_state.keys()):
            if key != 'page':
                del st.session_state[key]
        st.session_state.page = "landing"
        st.success("You have been logged out.")
        st.rerun()


# ---App Entry Point---
if "page" not in st.session_state:
    st.session_state.page = "landing"

if st.session_state.page == "landing":
    landing_page()
elif st.session_state.page == "login":
    login_page()
elif st.session_state.page == "register":
    register()
elif st.session_state.page == "main" and st.session_state.get("logged_in"):
    main_app()
else:
    st.session_state.page = "landing"
    st.rerun()

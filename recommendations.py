import streamlit as st
import requests
import json
import boto3
from decimal import Decimal
import os
from dotenv import load_dotenv
import database as db

load_dotenv()
LAMBDA_URL = os.getenv("LAMBDA_FUNCTION_URL")

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o) if o % 1 > 0 else int(o)
        return super(DecimalEncoder, self).default(o)

def get_reading_history(user_id):
    try:
        response = db.books_table.query(
            IndexName='user_id-index',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
        )
        items = response.get('Items', [])
        if not items:
            return None, f"No reading history found. Add books to get recommendations."
        return json.loads(json.dumps(items, cls=DecimalEncoder)), None
    except Exception:
        return None, "A database error occurred while fetching your history."

def fetch_recommendations_from_lambda(reading_history):
    try:
        response = requests.post(LAMBDA_URL, json={'reading_history': reading_history})
        response.raise_for_status()
        data = response.json()
        return data.get('recommendations'), data.get('top_genres'), data.get('top_authors'), None
    except Exception:
        return None, None, None, "Could not retrieve recommendations. The service may be down."


def create_book_card(book, is_history=False):
    with st.container():
        st.subheader(book.get('title', 'No Title'))
        st.caption(f"by {book.get('author', 'N/A')}")
        st.write(f"**Genre:** {book.get('genre', 'N/A')}")
        if is_history and 'rating' in book:
            try:
                rating_value = int(book['rating'])
                rating_stars = '⭐' * rating_value + '☆' * (5 - rating_value)
                st.write(f"**Your Rating:** {rating_stars}")
            except Exception:
                st.write("**Your Rating:** N/A")

def show_recommendations_page():
    st.title("Book Recommendations 💡")

    if not db.books_table or not LAMBDA_URL:
        st.error("CRITICAL ERROR: Application is not configured correctly. Check .env and db.py files.")
        return

    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error("Could not identify user. Please log in again.")
        return

    history, error_msg = get_reading_history(user_id)
    if error_msg:
        st.warning(error_msg)
        return

    if history:
        st.header("🕘 Based on Your Reading History")
        st.markdown("---")

        num_columns = 3
        for i in range(0, len(history), num_columns):
            cols = st.columns(num_columns)
            row_books = history[i:i + num_columns]
            for j, book in enumerate(row_books):
                with cols[j]:
                    create_book_card(book, is_history=True)

        st.markdown("---")

        if st.button('✨ Get My Recommendations!', key="get_recs"):
            with st.spinner('Analyzing your preferences...'):
                recommendations, top_genres, top_authors, rec_error = fetch_recommendations_from_lambda(history)


            st.header("Here Are Your Personalized Suggestions")
            if rec_error:
                st.warning(rec_error)
            elif recommendations:
                if top_genres or top_authors:
                    top_info = []
                    if top_genres:
                        top_info.append(f"**Top Genres:** {', '.join(top_genres)}")
                    if top_authors:
                        top_info.append(f"**Top Authors:** {', '.join(top_authors)}")
                    st.markdown(
                        f'<div style="background-color:#14532d; padding: 10px; border-radius: 8px; color: white;">{" | ".join(top_info)}</div>',
                        unsafe_allow_html=True)
                    st.markdown("")
                num_rec_columns = 3
                for i in range(0, len(recommendations), num_rec_columns):
                    rec_cols = st.columns(num_rec_columns)
                    row_recs = recommendations[i:i + num_rec_columns]
                    for j, book in enumerate(row_recs):
                        with rec_cols[j]:
                            create_book_card(book)
            else:
                st.info("We couldn't find any new recommendations for you at this time.")

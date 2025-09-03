import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import boto3
from boto3.dynamodb.conditions import Key

DYNAMODB_TABLE_NAME = 'BooksTable'
REGION = 'ap-south-1'

def get_user_books(user_id):
    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(DYNAMODB_TABLE_NAME)
    try:
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        return response.get('Items', [])
    except Exception as e:
        print("Error fetching books:", e)
        return []

def generate_pdf(df, user_id):
    import io
    import matplotlib.pyplot as plt
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Spacer
    from reportlab.lib import colors

    buffer = io.BytesIO()

    # Rating chart
    fig1, ax1 = plt.subplots()
    df['rating'].hist(bins=5, ax=ax1, color='skyblue', edgecolor='black')
    ax1.set_xlabel("Rating")
    ax1.set_ylabel("Count")
    img_rating = io.BytesIO()
    fig1.savefig(img_rating, format='png')
    plt.close(fig1)
    img_rating.seek(0)

    # Genre chart
    fig2, ax2 = plt.subplots()
    df['genre'].value_counts().plot(kind='bar', ax=ax2, color='lightgreen', edgecolor='black')
    ax2.set_ylabel("Count")
    img_genre = io.BytesIO()
    fig2.savefig(img_genre, format='png')
    plt.close(fig2)
    img_genre.seek(0)

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    table_data = [['Title', 'Genre', 'Rating', 'Date']]
    for _, row in df.iterrows():
        table_data.append([
            row['title'],
            row['genre'],
            f"{row['rating']:.1f}" if pd.notna(row['rating']) else '',
            row['timestamp'].date().isoformat() if pd.notna(row['timestamp']) else ''
        ])

    data_table = Table(table_data, repeatRows=1)
    data_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
    ]))

    elements.append(data_table)
    elements.append(Spacer(1, 12))
    elements.append(RLImage(img_rating, width=400, height=200))
    elements.append(Spacer(1, 12))
    elements.append(RLImage(img_genre, width=400, height=200))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def dashboard_page():
    if "user_id" not in st.session_state:
        st.error("Unauthorized access. Please log in.")
        return

    user_id = st.session_state["user_id"]
    st.title(f"📊 Here's your Dashboard")

    books = get_user_books(user_id)
    items = get_user_books(user_id)

    if not books:
        st.markdown("""
            <div style='
                background-color: #1e1e1e;
                padding: 30px;
                border-radius: 12px;
                text-align: center;
                border: 1px solid #444;
            '>
                <h3 style='color: #ffffff;'>No books found in your library</h3>
                <p style='color: #cccccc;'>Start your reading journey by adding your first book.</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("➕ Add Your First Book", use_container_width=True):
            st.session_state.page = "main"
            st.session_state.menu_selection = "Add Book"
            st.rerun()
        return

    df = pd.DataFrame(items)
    df['title'] = df.get('title', 'Untitled')
    df['genre'] = df.get('genre', 'Unknown')
    df['rating'] = pd.to_numeric(df.get('rating', 0), errors='coerce').round(1)
    df['timestamp'] = pd.to_datetime(df.get('timestamp', pd.NaT), errors='coerce')
    df['status'] = df.get('status', 'unknown').astype(str).str.lower()
    df = df[['title', 'genre', 'rating', 'status', 'timestamp']].sort_values(by='timestamp', ascending=True)
    df = df.reset_index(drop=True)

    st.markdown("""
    <style>
        .card {
            background-color: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
            text-align: center;
            box-shadow: 1px 1px 5px rgba(0,0,0,0.05);
        }
        .card h4 {
            margin: 0;
            font-size: 18px;
            color: #333;
        }
        .card p {
            font-size: 22px;
            font-weight: bold;
            color: #007bff;
            margin-top: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Your Books", csv_data, f'My_Books.csv', mime='text/csv', use_container_width=True)
    with col_dl2:
        pdf_bytes = generate_pdf(df, user_id)
        st.download_button("📄 Report", pdf_bytes, f'My_report.pdf', mime="application/pdf", use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    total_books = len(df)
    completed_books = df[df['status'].isin(['completed', 'done', 'read']) & (df['rating'] > 0)].shape[0]
    progress_pct = (completed_books / total_books * 100) if total_books > 0 else 0
    avg_rating = df[df['rating'] > 0]['rating'].mean()
    latest_book = df[df['timestamp'].notnull()].sort_values('timestamp', ascending=False).iloc[0] if df['timestamp'].notnull().any() else None
    monthly_counts = df.dropna(subset=['timestamp']).groupby(df['timestamp'].dt.to_period("M")).size() if df['timestamp'].notnull().any() else None
    avg_per_month = monthly_counts.mean() if monthly_counts is not None else None

    card_style = """
<style>
    .card {
        background-color: #2c2f33;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid #444;
        text-align: center;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.3);
    }
    .card h4 {
        margin: 0;
        font-size: 18px;
        color: #ffffff;
    }
    .card p {
        font-size: 22px;
        font-weight: bold;
        color: #1e90ff;
        margin-top: 8px;
    }
</style>
"""
    st.markdown(card_style, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class='card'>
            <h4>📚 Completion</h4>
            <p>{completed_books} / {total_books} ({progress_pct:.1f}%)</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class='card'>
            <h4>⭐ Average Rating</h4>
            <p>{avg_rating:.2f} / 5</p> 
        </div>
        """ if pd.notna(avg_rating) else """
        <div class='card'>
            <h4>⭐ Average Rating</h4>
            <p>–</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class='card'>
            <h4>📆 Avg Books</h4>
            <p>{avg_per_month:.2f}</p>
        </div>
        """ if avg_per_month else """
        <div class='card'>
            <h4>📆 Avg/Month</h4>
            <p>–</p>
        </div>
        """, unsafe_allow_html=True)

    # Most Recent Book box — consistent dark mode style
    if latest_book is not None:
        st.markdown(f"""
    <div style='background-color: #2c2f33; padding: 16px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #444;'>
        <h4 style='margin-bottom: 5px; color: #ffffff;'>📅 Most Recent Book</h4>
        <div style='padding: 12px; background-color: #1e1e1e; color: #ffffff; border-radius: 8px; box-shadow: 0px 2px 4px rgba(0,0,0,0.2);'>
            <strong>{latest_book['title']}</strong><br>
            <small>{latest_book['timestamp'].date()}</small>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    df_display = df.copy()
    df_display['timestamp'] = df_display['timestamp'].dt.strftime('%d-%m-%Y')
    df_display['S.No'] = df_display.index + 1
    df_display = df_display[['S.No', 'title', 'genre', 'rating', 'status', 'timestamp']]
    st.subheader("📘 Your Books")
    st.dataframe(df_display, hide_index=True)

    st.subheader("⏳ Pending Books")
    pending_df = df[(df['rating'].isna()) | (df['rating'] == 0) | (df['status'].isin(['to read', 'reading']))]
    if not pending_df.empty:
        st.warning(f"{len(pending_df)} pending book(s):")
        pending_display_df = pending_df.copy()
        pending_display_df['timestamp'] = pending_display_df['timestamp'].dt.strftime('%d-%m-%Y %H:%M:%S')
        pending_display_df['S.No'] = pending_display_df.index + 1
        pending_display_df = pending_display_df[['S.No', 'title', 'genre', 'status', 'timestamp']]
        st.dataframe(pending_display_df, hide_index=True)
    else:
        st.success("✅ All books completed!")

    st.subheader("📈 Rating Distribution")
    fig1, ax1 = plt.subplots()
    df['rating'].hist(bins=10, ax=ax1, color='skyblue', edgecolor='black')
    ax1.set_xlabel("Rating")
    ax1.set_ylabel("Count")
    st.pyplot(fig1)

    st.subheader("🥧 Favorite genres")
    fig2, ax2 = plt.subplots()
    df['genre'].value_counts().plot.pie(autopct='%1.1f%%', ax=ax2)
    ax2.set_ylabel('')
    st.pyplot(fig2)

    st.subheader("🏆 Top-Rated Books")
    top_rated = df[df['rating'] > 0].sort_values(by='rating', ascending=False).head(5)
    if not top_rated.empty:
        top_rated_display = top_rated.copy().reset_index(drop=True)
        top_rated_display['S.No'] = top_rated_display.index + 1
        st.dataframe(top_rated_display[['S.No', 'title', 'genre', 'rating']], hide_index=True)
    else:
        st.info("No rated books to show.")

    st.subheader("📚 Books Read Per Genre")
    genre_counts = df['genre'].value_counts()
    fig4, ax4 = plt.subplots()
    genre_counts.plot(kind='bar', ax=ax4, color='lightcoral', edgecolor='black')
    ax4.set_xlabel("Genre")
    ax4.set_ylabel("Count")
    ax4.set_title("Books per Genre")
    st.pyplot(fig4)

    if monthly_counts is not None:
        st.subheader("📆 Books Read Per Month")
        fig3, ax3 = plt.subplots()
        monthly_counts.plot(kind='bar', ax=ax3, color='orange', edgecolor='black')
        ax3.set_xlabel("Month")
        ax3.set_ylabel("Books Read")
        ax3.set_title("Books Read Per Month")
        st.pyplot(fig3)
    else:
        st.info("Not enough data to calculate monthly reading trends.")

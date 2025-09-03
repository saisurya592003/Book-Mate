from boto3.dynamodb.conditions import Key, Attr
from dotenv import load_dotenv
import boto3
import uuid
import os
from boto3.dynamodb.types import TypeDeserializer


# --- DynamoDB Connection ---
load_dotenv()
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv('AWS_REGION', 'ap-south-1'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

books_table = dynamodb.Table('BooksTable')
users_table = dynamodb.Table('UsersTable')


# --- User Management Functions ---
def save_user(user_id, name, email, password):
    """Saves a new user to the UsersTable."""
    users_table.put_item(Item={
        'email': email,
        'user_id': user_id,
        'name': name,
        'password': password
    })


def load_user(email):
    """Loads a user's data from the UsersTable using their email."""
    response = users_table.get_item(Key={'email': email})
    return response.get('Item')


def generate_next_book_id(user_id):
    """
    Generates a new book ID like BS_US001_001, BS_US001_002, etc.
    The sequence is specific to each user.
    """
    user_books = get_user_books(user_id).values()

    if not user_books:
        # This is the user's first book
        return f"BS_{user_id}_001"

    # Extract the numeric part of the book IDs
    ids = []
    for book in user_books:
        try:
            # Assumes format BS_USERID_XXX
            numeric_part = int(book['book_id'].split('_')[-1])
            ids.append(numeric_part)
        except (ValueError, IndexError):
            # Ignore malformed book IDs
            continue

    # Determine the next ID
    next_id_num = max(ids) + 1 if ids else 1

    # Format the new book ID with zero-padding
    return f"BS_{user_id}_{next_id_num:03d}"


# --- Book Management Functions ---
def generate_book_id():
    """Generates a unique book ID using UUID."""
    return f"BK{uuid.uuid4().hex[:6].upper()}"


def save_book(book_data):
    """Saves or updates a book's data in the BooksTable."""
    books_table.put_item(Item=book_data)


def get_user_books(user_id):
    """Retrieves all books for a given user_id."""
    response = books_table.query(
        KeyConditionExpression=Key('user_id').eq(user_id)
    )
    # Return as a dictionary for easy lookup by book_id
    return {b['book_id']: b for b in response.get('Items', [])}


def delete_book(user_id, book_id):
    """Deletes a book from the BooksTable."""
    books_table.delete_item(Key={'user_id': user_id, 'book_id': book_id})


def generate_next_user_id():
    """
    Generates a new sequential user ID like US001, US002, etc.
    Scans the UsersTable to find the highest current ID and increments it.
    """
    try:
        response = users_table.scan(ProjectionExpression="user_id")
        users = response.get('Items', [])

        if not users:
            return "US001"

        # Extract the numeric part of the IDs
        ids = []
        for user in users:
            if user.get('user_id', '').startswith("US"):
                try:
                    ids.append(int(user['user_id'][2:]))
                except (ValueError, TypeError):
                    continue

        if not ids:
            return "US001"

        # Determine the next ID
        next_id_num = max(ids) + 1

        # Format the new user ID with three-digit zero-padding
        return f"US{next_id_num:03d}"

    except Exception as e:
        # If the scan fails, fallback to a unique ID to prevent crashing
        print(f"ERROR generating sequential user ID: {e}. Falling back to UUID.")
        return f"U_{uuid.uuid4().hex[:8]}"


deserializer = TypeDeserializer()
def get_user(email):
    dynamodb_new = boto3.client('dynamodb', region_name='ap-south-1')
    response = dynamodb_new.get_item(
        TableName='UsersTable',
        Key={'email': {'S': email}}
    )

    item = response.get('Item')
    if not item:
        return {}

    user_data = {k: deserializer.deserialize(v) for k, v in item.items()}
    return user_data





# --- Rectified Book Query Functions ---

def query_books_by_genre(genre, user_id):
    try:
        response = books_table.query(
            IndexName='GenreIndex',
            KeyConditionExpression=Key('genre').eq(genre),
            FilterExpression=Attr('user_id').eq(user_id)
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error querying by genre: {e}")
        print("Please ensure a GSI named 'GenreIndex' with partition key 'genre' exists on the BooksTable.")
        return []


def query_books_by_rating(rating, user_id, comparison='gte'):
    if comparison not in ['eq', 'gte', 'lte', 'gt', 'lt']:
        raise ValueError("Invalid comparison operator. Use 'eq', 'gte', 'lte', 'gt', or 'lt'.")

    filter_expression = Attr('user_id').eq(user_id) & Attr('rating').__getattribute__(comparison)(rating)

    try:
        response = books_table.scan(
            FilterExpression=filter_expression
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error scanning by rating: {e}")
        return []


def query_books_by_status(status, user_id):
    try:
        response = books_table.query(
            IndexName='StatusIndex',
            KeyConditionExpression=Key('status').eq(status),
            FilterExpression=Attr('user_id').eq(user_id)
        )
        return response.get('Items', [])
    except Exception as e:
        print(f"Error querying by status: {e}")
        print("Please ensure a GSI named 'StatusIndex' with partition key 'status' exists on the BooksTable.")
        return []

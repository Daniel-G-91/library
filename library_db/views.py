from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Users, Books, Transactions
from django.contrib.auth.hashers import make_password, check_password
#from django.contrib.auth import authenticate, login
from django.db import connection, IntegrityError, DatabaseError
#from django.core.exceptions import ValidationError
import json, re, random


def home_view(request):
    return render(request, 'library.html')

def sign_up(request):
    
    if request.method == 'POST':
        
        try:

            data = json.loads(request.body)
            user_name = data.get('username', '').strip()
            email = data.get('email', '').strip()
            raw_password = data.get('password1', '').strip()

            errors=[]

            if not user_name or len(user_name) < 3:
                errors.append("Username must be at least 3 characters long.")
            if not email or not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
                errors.append("Invalid email format.")
            if not raw_password or len(raw_password) < 5:
                errors.append("Password must be at least 5 characters long.")

            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)

            password = make_password(raw_password)

            with connection.cursor() as cursor:
                try:
                    cursor.execute("EXEC create_user @user_name=%s, @user_email=%s, @user_password=%s",
                                    [user_name, email, password])
                    
                except DatabaseError as e:
                    error_message = str(e)
                   
                    if "Email is already registered" in error_message:
                        return JsonResponse({'success': False, 'errors': ["Email is already registered."]}, status=400)

                    if "Username is already registered" in error_message:
                        return JsonResponse({'success': False, 'errors': ["Username is already registered."]}, status=400)

            return JsonResponse({'success': True, 'message': 'User created successfully'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'errors': ["Invalid JSON format."]}, status=400)

        except Exception as e:
            return JsonResponse({'success': False, 'errors': ["Something went wrong."]}, status=500)

    return JsonResponse({'succes':False, 'errors': ['Invalid request']}, status=400)

def log_in(request):

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_name = data.get('username', '').strip()
            password = data.get('password', '').strip()

            # Validate input
            errors = []
            if not user_name:
                errors.append("Username is required.")
            if not password:
                errors.append("Password is required.")
            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)

            # Retrieve user data from DB
            with connection.cursor() as cursor:
                cursor.execute("SELECT user_id, user_password FROM Users WHERE user_name = %s", [user_name])
                user = cursor.fetchone()  # Fetch single row

            if user is None:
                return JsonResponse({'success': False, 'errors': ["Invalid username or password."]}, status=400)

            user_id = user[0]
            stored_hashed_password = user[1]  # Extract password from query result

            # Verify password
            if not check_password(password, stored_hashed_password):
                return JsonResponse({'success': False, 'errors': ["Invalid username or password."]}, status=400)

            # Successful login → Redirect to library_2.html
            request.session['user_id'] = user_id
            request.session['username'] = user_name
            
            return JsonResponse({'success': True, 'redirect_url': '/library/app/'})

        except Exception as e:
            return JsonResponse({'success': False, 'errors': ["Something went wrong."]}, status=500)

    return JsonResponse({'success': False, 'errors': ['Invalid request']}, status=400)


#@login_required
def library_view(request):
    
    user_id = request.session.get('user_id')
    user_name = request.session.get('username')
    
    if not user_id:
        return JsonResponse({'success': False, 'message': 'User not logged in'}, status=401)
    
    # Get borrowed books

    with connection.cursor() as cursor:
            cursor.execute("SELECT a.book_id, b.book_title, b.book_author, a.borrow_date, a.return_date "
                           "FROM transactions a "
                           "LEFT JOIN books b ON a.book_id=b.book_id "
                           "WHERE a.trx_status <> 0 AND a.user_id = %s", [user_id])
            books = cursor.fetchall()

    borrowed_books = []
    
    for book in books:
        book_data = {
            'book_id': book[0],
            'book_img': re.sub(r'[^a-zA-Z0-9]', '', book[1]).lower(),
            'book_title': book[1],
            'book_author': book[2],
            'borrow_date': book[3],
            'return_date': book[4]
        }
        borrowed_books.append(book_data)

    with connection.cursor() as cursor:
            cursor.execute("SELECT book_id, book_title, book_author, samples FROM books")
            lib_books = cursor.fetchall()

    stock = []

    for book in lib_books:
        book_data = {
            'book_id': book[0],
            'book_img': re.sub(r'[^a-zA-Z0-9]', '', book[1]).lower(),
            'book_title': book[1],
            'book_author': book[2],
            'samples': book[3]
        }
        stock.append(book_data)
        random.shuffle(stock)

    return render(request, 'app.html', {
        'username': user_name,
        'borrowed_books': borrowed_books,
        'stock': stock
    })

def extend_book(request):
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            book_id = data.get('book_id')
            user_id = request.session.get('user_id')
    
            if not user_id or not book_id:
                return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
            
            # Execute stored procedure
            with connection.cursor() as cursor:
                try:
                    cursor.execute("EXEC extend_borrow @user_id=%s, @book_id=%s", [user_id, book_id])
                    cursor.execute("SELECT return_date FROM transactions WHERE trx_status <> 0 AND user_id=%s AND book_id=%s", [user_id, book_id])
                    new_return_date = cursor.fetchone()[0]

                except DatabaseError as e:
                    error_message = str(e)
                    
                    if "You can't extend more than 3 times." in error_message:
                        return JsonResponse({'success': False, 'errors': ["You can't extend more than 3 times."]}, status=400)
                
                    return JsonResponse({'success': False, 'errors': [error_message]}, status=400)
                
                return JsonResponse({'success': True, 'message': "You've extended the period by 7 more days.", 'new_return_date': new_return_date})
        except:
            return JsonResponse({'success': False, 'message': 'Extend Error'}, status=400)

def return_book(request):

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            book_id = data.get('book_id')
            user_id = request.session.get('user_id')
    
            if not user_id or not book_id:
                return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
            
            # Execute stored procedure
            with connection.cursor() as cursor:
                try:
                    cursor.execute("EXEC return_book @user_id=%s, @book_id=%s", [user_id, book_id])

                    cursor.execute("SELECT a.book_id, b.book_title, b.book_author, a.borrow_date, a.return_date "
                                "FROM transactions a "
                                "LEFT JOIN books b ON a.book_id=b.book_id "
                                "WHERE a.trx_status <> 0 AND a.user_id = %s", [user_id])

                    borrowed_books = [
                        {
                            'book_id': row[0],
                            'book_img': re.sub(r'[^a-zA-Z0-9]', '', row[1]).lower(),
                            'book_title': row[1],
                            'book_author': row[2],
                            'borrow_date': row[3],
                            'return_date': row[4]
                        }
                        for row in cursor.fetchall()
                    ]

                except DatabaseError as e:
                    error_message = str(e)
                    
                    return JsonResponse({'success': False, 'errors': [error_message]}, status=400)
                
                return JsonResponse({'success': True, 'message': "The book was returned.", 'borrowed_books':borrowed_books, 'book_id':book_id})
        except:
            return JsonResponse({'success': False, 'message': 'Return Error'}, status=400)


def borrow_book(request):
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            book_id = data.get('book_id')
            user_id = request.session.get('user_id')
    
            if not user_id or not book_id:
                return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
            
            # Execute stored procedure
            with connection.cursor() as cursor:
                try:
                    cursor.execute("EXEC borrow_book @user_id=%s, @book_id=%s", [user_id, book_id])

                    cursor.execute("SELECT a.book_id, b.book_title, b.book_author, a.borrow_date, a.return_date "
                                "FROM transactions a "
                                "LEFT JOIN books b ON a.book_id=b.book_id "
                                "WHERE a.trx_status <> 0 AND a.user_id = %s", [user_id])

                    borrowed_books = [
                        {
                            'book_id': row[0],
                            'book_img': re.sub(r'[^a-zA-Z0-9]', '', row[1]).lower(),
                            'book_title': row[1],
                            'book_author': row[2],
                            'borrow_date': row[3],
                            'return_date': row[4]
                        }
                        for row in cursor.fetchall()
                    ]

                except DatabaseError as e:
                    error_message = str(e)
                    
                    if "multiple times" in error_message:
                        return JsonResponse({'success': False, 'errors': ["You can't borrow the same book multiple times."]}, status=400)
                    elif "not available" in error_message:
                        return JsonResponse({'success': False, 'errors': ["This book is not available in stock right now."]}, status=400)
                    elif "3 books" in error_message:
                        return JsonResponse({'success': False, 'errors': ["You can't borrow more than 3 books."]}, status=400)
                    else:
                        return JsonResponse({'success': False, 'errors': [error_message]}, status=400)
                                    
                return JsonResponse({'success': True, 'message': "You borrowed a new book. Enjoy reading!", 'borrowed_books':borrowed_books, 'book_id':book_id})
        except:
            return JsonResponse({'success': False, 'message': 'Return Error'}, status=400)


def log_out(request):
    request.session.flush()  # Clears the session
    return JsonResponse({'success': True, 'message': 'Logged out successfully.'})

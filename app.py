from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import psycopg2
import uuid
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Generate a random secret key

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Configure upload folder
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="pinterest",
        user="aranya",
        password="" 
    )
    return conn

@app.route('/')
def home():
    if 'user_id' not in session:
        return render_template('landing.html')
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get user's boards
                cur.execute("""
                    SELECT board_id, name FROM Pinboards 
                    WHERE user_id = %s
                    ORDER BY name
                """, (session['user_id'],))
                boards = [{'board_id': row[0], 'name': row[1]} for row in cur.fetchall()]
                
                # Get friends' pins
                cur.execute("""
                    SELECT 
                        p.pin_id,
                        p.picture_id,
                        p.pinned_at,
                        pic.tags,
                        u.username,
                        pb.name as board_name,
                        pic.storage_path
                    FROM Pins p
                    JOIN Users u ON p.user_id = u.user_id
                    JOIN Pinboards pb ON p.board_id = pb.board_id
                    JOIN Pictures pic ON p.picture_id = pic.picture_id
                    ORDER BY p.pinned_at DESC
                """, (session['user_id'], session['user_id'], session['user_id']))
                
                pins = []
                for row in cur.fetchall():
                    pin = {
                        'pin_id': row[0],
                        'picture_id': row[1],
                        'pinned_at': row[2],
                        'tags': row[3] if row[3] else [],
                        'username': row[4],
                        'board_name': row[5],
                        'storage_path': row[6]
                    }
                    pins.append(pin)
                
                return render_template('home.html', boards=boards, pins=pins)
    except Exception as e:
        print(f"Error in home route: {e}")
        flash('An error occurred while loading the home page.', 'danger')
        return render_template('home.html', boards=[], pins=[])

@app.route('/pin/<pin_id>')
@login_required
def view_pin(pin_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get user's boards
                cur.execute("""
                    SELECT board_id, name FROM Pinboards 
                    WHERE user_id = %s
                    ORDER BY name
                """, (session['user_id'],))
                boards = [{'board_id': row[0], 'name': row[1]} for row in cur.fetchall()]
                
                # Get pin details and find original pin
                cur.execute("""
                    WITH RECURSIVE pin_chain AS (
                        -- Start with the current pin
                        SELECT p.pin_id, p.picture_id, p.parent_pin_id, p.pinned_at,
                               u.username, pb.name as board_name, pic.tags, pic.storage_path,
                               p.user_id
                        FROM Pins p
                        JOIN Users u ON p.user_id = u.user_id
                        JOIN Pinboards pb ON p.board_id = pb.board_id
                        JOIN Pictures pic ON p.picture_id = pic.picture_id
                        WHERE p.pin_id = %s
                        
                        UNION ALL
                        
                        -- Recursively find parent pins
                        SELECT p.pin_id, p.picture_id, p.parent_pin_id, p.pinned_at,
                               u.username, pb.name as board_name, pic.tags, pic.storage_path,
                               p.user_id
                        FROM Pins p
                        JOIN pin_chain pc ON p.pin_id = pc.parent_pin_id
                        JOIN Users u ON p.user_id = u.user_id
                        JOIN Pinboards pb ON p.board_id = pb.board_id
                        JOIN Pictures pic ON p.picture_id = pic.picture_id
                    )
                    -- Get current pin and original pin details
                    SELECT 
                        pc.pin_id, pc.picture_id, pc.pinned_at, pc.tags,
                        pc.username, pc.board_name, pc.storage_path,
                        op.pin_id as original_pin_id,
                        op.username as original_username,
                        op.board_name as original_board_name,
                        op.pinned_at as original_pinned_at,
                        COALESCE((SELECT COUNT(*) FROM Likes l WHERE l.picture_id = pc.picture_id), 0) as like_count,
                        COALESCE((SELECT true FROM Likes l WHERE l.user_id = %s AND l.picture_id = pc.picture_id), false) as is_liked,
                        pc.user_id = %s as is_owner
                    FROM pin_chain pc
                    LEFT JOIN pin_chain op ON op.parent_pin_id IS NULL
                    WHERE pc.pin_id = %s
                """, (pin_id, session['user_id'], session['user_id'], pin_id))
                
                pin_data = cur.fetchone()
                if not pin_data:
                    flash('Pin not found.', 'danger')
                    return redirect(url_for('home'))
                
                # Get comments
                cur.execute("""
                    SELECT c.content, c.commented_at, u.username
                    FROM Comments c
                    JOIN Users u ON c.user_id = u.user_id
                    WHERE c.pin_id = %s
                    ORDER BY c.commented_at DESC
                """, (pin_id,))
                comments = []
                for row in cur.fetchall():
                    comments.append({
                        'content': row[0],
                        'commented_at': row[1],
                        'username': row[2]
                    })
                
                pin = {
                    'pin_id': pin_data[0],
                    'picture_id': pin_data[1],
                    'pinned_at': pin_data[2],
                    'tags': pin_data[3] if pin_data[3] else [],
                    'username': pin_data[4],
                    'board_name': pin_data[5],
                    'storage_path': pin_data[6],
                    'original_pin': {
                        'pin_id': pin_data[7],
                        'username': pin_data[8],
                        'board_name': pin_data[9],
                        'pinned_at': pin_data[10]
                    } if pin_data[7] else None,
                    'like_count': pin_data[11],
                    'is_liked': pin_data[12],
                    'is_owner': pin_data[13],
                    'comment_count': len(comments),
                    'comments': comments
                }
                
                return render_template('view_pin.html', pin=pin, boards=boards)
    except Exception as e:
        print(f"Error in view_pin route: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('An error occurred while loading the pin.', 'danger')
        return redirect(url_for('home'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form.get('full_name', '')
        
        # Hash the password
        password_hash = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if username or email already exists
            cur.execute('SELECT user_id FROM Users WHERE username = %s OR email = %s', (username, email))
            if cur.fetchone():
                flash('Username or email already exists!', 'error')
                return redirect(url_for('signup'))
            
            # Insert new user
            user_id = str(uuid.uuid4())
            cur.execute(
                'INSERT INTO Users (user_id, username, email, password_hash, full_name) VALUES (%s, %s, %s, %s, %s)',
                (user_id, username, email, password_hash, full_name)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('signup'))
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT user_id, password_hash FROM Users WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password!', 'error')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please login to access your profile.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get user data
    cur.execute('SELECT username, email, full_name FROM Users WHERE user_id = %s', (session['user_id'],))
    user_data = cur.fetchone()
    
    # Get friends list
    cur.execute('''
        SELECT u.username, u.full_name, f.status, f.requester_id = %s as is_requester
        FROM Users u
        JOIN Friendships f ON (f.requester_id = u.user_id OR f.addressee_id = u.user_id)
        WHERE (f.requester_id = %s OR f.addressee_id = %s)
        AND u.user_id != %s
    ''', (session['user_id'], session['user_id'], session['user_id'], session['user_id']))
    friends = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('profile.html', user_data=user_data, friends=friends)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    full_name = request.form.get('full_name', '')
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if current_password and new_password:
            # Verify current password
            cur.execute('SELECT password_hash FROM Users WHERE user_id = %s', (session['user_id'],))
            current_hash = cur.fetchone()[0]
            
            if not check_password_hash(current_hash, current_password):
                flash('Current password is incorrect!', 'error')
                return redirect(url_for('profile'))
            
            # Update password
            new_hash = generate_password_hash(new_password)
            cur.execute('UPDATE Users SET password_hash = %s WHERE user_id = %s',
                      (new_hash, session['user_id']))
        
        # Update full name
        cur.execute('UPDATE Users SET full_name = %s WHERE user_id = %s',
                   (full_name, session['user_id']))
        
        conn.commit()
        flash('Profile updated successfully!', 'success')
        
    except Exception as e:
        flash('An error occurred while updating your profile.', 'error')
        
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('profile'))

@app.route('/friends', methods=['GET', 'POST'])
def friends():
    if 'user_id' not in session:
        flash('Please login to access friends.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get search query if any
    search_query = request.args.get('search', '')
    
    # Get all users except current user and existing friends/requests
    if search_query:
        cur.execute('''
            SELECT u.user_id, u.username, u.full_name, 
                   CASE 
                       WHEN EXISTS (
                           SELECT 1 FROM Friendships f 
                           WHERE f.requester_id = %s AND f.addressee_id = u.user_id
                       ) THEN 'requested'
                       WHEN EXISTS (
                           SELECT 1 FROM Friendships f 
                           WHERE f.requester_id = u.user_id AND f.addressee_id = %s
                       ) THEN 'pending'
                       ELSE 'none'
                   END as request_status
            FROM Users u
            WHERE u.user_id != %s
            AND (u.username ILIKE %s OR u.full_name ILIKE %s)
            AND NOT EXISTS (
                SELECT 1 FROM Friendships f
                WHERE (f.requester_id = %s AND f.addressee_id = u.user_id AND f.status = 'accepted')
                OR (f.requester_id = u.user_id AND f.addressee_id = %s AND f.status = 'accepted')
            )
        ''', (session['user_id'], session['user_id'], session['user_id'], 
              f'%{search_query}%', f'%{search_query}%', session['user_id'], session['user_id']))
    else:
        cur.execute('''
            SELECT u.user_id, u.username, u.full_name,
                   CASE 
                       WHEN EXISTS (
                           SELECT 1 FROM Friendships f 
                           WHERE f.requester_id = %s AND f.addressee_id = u.user_id
                       ) THEN 'requested'
                       WHEN EXISTS (
                           SELECT 1 FROM Friendships f 
                           WHERE f.requester_id = u.user_id AND f.addressee_id = %s
                       ) THEN 'pending'
                       ELSE 'none'
                   END as request_status
            FROM Users u
            WHERE u.user_id != %s
            AND NOT EXISTS (
                SELECT 1 FROM Friendships f
                WHERE (f.requester_id = %s AND f.addressee_id = u.user_id AND f.status = 'accepted')
                OR (f.requester_id = u.user_id AND f.addressee_id = %s AND f.status = 'accepted')
            )
        ''', (session['user_id'], session['user_id'], session['user_id'], 
              session['user_id'], session['user_id']))
    
    users = cur.fetchall()
    
    # Get pending friend requests
    cur.execute('''
        SELECT u.user_id, u.username, u.full_name
        FROM Users u
        JOIN Friendships f ON f.requester_id = u.user_id
        WHERE f.addressee_id = %s AND f.status = 'pending'
    ''', (session['user_id'],))
    pending_requests = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('friends.html', users=users, pending_requests=pending_requests, search_query=search_query)

@app.route('/add_friend/<user_id>', methods=['POST'])
def add_friend(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session['user_id'] == user_id:
        flash('You cannot add yourself as a friend!', 'error')
        return redirect(url_for('friends'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if friendship already exists
        cur.execute('''
            SELECT status FROM Friendships 
            WHERE (requester_id = %s AND addressee_id = %s)
            OR (requester_id = %s AND addressee_id = %s)
        ''', (session['user_id'], user_id, user_id, session['user_id']))
        
        existing = cur.fetchone()
        if existing:
            flash('Friendship already exists!', 'error')
            return redirect(url_for('friends'))
        
        # Add new friendship request
        cur.execute('''
            INSERT INTO Friendships (requester_id, addressee_id, status)
            VALUES (%s, %s, 'pending')
        ''', (session['user_id'], user_id))
        
        conn.commit()
        flash('Friend request sent successfully!', 'success')
        
    except Exception as e:
        flash('An error occurred while sending friend request.', 'error')
        
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('friends'))

@app.route('/respond_friend_request/<user_id>/<action>', methods=['POST'])
def respond_friend_request(user_id, action):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if action == 'accept':
            cur.execute('''
                UPDATE Friendships 
                SET status = 'accepted', responded_at = CURRENT_TIMESTAMP
                WHERE requester_id = %s AND addressee_id = %s
            ''', (user_id, session['user_id']))
            flash('Friend request accepted!', 'success')
        elif action == 'reject':
            cur.execute('''
                UPDATE Friendships 
                SET status = 'rejected', responded_at = CURRENT_TIMESTAMP
                WHERE requester_id = %s AND addressee_id = %s
            ''', (user_id, session['user_id']))
            flash('Friend request rejected.', 'success')
        
        conn.commit()
        
    except Exception as e:
        flash('An error occurred while processing friend request.', 'error')
        
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('friends'))

@app.route('/pinboards')
def pinboards():
    if 'user_id' not in session:
        flash('Please login to view your pinboards.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get user's pinboards
    cur.execute('''
        SELECT board_id, name, created_at
        FROM Pinboards
        WHERE user_id = %s
        ORDER BY created_at DESC
    ''', (session['user_id'],))
    boards = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('pinboards.html', boards=boards)

@app.route('/create_pinboard', methods=['GET', 'POST'])
def create_pinboard():
    if 'user_id' not in session:
        flash('Please login to create a pinboard.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Check if pinboard name already exists for this user
            cur.execute('''
                SELECT board_id FROM Pinboards 
                WHERE user_id = %s AND name = %s
            ''', (session['user_id'], name))
            
            if cur.fetchone():
                flash('You already have a pinboard with this name.', 'error')
                return redirect(url_for('create_pinboard'))
            
            # Create new pinboard
            board_id = str(uuid.uuid4())
            cur.execute('''
                INSERT INTO Pinboards (board_id, user_id, name)
                VALUES (%s, %s, %s)
            ''', (board_id, session['user_id'], name))
            
            conn.commit()
            flash('Pinboard created successfully!', 'success')
            return redirect(url_for('manage_pinboards'))
            
        except Exception as e:
            conn.rollback()
            print(f"Error creating pinboard: {str(e)}")
            flash('An error occurred while creating the pinboard.', 'error')
            return redirect(url_for('create_pinboard'))
            
        finally:
            cur.close()
            conn.close()
    
    return render_template('create_pinboard.html')

@app.route('/pinboard/<board_id>')
def view_pinboard(board_id):
    if 'user_id' not in session:
        flash('Please login to view pinboards.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get pinboard details
        cur.execute('''
            SELECT p.name, p.allow_comments_from_friends_only, p.created_at,
                   u.username, u.full_name
            FROM Pinboards p
            JOIN Users u ON p.user_id = u.user_id
            WHERE p.board_id = %s
        ''', (board_id,))
        board = cur.fetchone()
        
        if not board:
            flash('Pinboard not found.', 'error')
            return redirect(url_for('pinboards'))
        
        # Get all pins in this board, including repins
        cur.execute('''
            SELECT pi.pin_id, p.picture_id, p.original_url, p.source_page_url, 
                   p.tags, pi.pinned_at, u.username, u.full_name,
                   pi.parent_pin_id, p.storage_path
            FROM Pins pi
            JOIN Pictures p ON pi.picture_id = p.picture_id
            JOIN Users u ON pi.user_id = u.user_id
            WHERE pi.board_id = %s
            ORDER BY pi.pinned_at DESC
        ''', (board_id,))
        
        pins = [{
            'pin_id': row[0],
            'picture_id': row[1],
            'original_url': row[2],
            'source_page_url': row[3],
            'tags': row[4],
            'pinned_at': row[5],
            'username': row[6],
            'full_name': row[7],
            'parent_pin_id': row[8],
            'storage_path': row[9]
        } for row in cur.fetchall()]
        
        # Debug: Print pin details
        for pin in pins:
            print(f"Pin {pin['pin_id']}:")
            print(f"  Source URL: {pin['source_page_url']}")
            print(f"  Storage Path: {pin['storage_path']}")
        
        return render_template('view_pinboard.html', 
                             board={'board_id': board_id, 'name': board[0]},
                             pins=pins)
        
    finally:
        cur.close()
        conn.close()

@app.route('/upload_pin', methods=['GET', 'POST'])
@app.route('/upload_pin/<board_id>', methods=['GET', 'POST'])
def upload_pin(board_id=None):
    if 'user_id' not in session:
        flash('Please login to upload pins.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user's boards if no board_id is provided
        boards = None
        if not board_id:
            cur.execute('''
                SELECT board_id, name
                FROM Pinboards
                WHERE user_id = %s
                ORDER BY name
            ''', (session['user_id'],))
            boards = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('upload_pin.html', board_id=board_id, boards=boards)
    
    else:  # POST request
        if 'image' not in request.files:
            flash('No image file provided.', 'error')
            return redirect(request.url)
        
        file = request.files['image']
        if file.filename == '':
            flash('No selected file.', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Generate unique filename and URL
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Save file
            file.save(file_path)
            
            # Get tags and process them
            tags_str = request.form.get('tags', '')
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            
            board_id = board_id or request.form['board_id']
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            try:
                # Generate a unique URL for the image
                image_url = f"/uploads/{unique_filename}"
                
                # Insert picture
                picture_id = str(uuid.uuid4())
                cur.execute('''
                    INSERT INTO Pictures (picture_id, original_url, source_page_url, 
                                        uploaded_by_user_id, storage_path, tags)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (picture_id, image_url, image_url, session['user_id'], 
                     file_path, tags))
                
                # Create pin with NULL parent_pin_id since it's an original upload
                pin_id = str(uuid.uuid4())
                cur.execute('''
                    INSERT INTO Pins (pin_id, picture_id, board_id, user_id, parent_pin_id)
                    VALUES (%s, %s, %s, %s, NULL)
                ''', (pin_id, picture_id, board_id, session['user_id']))
                
                conn.commit()
                flash('Pin uploaded successfully!', 'success')
                return redirect(url_for('pinboard', board_id=board_id))
                
            except Exception as e:
                flash('An error occurred while uploading the pin.', 'error')
                return redirect(request.url)
                
            finally:
                cur.close()
                conn.close()
        
        flash('Invalid file type.', 'error')
        return redirect(request.url)

@app.route('/upload_pin_url', methods=['POST'])
@app.route('/upload_pin_url/<board_id>', methods=['POST'])
def upload_pin_url(board_id=None):
    if 'user_id' not in session:
        flash('Please login to upload pins.', 'error')
        return redirect(url_for('login'))
    
    image_url = request.form['image_url']
    tags_str = request.form.get('tags', '')
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    board_id = board_id or request.form['board_id']
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if this image already exists in our system
        cur.execute('''
            SELECT p.picture_id, pi.pin_id, p.original_url, p.source_page_url
            FROM Pictures p
            JOIN Pins pi ON p.picture_id = pi.picture_id
            WHERE p.original_url = %s OR p.source_page_url = %s
            LIMIT 1
        ''', (image_url, image_url))
        existing_picture = cur.fetchone()
        
        if existing_picture:
            # This is a repin - use the existing picture and parent pin
            picture_id = existing_picture[0]
            parent_pin_id = existing_picture[1]
            
            # Create new pin with the parent_pin_id
            pin_id = str(uuid.uuid4())
            cur.execute('''
                INSERT INTO Pins (pin_id, picture_id, board_id, user_id, parent_pin_id)
                VALUES (%s, %s, %s, %s, %s)
            ''', (pin_id, picture_id, board_id, session['user_id'], parent_pin_id))
            
            conn.commit()
            flash('Pin repinned successfully!', 'success')
            return redirect(url_for('pinboard', board_id=board_id))
        
        else:
            # This is a new image - download and store it
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            
            # Generate unique filename
            filename = secure_filename(os.path.basename(image_url))
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Save file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Generate a unique URL for the stored image
            stored_url = f"/uploads/{unique_filename}"
            
            # Insert picture with original_url as the user-provided URL
            # and source_page_url as our stored URL
            picture_id = str(uuid.uuid4())
            cur.execute('''
                INSERT INTO Pictures (picture_id, original_url, source_page_url, 
                                    uploaded_by_user_id, storage_path, tags)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (picture_id, image_url, stored_url, session['user_id'], 
                 file_path, tags))
            
            # Create pin with NULL parent_pin_id since it's an original upload
            pin_id = str(uuid.uuid4())
            cur.execute('''
                INSERT INTO Pins (pin_id, picture_id, board_id, user_id, parent_pin_id)
                VALUES (%s, %s, %s, %s, NULL)
            ''', (pin_id, picture_id, board_id, session['user_id']))
            
            conn.commit()
            flash('Pin added successfully!', 'success')
            return redirect(url_for('pinboard', board_id=board_id))
        
    except Exception as e:
        flash('An error occurred while adding the pin.', 'error')
        return redirect(url_for('upload_pin', board_id=board_id))
        
    finally:
        cur.close()
        conn.close()

@app.route('/manage_pinboards')
def manage_pinboards():
    if 'user_id' not in session:
        flash('Please login to manage your pinboards.', 'error')
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '')

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if search_query:
            cur.execute('''
                SELECT board_id, name, created_at
                FROM Pinboards
                WHERE user_id = %s AND name ILIKE %s
                ORDER BY created_at DESC
            ''', (session['user_id'], f'%{search_query}%'))
        else:
            cur.execute('''
                SELECT board_id, name, created_at
                FROM Pinboards
                WHERE user_id = %s
                ORDER BY created_at DESC
            ''', (session['user_id'],))
        
        boards = [{
            'board_id': row[0],
            'name': row[1],
            'created_at': row[2]
        } for row in cur.fetchall()]
        
        return render_template('manage_pinboards.html', boards=boards, search_query=search_query)
        
    finally:
        cur.close()
        conn.close()

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        # Get the file extension to determine MIME type
        file_ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif'
        }
        mimetype = mime_types.get(file_ext, 'image/jpeg')
        
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            filename,
            mimetype=mimetype
        )
    except Exception as e:
        print(f"Error serving file {filename}: {str(e)}")
        return "File not found", 404

@app.route('/manage_streams')
def manage_streams():
    if 'user_id' not in session:
        flash('Please login to manage follow streams.', 'error')
        return redirect(url_for('login'))
    
    search_query = request.args.get('search', '')

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if search_query:
            cur.execute('''
                SELECT stream_id, name, created_at
                FROM FollowStreams
                WHERE user_id = %s AND name ILIKE %s
                ORDER BY created_at DESC
            ''', (session['user_id'], f'%{search_query}%'))
        else:
            cur.execute('''
                SELECT stream_id, name, created_at
                FROM FollowStreams
                WHERE user_id = %s
                ORDER BY created_at DESC
            ''', (session['user_id'],))
        
        streams = [{'stream_id': row[0], 'name': row[1], 'created_at': row[2]} for row in cur.fetchall()]
        
        # Get friends and their boards
        cur.execute('''
            SELECT u.user_id, u.username, p.board_id, p.name as board_name
            FROM Users u
            JOIN Friendships f ON (f.requester_id = u.user_id OR f.addressee_id = u.user_id)
            JOIN Pinboards p ON p.user_id = u.user_id
            WHERE (f.requester_id = %s OR f.addressee_id = %s)
            AND f.status = 'accepted'
            AND u.user_id != %s
            ORDER BY u.username, p.name
        ''', (session['user_id'], session['user_id'], session['user_id']))
        
        friends = {}
        for row in cur.fetchall():
            user_id, username, board_id, board_name = row
            if user_id not in friends:
                friends[user_id] = {'username': username, 'boards': []}
            friends[user_id]['boards'].append({'board_id': board_id, 'name': board_name})
        
        return render_template('manage_streams.html', streams=streams, friends=friends.values(), search_query=search_query)
        
    finally:
        cur.close()
        conn.close()

@app.route('/create_stream', methods=['POST'])
def create_stream():
    if 'user_id' not in session:
        flash('Please login to create a follow stream.', 'error')
        return redirect(url_for('login'))
    
    name = request.form['name']
    board_ids = request.form.getlist('board_ids')
    
    if not board_ids:
        flash('Please select at least one board for the stream.', 'error')
        return redirect(url_for('manage_streams'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Create the stream
        stream_id = str(uuid.uuid4())
        cur.execute('''
            INSERT INTO FollowStreams (stream_id, user_id, name)
            VALUES (%s, %s, %s)
        ''', (stream_id, session['user_id'], name))
        
        # Add boards to the stream
        for board_id in board_ids:
            try:
                cur.execute('''
                    INSERT INTO FollowStreamBoards (stream_id, board_id)
                    VALUES (%s, %s)
                ''', (stream_id, board_id))
            except Exception as e:
                print(f"Error adding board {board_id} to stream: {str(e)}")
                raise
        
        conn.commit()
        flash('Follow stream created successfully!', 'success')
        return redirect(url_for('manage_streams'))
        
    except Exception as e:
        conn.rollback()
        print(f"Error creating stream: {str(e)}")
        flash(f'An error occurred while creating the stream: {str(e)}', 'error')
        return redirect(url_for('manage_streams'))
        
    finally:
        cur.close()
        conn.close()

@app.route('/stream/<stream_id>')
def view_stream(stream_id):
    if 'user_id' not in session:
        flash('Please login to view follow streams.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get stream details
        cur.execute('''
            SELECT name, created_at
            FROM FollowStreams
            WHERE stream_id = %s AND user_id = %s
        ''', (stream_id, session['user_id']))
        stream = cur.fetchone()
        
        if not stream:
            flash('Stream not found.', 'error')
            return redirect(url_for('manage_streams'))
        
        # Get pins from all boards in the stream, ordered by pinned_at
        cur.execute('''
            SELECT p.picture_id, p.source_page_url, p.tags,
                   u.username, pb.name as board_name, pi.pinned_at
            FROM FollowStreamBoards fsb
            JOIN Pins pi ON fsb.board_id = pi.board_id
            JOIN Pictures p ON pi.picture_id = p.picture_id
            JOIN Users u ON pi.user_id = u.user_id
            JOIN Pinboards pb ON pi.board_id = pb.board_id
            WHERE fsb.stream_id = %s
            ORDER BY pi.pinned_at DESC
        ''', (stream_id,))
        
        # Convert tuples to dictionaries with named fields
        pins = [{
            'picture_id': row[0],
            'source_page_url': row[1],
            'tags': row[2],
            'username': row[3],
            'board_name': row[4],
            'pinned_at': row[5]
        } for row in cur.fetchall()]
        
        return render_template('view_stream.html', 
                             stream={'stream_id': stream_id, 'name': stream[0]},
                             pins=pins)
        
    finally:
        cur.close()
        conn.close()

@app.route('/repin/<pin_id>/<board_id>', methods=['GET', 'POST'])
def repin(pin_id, board_id):
    if 'user_id' not in session:
        flash('Please login to repin.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get the original pin's picture details
        cur.execute('''
            SELECT p.picture_id, p.original_url, p.source_page_url, p.storage_path, p.tags
            FROM Pins pi
            JOIN Pictures p ON pi.picture_id = p.picture_id
            WHERE pi.pin_id = %s
        ''', (pin_id,))
        result = cur.fetchone()
        
        if not result:
            flash('Original pin not found.', 'error')
            return redirect(url_for('home'))
        
        original_picture_id = result[0]
        original_url = result[1]
        source_page_url = result[2]  # Use the same source_page_url
        storage_path = result[3]
        original_tags = result[4] or []
        
        # Process tags from the form
        if request.method == 'POST':
            new_tags_str = request.form.get('tags', '')
            if new_tags_str:
                # Use new tags if provided
                tags = [tag.strip() for tag in new_tags_str.split(',') if tag.strip()]
            else:
                # Use original tags if no new tags provided
                tags = original_tags
        
        # Create new picture entry with the same image but new tags
        new_picture_id = str(uuid.uuid4())
        
        cur.execute('''
            INSERT INTO Pictures (picture_id, original_url, source_page_url, storage_path, tags)
            VALUES (%s, %s, %s, %s, %s)
        ''', (new_picture_id, original_url, source_page_url, storage_path, tags))
        
        # Create new pin with parent_pin_id
        new_pin_id = str(uuid.uuid4())
        cur.execute('''
            INSERT INTO Pins (pin_id, picture_id, board_id, user_id, parent_pin_id)
            VALUES (%s, %s, %s, %s, %s)
        ''', (new_pin_id, new_picture_id, board_id, session['user_id'], pin_id))
        
        conn.commit()
        flash('Pin repinned successfully!', 'success')
        return redirect(url_for('home'))
        
    except Exception as e:
        conn.rollback()
        flash('An error occurred while repinning.', 'error')
        return redirect(url_for('home'))
        
    finally:
        cur.close()
        conn.close()

@app.route('/like_pin/<picture_id>', methods=['POST'])
def like_pin(picture_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Find the original pin (the one with no parent_pin_id)
                cur.execute("""
                    WITH RECURSIVE pin_chain AS (
                        -- Start with the current pin
                        SELECT p.pin_id, p.picture_id, p.parent_pin_id
                        FROM Pins p
                        WHERE p.picture_id = %s
                        
                        UNION ALL
                        
                        -- Recursively find parent pins
                        SELECT p.pin_id, p.picture_id, p.parent_pin_id
                        FROM Pins p
                        JOIN pin_chain pc ON p.pin_id = pc.parent_pin_id
                    )
                    -- Get the original pin (the one with no parent_pin_id)
                    SELECT picture_id
                    FROM pin_chain
                    WHERE parent_pin_id IS NULL
                    LIMIT 1
                """, (picture_id,))
                
                original_picture = cur.fetchone()
                if not original_picture:
                    flash('Could not find the original pin.', 'danger')
                    return redirect(request.referrer or url_for('home'))
                
                original_picture_id = original_picture[0]
                
                # Check if user has already liked the original picture
                cur.execute("""
                    SELECT 1 FROM Likes 
                    WHERE user_id = %s AND picture_id = %s
                """, (session['user_id'], original_picture_id))
                
                if cur.fetchone():
                    # Unlike the picture
                    cur.execute("""
                        DELETE FROM Likes 
                        WHERE user_id = %s AND picture_id = %s
                    """, (session['user_id'], original_picture_id))
                else:
                    # Like the picture
                    cur.execute("""
                        INSERT INTO Likes (user_id, picture_id, liked_at)
                        VALUES (%s, %s, NOW())
                    """, (session['user_id'], original_picture_id))
                
                conn.commit()
                return redirect(request.referrer or url_for('home'))
    except Exception as e:
        print(f"Error in like_pin route: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('An error occurred while processing your like.', 'danger')
        return redirect(request.referrer or url_for('home'))

@app.route('/add_comment/<pin_id>', methods=['POST'])
@login_required
def add_comment(pin_id):
    try:
        content = request.form.get('content')
        if not content:
            flash('Comment cannot be empty.', 'danger')
            return redirect(request.referrer or url_for('home'))
            
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                comment_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO Comments (comment_id, pin_id, user_id, content, commented_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (comment_id, pin_id, session['user_id'], content))
                
                conn.commit()
                flash('Comment added successfully!', 'success')
                return redirect(request.referrer or url_for('home'))
    except Exception as e:
        print(f"Error adding comment: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('An error occurred while adding your comment.', 'danger')
        return redirect(request.referrer or url_for('home'))

@app.route('/delete_pin/<pin_id>', methods=['POST'])
@login_required
def delete_pin(pin_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # First check if the user owns this pin
                cur.execute("""
                    SELECT p.pin_id, p.picture_id, p.parent_pin_id
                    FROM Pins p
                    WHERE p.pin_id = %s AND p.user_id = %s
                """, (pin_id, session['user_id']))
                
                pin = cur.fetchone()
                if not pin:
                    flash('You can only delete your own pins.', 'danger')
                    return redirect(url_for('home'))
                
                # First, find all parent pins in the chain
                cur.execute("""
                    WITH RECURSIVE parent_chain AS (
                        -- Start with the current pin
                        SELECT p.pin_id, p.picture_id, p.parent_pin_id
                        FROM Pins p
                        WHERE p.pin_id = %s
                        
                        UNION
                        
                        -- Find parent pins
                        SELECT p.pin_id, p.picture_id, p.parent_pin_id
                        FROM Pins p
                        JOIN parent_chain pc ON p.pin_id = pc.parent_pin_id
                    )
                    SELECT pin_id, picture_id FROM parent_chain
                """, (pin_id,))
                
                parent_pins = cur.fetchall()
                
                # Then, find all child pins (repins)
                cur.execute("""
                    WITH RECURSIVE child_chain AS (
                        -- Start with the current pin
                        SELECT p.pin_id, p.picture_id, p.parent_pin_id
                        FROM Pins p
                        WHERE p.pin_id = %s
                        
                        UNION
                        
                        -- Find child pins (repins)
                        SELECT p.pin_id, p.picture_id, p.parent_pin_id
                        FROM Pins p
                        JOIN child_chain cc ON p.parent_pin_id = cc.pin_id
                    )
                    SELECT pin_id, picture_id FROM child_chain
                """, (pin_id,))
                
                child_pins = cur.fetchall()
                
                # Combine all pins to delete
                pins_to_delete = list(set(parent_pins + child_pins))
                
                if not pins_to_delete:
                    flash('Pin not found.', 'danger')
                    return redirect(url_for('home'))
                
                print(f"Found {len(pins_to_delete)} pins to delete")
                
                # Get all picture_ids and pin_ids
                picture_ids = [row[1] for row in pins_to_delete]
                pin_ids = [row[0] for row in pins_to_delete]
                
                # Delete all comments for these pins
                if pin_ids:
                    cur.execute("""
                        DELETE FROM Comments 
                        WHERE pin_id = ANY(%s::uuid[])
                    """, (pin_ids,))
                print("Deleted comments")
                
                # Delete all likes for these pictures
                if picture_ids:
                    cur.execute("""
                        DELETE FROM Likes 
                        WHERE picture_id = ANY(%s::uuid[])
                    """, (picture_ids,))
                print("Deleted likes")
                
                # Delete all pins in the chain
                if pin_ids:
                    cur.execute("""
                        DELETE FROM Pins 
                        WHERE pin_id = ANY(%s::uuid[])
                    """, (pin_ids,))
                print("Deleted pins")
                
                # Delete all pictures in the chain
                if picture_ids:
                    cur.execute("""
                        DELETE FROM Pictures 
                        WHERE picture_id = ANY(%s::uuid[])
                    """, (picture_ids,))
                print("Deleted pictures")
                
                conn.commit()
                flash('Pin and all its repins have been deleted successfully.', 'success')
                return redirect(url_for('home'))
                
    except Exception as e:
        print(f"Error deleting pin: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash(f'An error occurred while deleting the pin: {str(e)}', 'danger')
        return redirect(url_for('home'))

if __name__ == '__main__':
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)

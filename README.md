# Pinterest Clone

A full-featured Pinterest clone built with Flask and PostgreSQL, implementing core Pinterest functionalities like pinning, repinning, boards, streams, and social features.

## Table of Contents
- [Features](#features)
- [Technical Stack](#technical-stack)
- [Database Schema](#database-schema)
- [Routes Documentation](#routes-documentation)
- [Templates Documentation](#templates-documentation)
- [Setup and Installation](#setup-and-installation)
- [Security Features](#security-features)
- [Error Handling](#error-handling)
- [Future Enhancements](#future-enhancements)

## Features

### Core Features

#### User Authentication
- **Signup**: Create new account with username, email, and password
- **Login**: Secure authentication with session management
- **Logout**: Proper session termination
- **Profile Management**: Update user information and password

#### Pin Management
- **Upload Pins**: 
  - Upload images from local device
  - Add pins from external URLs
  - Add tags and descriptions
  - Choose destination board
- **View Pins**:
  - View pin details
  - See original source
  - View repin history
  - View comments and likes
- **Repin**:
  - Repin to any of your boards
  - Modify tags during repin
  - Maintain original pin reference
- **Delete Pins**:
  - Delete individual pins
  - Cascade deletion of repins
  - Clean up associated comments and likes

#### Board Management
- **Create Boards**:
  - Custom board names
  - Privacy settings (friends-only comments)
  - Board organization
- **View Boards**:
  - Grid layout of pins
  - Board details and settings
  - Pin organization
- **Manage Boards**:
  - Edit board settings
  - Reorganize pins
  - Delete boards

#### Stream Management
- **Create Streams**:
  - Combine multiple boards
  - Custom stream names
  - Follow friends' boards
- **View Streams**:
  - Aggregated pin feed
  - Real-time updates
  - Stream organization

#### Social Features
- **Friends System**:
  - Send friend requests
  - Accept/reject requests
  - View friend list
- **Comments**:
  - Add comments to pins
  - Board-level comment permissions
  - Friend-only commenting
- **Likes**:
  - Like/unlike pins
  - View like counts
  - Track liked pins

#### Search and Filtering
- **Tag-based Search**:
  - Search by multiple tags
  - Tag suggestions
  - Related pins
- **Stream Filtering**:
  - Filter by specific streams
  - Combine stream filters
- **Board Filtering**:
  - Filter by specific boards
  - Combine board filters

### Advanced Features

#### Image Management
- **Upload Processing**:
  - File type validation
  - Size restrictions
  - Secure storage
- **URL Processing**:
  - External image fetching
  - Duplicate detection
  - Source tracking

#### Content Organization
- **Tag System**:
  - Multiple tags per pin
  - Tag-based navigation
  - Tag suggestions
- **Stream Organization**:
  - Multiple board streams
  - Stream customization
  - Stream sharing

#### Privacy Controls
- **Board Privacy**:
  - Friends-only comments
  - Public/private boards
  - Board-level permissions
- **Content Access**:
  - Friend-based filtering
  - Content visibility controls
  - Privacy settings

## Technical Stack

### Backend
- **Framework**: Flask (Python)
  - Lightweight web framework
  - Jinja2 templating
  - Werkzeug utilities
- **Database**: PostgreSQL
  - UUID primary keys
  - Array data types
  - Complex queries
- **File Storage**: Local file system
  - Secure file handling
  - Path management
  - MIME type detection
- **Authentication**: Session-based with password hashing
  - Werkzeug security
  - Session management
  - Password hashing

### Frontend
- **Templating**: Jinja2
  - Template inheritance
  - Dynamic content
  - Form handling
- **CSS Framework**: Bootstrap 5
  - Responsive design
  - Grid system
  - Component library
- **Icons**: Font Awesome
  - Icon integration
  - Visual feedback
- **JavaScript**: Vanilla JS with Bootstrap components
  - DOM manipulation
  - Event handling
  - AJAX requests

## Database Schema

### Users
- `user_id` (UUID, PK): Unique identifier for users
- `username` (VARCHAR): Unique username
- `email` (VARCHAR): User's email address
- `password_hash` (VARCHAR): Hashed password
- `full_name` (VARCHAR): User's full name

### Pinboards
- `board_id` (UUID, PK): Unique identifier for boards
- `user_id` (UUID, FK): Owner of the board
- `name` (VARCHAR): Board name
- `allow_comments_from_friends_only` (BOOLEAN): Privacy setting
- `created_at` (TIMESTAMP): Creation timestamp

### Pictures
- `picture_id` (UUID, PK): Unique identifier for images
- `original_url` (VARCHAR): Source URL
- `source_page_url` (VARCHAR): Page URL
- `storage_path` (VARCHAR): Local storage path
- `tags` (TEXT[]): Array of tags

### Pins
- `pin_id` (UUID, PK): Unique identifier for pins
- `picture_id` (UUID, FK): Associated image
- `board_id` (UUID, FK): Destination board
- `user_id` (UUID, FK): Pin creator
- `parent_pin_id` (UUID, FK): Original pin reference
- `pinned_at` (TIMESTAMP): Pin creation time

### FollowStreams
- `stream_id` (UUID, PK): Unique identifier for streams
- `user_id` (UUID, FK): Stream owner
- `name` (VARCHAR): Stream name
- `created_at` (TIMESTAMP): Creation time

### FollowStreamBoards
- `stream_id` (UUID, FK): Associated stream
- `board_id` (UUID, FK): Included board

### Friendships
- `requester_id` (UUID, FK): Friend request sender
- `addressee_id` (UUID, FK): Friend request receiver
- `status` (VARCHAR): Request status (pending/accepted/rejected)
- `responded_at` (TIMESTAMP): Response time

### Comments
- `comment_id` (UUID, PK): Unique identifier for comments
- `pin_id` (UUID, FK): Associated pin
- `user_id` (UUID, FK): Comment author
- `content` (TEXT): Comment text
- `commented_at` (TIMESTAMP): Comment time

### Likes
- `user_id` (UUID, FK): User who liked
- `picture_id` (UUID, FK): Liked image
- `liked_at` (TIMESTAMP): Like time

## Routes Documentation

### Authentication Routes

#### `/` (Home)
- **Purpose**: Main application entry point
- **Methods**: GET
- **Authentication**: Optional
- **Functionality**:
  - Redirects to landing if not logged in
  - Shows feed if authenticated
  - Displays pins from followed streams

#### `/signup`
- **Purpose**: User registration
- **Methods**: GET, POST
- **Authentication**: Not required
- **Functionality**:
  - Form for new user details
  - Password hashing
  - Duplicate checking
  - Email validation

#### `/login`
- **Purpose**: User authentication
- **Methods**: GET, POST
- **Authentication**: Not required
- **Functionality**:
  - Credential validation
  - Session creation
  - Remember me option
  - Redirect to home

#### `/logout`
- **Purpose**: Session termination
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Session cleanup
  - Redirect to landing
  - Flash message

#### `/profile`
- **Purpose**: User profile management
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Display user info
  - Show friends list
  - Edit profile options

#### `/update_profile`
- **Purpose**: Profile information update
- **Methods**: POST
- **Authentication**: Required
- **Functionality**:
  - Update user details
  - Password change
  - Profile picture

### Pin Management Routes

#### `/pin/<pin_id>`
- **Purpose**: View individual pin
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Display pin details
  - Show comments
  - Like/unlike
  - Repin options

#### `/upload_pin`
- **Purpose**: Upload new pin
- **Methods**: GET, POST
- **Authentication**: Required
- **Functionality**:
  - File upload form
  - Image processing
  - Tag management
  - Board selection

#### `/upload_pin/<board_id>`
- **Purpose**: Upload to specific board
- **Methods**: GET, POST
- **Authentication**: Required
- **Functionality**:
  - Pre-selected board
  - Same as upload_pin
  - Board validation

#### `/upload_pin_url`
- **Purpose**: Upload from URL
- **Methods**: POST
- **Authentication**: Required
- **Functionality**:
  - URL validation
  - Image fetching
  - Duplicate checking
  - Source tracking

#### `/repin/<pin_id>/<board_id>`
- **Purpose**: Repin to another board
- **Methods**: GET, POST
- **Authentication**: Required
- **Functionality**:
  - Tag modification
  - Board selection
  - Original pin reference
  - Permission checking

#### `/delete_pin/<pin_id>`
- **Purpose**: Delete pin
- **Methods**: POST
- **Authentication**: Required
- **Functionality**:
  - Ownership verification
  - Cascade deletion
  - Cleanup operations
  - Success feedback

#### `/like_pin/<picture_id>`
- **Purpose**: Like/unlike pin
- **Methods**: POST
- **Authentication**: Required
- **Functionality**:
  - Toggle like status
  - Update counts
  - Real-time feedback
  - Permission checking

#### `/add_comment/<pin_id>`
- **Purpose**: Add comment
- **Methods**: POST
- **Authentication**: Required
- **Functionality**:
  - Comment validation
  - Permission checking
  - Real-time update
  - Success feedback

### Board Management Routes

#### `/pinboards`
- **Purpose**: List all pinboards
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Display user's boards
  - Board statistics
  - Quick actions
  - Organization options

#### `/create_pinboard`
- **Purpose**: Create new pinboard
- **Methods**: GET, POST
- **Authentication**: Required
- **Functionality**:
  - Board creation form
  - Privacy settings
  - Name validation
  - Success feedback

#### `/pinboard/<board_id>`
- **Purpose**: View specific pinboard
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Display board pins
  - Board settings
  - Pin organization
  - Quick actions

#### `/manage_pinboards`
- **Purpose**: Manage pinboards
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Board management
  - Settings update
  - Organization tools
  - Bulk actions

### Stream Management Routes

#### `/manage_streams`
- **Purpose**: Manage follow streams
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Stream list
  - Creation options
  - Management tools
  - Organization

#### `/create_stream`
- **Purpose**: Create new stream
- **Methods**: POST
- **Authentication**: Required
- **Functionality**:
  - Stream creation
  - Board selection
  - Name validation
  - Success feedback

#### `/stream/<stream_id>`
- **Purpose**: View specific stream
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Display stream pins
  - Stream settings
  - Organization tools
  - Quick actions

### Social Routes

#### `/friends`
- **Purpose**: Manage friends
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Friend list
  - Request management
  - Search friends
  - Quick actions

#### `/add_friend/<user_id>`
- **Purpose**: Send friend request
- **Methods**: POST
- **Authentication**: Required
- **Functionality**:
  - Request creation
  - Duplicate checking
  - Success feedback
  - Notification

#### `/respond_friend_request/<user_id>/<action>`
- **Purpose**: Accept/reject friend request
- **Methods**: POST
- **Authentication**: Required
- **Functionality**:
  - Request processing
  - Status update
  - Notification
  - Success feedback

### Search Route

#### `/search`
- **Purpose**: Search pins
- **Methods**: GET
- **Authentication**: Required
- **Functionality**:
  - Tag-based search
  - Stream filtering
  - Board filtering
  - Results display

## Templates Documentation

### Base Template (`base.html`)
- **Purpose**: Common layout
- **Components**:
  - Navigation bar
  - User menu
  - Flash messages
  - Footer
- **Features**:
  - Responsive design
  - Bootstrap integration
  - Font Awesome icons
  - Dynamic content

### Authentication Templates

#### `landing.html`
- **Purpose**: Landing page
- **Components**:
  - Welcome message
  - Login form
  - Signup link
  - Features showcase

#### `login.html`
- **Purpose**: Login form
- **Components**:
  - Email input
  - Password input
  - Remember me
  - Error messages

#### `signup.html`
- **Purpose**: Registration form
- **Components**:
  - Username input
  - Email input
  - Password input
  - Validation messages

#### `profile.html`
- **Purpose**: User profile
- **Components**:
  - User info
  - Friends list
  - Edit options
  - Statistics

### Pin Management Templates

#### `home.html`
- **Purpose**: Main feed
- **Components**:
  - Pin grid
  - Search bar
  - Filter options
  - Quick actions

#### `view_pin.html`
- **Purpose**: Pin details
- **Components**:
  - Pin image
  - Comments
  - Like button
  - Repin options

#### `upload_pin.html`
- **Purpose**: Upload form
- **Components**:
  - File input
  - Tag input
  - Board selection
  - Preview

#### `repin.html`
- **Purpose**: Repin form
- **Components**:
  - Image preview
  - Tag editor
  - Board selector
  - Original info

### Board Management Templates

#### `pinboards.html`
- **Purpose**: Board list
- **Components**:
  - Board grid
  - Create button
  - Quick actions
  - Statistics

#### `create_pinboard.html`
- **Purpose**: Board creation
- **Components**:
  - Name input
  - Privacy settings
  - Submit button
  - Validation

#### `view_pinboard.html`
- **Purpose**: Board view
- **Components**:
  - Pin grid
  - Board info
  - Settings
  - Actions

#### `manage_pinboards.html`
- **Purpose**: Board management
- **Components**:
  - Board list
  - Edit options
  - Delete buttons
  - Organization tools

### Stream Management Templates

#### `manage_streams.html`
- **Purpose**: Stream management
- **Components**:
  - Stream list
  - Create form
  - Edit options
  - Organization

#### `view_stream.html`
- **Purpose**: Stream view
- **Components**:
  - Pin feed
  - Stream info
  - Filter options
  - Actions

### Social Templates

#### `friends.html`
- **Purpose**: Friends management
- **Components**:
  - Friend list
  - Request list
  - Search bar
  - Actions

## Setup and Installation

1. **Prerequisites**
   - Python 3.x
   - PostgreSQL
   - pip (Python package manager)
   - Virtual environment

2. **Database Setup**
   ```sql
   -- Create database
   CREATE DATABASE pinterest;
   
   -- Connect to database
   \c pinterest;
   
   -- Create tables (see schema above)
   ```

3. **Environment Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

4. **Configuration**
   - Set up database connection in `app.py`
   - Configure upload folder path
   - Set secret key for session management
   - Configure allowed file types
   - Set maximum file size

5. **Run Application**
   ```bash
   python app.py
   ```

6. **Access Application**
   - Open browser and navigate to `http://localhost:5000`

## Security Features

### Authentication
- Password hashing using Werkzeug
- Session-based authentication
- CSRF protection
- Secure cookie handling

### Authorization
- Role-based access control
- Permission checking
- Friend-based access
- Board-level privacy

### Data Protection
- Input validation
- SQL injection prevention
- XSS protection
- File upload security

### Privacy Controls
- Board privacy settings
- Friend-only comments
- Content visibility
- User data protection

## Error Handling

### Database Errors
- Connection failures
- Query errors
- Constraint violations
- Transaction rollback

### File System Errors
- Upload failures
- Storage issues
- File type validation
- Path resolution

### Authentication Errors
- Invalid credentials
- Session expiration
- Permission denied
- Access control

### Input Validation
- Form validation
- Data type checking
- Required fields
- Format validation

## Future Enhancements

### Technical Improvements
- Image compression
- Caching system
- API endpoints
- WebSocket support

### User Experience
- Real-time updates
- Advanced search
- Mobile optimization
- Dark mode

### Social Features
- Direct messaging
- Group boards
- Activity feed
- Notifications

### Content Management
- Bulk operations
- Advanced filtering
- Analytics dashboard
- Content scheduling 
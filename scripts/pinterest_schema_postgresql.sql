
-- Users Table
CREATE TABLE Users (
    user_id UUID PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pinboards Table
CREATE TABLE Pinboards (
    board_id UUID PRIMARY KEY,
    user_id UUID REFERENCES Users(user_id),
    name TEXT NOT NULL,
    allow_comments_from_friends_only BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pictures Table
CREATE TABLE Pictures (
    picture_id UUID PRIMARY KEY,
    original_url TEXT,
    source_page_url TEXT,
    uploaded_by_user_id UUID REFERENCES Users(user_id),
    storage_path TEXT,
    tags TEXT[],
    first_pinned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pins Table
CREATE TABLE Pins (
    pin_id UUID PRIMARY KEY,
    picture_id UUID REFERENCES Pictures(picture_id),
    board_id UUID REFERENCES Pinboards(board_id),
    user_id UUID REFERENCES Users(user_id),
    parent_pin_id UUID REFERENCES Pins(pin_id),
    pinned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Likes Table
CREATE TABLE Likes (
    user_id UUID REFERENCES Users(user_id),
    picture_id UUID REFERENCES Pictures(picture_id),
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user_id, picture_id)
);

-- Comments Table
CREATE TABLE Comments (
    comment_id UUID PRIMARY KEY,
    pin_id UUID REFERENCES Pins(pin_id),
    user_id UUID REFERENCES Users(user_id),
    content TEXT NOT NULL,
    commented_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Friendships Table
CREATE TABLE Friendships (
    requester_id UUID REFERENCES Users(user_id),
    addressee_id UUID REFERENCES Users(user_id),
    status TEXT CHECK (status IN ('pending', 'accepted', 'rejected')),
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    PRIMARY KEY(requester_id, addressee_id)
);

-- FollowStreams Table
CREATE TABLE FollowStreams (
    stream_id UUID PRIMARY KEY,
    user_id UUID REFERENCES Users(user_id),
    name TEXT NOT NULL
);

-- FollowStreamBoards Table
CREATE TABLE FollowStreamBoards (
    stream_id UUID REFERENCES FollowStreams(stream_id),
    board_id UUID REFERENCES Pinboards(board_id),
    PRIMARY KEY(stream_id, board_id)
);


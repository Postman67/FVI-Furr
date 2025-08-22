-- The Mall Reviews table for the Furryville Index Database
-- This table stores user reviews and ratings for The Mall stalls only

CREATE TABLE IF NOT EXISTS the_mall_reviews (
    ReviewID INT AUTO_INCREMENT PRIMARY KEY,
    StallNumber INT NOT NULL,                     -- Stall number (INT as specified in readme)
    StreetName VARCHAR(255) NOT NULL,             -- Street name
    ReviewerID BIGINT NOT NULL,                   -- Discord user ID
    ReviewerName VARCHAR(255) NOT NULL,           -- Discord display name (plaintext)
    ReviewText TEXT NOT NULL,                     -- Review content
    Rating INT NOT NULL,                          -- Rating from 1-5 stars
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Ensure one review per user per stall
    UNIQUE KEY unique_user_stall_review (ReviewerID, StallNumber, StreetName),
    
    -- Constraints
    CONSTRAINT chk_rating CHECK (Rating >= 1 AND Rating <= 5),
    CONSTRAINT chk_street_name CHECK (StreetName IN ('Wall Street', 'Artist Alley', 'Woke Ave', 'Five', 'Poland Street'))
);

-- Create indexes for better performance
CREATE INDEX idx_reviewer_id ON the_mall_reviews(ReviewerID);
CREATE INDEX idx_stall_street ON the_mall_reviews(StallNumber, StreetName);
CREATE INDEX idx_rating ON the_mall_reviews(Rating);
CREATE INDEX idx_created_at ON the_mall_reviews(CreatedAt);

# Review System Documentation

## Overview
The review system allows Discord users to submit reviews and ratings for stalls in both Warp Hall and The Mall. Each user can submit one review per stall, with ratings from 1-5 stars.

## Database Schema

### Reviews Table
The `reviews` table stores all user reviews with the following structure:

- `ReviewID`: Auto-incrementing primary key
- `ReviewerID`: Discord user ID (BIGINT)
- `ReviewerName`: Discord display name (VARCHAR, updated on edit)
- `TableName`: Location ('warp_hall' or 'the_mall')
- `StallNumber`: Stall number (DECIMAL to support The Mall's fractional numbers)
- `StreetName`: Street name (NULL for Warp Hall, required for The Mall)
- `Rating`: Star rating (1-5 INTEGER)
- `ReviewText`: Review content (TEXT)
- `DateCreated`: Timestamp of creation
- `DateModified`: Timestamp of last modification

### Constraints
- One review per user per stall (enforced by unique constraints)
- Rating must be between 1-5
- TableName must be 'warp_hall' or 'the_mall'
- StreetName must be NULL for Warp Hall, NOT NULL for The Mall

## Commands

### `/review`
**Description**: Submit a review for a stall
**Parameters**:
- `table`: Location (Warp Hall or The Mall)
- `stall_number`: The stall number to review

**Permissions**: Available to all users (no role restrictions)

**Workflow**:
1. User selects table and enters stall number
2. For The Mall: User selects street name from dropdown
3. System validates stall exists and user hasn't already reviewed it
4. User fills out review modal with rating (1-5) and review text
5. Review is saved to database with success confirmation

**Validation**:
- Stall must exist in the specified table
- User cannot have existing review for the same stall
- Rating must be 1-5
- Warp Hall stall numbers must be integers
- The Mall stall numbers can be decimals

## Features

### Interactive Elements
- **Street Selection**: For The Mall stalls, users select from a dropdown of valid streets
- **Review Modal**: Clean form interface for rating and review text
- **Success Embeds**: Formatted confirmation with star display

### Data Validation
- Stall existence verification
- Duplicate review prevention
- Rating range enforcement
- Stall number format validation

### User Experience
- Ephemeral responses for error messages
- Clear feedback for all actions
- Star visualization (⭐☆) for ratings
- Consistent embed formatting

## Error Handling
- Database connection failures
- Invalid stall numbers
- Non-existent stalls
- Duplicate review attempts
- Invalid rating values

## Implementation Notes
- Uses the same permission-free approach as requested
- Maintains user plaintext names for display
- Supports both integer (Warp Hall) and decimal (The Mall) stall numbers
- Follows existing codebase patterns and styling

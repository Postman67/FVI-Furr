# Implement review submissions and editing

## Goals:
- Let a normal user run /review to review and rate a stall
- Let a user run /reviewedit to edit their review and rating of a stall

## Limits:
- /review commands should be avaliable to all users regardless of role
- One review and rating per user per stall
- Rating should be a value of 1-5 to be represented as stars

## Methods:
- Track user uniqeuness via Discord user ID (ReviewerID field in DB)
- Record user plaintext name (ReviewerName field in DB). 
- Update plaintext name with most up to date name if /reviewedit is ever run across all reviews with that user ID
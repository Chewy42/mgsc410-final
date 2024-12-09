# Purchase History Database Schema

## Products Table
Primary table containing product and review information.

| Column Name | Type | Description | Index |
|------------|------|-------------|--------|
| product_id | INTEGER | Primary Key, Auto-increment | PRIMARY |
| title | TEXT | Product title | YES |
| category | TEXT | Product category | YES |
| description | TEXT | Product description | NO |
| price | REAL | Product price | YES |

## Reviews Table
Contains review information for each product.

| Column Name | Type | Description | Index |
|------------|------|-------------|--------|
| review_id | INTEGER | Primary Key, Auto-increment | PRIMARY |
| product_id | INTEGER | Foreign Key to products | YES |
| user_id | TEXT | User identifier | YES |
| review_summary | TEXT | Summary of the review | NO |
| review_rating | REAL | Rating given in the review | YES |
| review_text | TEXT | Full review text | NO |
| review_timestamp | TIMESTAMP | Time when review was posted | YES |
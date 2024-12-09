STRING = paragraphs or long strings of text
CATEGORICAL = must be converted to categorical
FLOAT32 = must be converted to a performant floating point type
INT32 = must be converted to a performant integer type
AI_GENERATED_STRING = AI Generated summaries that need to be handled specially or looked at closer

To handle flattened columns:
1. Extract slices containing 'asin' fields
2. Start from 'properties.purchase_history.X.item.asin'
3. End at corresponding 'properties.purchase_history.X.review.timestamp' fields
4. X represents the purchase history index (1-based)

Iterate through these fields for each purchase:
- properties.purchase_history.X.item.title: STRING
- properties.purchase_history.X.item.category: CATEGORICAL
- properties.purchase_history.X.item.description: STRING
- properties.purchase_history.X.item.price: FLOAT32
- properties.purchase_history.X.review.summary: AI_GENERATED_STRING
- properties.purchase_history.X.review.rating: CATEGORICAL
- properties.purchase_history.X.review.text: STRING
- properties.purchase_history.X.review.timestamp: INT32

Replace X with (index + 1) for each iteration.

Important: Check if the 'asin' field is empty before processing each purchase.
If empty, skip the remaining fields for that purchase history (row) and move to the next index (next purchase/row).
This indicates the end of the purchase history for the current item.

I want to make a function that loads in the clothing_cleaned.csv dataset and returns a cleaned and performant dataset
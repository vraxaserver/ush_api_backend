# Gift Cards

List gift card templates:
    - GET /api/v1/promotions/gift-card-templates/

Purchase a gift card:
    - POST /api/v1/promotions/gift-cards/
    (Requires template_id)

List user's gift cards:
    - GET /api/v1/promotions/gift-cards/

Check gift card balance:
    - POST /api/v1/promotions/gift-cards/check_balance/
    (Requires code and pin)

Transfer gift card:
    - POST /api/v1/promotions/gift-cards/transfer/
    (Requires gift_card_id and recipient_email or recipient_phone)

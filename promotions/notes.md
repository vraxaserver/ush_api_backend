# Vouchers

## How customers can receive vouchers:

1. When customer login to the app, the app will check if the customer has any vouchers and display them in the app voucher section.
2. When new voucher is created a notification will be sent to the customer email and phone number as well as in app notification section.
3. Following api will list all the vouchers for the current user:
    - GET /api/v1/promotions/list-my-vouchers/

## How customers can use vouchers:

1. Customer can use voucher in the app by going to the voucher section and selecting (use now button) the voucher they want to use. In checkout page this voucher will appear with apply button. When press apply button the system will check if the voucher is valid and apply it.
2. Customer can also use voucher by puting code in checkout page. In checkout page there will be a field for voucher code. When customer enter the voucher code and press apply button the system will check if the voucher is valid and apply it.
3. Following api will validate a voucher code:
    - POST /api/v1/promotions/vouchers/validate/
4. Following api will apply a voucher code:
    - POST /api/v1/promotions/vouchers/apply/



# Gift Cards

List gift cards:
    - GET /api/v1/promotions/gift-card-templates/





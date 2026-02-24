✅ Implementation Summary
1. 
spacenter/models.py
 — Service Model
Added is_eligible_for_loyalty boolean field (default False) so admins can opt services into the loyalty program.
2. 
promotions/models.py
 — Loyalty Models
LoyaltyTracker
 — Tracks per-customer, per-service booking counts:
booking_count (rolling counter, resets on reward)
bookings_required (configurable, default 5)
total_bookings / total_rewards_earned (lifetime stats)
record_booking()
 method that increments and auto-issues rewards
unique_together on 
(customer, service)
 for data integrity
LoyaltyReward
 — One-time free booking rewards:
Statuses: 
available
, redeemed, 
expired
, cancelled
Links to both the earning booking and redemption booking
Optional expires_at for time-limited rewards
redeem()
 method with validation
3. 
promotions/signals.py
 — Automatic Tracking
pre_save signal on 
Booking
 model detects when status transitions to COMPLETED
Checks if the service has is_eligible_for_loyalty = True
Automatically increments the tracker and issues rewards at threshold
4. 
promotions/serializers.py
 — API Serializers
LoyaltyTrackerSerializer
 — Progress info with computed 
progress_percentage
 and 
bookings_remaining
LoyaltyRewardSerializer
 — Reward details with 
is_available
 flag
LoyaltyRedeemSerializer
 — Handles reward redemption with ownership + status validation
5. 
promotions/views.py
 — API Views
LoyaltyTrackerViewSet
 (read-only) — List loyalty progress per service
LoyaltyRewardViewSet
 (read-only + 
redeem
 action) — List and redeem rewards
LoyaltyStatusView
 — Dashboard summary endpoint with all trackers + available rewards
6. 
promotions/urls.py
 — Routes
Endpoint	Method	Description
/api/v1/promotions/loyalty-trackers/	GET	List loyalty progress
/api/v1/promotions/loyalty-rewards/	GET	List earned rewards
/api/v1/promotions/loyalty-rewards/redeem/	POST	Redeem a reward
/api/v1/promotions/loyalty/status/	GET	Dashboard summary
7. 
promotions/admin.py
 — Admin Interface
LoyaltyTrackerAdmin — Visual progress bar, search, filters by spa center
LoyaltyRewardAdmin — Color-coded status badges, bulk expire/cancel actions
Both are read-only (no manual creation — auto-managed by the booking flow)
8. 
spacenter/admin.py
 & 
spacenter/serializers.py
is_eligible_for_loyalty added to Service admin (list_display, list_filter, list_editable, and a dedicated "Loyalty Program" fieldset)
Added to 
ServiceSerializer
, 
ServiceCreateSerializer
, and 
ServiceListSerializer
 API responses
📋 How It Works (Flow)
Admin marks a service as loyalty-eligible via admin or API
Customer books and completes a booking for that service
Signal fires → 
LoyaltyTracker
 counter increments
After 5 completed bookings → 
LoyaltyReward
 auto-issued (counter resets to 0)
Customer views rewards via /loyalty/status/ or /loyalty-rewards/
Customer redeems reward via POST /loyalty-rewards/redeem/ with 
reward_id
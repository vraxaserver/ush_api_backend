"""
Booking Views for Spa Center Management.

Views for service arrangements, availability, and booking management.
Includes efficient availability calculation with merged timelines.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta

from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from spacenter.models import Service, SpaCenter

from .models import Booking, ServiceArrangement, TimeSlot
from .serializers import (
    BookingCreateSerializer,
    BookingListSerializer,
    BookingSerializer,
    ServiceArrangementListSerializer,
    ServiceArrangementSerializer,
    TimeSlotSerializer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Service Arrangement Views
# =============================================================================


class ServiceArrangementListView(generics.ListAPIView):
    """
    List all active arrangements for a specific service.
    
    GET /api/v1/bookings/services/{service_id}/arrangements/
    
    Returns all arrangements (rooms/setups) available for the specified service.
    """

    serializer_class = ServiceArrangementListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        service_id = self.kwargs.get("service_id")
        return ServiceArrangement.objects.filter(
            service_id=service_id,
            is_active=True,
        ).select_related("service", "spa_center").order_by("room_no")


# =============================================================================
# Availability Views
# =============================================================================


class ServiceAvailabilityView(APIView):
    """
    Get booked time slots for all arrangements of a service.
    
    GET /api/v1/bookings/services/{service_id}/availability/
    
    Query Parameters:
        - date_from: Start date (YYYY-MM-DD), defaults to today
        - date_to: End date (YYYY-MM-DD), defaults to 30 days from today
    
    Response format:
    {
        "service_id": "uuid",
        "date_from": "2026-01-19",
        "date_to": "2026-02-18",
        "spa_center": {
            "id": "uuid",
            "name": "...",
            "opening_time": "09:00",
            "closing_time": "21:00"
        },
        "arrangements": [
            {"id": "uuid", "label": "Room 1", "type": "single_room"}
        ],
        "booked_slots": {
            "arrangement_1_id": {
                "2026-01-19": {
                    "8:00 - 9:00": "booked",
                    "9:00 - 10:00": "booked"
                },
                "2026-01-20": {
                    "10:00 - 11:00": "booked"
                }
            },
            "arrangement_2_id": {...}
        },
        "merged_availability": {
            "2026-01-19": {
                "8:00 - 9:00": "available",  // at least one arrangement is free
                "9:00 - 10:00": "booked"     // all arrangements are booked
            }
        }
    }
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, service_id):
        # Parse date parameters
        today = timezone.now().date()
        date_from_str = request.query_params.get("date_from")
        date_to_str = request.query_params.get("date_to")

        try:
            date_from = (
                datetime.strptime(date_from_str, "%Y-%m-%d").date()
                if date_from_str
                else today
            )
            date_to = (
                datetime.strptime(date_to_str, "%Y-%m-%d").date()
                if date_to_str
                else today + timedelta(days=4)  # 5 days including today
            )
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure date_from is not in the past
        if date_from < today:
            date_from = today

        # Validate date range
        if date_to < date_from:
            return Response(
                {"error": "date_to must be greater than or equal to date_from."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get service and validate
        try:
            service = Service.objects.get(id=service_id, is_active=True)
        except Service.DoesNotExist:
            return Response(
                {"error": "Service not found or not active."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get spa center info (from first arrangement or service)
        arrangements = ServiceArrangement.objects.filter(
            service_id=service_id,
            is_active=True,
        ).select_related("spa_center")

        if not arrangements.exists():
            return Response(
                {"error": "No arrangements found for this service."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get spa center from first arrangement
        spa_center = arrangements.first().spa_center

        # Get all booked time slots for the date range
        booked_slots = TimeSlot.objects.filter(
            arrangement__in=arrangements,
            date__gte=date_from,
            date__lte=date_to,
        ).select_related("arrangement")

        # Build booked slots response
        booked_slots_data = defaultdict(lambda: defaultdict(dict))
        
        for slot in booked_slots:
            arr_id = str(slot.arrangement_id)
            date_str = slot.date.isoformat()
            
            # Get all blocked hour slots for this booking
            blocked_hours = slot.get_blocked_hour_slots()
            for hour_slot in blocked_hours:
                booked_slots_data[arr_id][date_str][hour_slot] = "booked"

        # Generate all possible time slots from spa opening to closing
        opening_hour = spa_center.default_opening_time.hour
        closing_hour = spa_center.default_closing_time.hour
        all_hour_slots = [
            f"{h:02d}:00 - {h+1:02d}:00"
            for h in range(opening_hour, closing_hour)
        ]

        # Group arrangements by type
        arrangements_by_type = defaultdict(list)
        for arr in arrangements:
            arrangements_by_type[arr.arrangement_type].append(str(arr.id))

        # Calculate merged availability per arrangement type
        # A slot is "available" if at least one arrangement of that type is free (OR condition)
        merged_availability = defaultdict(lambda: defaultdict(dict))
        
        current_date = date_from
        while current_date <= date_to:
            date_str = current_date.isoformat()
            
            for arr_type, arr_ids in arrangements_by_type.items():
                for hour_slot in all_hour_slots:
                    # Check if at least one arrangement of this type is available
                    is_available = False
                    for arr_id in arr_ids:
                        if (
                            arr_id not in booked_slots_data
                            or date_str not in booked_slots_data[arr_id]
                            or hour_slot not in booked_slots_data[arr_id][date_str]
                        ):
                            is_available = True
                            break
                    
                    merged_availability[arr_type][date_str][hour_slot] = (
                        "available" if is_available else "booked"
                    )
            
            current_date += timedelta(days=1)

        # Convert nested defaultdicts to regular dicts for JSON serialization
        merged_availability_dict = {
            arr_type: dict(dates)
            for arr_type, dates in merged_availability.items()
        }

        # Build response
        response_data = {
            "service_id": str(service_id),
            "service_name": service.name,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "spa_center": {
                "id": str(spa_center.id),
                "name": spa_center.name,
                "opening_time": spa_center.default_opening_time.strftime("%H:%M"),
                "closing_time": spa_center.default_closing_time.strftime("%H:%M"),
            },
            "arrangements": [
                {
                    "id": str(arr.id),
                    "label": arr.arrangement_label,
                    "type": arr.arrangement_type,
                    "room_no": arr.room_no,
                    "booked_slots": dict(booked_slots_data.get(str(arr.id), {})),
                }
                for arr in arrangements
            ],
            "timeslots_availability": merged_availability_dict,
        }

        return Response(response_data)


# =============================================================================
# Booking Views
# =============================================================================


class UpcomingBookingsView(generics.ListAPIView):
    """
    List upcoming bookings for the authenticated customer.
    
    GET /api/v1/bookings/upcoming-bookings/
    
    Returns all bookings for the current user with date >= today, ordered by date.
    """

    serializer_class = BookingListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(
            customer=self.request.user,
            time_slot__date__gte=timezone.now().date()
        ).select_related(
            "spa_center",
            "service_arrangement__service",
            "time_slot",
        ).order_by("time_slot__date", "time_slot__start_time")


class PastBookingsView(generics.ListAPIView):
    """
    List past bookings for the authenticated customer.
    
    GET /api/v1/bookings/past-bookings/
    
    Returns all bookings for the current user with date < today, ordered by date desc.
    """

    serializer_class = BookingListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(
            customer=self.request.user,
            time_slot__date__lt=timezone.now().date()
        ).select_related(
            "spa_center",
            "service_arrangement__service",
            "time_slot",
        ).order_by("-time_slot__date", "-time_slot__start_time")


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for booking management.
    
    Endpoints:
        POST /api/v1/bookings/ - Create a new booking
        GET /api/v1/bookings/{id}/ - Get booking details
        PATCH /api/v1/bookings/{id}/ - Update booking (status, notes)
        DELETE /api/v1/bookings/{id}/ - Cancel booking
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        if self.action == "list":
            return BookingListSerializer
        return BookingSerializer

    def get_queryset(self):
        user = self.request.user
        
        # Staff can see all bookings, customers only see their own
        if hasattr(user, "employee_profile") or user.is_staff:
            queryset = Booking.objects.all()
        else:
            queryset = Booking.objects.filter(customer=user)
        
        return queryset.select_related(
            "spa_center",
            "service_arrangement__service",
            "service_arrangement__spa_center",
            "time_slot",
            "therapist__employee_profile__user",
        ).prefetch_related("add_on_services")

    def perform_create(self, serializer):
        """Create booking for the authenticated user."""
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Cancel a booking instead of deleting."""
        booking = self.get_object()
        
        # Only allow cancellation of REQUESTED or CONFIRMED bookings
        if booking.status not in [
            Booking.BookingStatus.REQUESTED,
            Booking.BookingStatus.CONFIRMED,
            Booking.BookingStatus.PAYMENT_PENDING,
        ]:
            return Response(
                {"error": f"Cannot cancel a booking with status '{booking.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        booking.status = Booking.BookingStatus.CANCELED
        booking.save(update_fields=["status", "updated_at"])
        
        # Free up the time slot by deleting it
        if booking.time_slot:
            booking.time_slot.delete()
        
        return Response(
            {"message": "Booking cancelled successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, id=None):
        """Confirm a booking (staff only)."""
        booking = self.get_object()
        
        if not request.user.is_staff:
            return Response(
                {"error": "Only staff can confirm bookings."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        if booking.status not in [
            Booking.BookingStatus.REQUESTED,
            Booking.BookingStatus.PAYMENT_SUCCESS,
        ]:
            return Response(
                {"error": f"Cannot confirm a booking with status '{booking.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        booking.status = Booking.BookingStatus.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])
        
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, id=None):
        """Mark a booking as completed (staff only)."""
        booking = self.get_object()
        
        if not request.user.is_staff:
            return Response(
                {"error": "Only staff can complete bookings."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        if booking.status != Booking.BookingStatus.CONFIRMED:
            return Response(
                {"error": "Only confirmed bookings can be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        booking.status = Booking.BookingStatus.COMPLETED
        booking.save(update_fields=["status", "updated_at"])
        
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"], url_path="update-payment-status")
    def update_payment_status(self, request, id=None):
        """
        Update booking status based on payment result.
        
        POST /api/v1/bookings/{id}/update-payment-status/
        
        Request body:
            {
                "payment_success": true  // or false
            }
        
        If payment_success is true, status changes from "requested" to "payment_success".
        If payment_success is false, status changes from "requested" to "payment_pending".
        """
        booking = self.get_object()
        
        # Check if booking is in "requested" status
        if booking.status != Booking.BookingStatus.REQUESTED:
            return Response(
                {"error": f"Cannot update payment status for booking with status '{booking.status}'. Only 'requested' bookings can be updated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Get payment_success from request data
        payment_success = request.data.get("payment_success")
        if payment_success is None:
            return Response(
                {"error": "The 'payment_success' field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Update status based on payment result
        if payment_success:
            booking.status = Booking.BookingStatus.PAYMENT_SUCCESS
        else:
            booking.status = Booking.BookingStatus.PAYMENT_PENDING
        
        booking.save(update_fields=["status", "updated_at"])
        
        return Response(BookingSerializer(booking).data)

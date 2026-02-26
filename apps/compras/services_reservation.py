# apps/compras/services_reservation.py
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from apps.compras.models import ProductVariant, Reservation

class ReservationService:
    @staticmethod
    @transaction.atomic
    def create_reservation(student, variant_id, qty):
        variant = ProductVariant.objects.select_for_update().get(id=variant_id)
        
        if variant.stock_quantity < qty:
            return False, "Stock insuficiente para o tamanho selecionado."

        # 1. Bloquear stock
        variant.stock_quantity -= qty
        variant.save()

        # 2. Criar Reserva (Expira em 48h)
        reservation = Reservation.objects.create(
            student=student,
            variant=variant,
            quantity=qty,
            expires_at=timezone.now() + timedelta(hours=48)
        )

        return True, f"Reserva {reservation.id} efetuada. Levante na secretaria em 48h."

    @staticmethod
    @transaction.atomic
    def cancel_expired_reservations():
        """Task para devolver stock de reservas não levantadas"""
        expired = Reservation.objects.filter(status='PENDING', expires_at__lt=timezone.now())
        for res in expired:
            res.variant.stock_quantity += res.quantity
            res.variant.save()
            res.status = 'CANCELLED'
            res.save()
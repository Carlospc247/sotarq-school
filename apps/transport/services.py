# apps/transport/services.py
from apps.core.tasks import task_send_whatsapp_notification
from apps.transport.models import BusEvent

class TransportService:
    @staticmethod
    def process_checkpoint(student, bus, event_type, coords=None):
        """
        Regista o evento e notifica o Encarregado com link de mapa.
        """
        event = BusEvent.objects.create(
            student=student, bus=bus, 
            event_type=event_type,
            lat=coords.get('lat') if coords else None,
            lng=coords.get('lng') if coords else None
        )

        # Mensagens Dinâmicas (Rigor SOTARQ)
        msgs = {
            'IN': f"✅ *SOTARQ TRANSPORT*: {student.full_name} embarcou com sucesso no autocarro {bus.plate_number}. Rastreio ativo.",
            'OUT': f"🏫 *SOTARQ TRANSPORT*: {student.full_name} chegou à escola e já desembarcou em segurança.",
            'HOME': f"🏠 *SOTARQ TRANSPORT*: {student.full_name} foi entregue na residência com sucesso."
        }

        # Busca Encarregado Financeiro
        guardian = student.guardians.filter(is_financial_responsible=True).first()
        if guardian and guardian.guardian.phone:
            # Se estiver em rota, enviamos o link do mapa para o pai monitorar
            if event_type == 'IN':
                msgs['IN'] += f"\n📍 Acompanhe em tempo real: https://sotarq.school/transport/track/{bus.id}/"
            
            task_send_whatsapp_notification.delay(guardian.guardian.phone, msgs[event_type])
        
        return True
import segno
import base64
from io import BytesIO

def generate_decay_qr(decay):
    info = f"Распад №{decay.decay_id}\nПрошло времени: {decay.pass_time}\n\n"
    info += "Состав распада:\n"
    for elementDecay in decay.decay_elements.all():
        element = elementDecay.element
        info += f"{element.name}\n"
        info += f"\tКоличество: {elementDecay.quantity}\n"
        info += f"\tОставшееся количество: {elementDecay.remaining_quantity}\n"
    qr = segno.make(info)
    buffer = BytesIO()
    qr.save(buffer, kind='png')
    buffer.seek(0)
    qr_image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    return qr_image_base64
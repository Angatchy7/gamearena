from .models import Notification


def send_notification(
    *,
    recipient,
    title,
    message,
    notification_type=Notification.Type.SYSTEM,
):

    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
    )